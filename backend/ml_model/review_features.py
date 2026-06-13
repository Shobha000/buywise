"""
Review Feature Extractor — BuyWise Custom ML Model
Converts raw review data into numerical feature vectors for ML training.
"""

import json
import math
import re
from datetime import datetime


# ─── Aspect Keyword Dictionary ────────────────────────────────────────────────
ASPECT_KEYWORDS = {
    "battery": ["battery", "charge", "charging", "mah", "drain", "standby", "backup", "power"],
    "camera":  ["camera", "photo", "picture", "video", "zoom", "lens", "megapixel", "mp", "selfie", "image quality"],
    "display": ["display", "screen", "amoled", "lcd", "brightness", "resolution", "refresh", "panel", "hdr", "nits"],
    "performance": ["performance", "speed", "fast", "slow", "lag", "processor", "cpu", "gpu", "ram", "smooth", "gaming", "multitask"],
    "design":  ["design", "build", "look", "feel", "premium", "slim", "thin", "weight", "colour", "color", "finish", "metal", "glass"],
    "price":   ["price", "cost", "value", "worth", "expensive", "cheap", "affordable", "budget", "money", "rupee", "rs", "$", "overpriced"],
    "software": ["software", "os", "android", "ios", "update", "ui", "ux", "interface", "app", "feature", "bloatware", "bug"],
    "build":   ["durability", "durable", "sturdy", "solid", "robust", "scratch", "drop", "waterproof", "ip68", "quality"],
}

# Positive / negative aspect words
POSITIVE_WORDS = {
    "excellent", "great", "good", "amazing", "awesome", "fantastic", "superb", "outstanding",
    "perfect", "love", "best", "impressive", "brilliant", "wonderful", "smooth", "fast",
    "crisp", "sharp", "bright", "solid", "premium", "durable", "reliable", "highly recommend",
    "satisfied", "happy", "pleased", "recommend", "worth",
}
NEGATIVE_WORDS = {
    "bad", "terrible", "poor", "worst", "horrible", "awful", "disappointing", "slow",
    "lag", "laggy", "issue", "problem", "broken", "defective", "waste", "avoid",
    "regret", "damaged", "useless", "overpriced", "expensive", "not worth", "fail",
    "failed", "crash", "crashing", "heating", "hot", "drain", "dead",
}

PRICE_POSITIVE = {"worth", "affordable", "value", "budget", "cheap", "bargain", "reasonable"}
PRICE_NEGATIVE = {"expensive", "overpriced", "costly", "waste", "not worth"}

RECOMMEND_PHRASES = [
    "highly recommend", "would recommend", "must buy", "go for it",
    "worth buying", "best buy", "excellent choice", "great purchase",
]
AGAINST_PHRASES = [
    "do not recommend", "don't recommend", "avoid", "stay away",
    "waste of money", "not worth", "regret buying",
]


def extract_features(review_text: str, rating: float | None = None,
                     sentiment: str | None = None,
                     sentiment_score: float | None = None,
                     is_fake: bool = False,
                     scraped_at: datetime | None = None,
                     topics_json: str | None = None) -> dict:
    """
    Extract 20+ engineered features from a single review.
    Returns a dict of feature_name → numeric value.
    """
    text = review_text or ""
    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)
    char_count = len(text)

    # ── Text Statistics ───────────────────────────────────────────────────────
    avg_word_len = sum(len(w) for w in words) / max(word_count, 1)
    exclamation_count = text.count("!")
    question_count = text.count("?")
    caps_ratio = sum(1 for c in text if c.isupper()) / max(char_count, 1)
    digit_ratio = sum(1 for c in text if c.isdigit()) / max(char_count, 1)
    sentence_count = max(len(re.findall(r"[.!?]+", text)), 1)
    avg_sentence_len = word_count / sentence_count

    # ── Sentiment Features ────────────────────────────────────────────────────
    pos_word_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_word_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    sentiment_polarity = (pos_word_count - neg_word_count) / max(word_count, 1)
    rating_norm = (rating or 3.0) / 5.0
    sentiment_conf = sentiment_score or 0.5

    # ── Price-Value Signal ────────────────────────────────────────────────────
    price_pos = sum(1 for w in words if w in PRICE_POSITIVE)
    price_neg = sum(1 for w in words if w in PRICE_NEGATIVE)
    price_value_signal = (price_pos - price_neg) / max(price_pos + price_neg + 1, 1)

    # ── Recommendation Signal ─────────────────────────────────────────────────
    recommends = any(phrase in text_lower for phrase in RECOMMEND_PHRASES)
    discourages = any(phrase in text_lower for phrase in AGAINST_PHRASES)
    recommendation_signal = 1.0 if recommends else (-1.0 if discourages else 0.0)

    # ── Review Quality ────────────────────────────────────────────────────────
    # Quality = length in useful range + specificity (mentions aspects) + no spam patterns
    length_score = min(word_count / 50.0, 1.0)  # saturates at 50 words
    aspect_mentions = sum(
        1 for kws in ASPECT_KEYWORDS.values()
        if any(kw in text_lower for kw in kws)
    )
    specificity_score = min(aspect_mentions / 4.0, 1.0)
    spam_score = min((exclamation_count / max(word_count, 1)) * 10, 1.0)
    quality_score = (length_score * 0.4 + specificity_score * 0.4 + (1 - spam_score) * 0.2)

    # ── Authenticity Signal ───────────────────────────────────────────────────
    # Short, all-caps, excessive punctuation → less authentic
    too_short = 1.0 if word_count < 5 else 0.0
    too_caps = 1.0 if caps_ratio > 0.5 else 0.0
    is_fake_flag = 1.0 if is_fake else 0.0
    authenticity_score = max(0.0, 1.0 - (too_short * 0.4 + too_caps * 0.3 + is_fake_flag * 0.3))

    # ── Topic Diversity ───────────────────────────────────────────────────────
    topic_count = 0
    if topics_json:
        try:
            topic_count = len(json.loads(topics_json))
        except Exception:
            pass

    return {
        # Text stats
        "word_count": word_count,
        "char_count": char_count,
        "avg_word_len": round(avg_word_len, 3),
        "exclamation_count": exclamation_count,
        "question_count": question_count,
        "caps_ratio": round(caps_ratio, 4),
        "digit_ratio": round(digit_ratio, 4),
        "sentence_count": sentence_count,
        "avg_sentence_len": round(avg_sentence_len, 2),
        # Sentiment
        "pos_word_count": pos_word_count,
        "neg_word_count": neg_word_count,
        "sentiment_polarity": round(sentiment_polarity, 4),
        "rating_norm": round(rating_norm, 4),
        "sentiment_conf": round(sentiment_conf, 4),
        # Signals
        "price_value_signal": round(price_value_signal, 4),
        "recommendation_signal": recommendation_signal,
        "aspect_mentions": aspect_mentions,
        "topic_count": topic_count,
        # Derived
        "quality_score": round(quality_score, 4),
        "authenticity_score": round(authenticity_score, 4),
    }


def extract_aspect_sentiments(review_texts: list[str], ratings: list[float | None]) -> dict:
    """
    Aggregate aspect-level sentiments across all reviews.
    Returns dict: aspect → score (0-100).
    """
    aspect_scores: dict[str, list[float]] = {k: [] for k in ASPECT_KEYWORDS}
    avg_rating = sum(r for r in ratings if r) / max(sum(1 for r in ratings if r), 1)

    for text, rating in zip(review_texts, ratings):
        text_lower = text.lower()
        words = set(text_lower.split())
        pos = sum(1 for w in words if w in POSITIVE_WORDS)
        neg = sum(1 for w in words if w in NEGATIVE_WORDS)
        # Base polarity for this review
        polarity = (pos - neg) / max(pos + neg + 1, 1)
        # Use rating as strong signal if available
        rating_signal = ((rating or avg_rating) - 3.0) / 2.0  # -1 to +1

        for aspect, keywords in ASPECT_KEYWORDS.items():
            mentioned = any(kw in text_lower for kw in keywords)
            if not mentioned:
                continue
            # Aspect score: blend text polarity + rating signal
            score = (polarity * 0.5 + rating_signal * 0.5 + 1.0) / 2.0  # 0-1
            aspect_scores[aspect].append(score)

    result = {}
    for aspect, scores in aspect_scores.items():
        if scores:
            result[aspect] = round(sum(scores) / len(scores) * 100)
        else:
            result[aspect] = None  # not mentioned → show as N/A

    return result


def extract_review_trend(reviews_with_dates: list[dict]) -> str:
    """
    Compare sentiment of recent reviews vs older reviews.
    Returns "Improving", "Declining", or "Stable".
    """
    if len(reviews_with_dates) < 4:
        return "Stable"

    sorted_reviews = sorted(
        reviews_with_dates,
        key=lambda r: r.get("scraped_at") or datetime.min,
    )
    midpoint = len(sorted_reviews) // 2
    older = sorted_reviews[:midpoint]
    recent = sorted_reviews[midpoint:]

    def avg_pos(group):
        pos = sum(1 for r in group if r.get("sentiment") == "POSITIVE")
        return pos / max(len(group), 1)

    older_rate = avg_pos(older)
    recent_rate = avg_pos(recent)
    diff = recent_rate - older_rate

    if diff > 0.12:
        return "Improving"
    elif diff < -0.12:
        return "Declining"
    return "Stable"
