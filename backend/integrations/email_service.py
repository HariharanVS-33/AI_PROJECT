"""
Email notification service - sends lead details to customer care.
"""
import smtplib
from email.message import EmailMessage
import logging
from backend.config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, CUSTOMER_CARE_EMAIL

logger = logging.getLogger(__name__)

def _is_configured() -> bool:
    return bool(SMTP_SERVER and SMTP_PORT and SMTP_USERNAME and SMTP_PASSWORD and CUSTOMER_CARE_EMAIL)

def send_lead_email(lead_data: dict) -> bool:
    """
    Send lead details to the configured customer care email via SMTP.
    Returns True if successful, False otherwise.
    """
    if not _is_configured():
        logger.warning("SMTP configuration is missing - skipping email notification.")
        return False

    try:
        msg = EmailMessage()
        
        # Build email content
        subject = f"New Lead: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}"
        if lead_data.get("company_name", "").lower() not in ("skip", "n/a", "-", ""):
            subject += f" from {lead_data.get('company_name', '')}"
            
        msg['Subject'] = subject
        msg['From'] = SMTP_USERNAME
        msg['To'] = CUSTOMER_CARE_EMAIL

        body = "A new lead has been qualified via the chatbot:\n\n"
        
        fields = [
            ("First Name", "first_name"),
            ("Last Name", "last_name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Company", "company_name"),
            ("Address", "address"),
        ]
        
        for label, key in fields:
            val = lead_data.get(key, "N/A")
            body += f"{label}: {val}\n"
            
        body += "\nThis is an automated message."
        
        msg.set_content(body)

        # Send the email
        with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"✅ Lead email sent successfully to {CUSTOMER_CARE_EMAIL}")
        return True

    except Exception as e:
        logger.error(f"Failed to send lead email: {e}")
        return False
