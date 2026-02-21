"""
FastAPI application entrypoint.
Mounts API routers and serves the frontend static files.
"""
import logging
import threading
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.api import chat as chat_router
from backend.api import admin as admin_router
from backend import database as db
from backend.integrations import chromadb_client as vdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _initial_scrape_if_empty():
    """If the knowledge base is empty, trigger an initial scrape."""
    count = vdb.get_document_count()
    if count == 0:
        logger.info("📭 Knowledge base is empty — starting initial scrape...")
        from backend.scraper.scraper import scrape_website
        from backend.scraper.etl import run_etl
        pages = scrape_website()
        run_etl(pages)
    else:
        logger.info(f"📚 Knowledge base ready — {count} document chunks loaded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🚀 Starting Healthcare Lead Agent...")

    # Init SQLite
    db.init_db()

    # Init ChromaDB (creates collection if not exists)
    vdb.get_document_count()

    # Scrape in background thread so startup is fast
    thread = threading.Thread(target=_initial_scrape_if_empty, daemon=True)
    thread.start()

    yield  # App is running

    logger.info("👋 Shutting down...")


app = FastAPI(
    title="HC Lead Agent API",
    description="Healthcare Dealer/Distributor Lead Conversational Agent",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(chat_router.router, prefix="/api", tags=["Chat"])
app.include_router(admin_router.router, prefix="/api", tags=["Admin"])

# Serve frontend static files — must be LAST
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    logger.info(f"📁 Serving frontend from {frontend_dir}")
else:
    logger.warning(f"Frontend directory not found at {frontend_dir}")
