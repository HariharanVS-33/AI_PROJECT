import sys
from backend.integrations.email_service import send_lead_email
import logging

logging.basicConfig(level=logging.INFO)

test_lead = {
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "phone": "1234567890",
    "company_name": "Acme Corp",
    "address": "123 Test St"
}

if __name__ == "__main__":
    success = send_lead_email(test_lead)
    if success:
        print("Test email sent success!")
        sys.exit(0)
    else:
        print("Test email failed.")
        sys.exit(1)
