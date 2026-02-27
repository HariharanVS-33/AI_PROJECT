"""
Lead qualification state machine.
States: NOT_STARTED → CONSENT_PENDING → COLLECTING → CONFIRMING → COMPLETED
"""
import re
import logging
from backend.integrations import email_service
from backend import database as db

logger = logging.getLogger(__name__)

# Fields to collect in order: (field_key, human_label, question, required)
FIELDS = [
    ("first_name",       "First Name",         "What's your **first name**?", True),
    ("last_name",        "Last Name",           "And your **last name**?", True),
    ("email",            "Email Address",       "Could you share your **email address**?", True),
    ("phone",            "Contact Number",      "What's your **contact number**?", True),
    ("company_name",     "Company",             "What's the name of your **company**? *(If not applicable, just type 'skip')*", False),
    ("address",          "Address",             "What is your **complete postal address**?", True),
]

REQUIRED_FIELDS = [f for f in FIELDS if f[3]]
ALL_FIELDS = FIELDS

CONSENT_MESSAGE = (
    "To connect you with our sales team, I'll need to collect a few details "
    "about you and your business. This information will be stored securely in "
    "our CRM and used only to process your enquiry.\n\n"
    "**Do you agree to proceed?**"
)

CONFIRMATION_PROMPT = """Before I submit your details, here's a summary:

{summary}

Is everything correct? *(Reply **Yes** to confirm or **No** to make changes)*"""


def _is_affirmative(text: str) -> bool:
    text = text.lower().strip()
    return any(w in text for w in ["yes", "y", "sure", "ok", "okay", "agree",
                                    "proceed", "yeah", "yep", "correct", "right",
                                    "fine", "go ahead", "please", "do it"])


def _is_negative(text: str) -> bool:
    text = text.lower().strip()
    return any(w in text for w in ["no", "n", "nope", "cancel", "stop",
                                    "don't", "dont", "not", "decline"])


def _is_skip(text: str) -> bool:
    text = text.lower().strip()
    return text in ("skip", "s", "-", "na", "n/a", "no", "pass")


def _validate_field(field_key: str, value: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    value = value.strip()
    if field_key == "email":
        if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value):
            return True, ""
        return False, "That doesn't look like a valid email address. Please enter a valid **email** (e.g., name@email.com)."
    if field_key == "phone":
        # Check if contains at least 7 digits
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 7:
            return True, ""
        return False, "Please enter a valid phone number."
    if field_key == "first_name" or field_key == "last_name":
        if len(value) >= 2 and value.replace(" ", "").isalpha():
            return True, ""
        return False, "Please enter a valid name (letters only, at least 2 characters)."
    if len(value) >= 2:
        return True, ""
    return False, "Please provide a more detailed answer."


def _build_summary(lead_data: dict) -> str:
    lines = []
    field_map = {f[0]: f[1] for f in FIELDS}
    for key, label in field_map.items():
        val = lead_data.get(key)
        if val:
            lines.append(f"- **{label}**: {val}")
    return "\n".join(lines)


def handle_qualification(session: dict, user_message: str) -> tuple[str, list | None]:
    """
    Main entry point for the lead qualification flow.
    Returns (response_text, quick_replies_or_None)
    """
    status = session.get("lead_status", "NOT_STARTED")

    if status == "CONSENT_PENDING":
        return _handle_consent(session, user_message)

    elif status == "COLLECTING":
        return _handle_collection(session, user_message)

    elif status == "CONFIRMING":
        return _handle_confirmation(session, user_message)

    # Fallback
    return "Something went wrong. Let me restart the qualification. " + CONSENT_MESSAGE, ["Yes", "No"]


def initiate_qualification(session: dict) -> tuple[str, list | None]:
    """Trigger the consent request."""
    session["lead_status"] = "CONSENT_PENDING"
    return CONSENT_MESSAGE, ["Yes, I agree", "No, thanks"]


def _handle_consent(session: dict, message: str) -> tuple[str, list | None]:
    if _is_affirmative(message):
        session["lead_status"] = "COLLECTING"
        session["current_field_index"] = 0
        session["lead_data"] = {}
        first_question = FIELDS[0][2]
        return (
            "Thank you for agreeing! Let's get started — I'll ask a few quick questions.\n\n"
            + first_question,
            None,
        )
    else:
        session["lead_status"] = "NOT_STARTED"
        return (
            "No problem at all! I'll keep our conversation focused on answering "
            "your questions. Feel free to ask me anything about our products or services.",
            None,
        )


def _handle_collection(session: dict, message: str) -> tuple[str, list | None]:
    idx = session.get("current_field_index", 0)
    lead_data = session.setdefault("lead_data", {})

    if idx >= len(ALL_FIELDS):
        # All fields done — move to confirmation
        return _start_confirmation(session)

    field_key, label, question, required = ALL_FIELDS[idx]

    # Handle optional skip
    if not required and _is_skip(message):
        idx += 1
        session["current_field_index"] = idx
        if idx >= len(ALL_FIELDS):
            return _start_confirmation(session)
        return ALL_FIELDS[idx][2], None

    # Validate
    is_valid, error_msg = _validate_field(field_key, message)
    if not is_valid:
        return error_msg, None

    # Save the value
    lead_data[field_key] = message.strip()
    idx += 1
    session["current_field_index"] = idx

    # Next field
    if idx < len(ALL_FIELDS):
        next_field = ALL_FIELDS[idx]
        ack = _acknowledgement(field_key, message.strip())
        return f"{ack}\n\n{next_field[2]}", None

    # All done
    return _start_confirmation(session)


def _start_confirmation(session: dict) -> tuple[str, list | None]:
    session["lead_status"] = "CONFIRMING"
    summary = _build_summary(session.get("lead_data", {}))
    return CONFIRMATION_PROMPT.format(summary=summary), ["Yes, submit", "No, make changes"]


def _handle_confirmation(session: dict, message: str) -> tuple[str, list | None]:
    if _is_affirmative(message):
        lead_data = session.get("lead_data", {})
        lead_data["session_id"] = session.get("session_id", "")
        session["lead_status"] = "COMPLETED"

        # Send Email Notification
        email_service.send_lead_email(lead_data)

        # Save to SQLite
        try:
            db.save_lead(session.get("session_id", ""), lead_data)
        except Exception as e:
            logger.error(f"Failed to save lead to DB: {e}")

        name = lead_data.get("first_name", "there")
        return (
            f"✅ **Thank you, {name}!** Your details have been submitted successfully.\n\n"
            "Our sales team will review your information and get in touch with you "
            "within **1 business day**.\n\n"
            "In the meantime, feel free to ask me any product questions you may have!",
            None,
        )
    else:
        # Restart collection
        session["lead_status"] = "COLLECTING"
        session["current_field_index"] = 0
        session["lead_data"] = {}
        return (
            "No problem! Let's start over. I'll ask you the questions again.\n\n"
            + FIELDS[0][2],
            None,
        )


def _acknowledgement(field_key: str, value: str) -> str:
    acks = {
        "first_name": f"Nice to meet you, **{value}**!",
        "last_name": "Got it!",
        "email": "Perfect, email noted.",
        "phone": "Contact number saved.",
        "company_name": f"Great, **{value}** — noted!",
        "address": "Address noted.",
    }
    return acks.get(field_key, "Got it!")


def get_progress(session: dict) -> dict:
    """Return progress info for the frontend progress bar."""
    status = session.get("lead_status", "NOT_STARTED")
    if status not in ("COLLECTING", "CONFIRMING", "COMPLETED"):
        return {"show": False, "current": 0, "total": len(REQUIRED_FIELDS)}

    collected = len([k for k in session.get("lead_data", {}) if k in {f[0] for f in REQUIRED_FIELDS}])
    return {
        "show": True,
        "current": collected,
        "total": len(REQUIRED_FIELDS),
    }
