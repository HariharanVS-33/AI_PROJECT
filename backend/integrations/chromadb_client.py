"""
ChromaDB vector store client — stores and retrieves knowledge base chunks.
"""
import chromadb
import os
import logging
from backend.config import CHROMA_DB_PATH

logger = logging.getLogger(__name__)

COLLECTION_NAME = "polymedicure_kb"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB collection '{COLLECTION_NAME}' ready — {_collection.count()} docs")
    return _collection


def get_document_count() -> int:
    """Return number of documents in the knowledge base."""
    try:
        return _get_collection().count()
    except Exception as e:
        logger.error(f"ChromaDB count error: {e}")
        return 0


def add_documents(ids: list, documents: list, embeddings: list, metadatas: list) -> None:
    """Upsert document chunks into ChromaDB."""
    try:
        collection = _get_collection()
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(f"✅ Upserted {len(ids)} chunks into ChromaDB")
    except Exception as e:
        logger.error(f"ChromaDB add_documents error: {e}")
        raise


def search(query_embedding: list, n_results: int = 5) -> list:
    """
    Semantic search. Returns list of dicts with 'content', 'source', 'distance'.
    """
    try:
        collection = _get_collection()
        if collection.count() == 0:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "content": doc,
                "source": meta.get("source_url", ""),
                "title": meta.get("page_title", ""),
                "distance": dist,
            })
        return chunks
    except Exception as e:
        logger.error(f"ChromaDB search error: {e}")
        return []


def clear_collection() -> None:
    """Delete all documents in the collection (for re-indexing)."""
    global _collection
    try:
        if _client:
            _client.delete_collection(COLLECTION_NAME)
            _collection = None
            logger.info("ChromaDB collection cleared")
    except Exception as e:
        logger.error(f"ChromaDB clear error: {e}")
