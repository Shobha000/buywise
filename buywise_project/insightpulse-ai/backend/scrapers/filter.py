"""
Review Relevance Filter — BuyWise
Ensures search results are about the exact product, not accessories or related items.
"""

import re
from collections import defaultdict

# ─── Accessory Blocklist ──────────────────────────────────────────────────────
ACCESSORY_KEYWORDS = {
    "case", "cases", "cover", "covers", "back cover", "flip cover",
    "screen protector", "tempered glass", "glass protector",
    "charger", "charging", "cable", "adapter", "adaptor",
    "pouch", "skin", "skins", "bumper", "bumpers",
    "stand", "holder", "wallet", "sleeve", "bag",
    "earphone", "earbud", "headphone", "headset",
    "lens", "camera lens", "ring light",
    "power bank", "powerbank",
    "grip", "pop socket", "popsocket",
    "screen guard", "privacy filter",
    "stylus", "pen",
    "mount", "car mount",
    "for iphone", "for samsung", "for redmi", "for oneplus", "for pixel",
    "compatible with",
}

_STOPWORDS = {"the", "a", "an", "and", "or", "for", "with", "of", "in", "on", "at", "to"}
_MODEL_PATTERN = re.compile(r"\d+|\bmini\b|\bpro\b|\bmax\b|\bultra\b|\bplus\b|\blite\b|\bair\b|\bfe\b|\bse\b")


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_accessory(product_title: str) -> bool:
    title_lower = product_title.lower()
    for kw in ACCESSORY_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", title_lower):
            return True
    return False


def relevance_score(query: str, product_title: str) -> float:
    """
    Score how relevant a product title is to the search query (0.0 – 1.0).
    Model numbers and variant suffixes (mini, pro, ultra…) are weighted heaviest.
    Brand matches are also strictly required for generic queries.
    """
    q_norm = _normalize(query)
    t_norm = _normalize(product_title)

    # Exact phrase match — perfect
    if q_norm in t_norm:
        return 1.0

    q_words = set(q_norm.split()) - _STOPWORDS
    if not q_words:
        return 0.5

    # Word overlap
    t_words = set(t_norm.split()) - _STOPWORDS
    word_score = len(q_words & t_words) / len(q_words)

    # Model-specific tokens (numbers + variant names) — most critical
    model_tokens = _MODEL_PATTERN.findall(q_norm)
    
    # Brand / first keyword of query
    q_significant = [w for w in q_norm.split() if w not in _STOPWORDS and not w.isdigit()]
    brand_score = 1.0 if (q_significant and q_significant[0] in t_norm) else 0.0

    if model_tokens:
        model_matched = sum(1 for tok in model_tokens if tok in t_norm)
        model_score = model_matched / len(model_tokens)
        if model_score == 0:
            return 0.1  # highly penalize missing models
        return round(word_score * 0.3 + model_score * 0.5 + brand_score * 0.2, 3)
    else:
        # No model constraint → accept by words and brand alone
        return round(word_score * 0.6 + brand_score * 0.4, 3)


def filter_reviews(query: str, reviews: list[dict], min_score: float = 0.3) -> list[dict]:
    """
    Filter reviews to only include those about the exact searched product.
    - Removes accessories (case, cover, charger…)
    - Removes low-relevance products using relevance_score
    - Mock reviews (product title == query) always pass without scoring
    """
    q_norm = _normalize(query)
    model_tokens = _MODEL_PATTERN.findall(q_norm)
    filtered = []

    for review in reviews:
        product_title = review.get("product", "")
        t_norm = _normalize(product_title)

        # Mock-generated reviews: product title IS the query → always pass
        if t_norm == q_norm:
            filtered.append(review)
            continue

        # Remove accessories
        if is_accessory(product_title):
            continue

        # Score and accept if above threshold
        score = relevance_score(query, product_title)
        if score >= min_score:
            filtered.append(review)
            continue

        # Hard fallback: if EVERY model-specific token from query is in title → accept
        # (catches "Apple iPhone 12 mini 64GB" when query is "iphone 12 mini")
        if model_tokens and all(tok in t_norm for tok in model_tokens):
            filtered.append(review)

    return filtered


# ─── Search Analytics ─────────────────────────────────────────────────────────

def compute_search_analytics(query: str, reviews: list, by_source_raw: dict) -> dict:
    """
    Compute analytics over the final filtered review set.
    """
    import json

    total = len(reviews)
    if total == 0:
        return {
            "total": 0,
            "positive": 0, "negative": 0, "neutral": 0,
            "fake_count": 0, "fake_percent": 0.0,
            "avg_rating": 0.0, "avg_sentiment_score": 0.0,
            "by_source_stats": {}, "top_topics": [], "sentiment_distribution": [],
        }

    positive = sum(1 for r in reviews if getattr(r, "sentiment", None) == "POSITIVE")
    negative = sum(1 for r in reviews if getattr(r, "sentiment", None) == "NEGATIVE")
    neutral  = sum(1 for r in reviews if getattr(r, "sentiment", None) == "NEUTRAL")
    fake_count = sum(1 for r in reviews if getattr(r, "is_fake", False))
    ratings = [r.rating for r in reviews if r.rating is not None]
    scores  = [r.sentiment_score for r in reviews if r.sentiment_score is not None]

    source_groups: dict[str, list] = defaultdict(list)
    for r in reviews:
        source_groups[r.source].append(r)

    by_source_stats: dict = {}
    sentiment_distribution = []
    for src, rlist in source_groups.items():
        sp = sum(1 for r in rlist if getattr(r, "sentiment", None) == "POSITIVE")
        sn = sum(1 for r in rlist if getattr(r, "sentiment", None) == "NEGATIVE")
        su = sum(1 for r in rlist if getattr(r, "sentiment", None) == "NEUTRAL")
        sf = sum(1 for r in rlist if getattr(r, "is_fake", False))
        sr = [r.rating for r in rlist if r.rating is not None]
        by_source_stats[src] = {
            "total": len(rlist), "positive": sp, "negative": sn,
            "neutral": su, "fake": sf,
            "avg_rating": round(sum(sr) / len(sr), 2) if sr else 0.0,
        }
        sentiment_distribution.append({"source": src, "positive": sp, "negative": sn, "neutral": su})

    topic_counts: dict[str, int] = defaultdict(int)
    for r in reviews:
        if r.topics:
            try:
                for t in json.loads(r.topics):
                    topic_counts[t.lower().strip()] += 1
            except Exception:
                pass
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total": total,
        "positive": positive, "negative": negative, "neutral": neutral,
        "fake_count": fake_count,
        "fake_percent": round(fake_count / total * 100, 1),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
        "avg_sentiment_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "by_source_stats": by_source_stats,
        "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
        "sentiment_distribution": sentiment_distribution,
    }
