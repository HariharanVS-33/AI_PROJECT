"""
HubSpot CRM integration — creates/updates contacts and companies via REST API.
"""
import httpx
import logging
from backend.config import HUBSPOT_PRIVATE_APP_TOKEN, HUBSPOT_BASE_URL

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {HUBSPOT_PRIVATE_APP_TOKEN}",
        "Content-Type": "application/json",
    }


def _is_configured() -> bool:
    return bool(HUBSPOT_PRIVATE_APP_TOKEN and HUBSPOT_PRIVATE_APP_TOKEN != "your_hubspot_private_app_token_here")


def create_or_update_contact(lead_data: dict) -> str | None:
    """
    Create or update a HubSpot contact (dedup by email).
    Returns the HubSpot contact ID or None on failure.
    """
    if not _is_configured():
        logger.warning("HubSpot token not configured — skipping CRM push")
        return None

    properties = {
        "firstname": lead_data.get("first_name", ""),
        "lastname": lead_data.get("last_name", ""),
        "email": lead_data.get("email", ""),
        "phone": lead_data.get("phone", ""),
        "address": lead_data.get("address", ""),
        "company": lead_data.get("company_name", ""),
        "leadsource": "Website Chatbot",
        "chatbot_consent_given": "true",
        "chatbot_session_id": lead_data.get("session_id", ""),
        "lead_qualification_status": "Qualified",
    }

    try:
        with httpx.Client(timeout=15) as client:
            # Try to upsert by email
            response = client.post(
                f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/upsert",
                headers=_headers(),
                json={
                    "properties": properties,
                    "idProperty": "email",
                },
            )
            if response.status_code in (200, 201):
                contact_id = response.json().get("id")
                logger.info(f"✅ HubSpot contact upserted: {contact_id}")
                return contact_id
            else:
                # Fallback: plain create
                response = client.post(
                    f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts",
                    headers=_headers(),
                    json={"properties": properties},
                )
                if response.status_code in (200, 201):
                    contact_id = response.json().get("id")
                    logger.info(f"✅ HubSpot contact created: {contact_id}")
                    return contact_id
                else:
                    logger.error(f"HubSpot contact error: {response.status_code} {response.text}")
                    return None
    except Exception as e:
        logger.error(f"HubSpot create_or_update_contact exception: {e}")
        return None


def create_or_update_company(lead_data: dict) -> str | None:
    """
    Create or update a HubSpot company (dedup by name).
    Returns the HubSpot company ID or None on failure.
    """
    if not _is_configured():
        return None

    properties = {
        "name": lead_data.get("company_name", ""),
        "industry": "HEALTHCARE",
        "address": lead_data.get("address", ""),
    }

    try:
        with httpx.Client(timeout=15) as client:
            # Search for existing company
            search_response = client.post(
                f"{HUBSPOT_BASE_URL}/crm/v3/objects/companies/search",
                headers=_headers(),
                json={
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "name",
                            "operator": "EQ",
                            "value": lead_data.get("company_name", ""),
                        }]
                    }],
                    "limit": 1,
                },
            )
            results = search_response.json().get("results", [])
            if results:
                return results[0]["id"]

            # Create new company
            response = client.post(
                f"{HUBSPOT_BASE_URL}/crm/v3/objects/companies",
                headers=_headers(),
                json={"properties": properties},
            )
            if response.status_code in (200, 201):
                company_id = response.json().get("id")
                logger.info(f"✅ HubSpot company created: {company_id}")
                return company_id
            else:
                logger.error(f"HubSpot company error: {response.status_code} {response.text}")
                return None
    except Exception as e:
        logger.error(f"HubSpot create_or_update_company exception: {e}")
        return None


def associate_contact_company(contact_id: str, company_id: str) -> None:
    """Associate a contact with a company in HubSpot."""
    if not _is_configured() or not contact_id or not company_id:
        return

    try:
        with httpx.Client(timeout=15) as client:
            client.put(
                f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/contact_to_company",
                headers=_headers(),
            )
        logger.info(f"✅ HubSpot association: contact {contact_id} ↔ company {company_id}")
    except Exception as e:
        logger.error(f"HubSpot associate error: {e}")


def push_lead_to_hubspot(lead_data: dict) -> dict:
    """
    Full HubSpot push: contact + company + association.
    Returns {"contact_id": ..., "company_id": ...}
    """
    contact_id = create_or_update_contact(lead_data)
    company_id = create_or_update_company(lead_data)
    if contact_id and company_id:
        associate_contact_company(contact_id, company_id)
    return {"contact_id": contact_id, "company_id": company_id}
