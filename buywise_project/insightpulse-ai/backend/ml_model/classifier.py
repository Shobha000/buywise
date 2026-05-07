"""
Review Analysis Classifier — BuyWise Custom ML Model
Trains on collected review data using TF-IDF + LogisticRegression.
Auto-saves and auto-loads from disk.
"""

import json
import logging
import os
import pickle
import threading
from datetime import datetime

import numpy as np

logger = logging.getLogger("buywise")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "saved", "review_model.pkl")
META_PATH  = os.path.join(os.path.dirname(__file__), "saved", "model_meta.json")

_model_lock = threading.Lock()
_model_cache = None
_model_meta_cache = None

# ─── Model Status ─────────────────────────────────────────────────────────────

def get_model_status() -> dict:
    meta = _load_meta()
    return {
        "trained": meta.get("trained", False),
        "review_count": meta.get("review_count", 0),
        "accuracy": meta.get("accuracy", None),
        "last_trained": meta.get("last_trained", None),
        "model_version": meta.get("model_version", "v1"),
        "features_used": meta.get("features_used", []),
    }


def _load_meta() -> dict:
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"trained": False}


def _save_meta(meta: dict):
    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2, default=str)


def _load_model():
    global _model_cache, _model_meta_cache
    if _model_cache is not None:
        return _model_cache
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                _model_cache = pickle.load(f)
            _model_meta_cache = _load_meta()
            logger.info(f"[MLModel] Loaded model from disk ({_model_meta_cache.get('review_count', '?')} reviews)")
            return _model_cache
        except Exception as e:
            logger.warning(f"[MLModel] Could not load model: {e}")
    return None


def _save_model(model):
    global _model_cache
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    _model_cache = model
    logger.info("[MLModel] Model saved to disk")


# ─── Training ─────────────────────────────────────────────────────────────────

def train_model(reviews: list) -> dict:
    """
    Train a TF-IDF + LogisticRegression model on collected reviews.
    'reviews' is a list of Review ORM objects.
    Returns training stats dict.
    """
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier, VotingClassifier
    from sklearn.model_selection import cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import LinearSVC

    from backend.ml_model.review_features import extract_features

    logger.info(f"[MLModel] Starting training on {len(reviews)} reviews")

    # ── Prepare data ──────────────────────────────────────────────────────────
    texts, labels, feature_rows = [], [], []

    for r in reviews:
        text = getattr(r, "text", "") or ""
        sentiment = getattr(r, "sentiment", None)
        if not text or not sentiment or sentiment not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
            continue

        label = {"POSITIVE": 2, "NEUTRAL": 1, "NEGATIVE": 0}[sentiment]
        texts.append(text)
        labels.append(label)

        feats = extract_features(
            review_text=text,
            rating=getattr(r, "rating", None),
            sentiment=sentiment,
            sentiment_score=getattr(r, "sentiment_score", None),
            is_fake=getattr(r, "is_fake", False),
            scraped_at=getattr(r, "scraped_at", None),
            topics_json=getattr(r, "topics", None),
        )
        feature_rows.append(list(feats.values()))

    if len(texts) < 10:
        logger.warning(f"[MLModel] Not enough data to train ({len(texts)} samples). Need at least 10.")
        return {"success": False, "reason": f"Only {len(texts)} labeled reviews. Need at least 10.", "count": len(texts)}

    texts_arr = np.array(texts)
    labels_arr = np.array(labels)
    features_arr = np.array(feature_rows, dtype=float)
    feature_names = list(extract_features("test").keys())

    # ── Build Pipeline ────────────────────────────────────────────────────────
    # Combine TF-IDF (text) with engineered features
    from sklearn.pipeline import FeatureUnion
    from sklearn.base import BaseEstimator, TransformerMixin

    class TextSelector(BaseEstimator, TransformerMixin):
        def fit(self, X, y=None): return self
        def transform(self, X): return [x[0] for x in X]  # extract text

    class FeatureSelector(BaseEstimator, TransformerMixin):
        def fit(self, X, y=None): return self
        def transform(self, X):
            return np.array([x[1] for x in X], dtype=float)

    # Pack (text, features) as input
    combined_input = list(zip(texts, features_arr.tolist()))

    union = FeatureUnion([
        ("tfidf", Pipeline([
            ("select", TextSelector()),
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=5000,
                sublinear_tf=True,
                min_df=1,
            )),
        ])),
        ("numeric", Pipeline([
            ("select", FeatureSelector()),
            ("scale", StandardScaler()),
        ])),
    ])

    pipeline = Pipeline([
        ("features", union),
        ("clf", LogisticRegression(
            C=1.0, max_iter=500, multi_class="multinomial",
            solver="lbfgs", random_state=42,
        )),
    ])

    # ── Train & Evaluate ──────────────────────────────────────────────────────
    n_splits = min(3, len(set(labels_arr)))  # at least 3 samples per class needed
    try:
        scores = cross_val_score(pipeline, combined_input, labels_arr, cv=n_splits, scoring="accuracy")
        accuracy = round(float(scores.mean()), 4)
        logger.info(f"[MLModel] CV Accuracy: {accuracy:.2%} ± {scores.std():.2%}")
    except Exception as e:
        logger.warning(f"[MLModel] CV failed: {e} — training without CV")
        accuracy = None

    pipeline.fit(combined_input, labels_arr)

    with _model_lock:
        _save_model(pipeline)

    # ── Save metadata ─────────────────────────────────────────────────────────
    meta = {
        "trained": True,
        "review_count": len(texts),
        "accuracy": accuracy,
        "last_trained": datetime.utcnow().isoformat(),
        "model_version": "v1",
        "features_used": feature_names,
        "label_map": {"0": "NEGATIVE", "1": "NEUTRAL", "2": "POSITIVE"},
        "class_distribution": {
            "POSITIVE": int(np.sum(labels_arr == 2)),
            "NEUTRAL":  int(np.sum(labels_arr == 1)),
            "NEGATIVE": int(np.sum(labels_arr == 0)),
        },
    }
    _save_meta(meta)

    logger.info(f"[MLModel] Training complete. Accuracy={accuracy}, Reviews={len(texts)}")
    return {
        "success": True,
        "review_count": len(texts),
        "accuracy": accuracy,
        "class_distribution": meta["class_distribution"],
    }


# ─── Inference ────────────────────────────────────────────────────────────────

def predict_review(text: str, rating: float | None = None,
                   sentiment_score: float | None = None) -> dict | None:
    """
    Use the trained model to predict sentiment + quality for a review.
    Returns dict with model_sentiment, model_confidence, quality_score.
    Returns None if model not trained.
    """
    from backend.ml_model.review_features import extract_features

    model = _load_model()
    if model is None:
        return None

    try:
        feats = extract_features(text, rating=rating, sentiment_score=sentiment_score)
        feature_values = list(feats.values())
        input_data = [(text, feature_values)]

        proba = model.predict_proba(input_data)[0]
        label_idx = int(np.argmax(proba))
        label_map = {0: "NEGATIVE", 1: "NEUTRAL", 2: "POSITIVE"}
        confidence = round(float(proba[label_idx]), 4)

        return {
            "model_sentiment": label_map[label_idx],
            "model_confidence": confidence,
            "quality_score": round(feats["quality_score"] * 100),
            "authenticity_score": round(feats["authenticity_score"] * 100),
            "sentiment_polarity": feats["sentiment_polarity"],
        }
    except Exception as e:
        logger.warning(f"[MLModel] Prediction failed: {e}")
        return None


def compute_report_scores(reviews: list) -> dict:
    """
    Compute all model-based scores for report generation.
    Returns enriched score dict.
    """
    from backend.ml_model.review_features import (
        extract_aspect_sentiments,
        extract_review_trend,
        RECOMMEND_PHRASES,
        AGAINST_PHRASES,
    )

    texts = [getattr(r, "text", "") or "" for r in reviews]
    ratings = [getattr(r, "rating", None) for r in reviews]

    # ── Aspect Sentiments ─────────────────────────────────────────────────────
    aspect_sentiment = extract_aspect_sentiments(texts, ratings)

    # ── Review Quality ────────────────────────────────────────────────────────
    from backend.ml_model.review_features import extract_features
    quality_scores, authenticity_scores = [], []
    for r in reviews:
        feats = extract_features(
            review_text=getattr(r, "text", "") or "",
            rating=getattr(r, "rating", None),
            sentiment=getattr(r, "sentiment", None),
            sentiment_score=getattr(r, "sentiment_score", None),
            is_fake=getattr(r, "is_fake", False),
            scraped_at=getattr(r, "scraped_at", None),
            topics_json=getattr(r, "topics", None),
        )
        quality_scores.append(feats["quality_score"])
        authenticity_scores.append(feats["authenticity_score"])

    avg_quality = round(sum(quality_scores) / max(len(quality_scores), 1) * 100)
    avg_authenticity = round(sum(authenticity_scores) / max(len(authenticity_scores), 1) * 100)

    # ── Price-Value Score ─────────────────────────────────────────────────────
    price_signals = []
    for r in reviews:
        text_lower = (getattr(r, "text", "") or "").lower()
        from backend.ml_model.review_features import PRICE_POSITIVE, PRICE_NEGATIVE
        words = set(text_lower.split())
        pos = sum(1 for w in words if w in PRICE_POSITIVE)
        neg = sum(1 for w in words if w in PRICE_NEGATIVE)
        if pos + neg > 0:
            price_signals.append((pos - neg) / (pos + neg))
    price_value_score = round((sum(price_signals) / max(len(price_signals), 1) + 1) / 2 * 100) if price_signals else None

    # ── Recommendation Confidence ─────────────────────────────────────────────
    rec_count, against_count = 0, 0
    for r in reviews:
        text_lower = (getattr(r, "text", "") or "").lower()
        if any(p in text_lower for p in RECOMMEND_PHRASES):
            rec_count += 1
        elif any(p in text_lower for p in AGAINST_PHRASES):
            against_count += 1
    total = len(reviews)
    recommendation_confidence = round(rec_count / max(total, 1) * 100)
    against_confidence = round(against_count / max(total, 1) * 100)

    # ── Review Trend ──────────────────────────────────────────────────────────
    reviews_with_dates = [
        {"sentiment": getattr(r, "sentiment", None), "scraped_at": getattr(r, "scraped_at", None)}
        for r in reviews
    ]
    trend = extract_review_trend(reviews_with_dates)

    # ── Model Status ──────────────────────────────────────────────────────────
    model_status = get_model_status()

    return {
        "aspect_sentiment": aspect_sentiment,
        "review_quality_score": avg_quality,
        "authenticity_score": avg_authenticity,
        "price_value_score": price_value_score,
        "recommendation_confidence": recommendation_confidence,
        "against_confidence": against_confidence,
        "review_trend": trend,
        "model_trained": model_status["trained"],
        "model_accuracy": model_status.get("accuracy"),
    }
