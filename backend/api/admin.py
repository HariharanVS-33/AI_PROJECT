"""
Admin API — health check + scrape trigger.
"""
import logging
import threading
from fastapi import APIRouter
from backend.models.schemas import HealthResponse, ScrapeResponse
from backend.integrations import chromadb_client as vdb

logger = logging.getLogger(__name__)
router = APIRouter()

_scrape_running = False


def _run_scrape_in_background():
    """Run the full scrape + ETL pipeline in a background thread."""
    global _scrape_running
    try:
        from backend.scraper.scraper import scrape_website
        from backend.scraper.etl import run_etl
        logger.info("🔄 Background scrape started...")
        pages = scrape_website()
        count = run_etl(pages)
        logger.info(f"✅ Background scrape complete — {count} chunks indexed")
    except Exception as e:
        logger.error(f"Background scrape failed: {e}")
    finally:
        _scrape_running = False


@router.get("/health", response_model=HealthResponse)
def health():
    """Health check — returns KB document count."""
    count = vdb.get_document_count()
    return HealthResponse(
        status="healthy",
        kb_document_count=count,
        kb_ready=count > 0,
    )


@router.post("/admin/scrape", response_model=ScrapeResponse)
def trigger_scrape():
    """Trigger a re-scrape of the target website in the background."""
    global _scrape_running
    if _scrape_running:
        return ScrapeResponse(status="already_running", message="Scrape is already in progress.")

    _scrape_running = True
    thread = threading.Thread(target=_run_scrape_in_background, daemon=True)
    thread.start()

    return ScrapeResponse(
        status="started",
        message="Scraping started in background. This may take a few minutes.",
    )
