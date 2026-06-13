"""
ML Pipeline — BuyWise
Loads HuggingFace models once at startup and exposes simple analyze() function.
Falls back to rule-based methods if models aren't installed.
"""

import json
import logging
import re
import threading
from typing import Any

logger = logging.getLogger(__name__)

# ─── Model globals (loaded lazily, thread-safe) ───────────────────────────────
_sentiment_pipeline = None
_summarizer_pipeline = None
_kw_model = None
_models_loaded = False
_load_lock = threading.Lock()


def _load_models():
    global _sentiment_pipeline, _summarizer_pipeline, _kw_model, _models_loaded
    if _models_loaded:
        return
    with _load_lock:          # Only ONE thread loads; others wait here
        if _models_loaded:    # Double-check after acquiring lock
            return
        try:
            from transformers import pipeline
            logger.info("Loading sentiment model...")
            _sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                truncation=True,
                max_length=512,
            )
            logger.info("Loading summarization model...")
            _summarizer_pipeline = pipeline(
                "summarization",
                model="sshleifer/distilbart-cnn-12-6",
                truncation=True,
            )
            logger.info("Loading KeyBERT model...")
            from keybert import KeyBERT
            _kw_model = KeyBERT(model="all-MiniLM-L6-v2")
            logger.info("All ML models loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load HuggingFace models ({e}). Using rule-based fallback.")
        finally:
            _models_loaded = True  # Always mark done (even on failure)


# ─── Sentiment ───────────────────────────────────────────────────────────────

def _rule_based_sentiment(text: str) -> tuple[str, float]:
    """Fallback rule-based sentiment using keyword counting."""
    positive_words = {
        "great", "excellent", "amazing", "love", "perfect", "best", "fantastic",
        "wonderful", "awesome", "good", "happy", "recommend", "helpful", "nice",
        "superb", "outstanding", "brilliant", "impressed", "satisfied", "enjoy"
    }
    negative_words = {
        "terrible", "awful", "bad", "worst", "hate", "poor", "horrible", "useless",
        "disappointed", "broken", "waste", "refund", "never", "avoid", "scam",
        "faulty", "defective", "unhappy", "frustrating", "fail"
    }
    tokens = re.findall(r"\b\w+\b", text.lower())
    pos = sum(1 for t in tokens if t in positive_words)
    neg = sum(1 for t in tokens if t in negative_words)
    total = pos + neg
    if total == 0:
        return "NEUTRAL", 0.5
    score = pos / total
    if score >= 0.6:
        return "POSITIVE", round(score, 3)
    elif score <= 0.4:
        return "NEGATIVE", round(1 - score, 3)
    return "NEUTRAL", 0.5


def analyze_sentiment(text: str) -> tuple[str, float]:
    if _sentiment_pipeline:
        try:
            result = _sentiment_pipeline(text[:512])[0]
            label = result["label"]  # POSITIVE / NEGATIVE
            score = round(result["score"], 4)
            return label, score
        except Exception as e:
            logger.warning(f"Sentiment model error: {e}")
    return _rule_based_sentiment(text)


# ─── Fake Detection ───────────────────────────────────────────────────────────

def detect_fake(text: str, rating: float | None) -> tuple[bool, float]:
    """
    Heuristic-based fake review detection.
    Signals: very short text, excessive punctuation/caps, generic phrases, extreme rating.
    """
    fake_score = 0.0
    reasons = 0

    word_count = len(text.split())
    if word_count < 8:
        fake_score += 0.3
        reasons += 1

    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps_ratio > 0.4:
        fake_score += 0.2
        reasons += 1

    exclamation_count = text.count("!")
    if exclamation_count >= 3:
        fake_score += 0.15
        reasons += 1

    generic_phrases = [
        "best product ever", "absolutely love", "highly recommend", "five stars",
        "amazing product", "must buy", "great value", "works perfectly",
        "exactly as described", "no complaints"
    ]
    lower_text = text.lower()
    matches = sum(1 for phrase in generic_phrases if phrase in lower_text)
    if matches >= 2:
        fake_score += 0.25
        reasons += 1

    # Repetitive characters
    if re.search(r"(.)\1{3,}", text):
        fake_score += 0.1

    fake_score = min(fake_score, 1.0)
    is_fake = fake_score >= 0.45
    return is_fake, round(fake_score, 3)


# ─── Topic Extraction ─────────────────────────────────────────────────────────

_FALLBACK_TOPICS = [
    "quality", "price", "delivery", "service", "packaging",
    "design", "performance", "value", "support", "durability"
]


def extract_topics(text: str) -> list[str]:
    if _kw_model:
        try:
            keywords = _kw_model.extract_keywords(
                text, keyphrase_ngram_range=(1, 2), stop_words="english", top_n=5
            )
            return [kw[0] for kw in keywords]
        except Exception as e:
            logger.warning(f"KeyBERT error: {e}")

    # Fallback: match known topic words
    lower = text.lower()
    found = [t for t in _FALLBACK_TOPICS if t in lower]
    return found[:5] if found else ["general"]


# ─── Summarization ────────────────────────────────────────────────────────────

def summarize_text(text: str) -> str:
    if len(text.split()) < 30:
        return text  # Too short to summarize

    if _summarizer_pipeline:
        try:
            result = _summarizer_pipeline(text[:1024], max_length=60, min_length=15, do_sample=False)
            return result[0]["summary_text"]
        except Exception as e:
            logger.warning(f"Summarizer error: {e}")

    # Fallback: return first 2 sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:2])


# ─── Master Analysis Function ─────────────────────────────────────────────────

def analyze_review(text: str, rating: float | None = None) -> dict[str, Any]:
    """Full ML pipeline — sentiment + topics + fake + summarization. Use for reports."""
    _load_models()
    sentiment, sentiment_score = analyze_sentiment(text)
    is_fake, fake_confidence = detect_fake(text, rating)
    topics = extract_topics(text)
    summary = summarize_text(text)
    return {
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "topics": json.dumps(topics),
        "is_fake": is_fake,
        "fake_confidence": fake_confidence,
        "summary": summary,
    }


def analyze_review_fast(text: str, rating: float | None = None) -> dict[str, Any]:
    """
    Fast ML pipeline for search results — skips slow DistilBART summarization.
    Uses 2-sentence rule-based summary instead. ~10x faster than full pipeline.
    """
    _load_models()
    sentiment, sentiment_score = analyze_sentiment(text)
    is_fake, fake_confidence = detect_fake(text, rating)
    topics = extract_topics(text)
    # Fast summary: first 2 sentences, no heavy model
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    summary = " ".join(sentences[:2])[:200] if sentences else text[:200]
    return {
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "topics": json.dumps(topics),
        "is_fake": is_fake,
        "fake_confidence": fake_confidence,
        "summary": summary,
    }


def _load_sentiment():
    """Return the loaded sentiment pipeline (for reuse in report engine)."""
    _load_models()
    return _sentiment_pipeline


def _load_summarizer():
    """Return the loaded summarizer pipeline (for reuse in report engine)."""
    _load_models()
    return _summarizer_pipeline
