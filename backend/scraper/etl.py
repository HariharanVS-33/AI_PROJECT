"""
ETL Pipeline — chunks scraped pages, generates embeddings, indexes into ChromaDB.
"""
import hashlib
import logging
import time
from backend.config import CHUNK_CHAR_SIZE, CHUNK_OVERLAP_CHARS
from backend.integrations import gemini as gem
from backend.integrations import chromadb_client as vdb

logger = logging.getLogger(__name__)

EMBED_BATCH_DELAY = 0.2    # Seconds between embedding calls (rate limit safety)


def _chunk_text(text: str, url: str, title: str) -> list[dict]:
    """Split text into overlapping chunks with metadata."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_CHAR_SIZE
        chunk_text = text[start:end].strip()
        if len(chunk_text) > 80:
            chunk_id = hashlib.md5(f"{url}-{idx}".encode()).hexdigest()
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "source_url": url,
                "page_title": title,
            })
            idx += 1
        start = end - CHUNK_OVERLAP_CHARS
    return chunks


def run_etl(pages: list[dict]) -> int:
    """
    Process pages → chunks → embeddings → ChromaDB.
    Returns number of chunks indexed.
    """
    if not pages:
        logger.warning("ETL: no pages provided")
        return 0

    all_chunks = []
    for page in pages:
        chunks = _chunk_text(page["text"], page["url"], page["title"])
        all_chunks.extend(chunks)

    logger.info(f"📦 ETL: {len(pages)} pages → {len(all_chunks)} chunks")

    ids, documents, embeddings, metadatas = [], [], [], []
    failed = 0

    for i, chunk in enumerate(all_chunks):
        embedding = gem.get_document_embedding(chunk["text"])
        if not embedding:
            failed += 1
            continue

        ids.append(chunk["id"])
        documents.append(chunk["text"])
        embeddings.append(embedding)
        metadatas.append({
            "source_url": chunk["source_url"],
            "page_title": chunk["page_title"],
        })

        # Batch upsert every 50 chunks
        if len(ids) >= 50:
            vdb.add_documents(ids, documents, embeddings, metadatas)
            ids, documents, embeddings, metadatas = [], [], [], []
            logger.info(f"   ↳ Indexed {i+1}/{len(all_chunks)} chunks...")

        time.sleep(EMBED_BATCH_DELAY)

    # Flush remaining
    if ids:
        vdb.add_documents(ids, documents, embeddings, metadatas)

    total_indexed = len(all_chunks) - failed
    logger.info(f"✅ ETL complete — {total_indexed} chunks indexed ({failed} failed)")
    return total_indexed
