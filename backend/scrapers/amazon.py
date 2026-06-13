"""
Amazon Scraper — BuyWise
Extracts REAL reviews from Amazon product pages using the reviewsMedley
section (highlighted reviews on the DP page). Falls back to review-body
snippets. Returns NOT_AVAILABLE when blocked.
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

AMAZON_BASE = "https://www.amazon.in"

# Amazon CDN patterns for real review images (not tracking pixels or icons)
_AMAZON_IMG_RE = re.compile(r'(images-amazon\.com|m\.media-amazon\.com|ssl-images-amazon\.com)')


def _extract_review_images_amazon(node) -> list[str]:
    """Extract real review photo URLs from an Amazon review container node."""
    if not node:
        return []
    images = []
    for img in node.find_all("img", src=True):
        src = img.get("src", "") or img.get("data-src", "")
        # Only real review images from Amazon CDN — skip tracking pixels (<50px)
        if not _AMAZON_IMG_RE.search(src):
            continue
        # Skip tiny sprites/icons — review photos are typically > 60px
        w = img.get("width", "")
        h = img.get("height", "")
        try:
            if int(w) < 60 or int(h) < 60:
                continue
        except (ValueError, TypeError):
            pass
        # Normalise: replace thumbnail suffix with larger version
        src = re.sub(r'\._[A-Z]{2}\d+_\.', '._SL300_.', src)
        if src not in images:
            images.append(src)
    return images[:5]  # max 5 images per review



class AmazonScraper(BaseScraper):
    source_name = "Amazon"
    max_reviews = 20

    def search_and_scrape(self, product_name: str) -> ScrapeResult:
        session = get_session()
        session.headers.update({"Referer": "https://www.amazon.in/"})
        query = urllib.parse.quote_plus(product_name)
        search_url = f"{AMAZON_BASE}/s?k={query}"
        logger.info(f"[Amazon] Searching: {search_url}")

        soup = fetch_page(search_url, session)
        if not soup:
            logger.warning("[Amazon] Could not fetch search page")
            return NOT_AVAILABLE

        page_title = soup.find("title")
        if page_title:
            t = page_title.text.lower()
            if any(w in t for w in ["sign-in", "signin", "robot check", "captcha"]):
                logger.warning("[Amazon] Search page blocked")
                return NOT_AVAILABLE

        # ── Extract ASINs ─────────────────────────────────────────────────────
        from backend.scrapers.filter import is_accessory, relevance_score

        result_divs = soup.select("div[data-component-type='s-search-result'][data-asin]")
        asins: list[str] = []
        product_titles: dict[str, str] = {}

        for div in result_divs:
            asin = div.get("data-asin", "").strip()
            if not asin or len(asin) != 10:
                continue
            img_tag   = div.select_one("img")
            title_tag = div.select_one("h2 span")
            title = ""
            if img_tag and img_tag.get("alt"):
                title = img_tag.get("alt")
            elif title_tag:
                title = title_tag.get_text(strip=True)
            title = title.replace("Sponsored Ad - ", "").strip()[:120] or product_name
            if is_accessory(title):
                logger.debug(f"[Amazon] Skipping accessory: {title[:60]}")
                continue
            score = relevance_score(product_name, title)
            if score < 0.25:
                logger.debug(f"[Amazon] Low relevance ({score:.2f}): {title[:60]}")
                continue
            asins.append(asin)
            product_titles[asin] = title

        logger.info(f"[Amazon] {len(asins)} relevant ASINs found")
        if not asins:
            return NOT_AVAILABLE

        all_reviews: list[dict] = []

        for asin in asins[:8]:
            if len(all_reviews) >= self.max_reviews:
                break
            product_title = product_titles.get(asin, product_name)
            random_delay(0.2, 0.5)

            # Try dedicated review pages first (often blocked), then DP page
            candidate_urls = [
                f"{AMAZON_BASE}/product-reviews/{asin}?sortBy=recent&pageNumber=1",
                f"{AMAZON_BASE}/product-reviews/{asin}?sortBy=helpful&pageNumber=1",
                f"{AMAZON_BASE}/dp/{asin}",
            ]

            for url in candidate_urls:
                soup_r = fetch_page(url, session)
                if not soup_r:
                    continue

                pg_title = soup_r.find("title")
                if pg_title and any(w in pg_title.text.lower() for w in
                                     ["sign-in", "signin", "robot check", "captcha"]):
                    logger.info(f"[Amazon] {url[-50:]} blocked")
                    continue

                # ── Strategy 1: structured div[data-hook='review'] ─────────────
                review_divs = soup_r.select("div[data-hook='review']")
                if review_divs:
                    logger.info(f"[Amazon] {len(review_divs)} structured reviews from {url[-50:]}")
                    for div in review_divs:
                        r = self._parse_structured_review(div, product_title)
                        if r:
                            all_reviews.append(r)
                    break

                # ── Strategy 2: review-body spans with sibling star ratings ────
                reviews = self._extract_dp_reviews(soup_r, product_title)
                if reviews:
                    logger.info(f"[Amazon] {len(reviews)} DP reviews from {url[-50:]}")
                    all_reviews.extend(reviews)
                    break

        logger.info(f"[Amazon] Total real reviews: {len(all_reviews)}")
        if not all_reviews:
            return NOT_AVAILABLE
        return ScrapeResult(available=True, reviews=all_reviews[:self.max_reviews])

    def _parse_structured_review(self, div, product_title: str) -> dict | None:
        """Parse a div[data-hook='review'] into a review dict."""
        try:
            # Author
            author_tag = div.select_one("span.a-profile-name")
            author = author_tag.get_text(strip=True) if author_tag else get_random_name()

            # Rating
            rating = 3.0
            for sel in ["i[data-hook='review-star-rating'] span",
                        "i[data-hook='cmps-review-star-rating'] span"]:
                rt = div.select_one(sel)
                if rt:
                    m = re.search(r"[\d.]+", rt.get_text())
                    if m:
                        rating = float(m.group())
                        break

            # Body text
            body = div.select_one("span[data-hook='review-body'] span")
            text = body.get_text(strip=True) if body else ""
            if len(text) < 15:
                return None

            # Images — look for img tags inside the review div
            images = _extract_review_images_amazon(div)

            result = {
                "source":     "Amazon",
                "product":    product_title,
                "author":     author,
                "text":       text[:1000],
                "rating":     round(min(max(rating, 1.0), 5.0), 1),
                "scraped_at": datetime.utcnow(),
            }
            if images:
                import json
                result["images"] = json.dumps(images)
            return result
        except Exception as e:
            logger.debug(f"[Amazon] Parse error: {e}")
            return None

    def _extract_dp_reviews(self, soup, product_title: str) -> list[dict]:
        """
        Extract real reviews from the Amazon DP (product detail) page.
        The page contains 'review-body' spans; we walk up the DOM to find
        the nearest star rating in a sibling/ancestor node.
        """
        reviews = []
        seen = set()

        # Find all review body spans on the page
        body_spans = soup.select("span[data-hook='review-body'] span")
        if not body_spans:
            # Broader fallback: any span inside data-hook=review-body
            body_spans = soup.select("span[data-hook='review-body']")

        for body in body_spans:
            text = body.get_text(strip=True).replace("Read more", "").strip()
            if len(text) < 20 or text in seen:
                continue
            seen.add(text)

            # Walk up to find star rating, author, and images, but STOP at the review boundary
            rating = None
            author = get_random_name()
            container = body
            review_boundary = None

            for _ in range(8):
                container = container.parent
                if not container:
                    break
                
                # Stop walking up if we hit the boundary of a single review
                if container.name == "div" and (
                    container.get("data-hook") == "review" or 
                    str(container.get("id", "")).startswith("customer_review") or
                    "review" in container.get("class", [])
                ):
                    review_boundary = container
                    break

            # The best container to extract author/images from is the boundary, 
            # or if we couldn't find a boundary, just the local container we stopped at.
            target_container = review_boundary if review_boundary else container

            # Star rating
            if target_container:
                for star_sel in [
                    "i.a-icon-star span.a-icon-alt",
                    "span.a-icon-alt",
                    "i[class*='a-icon-star'] span",
                ]:
                    star = target_container.select_one(star_sel)
                    if star:
                        m = re.search(r"([\d.]+)\s*out of", star.get_text())
                        if m:
                            rating = float(m.group(1))
                            break

                # Author
                auth = target_container.select_one("span.a-profile-name")
                if auth and auth.get_text(strip=True):
                    author = auth.get_text(strip=True)

            # Images
            images = _extract_review_images_amazon(target_container) if target_container else []

            r = {
                "source":     "Amazon",
                "product":    product_title,
                "author":     author,
                "text":       text[:1000],
                "rating":     round(min(max(rating or 3.5, 1.0), 5.0), 1),
                "scraped_at": datetime.utcnow(),
            }
            if images:
                import json
                r["images"] = json.dumps(images)
            reviews.append(r)

        return reviews


def _check_amazon_availability(product_name: str) -> bool | None:
    try:
        session = get_session()
        query = urllib.parse.quote_plus(product_name)
        url = f"{AMAZON_BASE}/s?k={query}"
        resp = session.get(url, timeout=3, allow_redirects=True)
        if resp.status_code != 200:
            return None
        html = resp.text
        if 'data-component-type="s-search-result"' in html:
            return True
        if "did not match any products" in html.lower():
            return False
        return None
    except Exception:
        return None
