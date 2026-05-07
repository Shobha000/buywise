"""
market_engine.py — BuyWise
Market-wide recommendation engine: returns the highest-rated genuine product
for any query + buy links across Amazon, Flipkart and other scraped sources.
"""
import os
import re
import logging
import sqlite3
import urllib.parse

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
DB_PATH  = os.path.join(BASE_DIR, "buywise.db")

MIN_REVIEWS = 5   # minimum genuine reviews required before recommending



def get_available_categories(n: int = 6) -> list:
    """Return top-N product names from DB (by review count) as suggestions."""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            """
            SELECT product, COUNT(*) AS cnt FROM reviews
            WHERE product IS NOT NULL AND product != ''
            GROUP BY product ORDER BY cnt DESC LIMIT 20
            """,
            conn,
        )
        conn.close()
    except Exception:
        return []
    seen, cats = set(), []
    for p in df["product"].tolist():
        first = p.split()[0].lower().strip("()[]")
        if first not in seen and len(first) > 2:
            seen.add(first)
            cats.append(p[:40] + ("…" if len(p) > 40 else ""))
        if len(cats) >= n:
            break
    return cats


SOURCE_PRIORITY = ["Amazon", "Flipkart", "G2", "Trustpilot", "Google Reviews", "Yelp"]

BUY_TEMPLATES = {
    "Amazon":         "https://www.amazon.in/s?k={q}",
    "Flipkart":       "https://www.flipkart.com/search?q={q}",
    "G2":             "https://www.g2.com/search?query={q}",
    "Trustpilot":     "https://www.trustpilot.com/search?query={q}",
    "Google Reviews": "https://www.google.com/search?q={q}+buy",
    "Yelp":           "https://www.yelp.com/search?find_desc={q}",
}


def _make_buy_url(source: str, product_name: str, stored_url: str | None = None) -> str:
    """Return the best purchase URL for a product on a given source."""
    if stored_url and str(stored_url).startswith("http"):
        return stored_url
    q = urllib.parse.quote_plus(product_name[:80])
    template = BUY_TEMPLATES.get(source, "https://www.google.com/search?q={q}+buy")
    return template.format(q=q)


def _fallback_links(query: str) -> dict:
    """Generate search links for any query on major shopping platforms."""
    q = urllib.parse.quote_plus(query[:80])
    return {
        "Amazon":   f"https://www.amazon.in/s?k={q}",
        "Flipkart": f"https://www.flipkart.com/search?q={q}",
        "Google":   f"https://www.google.com/search?q={q}+buy+online",
    }


def get_market_recommendation(query: str) -> dict:
    """
    Market-wide product recommendation engine.

    Pipeline:
    1. Match query tokens against all products in DB (every source)
    2. Filter out fake reviews
    3. Rank by: avg_genuine_rating (70%) + review_volume (30%)
    4. Return best product + buy links for every platform that has it
       (+ always include Amazon & Flipkart fallback search links)

    Returns dict with:
      found=True        -> full recommendation with buy_links
      found=False       -> not in DB, with fallback search links
      found='low_data'  -> matched but < MIN_REVIEWS genuine reviews
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            """
            SELECT product, source, rating, is_fake, source_url
            FROM reviews
            WHERE product IS NOT NULL AND product != ''
            """,
            conn,
        )
        conn.close()
    except Exception as exc:
        log.warning(f"Market recommendation DB error: {exc}")
        return {"found": False, "suggestions": [], "buy_links": _fallback_links(query)}

    if df.empty:
        return {"found": False, "suggestions": [], "buy_links": _fallback_links(query)}

    # ── Token matching ────────────────────────────────────────────
    stop = {
        "the", "a", "an", "is", "are", "for", "of", "to", "in", "and",
        "which", "what", "best", "good", "buy", "recommend", "suggest",
        "me", "should", "i", "can", "you", "give", "show", "tell", "find",
        "want", "need", "please", "get", "product", "item", "thing",
        "one", "some", "any", "will", "would", "could", "use", "where",
        "purchase", "order", "shop", "market", "price", "cheap", "expensive",
    }
    tokens = [
        t.strip("?.,!") for t in query.lower().split()
        if len(t) > 2 and t.strip("?.,!") not in stop
    ]

    if tokens:
        mask = df["product"].str.lower().apply(
            lambda name: any(tok in name for tok in tokens)
        )
        matched = df[mask]
    else:
        matched = df

    if matched.empty:
        return {
            "found":       False,
            "suggestions": get_available_categories(6),
            "buy_links":   _fallback_links(query),
        }

    # ── Aggregate per (product, source), filter fakes ─────────────
    genuine = matched[matched["is_fake"] != 1].copy()
    if genuine.empty:
        genuine = matched.copy()

    # Per-product stats across all sources
    agg = (
        genuine.groupby("product")
        .agg(
            avg_rating=("rating", "mean"),
            genuine_count=("rating", "count"),
        )
        .reset_index()
    )

    if agg.empty or int(agg["genuine_count"].max()) < MIN_REVIEWS:
        top = agg.nlargest(1, "avg_rating").iloc[0]["product"] if not agg.empty else ""
        return {
            "found":        "low_data",
            "product":      str(top)[:60],
            "review_count": int(agg["genuine_count"].max()) if not agg.empty else 0,
            "suggestions":  get_available_categories(6),
            "buy_links":    _fallback_links(query),
        }

    # ── Score: rating 70% + volume 30% ───────────────────────────
    max_r   = agg["avg_rating"].max() or 5
    max_vol = agg["genuine_count"].max() or 1
    agg["score"] = (
        (agg["avg_rating"] / max_r) * 0.7
        + (agg["genuine_count"] / max_vol) * 0.3
    )

    best_row = agg.nlargest(1, "score").iloc[0]
    name     = best_row["product"]
    display  = name if len(name) <= 60 else name[:57] + "…"

    # ── Collect buy links per source ──────────────────────────────
    product_rows = matched[matched["product"] == name].drop_duplicates("source")
    buy_links: dict = {}
    for _, row in product_rows.iterrows():
        src = row["source"]
        url = _make_buy_url(src, name, row.get("source_url"))
        buy_links[src] = url

    # Always ensure Amazon + Flipkart are present
    q = urllib.parse.quote_plus(name[:80])
    if "Amazon" not in buy_links:
        buy_links["Amazon"] = f"https://www.amazon.in/s?k={q}"
    if "Flipkart" not in buy_links:
        buy_links["Flipkart"] = f"https://www.flipkart.com/search?q={q}"

    # Sort by preferred source order
    buy_links = {
        k: buy_links[k]
        for k in SOURCE_PRIORITY + [s for s in buy_links if s not in SOURCE_PRIORITY]
        if k in buy_links
    }

    return {
        "found":        True,
        "product":      display,
        "full_name":    name,
        "rating":       round(float(best_row["avg_rating"]), 1),
        "review_count": int(best_row["genuine_count"]),
        "trust_score":  round(float(best_row["score"]) * 100, 1),
        "buy_links":    buy_links,
        "reason": (
            f"**{display}** is the highest-rated product for your search — "
            f"⭐ {round(float(best_row['avg_rating']), 1)}/5 from "
            f"{int(best_row['genuine_count'])} genuine, verified reviews "
            f"(market score: {round(float(best_row['score'])*100, 1)}/100)."
        ),
    }
