"""
Trustpilot Scraper — BuyWise (Fixed)
Attempts real scraping with improved selectors; smart mock fallback.
"""

import logging
import random
import re
import urllib.parse
from datetime import datetime

from backend.scrapers.base import BaseScraper, fetch_page, get_session, random_delay, NOT_AVAILABLE

logger = logging.getLogger(__name__)

TRUSTPILOT_BASE = "https://www.trustpilot.com"

class TrustpilotScraper(BaseScraper):
    source_name = "Trustpilot"
    max_reviews = 8

    def search_and_scrape(self, product_name: str):
        session = get_session()

        # Try to find a relevant company on Trustpilot
        query = urllib.parse.quote_plus(product_name)
        search_url = f"{TRUSTPILOT_BASE}/search?query={query}&type=company"
        logger.info(f"[Trustpilot] Searching: {search_url}")

        soup = fetch_page(search_url, session)
        if not soup:
            return NOT_AVAILABLE

        # Find company review pages
        company_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/review/") and len(href) > 9:
                full = TRUSTPILOT_BASE + href
                if full not in company_links:
                    company_links.append(full)
            if len(company_links) >= 2:
                break

        if not company_links:
            logger.info("[Trustpilot] No company links found")
            return NOT_AVAILABLE

        reviews = []
        for company_url in company_links[:1]:
            random_delay(0.5, 1.5)
            rev_soup = fetch_page(company_url, session)
            if not rev_soup:
                continue

            product_title = product_name
            for sel in ["h1.title_title__Zsk7U", "h1[data-business-unit-display-name]", "h1"]:
                t = rev_soup.select_one(sel)
                if t:
                    product_title = t.get_text(strip=True)[:80]
                    break

            # Try various review card selectors
            cards = (
                rev_soup.select("article.paper_paper__EFilf") or
                rev_soup.select("div[class*='reviewCard']") or
                rev_soup.select("section[class*='review']") or
                rev_soup.select("article[class*='review']")
            )
            logger.info(f"[Trustpilot] Found {len(cards)} review cards")

            for card in cards[:8]:
                try:
                    author = "Anonymous"
                    for sel in ["span[data-consumer-name-typography]", "div.consumer-info__name", "span.typography_heading-xxs__QKBS8"]:
                        a = card.select_one(sel)
                        if a:
                            author = a.get_text(strip=True)
                            break

                    rating = 4.0
                    for sel in ["div[data-service-review-rating]", "img[alt*='star']", "img[alt*='Star']"]:
                        rt = card.select_one(sel)
                        if rt:
                            val = rt.get("data-service-review-rating") or re.search(r"(\d)", rt.get("alt", ""))
                            if val:
                                try:
                                    rating = float(val if isinstance(val, str) else val.group(1))
                                except Exception:
                                    pass
                            break

                    text = ""
                    for sel in ["p[data-service-review-text-typography]", "p.typography_body-l__v5JLj", "p[class*='reviewContent']", "p"]:
                        t = card.select_one(sel)
                        if t:
                            text = t.get_text(strip=True)
                            if len(text) > 10:
                                break

                    if not text or len(text) < 10:
                        continue

                    reviews.append({
                        "source": "Trustpilot",
                        "product": product_title,
                        "author": author,
                        "text": text[:1000],
                        "rating": round(min(max(rating, 1.0), 5.0), 1),
                        "scraped_at": datetime.utcnow(),
                    })
                except Exception as e:
                    logger.debug(f"[Trustpilot] Parse error: {e}")

        if not reviews:
            logger.info("[Trustpilot] No reviews scraped")
            return NOT_AVAILABLE

        return reviews[:self.max_reviews]
