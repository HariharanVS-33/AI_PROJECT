"""
Gemini AI integration — LLM response generation + text embeddings.
Uses the new google-genai SDK (google.genai).
"""
from google import genai
from google.genai import types
from backend.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_EMBEDDING_MODEL
import logging

logger = logging.getLogger(__name__)

# Configure client
_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """You are a professional AI assistant for PolyMedicure, a leading Indian healthcare device manufacturer specialising in cardiology, IV infusion, blood management, dialysis, respiratory care, and safety medical devices.

YOUR RULES — follow strictly:
1. Answer ONLY using the provided context information about PolyMedicure products and services.
2. If the answer is NOT in the provided context, say: "I don't have that specific information right now. Please contact our sales team directly for assistance."
3. Be warm, professional, and concise in your responses.
4. When a user shows interest in becoming a distributor, dealer, or partner — smoothly express enthusiasm and indicate that you'll collect some details to connect them with the sales team.
5. Do NOT reveal pricing, stock levels, or internal business data not in the context.
6. Do NOT make up product specifications — only state what is in the context.
7. Use bullet points or short paragraphs for readability.
8. Always end responses helpfully with an invitation for follow-up questions."""


def _build_contents(conversation_history: list, context: str = "") -> list:
    """Build the contents list for the Gemini API call."""
    if not conversation_history:
        return []

    contents = []
    for msg in conversation_history[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=msg["parts"][0])]
        ))

    # Last user message — inject context
    last_text = conversation_history[-1]["parts"][0]
    if context:
        last_text = (
            f"[RETRIEVED CONTEXT — use this to answer]\n{context}\n\n"
            f"[USER QUESTION]\n{last_text}"
        )
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=last_text)]
    ))
    return contents


def generate_response(conversation_history: list, context: str = "") -> str:
    """Generate a grounded chat response."""
    try:
        contents = _build_contents(conversation_history, context)
        if not contents:
            return "Hello! How can I help you today?"

        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.5,
                max_output_tokens=1024,
            ),
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini generate_response error: {e}")
        return "I'm having a momentary issue. Please try again in a few seconds."


def generate_simple_response(prompt: str) -> str:
    """Single-turn generation for classification / summaries."""
    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=50,
            ),
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini generate_simple_response error: {e}")
        return ""


def get_embedding(text: str) -> list:
    """Get a query embedding vector."""
    try:
        result = _client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.error(f"Gemini get_embedding error: {e}")
        return []


def get_document_embedding(text: str) -> list:
    """Get a document embedding vector (for indexing)."""
    try:
        result = _client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.error(f"Gemini get_document_embedding error: {e}")
        return []
