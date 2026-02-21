"""
Web scraper for polymedicure.com — uses requests + BeautifulSoup.
Crawls product pages, FAQs, about pages within the target domain.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import time
from backend.config import TARGET_WEBSITE_URL

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; HCLeadAgent/1.0; "
        "+https://hcleadagent.com/bot)"
    )
}

# Pages to always include
SEED_PATHS = [
    "/",
    "/about-us/",
    "/product-category/cardiology/",
    "/product-category/i-v-infusion-therapy/",
    "/product-category/blood-management/",
    "/product-category/respiratory-care/",
    "/product-category/urology/",
    "/product-category/dialysis-products/",
    "/product-category/safety-devices/",
    "/product-category/oncology/",
    "/contact-us/",
]

MAX_PAGES = 120          # Cap total pages crawled
REQUEST_DELAY = 0.5      # Seconds between requests (be polite)


def _extract_text(soup: BeautifulSoup, url: str) -> dict | None:
    """Extract meaningful text from a page. Returns dict or None."""
    # Remove noise elements
    for tag in soup.find_all(["script", "style", "nav", "footer",
                               "header", "noscript", "iframe",
                               "form", "button", "svg"]):
        tag.decompose()

    # Title
    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    # Main content text
    main = soup.find("main") or soup.find("article") or soup.find("div", class_=lambda x: x and "content" in x.lower())
    if main:
        text = main.get_text(separator=" ", strip=True)
    else:
        text = soup.get_text(separator=" ", strip=True)

    # Clean up whitespace
    import re
    text = re.sub(r"\s{2,}", " ", text).strip()

    if len(text) < 80:
        return None  # Skip near-empty pages

    return {
        "url": url,
        "title": title,
        "text": text,
    }


def _is_valid_url(url: str, base_domain: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if base_domain not in parsed.netloc:
        return False
    # Skip media/downloads
    skip_extensions = (".jpg", ".jpeg", ".png", ".gif", ".pdf",
                       ".zip", ".svg", ".webp", ".ico", ".mp4")
    if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
        return False
    # Skip admin/wp-admin paths
    skip_paths = ("/wp-admin", "/wp-login", "/cart", "/checkout",
                  "/my-account", "/feed", "/xmlrpc")
    if any(s in parsed.path for s in skip_paths):
        return False
    return True


def scrape_website() -> list[dict]:
    """
    Crawl the target website and return list of page dicts:
    [{"url": ..., "title": ..., "text": ...}]
    """
    base_domain = urlparse(TARGET_WEBSITE_URL).netloc
    visited: set = set()
    to_visit: list = []
    pages: list = []

    # Seed URLs
    for path in SEED_PATHS:
        url = urljoin(TARGET_WEBSITE_URL, path)
        to_visit.append(url)

    logger.info(f"🕷️  Starting scrape of {TARGET_WEBSITE_URL} ...")

    while to_visit and len(visited) < MAX_PAGES:
        url = to_visit.pop(0)
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            if "text/html" not in resp.headers.get("Content-Type", ""):
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Extract text
            page_data = _extract_text(soup, url)
            if page_data:
                pages.append(page_data)
                logger.info(f"   ✓ {url} ({len(page_data['text'])} chars)")

            # Collect new links
            for a_tag in soup.find_all("a", href=True):
                link = urljoin(url, a_tag["href"])
                link = link.split("#")[0].rstrip("/") + "/"
                if link not in visited and _is_valid_url(link, base_domain):
                    to_visit.append(link)

            time.sleep(REQUEST_DELAY)

        except Exception as e:
            logger.warning(f"   ✗ Failed to scrape {url}: {e}")
            continue

    logger.info(f"🕷️  Scraping complete — {len(pages)} pages extracted")
    return pages
