"""
Base Scraper — BuyWise
Shared session, rotating user agents, browser-like headers, delay logic.
"""

import logging
import random
import time
from abc import ABC, abstractmethod

from curl_cffi import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def get_session() -> requests.Session:
    """Create a requests session with TLS fingerprint impersonation."""
    session = requests.Session(impersonate="chrome110")
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,en-IN;q=0.8,hi;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    })
    return session


def random_delay(min_s: float = 0.1, max_s: float = 0.4):
    """Sleep for a short random duration to avoid rate limiting."""
    time.sleep(random.uniform(min_s, max_s))


def fetch_page(url: str, session: requests.Session | None = None, timeout: int = 15) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    s = session or get_session()
    try:
        response = s.get(url, timeout=timeout, allow_redirects=True)
        # curl_cffi doesn't throw an exception on 403, so we check status code
        if response.status_code >= 400:
            logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
            return None
        return BeautifulSoup(response.text, "lxml")
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def get_random_name() -> str:
    """Generate a realistic random name for reviews without an author."""
    first_names = [
        "Aarav", "Priya", "Rahul", "Neha", "Vikram", "Sneha", "Aditya", "Riya",
        "Rohan", "Anjali", "Karan", "Kavita", "Amit", "Pooja", "Arjun", "Kirti",
        "Siddharth", "Megha", "Manish", "Divya", "Suresh", "Nisha", "Gaurav",
        "John", "David", "Michael", "Sarah", "Emily", "Jessica"
    ]
    last_names = [
        "Sharma", "Patel", "Singh", "Kumar", "Gupta", "Desai", "Joshi", "Verma",
        "Mehta", "Shah", "Reddy", "Rao", "Nair", "Das", "Bose", "Chopra",
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Davis"
    ]
    return f"{random.choice(first_names)} {random.choice(last_names)}"


# ─── Scrape Result ────────────────────────────────────────────────────────────

class ScrapeResult:
    """
    Wraps scraper output with product availability status.
    available=True  → product found on this site, reviews populated
    available=False → product genuinely NOT found on this site, reviews=[]
    available=None  → site blocked / timed out, availability unknown
    """
    __slots__ = ("available", "reviews")

    def __init__(self, available: bool | None, reviews: list[dict]):
        self.available = available
        self.reviews   = reviews

    def __repr__(self):
        return f"ScrapeResult(available={self.available}, n={len(self.reviews)})"


# Singleton for "not available" response
NOT_AVAILABLE = ScrapeResult(available=False, reviews=[])


# ─── Base Scraper Interface ───────────────────────────────────────────────────

class BaseScraper(ABC):
    source_name: str = "Unknown"
    max_reviews: int = 10

    @abstractmethod
    def search_and_scrape(self, product_name: str) -> ScrapeResult:
        """
        Search for product_name and return a ScrapeResult.
        - available=True  → found reviews
        - available=False → searched but product not listed on this site
        - available=None  → couldn't reach site (blocked/timeout)
        """
        ...

    def safe_scrape(self, product_name: str) -> ScrapeResult:
        """Wraps search_and_scrape with error handling."""
        try:
            result = self.search_and_scrape(product_name)
            if result.available is False:
                logger.info(f"[{self.source_name}] ❌ Product not available for '{product_name}'")
            elif result.available:
                logger.info(f"[{self.source_name}] ✅ Found {len(result.reviews)} reviews for '{product_name}'")
            else:
                logger.info(f"[{self.source_name}] ⚠️ Site unreachable, {len(result.reviews)} mock reviews for '{product_name}'")
            return result
        except Exception as e:
            logger.error(f"[{self.source_name}] Scraper failed for '{product_name}': {e}")
            return ScrapeResult(available=None, reviews=[])
