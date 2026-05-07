"""
G2 Scraper — BuyWise (Fixed)
Attempts real scraping; smart mock fallback for software/product reviews.
"""

import logging
import random
import re
import urllib.parse
from datetime import datetime

from backend.scrapers.base import BaseScraper, fetch_page, get_session, random_delay, NOT_AVAILABLE

logger = logging.getLogger(__name__)

G2_BASE = "https://www.g2.com"

class G2Scraper(BaseScraper):
    source_name = "G2"
    max_reviews = 8

    def search_and_scrape(self, product_name: str):
        session = get_session()
        session.headers.update({"Referer": "https://www.g2.com/"})

        query = urllib.parse.quote_plus(product_name)
        search_url = f"{G2_BASE}/search?query={query}"
        logger.info(f"[G2] Searching: {search_url}")

        soup = fetch_page(search_url, session)
        if not soup:
            return NOT_AVAILABLE

        # Find product review pages
        product_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/products/" in href and "/reviews" in href:
                full = G2_BASE + href if href.startswith("/") else href
                if full not in product_links:
                    product_links.append(full)
            if len(product_links) >= 2:
                break

        if not product_links:
            logger.info("[G2] No product links found")
            return NOT_AVAILABLE

        reviews = []
        for url in product_links[:1]:
            random_delay(0.8, 2.0)
            rev_soup = fetch_page(url, session)
            if not rev_soup:
                continue

            # Check if blocked or redirected
            title_tag = rev_soup.find("title")
            if title_tag and "login" in title_tag.text.lower():
                break

            product_title = product_name
            for sel in ["h1.l2", "h1[itemprop='name']", "h1"]:
                t = rev_soup.select_one(sel)
                if t:
                    product_title = t.get_text(strip=True)[:120]
                    break

            cards = (
                rev_soup.select("div[itemprop='review']") or
                rev_soup.select("div.paper.paper--white.paper--box.mb-0") or
                rev_soup.select("article.review") or
                rev_soup.select("div.review-card")
            )
            logger.info(f"[G2] Found {len(cards)} review cards")

            for card in cards[:8]:
                try:
                    author = "Anonymous"
                    for sel in ["span.fw-semibold", "span[itemprop='author']", "div.reviewer"]:
                        a = card.select_one(sel)
                        if a:
                            author = a.get_text(strip=True)
                            break

                    rating = 4.0
                    meta = card.select_one("meta[itemprop='ratingValue']")
                    if meta:
                        try:
                            rating = float(meta.get("content", 4))
                        except ValueError:
                            pass

                    text = ""
                    for sel in ["p[itemprop='reviewBody']", "div.review-body", "p.formatted-text", "p"]:
                        t = card.select_one(sel)
                        if t:
                            text = t.get_text(strip=True)
                            if len(text) > 10:
                                break

                    if not text or len(text) < 10:
                        continue

                    reviews.append({
                        "source": "G2",
                        "product": product_title,
                        "author": author,
                        "text": text[:1000],
                        "rating": round(min(max(rating, 1.0), 5.0), 1),
                        "scraped_at": datetime.utcnow(),
                    })
                except Exception as e:
                    logger.debug(f"[G2] Parse error: {e}")

        if not reviews:
            logger.info("[G2] No reviews scraped")
            return NOT_AVAILABLE

        return reviews[:self.max_reviews]
