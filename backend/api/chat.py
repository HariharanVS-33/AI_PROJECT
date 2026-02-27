"""
Chat API — main conversation endpoint.
POST /api/chat
POST /api/session/init
"""
import logging
from fastapi import APIRouter, HTTPException
from backend.models.schemas import ChatRequest, ChatResponse, SessionInitResponse
from backend.core import session_manager as sm
from backend.core import intent as intent_classifier
from backend.core import lead_qualifier as lq
from backend.core import rag
from backend import database as db

logger = logging.getLogger(__name__)
router = APIRouter()

OUT_OF_SCOPE_RESPONSE = (
    "I'm specialised in healthcare device queries and distribution opportunities "
    "for PolyMedicure. I'm not able to help with that topic, but I'd love to assist "
    "with any questions about our medical products or becoming a dealer! 😊"
)

SALES_TRIGGER_INTENTS = {"sales_intent", "distributor_query"}


@router.post("/session/init", response_model=SessionInitResponse)
def init_session():
    """Create a new chat session."""
    session_id = sm.create_session()
    return SessionInitResponse(session_id=session_id)


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Main chat handler — orchestrates intent → RAG → lead qualification."""
    session = sm.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired. Please refresh to start a new session.")

    user_message = request.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    sm.update_session_activity(request.session_id)

    # Add user message to history
    sm.add_to_history(session, "user", user_message)
    lead_status = session.get("lead_status", "NOT_STARTED")

    # ── Lead qualification flow takes priority if active ──────────────────────
    if lead_status in ("CONSENT_PENDING", "COLLECTING", "CONFIRMING"):
        response_text, quick_replies = lq.handle_qualification(session, user_message)
        sm.add_to_history(session, "model", response_text)
        db.save_message(request.session_id, "user", user_message, "lead_qualification")
        db.save_message(request.session_id, "assistant", response_text, "lead_qualification")

        progress = lq.get_progress(session)
        return ChatResponse(
            response=response_text,
            intent="lead_qualification",
            lead_status=session.get("lead_status", "NOT_STARTED"),
            quick_replies=quick_replies,
        )

    # ── Intent classification ─────────────────────────────────────────────────
    detected_intent = intent_classifier.classify(user_message)
    logger.info(f"Session {request.session_id[:8]}... | Intent: {detected_intent}")

    # ── Out of scope ──────────────────────────────────────────────────────────
    if detected_intent == "out_of_scope":
        response_text = OUT_OF_SCOPE_RESPONSE
        sm.add_to_history(session, "model", response_text)
        db.save_message(request.session_id, "user", user_message, detected_intent)
        db.save_message(request.session_id, "assistant", response_text, detected_intent)
        return ChatResponse(
            response=response_text,
            intent=detected_intent,
            lead_status=lead_status,
        )

    # ── Sales / distributor intent → trigger qualification ────────────────────
    if detected_intent in SALES_TRIGGER_INTENTS and lead_status == "NOT_STARTED":
        # First give a RAG response to the question, then transition
        rag_result = rag.query(user_message, session["history"])
        rag_response = rag_result["response"]

        # Append transition to qualification
        transition = (
            "\n\n---\n\nIt sounds like you're interested in our products or partnering with us! "
            "I'd love to connect you with our sales team. "
        )
        consent_msg = lq.CONSENT_MESSAGE
        full_response = rag_response + transition + "\n\n" + consent_msg

        session["lead_status"] = "CONSENT_PENDING"
        sm.add_to_history(session, "model", full_response)
        db.save_message(request.session_id, "user", user_message, detected_intent)
        db.save_message(request.session_id, "assistant", full_response, detected_intent)

        return ChatResponse(
            response=full_response,
            intent=detected_intent,
            lead_status="CONSENT_PENDING",
            quick_replies=["Yes, I agree", "No, thanks"],
        )

    # ── Standard RAG query ────────────────────────────────────────────────────
    rag_result = rag.query(user_message, session["history"])
    response_text = rag_result["response"]

    sm.add_to_history(session, "model", response_text)
    db.save_message(request.session_id, "user", user_message, detected_intent)
    db.save_message(request.session_id, "assistant", response_text, detected_intent)

    return ChatResponse(
        response=response_text,
        intent=detected_intent,
        lead_status=lead_status,
    )
