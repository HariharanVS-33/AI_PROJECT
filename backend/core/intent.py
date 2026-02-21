"""
Intent classifier using Gemini few-shot prompting.
"""
import logging
from backend.integrations import gemini as gem

logger = logging.getLogger(__name__)

VALID_INTENTS = {
    "product_query",
    "distributor_query",
    "territory_query",
    "pricing_query",
    "sales_intent",
    "general_enquiry",
    "out_of_scope",
}

CLASSIFICATION_PROMPT = """Classify the user message into EXACTLY ONE of these intents. Reply with only the intent name.

Intents:
- product_query: Asking about a medical product, specification, catalogue, or usage
- distributor_query: Asking about becoming a distributor, dealer, or channel partner
- territory_query: Asking about regions, coverage areas, or geographic availability
- pricing_query: Asking about pricing, discounts, quotes, or payment terms
- sales_intent: Showing intent to buy, partner, or saying they want to proceed with something
- general_enquiry: General greetings, company info, or miscellaneous questions
- out_of_scope: Completely unrelated to healthcare devices or PolyMedicure

Examples:
"Tell me about your cardiology products" → product_query
"How do I become a distributor in Kerala?" → distributor_query
"Do you have dealers in South India?" → territory_query
"What is the price of your IV cannulas?" → pricing_query
"Yes, I'm interested in partnering with you" → sales_intent
"What is your company history?" → general_enquiry
"Tell me a joke" → out_of_scope
"What's the weather today?" → out_of_scope

User message: "{message}"

Intent:"""


def classify(message: str) -> str:
    """Classify a user message into one of the defined intents."""
    try:
        prompt = CLASSIFICATION_PROMPT.format(message=message.strip())
        raw = gem.generate_simple_response(prompt).strip().lower()

        # Match to valid intents
        for intent in VALID_INTENTS:
            if intent in raw:
                return intent

        logger.warning(f"Intent classifier got unexpected response: '{raw}' — defaulting to general_enquiry")
        return "general_enquiry"

    except Exception as e:
        logger.error(f"Intent classification error: {e}")
        return "general_enquiry"
