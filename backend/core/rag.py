"""
RAG Pipeline — retrieves relevant context and generates grounded responses.
"""
import logging
from backend.config import RAG_SIMILARITY_THRESHOLD
from backend.integrations import gemini as gem
from backend.integrations import chromadb_client as vdb

logger = logging.getLogger(__name__)

FALLBACK_RESPONSE = (
    "I don't have specific information about that in my current knowledge base. "
    "For detailed assistance, please reach out to our sales team at "
    "**sales@polymedicure.com** or visit [polymedicure.com](https://www.polymedicure.com). "
    "Is there anything else I can help you with?"
)


def query(user_message: str, conversation_history: list) -> dict:
    """
    Run RAG query:
    1. Embed user message
    2. Retrieve top-K chunks
    3. Filter by similarity threshold
    4. Generate grounded response
    Returns {"response": str, "context_found": bool, "sources": list}
    """
    # 1. Embed the query
    query_embedding = gem.get_embedding(user_message)
    if not query_embedding:
        return {"response": FALLBACK_RESPONSE, "context_found": False, "sources": []}

    # 2. Retrieve chunks
    chunks = vdb.search(query_embedding, n_results=5)
    if not chunks:
        return {"response": FALLBACK_RESPONSE, "context_found": False, "sources": []}

    # 3. Filter by similarity threshold (distance < threshold means more similar)
    relevant_chunks = [c for c in chunks if c["distance"] < RAG_SIMILARITY_THRESHOLD]
    if not relevant_chunks:
        # Use best available chunks but flag low confidence
        relevant_chunks = chunks[:2]
        low_confidence = True
    else:
        low_confidence = False

    # 4. Build context block
    context_parts = []
    sources = []
    for chunk in relevant_chunks:
        context_parts.append(f"Source: {chunk['title']} ({chunk['source']})\n{chunk['content']}")
        if chunk["source"] not in sources:
            sources.append(chunk["source"])

    context = "\n\n---\n\n".join(context_parts)

    # 5. Generate response
    if low_confidence:
        # Add a note to guide the LLM to acknowledge uncertainty
        user_msg_with_note = (
            f"{user_message}\n\n"
            "[Note: Retrieved context may not perfectly match this query. "
            "If the context doesn't contain the answer, say so and offer to connect the user with sales.]"
        )
        history_copy = conversation_history[:-1] + [
            {"role": "user", "parts": [user_msg_with_note]}
        ]
        response = gem.generate_response(history_copy, context)
    else:
        response = gem.generate_response(conversation_history, context)

    return {
        "response": response,
        "context_found": True,
        "sources": sources,
    }
