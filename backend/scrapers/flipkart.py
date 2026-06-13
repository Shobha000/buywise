"""
Flipkart Scraper — BuyWise
Extracts REAL reviews from Flipkart product pages using the proven Level-5
DOM walk from rating-anchor divs. Deduplicated. Returns NOT_AVAILABLE when blocked.

Structure confirmed by live DOM analysis:
  div (rating digit) → parent → parent → parent → parent → parent
  Level 5 text: "5|Just wow!|7 months ago|The phone offers exceptional performance..."
"""

import logging
import re
import urllib.parse
from datetime import datetime

from backend.scrapers.base import (
    BaseScraper, ScrapeResult, NOT_AVAILABLE,
    fetch_page, get_session, random_delay, get_random_name,
)

logger = logging.getLogger(__name__)

FLIPKART_BASE = "https://www.flipkart.com"

# Flipkart review images live on rukminim CDN but NOT in /www/ or /promos/ paths
_FK_IMG_RE = re.compile(r'rukminim[12]\.flixcart\.com')
_FK_IMG_SKIP = re.compile(r'/www/|/promos/')


def _extract_review_images_flipkart(node) -> list[str]:
    """Extract real review photo URLs from a Flipkart review container node."""
    if not node:
        return []
    images = []
    for img in node.find_all("img", src=True):
        src = img.get("src", "") or img.get("data-src", "")
        if not _FK_IMG_RE.search(src):
            continue
        if _FK_IMG_SKIP.search(src):
            continue  # Skip promo/UI images
        # Flipkart review images: upgrade to 400x400 size
        src = re.sub(r'/\d+/\d+/', '/400/400/', src)
        if src not in images:
            images.append(src)
    return images[:5]

# Noise patterns to remove from extracted review text
_NOISE = re.compile(
    r"(READ MORE|Read more|Certified Buyer|Report Abuse|"
    r"Was this review helpful\??|Helpful\?|Upvote|Comment|"
    r"(\d+) (month|year|day|week)s? ago)",
    re.IGNORECASE,
)

def _clean(text: str) -> str:
    """Strip rating prefix, timestamps, and UI noise from review text."""
    text = re.sub(r"^[1-5](?:\.0)?\s*", "", text.strip())  # Leading rating digit
    text = _NOISE.sub("", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def _parse_level5(text: str) -> tuple[float, str, str]:
    """
    Parse a Level-5 ancestor text block:
      '5|Just wow!|7 months ago|The phone offers...|Reviewer Name|...'
    Returns (rating, title, review_body).
    """
    parts = [p.strip() for p in text.split("|") if p.strip()]
    if not parts:
        return 3.0, "", text

    # Rating: first part is a single digit
    rating = 3.0
    idx = 0
    if re.match(r"^[1-5]$", parts[0]):
        rating = float(parts[0])
        idx = 1

    # Optional short title (second part, typically < 60 chars)
    title = ""
    if idx < len(parts) and len(parts[idx]) < 60 and not re.match(r"\d+\s*(month|year)", parts[idx]):
        title = parts[idx]
        idx += 1

    # Skip timestamp (e.g. "7 months ago")
    if idx < len(parts) and re.match(r"\d+\s*(month|year|day|week)", parts[idx], re.I):
        idx += 1

    # Body: everything after, up to a short trailing author name
    body_parts = parts[idx:]
    # Drop very short trailing parts (reviewer name, badge, counts)
    while body_parts and len(body_parts[-1]) < 30 and not re.search(r"[.!?]", body_parts[-1]):
        body_parts.pop()

    body = " ".join(body_parts).strip()
    if not body and title:
        body = title
    return rating, title, body


class FlipkartScraper(BaseScraper):
    source_name = "Flipkart"
    max_reviews = 20

    def search_and_scrape(self, product_name: str) -> ScrapeResult:
        session = get_session()
        session.headers.update({"Referer": "https://www.flipkart.com/"})
        query = urllib.parse.quote_plus(product_name)
        search_url = f"{FLIPKART_BASE}/search?q={query}&sort=relevance"
        logger.info(f"[Flipkart] Searching: {search_url}")

        soup = fetch_page(search_url, session, timeout=12)
        if not soup:
            logger.warning("[Flipkart] Could not fetch search page")
            return NOT_AVAILABLE

        page_title = soup.find("title")
        if page_title:
            t = page_title.text.lower()
            if any(w in t for w in ["login", "captcha", "blocked"]):
                logger.warning("[Flipkart] Search page blocked")
                return NOT_AVAILABLE

        # ── Extract product links ─────────────────────────────────────────────
        from backend.scrapers.filter import is_accessory, relevance_score

        product_links: list[tuple[str, str]] = []
        seen_urls: set[str] = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/p/" not in href or "pid=" not in href:
                continue
            parts = href.strip("/").split("/")
            title_slug = parts[0].replace("-", " ") if parts else ""

            if is_accessory(title_slug):
                logger.debug(f"[Flipkart] Accessory skip: {title_slug[:60]}")
                continue
            score = relevance_score(product_name, title_slug)
            if score < 0.25:
                logger.debug(f"[Flipkart] Low relevance ({score:.2f}): {title_slug[:60]}")
                continue

            full = (FLIPKART_BASE + href if href.startswith("/") else href).split("?")[0]
            if full not in seen_urls:
                seen_urls.add(full)
                product_links.append((full, title_slug))
            if len(product_links) >= 5:
                break

        if not product_links:
            logger.info("[Flipkart] No relevant product links found")
            return NOT_AVAILABLE

        logger.info(f"[Flipkart] {len(product_links)} product pages to scrape")

        all_reviews: list[dict] = []
        global_seen: set[str] = set()

        for product_url, title_slug in product_links:
            if len(all_reviews) >= self.max_reviews:
                break
            random_delay(0.4, 0.9)

            soup_p = fetch_page(product_url, session, timeout=12)
            if not soup_p:
                continue

            prod_title_tag = soup_p.find("title")
            if prod_title_tag and "login" in prod_title_tag.text.lower():
                logger.warning(f"[Flipkart] Login wall at {product_url[-60:]}")
                continue

            # Get real product title from page
            product_title = product_name
            for sel in ["span.B_NuCI", "h1.yhB1nd", "h1"]:
                t_el = soup_p.select_one(sel)
                if t_el:
                    candidate = t_el.get_text(strip=True)
                    if "flipkart" not in candidate.lower() and "|" not in candidate:
                        product_title = candidate[:120]
                        break

            # ── Level-5 DOM walk from rating-anchor divs ──────────────────────
            rating_divs = soup_p.find_all("div", string=re.compile(r"^[1-5]$"))
            logger.info(f"[Flipkart] {product_url[-60:]}: {len(rating_divs)} rating anchors")

            seen_l5: set[str] = set()

            for r_div in rating_divs:
                node = r_div
                for _ in range(5):         # Walk exactly 5 levels up (confirmed sweet spot)
                    if node.parent:
                        node = node.parent

                raw_text = node.get_text(separator="|", strip=True)

                # Accept only texts that look like a review (not rating histogram)
                if raw_text in seen_l5:
                    continue
                if len(raw_text) < 40 or len(raw_text) > 5000:
                    continue
                # Must contain actual word content, not just digits/symbols
                if not re.search(r"[a-zA-Z]{4,}", raw_text):
                    continue

                seen_l5.add(raw_text)
                rating, title, body = _parse_level5(raw_text)

                if len(body) < 15:
                    continue

                # Deduplicate across all products
                body_key = body[:80]
                if body_key in global_seen:
                    continue
                global_seen.add(body_key)

                # Extract review images from the node
                import json
                images = _extract_review_images_flipkart(node)

                rev = {
                    "source":     "Flipkart",
                    "product":    product_title,
                    "author":     get_random_name(),
                    "text":       _clean(body)[:1000],
                    "rating":     round(min(max(rating, 1.0), 5.0), 1),
                    "scraped_at": datetime.utcnow(),
                }
                if images:
                    rev["images"] = json.dumps(images)
                all_reviews.append(rev)

            logger.info(
                f"[Flipkart] {product_url[-60:]}: "
                f"{len(all_reviews)} reviews total so far"
            )

        logger.info(f"[Flipkart] Final: {len(all_reviews)} real reviews")
        if not all_reviews:
            return NOT_AVAILABLE
        return ScrapeResult(available=True, reviews=all_reviews[:self.max_reviews])
