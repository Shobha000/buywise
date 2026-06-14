import os
import re
import json
import logging
import sqlite3

import numpy as np
import pandas as pd
import joblib
from textblob import TextBlob
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier

log = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(BASE_DIR, "reviewguard_model.pkl")
VECTORIZER_PATH = os.path.join(BASE_DIR, "reviewguard_vectorizer.pkl")
DATA_PATH = os.path.join(BASE_DIR, "reviews.csv")
DB_PATH = os.path.join(BASE_DIR, "buywise.db")

# ─── Feature Engineering ──────────────────────────────────────────────────────
def extra_features(text: str) -> list:
    """
    8-dimensional meta-feature vector — must match train_with_kaggle.py exactly.
    [word_count, exclamations, caps_ratio, unique_ratio, avg_word_len,
     repeat_pattern, polarity, subjectivity]
    """
    words   = text.split()
    wcount  = len(words)
    excl    = text.count("!")
    caps_r  = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    uniq_r  = len(set(words)) / max(wcount, 1)
    avg_wl  = sum(len(w) for w in words) / max(wcount, 1)
    repeat  = 1 if re.search(r"(.{2,})\1{2,}", text.lower()) else 0
    try:
        blob = TextBlob(text)
        polarity     = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
    except Exception:
        polarity, subjectivity = 0.0, 0.5
    return [wcount, excl, caps_r, uniq_r, avg_wl, repeat, polarity, subjectivity]

# ─── Training System ──────────────────────────────────────────────────────────
def train_model():
    """
    Minimal fallback trainer using a small synthetic dataset.
    For production quality, run:  python -m backend.train_with_kaggle
    """
    log.warning(
        "⚠️  Falling back to synthetic training data.\n"
        "    For a production model run: python -m backend.train_with_kaggle"
    )
    data = {
        "review": [
            # Genuine
            "Amazing chair, very comfortable for long hours.",
            "The build quality is excellent and worth every penny.",
            "Great value for money, easy to assemble.",
            "Best ergonomic chair I've owned so far.",
            "The lumbar support is fantastic and relieves back pain.",
            "Fast shipping and well packaged, arrived in perfect condition.",
            "Solid performance with no issues after 6 months of daily use.",
            "Highly recommend this office chair for remote workers.",
            "Beautiful design and very sturdy construction.",
            "Comfortable seating and smooth wheels on hardwood.",
            "Really happy with this purchase, exceeded expectations.",
            "Excellent customer support resolved my issue quickly.",
            "The fabric is breathable and high quality.",
            "Perfect for my home office setup and long work sessions.",
            "Good adjustment options for height and tilt angle.",
            # Fake/Suspicious
            "Best product ever!!!! Must buy now wow wow",
            "FREE IPHONE CLICK HERE!!!",
            "AMAZING AMAZING AMAZING BUY NOW!!!",
            "Worst product, scam scam scam!!",
            "DO NOT BUY THIS SCAM SCAM!!",
            "i love it i love it i love it i love it",
            "win a free prize by clicking this link!!!!",
            "LEGIT 100% WORKS NO SCAM",
            "This is the best thing in the world ever!!!!!!!!!",
            "BUY NOW BUY NOW BUY NOW",
            "!!!!!!!!! BEST DEAL EVER !!!!!!!!!",
            "Click here for 90% discount now!!",
        ] * 10,
        "label": ([0] * 15 + [1] * 12) * 10
    }
    df = pd.DataFrame(data)
    vectorizer = TfidfVectorizer(
        stop_words="english", max_features=5_000, ngram_range=(1, 2)
    )
    text_X  = vectorizer.fit_transform(df["review"]).toarray()
    meta_X  = np.array([extra_features(x) for x in df["review"]])
    X       = np.hstack((text_X, meta_X))
    y       = df["label"].values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model = RandomForestClassifier(
        n_estimators=200, max_depth=15,
        class_weight="balanced", random_state=42
    )
    model.fit(X_train, y_train)
    joblib.dump(model,      MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    log.info("✅  Synthetic fallback model trained and saved.")
    return model, vectorizer

# ─── Global State ─────────────────────────────────────────────────────────────
_model = None
_vectorizer = None

def _get_model():
    global _model, _vectorizer
    if _model is None:
        try:
            _model = joblib.load(MODEL_PATH)
            _vectorizer = joblib.load(VECTORIZER_PATH)
        except:
            _model, _vectorizer = train_model()
    return _model, _vectorizer

# ─── Inference ─────────────────────────────────────────────────────────────
def analyze_review(text: str) -> dict:
    from scipy.sparse import hstack as sp_hstack, csr_matrix
    model, vectorizer = _get_model()
    tfidf   = vectorizer.transform([text])          # sparse
    meta    = csr_matrix(np.array(extra_features(text), dtype=np.float32).reshape(1, -1))
    X_input = sp_hstack([tfidf, meta], format="csr")

    pred      = model.predict(X_input)[0]
    probs     = model.predict_proba(X_input)[0]
    fake_prob = float(probs[1])

    polarity = TextBlob(text).sentiment.polarity
    sent = "Positive" if polarity > 0.2 else "Negative" if polarity < -0.2 else "Neutral"

    return {
        "review":                 text,
        "sentiment":             sent,
        "fake_review_prediction": "Suspicious Review" if pred == 1 else "Likely Genuine",
        "fake_probability":      round(fake_prob * 100, 2),
        "trust_score":           round(100 - fake_prob * 100, 2),
        "is_fake":               bool(pred == 1),
    }


# ─── DB helpers ────────────────────────────────────────────────────────────
def _load_all_products() -> pd.DataFrame:
    """Return aggregated product stats from the DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            """
            SELECT product,
                   COUNT(*)        AS review_count,
                   AVG(rating)     AS avg_rating,
                   SUM(CASE WHEN is_fake = 0 THEN 1 ELSE 0 END) AS genuine_count,
                   AVG(sentiment_score) AS avg_sentiment
            FROM reviews
            WHERE product IS NOT NULL AND product != ''
            GROUP BY product
            HAVING review_count >= 1
            ORDER BY review_count DESC
            """,
            conn,
        )
        conn.close()
        return df
    except Exception as exc:
        log.warning(f"DB load error: {exc}")
        return pd.DataFrame()


def get_db_stats() -> dict:
    """High-level stats about what is in the DB — used by chatbot."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reviews")
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT product) FROM reviews")
        products = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM reviews WHERE is_fake = 1")
        fake_count = cur.fetchone()[0]
        cur.execute("SELECT AVG(rating) FROM reviews")
        avg_rating = cur.fetchone()[0] or 0
        conn.close()
        return {
            "total_reviews":  total,
            "total_products": products,
            "fake_count":     fake_count,
            "avg_rating":     round(avg_rating, 2),
        }
    except Exception:
        return {}


MIN_REVIEWS = 5   # minimum reviews needed before a product can be recommended


def search_products(query: str) -> tuple[pd.DataFrame, bool]:
    """
    Fuzzy keyword search.
    Returns (matched_df, found) where found=False means no product in DB
    matched the query — caller should NOT fall back to unrelated products.
    """
    products_df = _load_all_products()
    if products_df.empty:
        return products_df, False

    # Tokens to skip — pure intent/filler words, not product keywords
    stop = {
        "the", "a", "an", "is", "are", "for", "of", "to", "in", "and",
        "which", "what", "best", "good", "buy", "recommend", "suggest",
        "me", "should", "i", "can", "you", "give", "show", "tell", "find",
        "want", "need", "please", "get", "product", "item", "thing",
        "one", "some", "any", "will", "would", "could", "use",
    }
    tokens = [
        t.strip("?.,!") for t in query.lower().split()
        if len(t) > 2 and t.strip("?.,!") not in stop
    ]

    if not tokens:
        # Generic query with no product keyword — return all
        return products_df, True

    mask = products_df["product"].str.lower().apply(
        lambda name: any(tok in name for tok in tokens)
    )
    matched = products_df[mask]

    if matched.empty:
        # No product in DB matches — return empty, found=False
        return pd.DataFrame(), False

    return matched, True


def get_available_categories(n: int = 6) -> list[str]:
    """Return top-N category hints from actual DB products (for helpful error messages)."""
    df = _load_all_products()
    if df.empty:
        return []
    # Sort by review count, take top N, extract first meaningful word
    top = df.nlargest(n * 2, "review_count")["product"].tolist()
    seen, cats = set(), []
    for p in top:
        first = p.split()[0].lower().strip("()[]")
        if first not in seen and len(first) > 2:
            seen.add(first)
            cats.append(p[:40] + ("…" if len(p) > 40 else ""))
        if len(cats) >= n:
            break
    return cats


def get_recommendation(query: str) -> dict:
    """
    Find the best-scoring product matching the query.
    Score = avg_rating (60%) + genuine_ratio (40%).

    Returns dict with:
      found=True  → normal recommendation
      found=False → category not in DB (with suggestions)
      found='low_data' → matched but not enough reviews
    """
    df, found = search_products(query)

    if not found or df.empty:
        return {
            "found": False,
            "suggestions": get_available_categories(6),
        }

    # Enforce minimum review count for trustworthy recommendations
    qualified = df[df["review_count"] >= MIN_REVIEWS]
    if qualified.empty:
        # Matched products exist but all have too few reviews
        best_name = df.nlargest(1, "review_count").iloc[0]["product"]
        return {
            "found": "low_data",
            "product": best_name[:60],
            "review_count": int(df["review_count"].max()),
            "suggestions": get_available_categories(6),
        }

    qualified = qualified.copy()
    qualified["genuine_ratio"] = (
        qualified["genuine_count"] / qualified["review_count"].clip(lower=1)
    )
    max_r = qualified["avg_rating"].max() or 5
    qualified["score"] = (
        (qualified["avg_rating"] / max_r) * 0.6
        + qualified["genuine_ratio"] * 0.4
    )

    best    = qualified.sort_values("score", ascending=False).iloc[0]
    name    = best["product"]
    display = name if len(name) <= 60 else name[:57] + "…"

    return {
        "found":         True,
        "product":       display,
        "full_name":     name,
        "rating":        round(float(best["avg_rating"]), 1),
        "review_count":  int(best["review_count"]),
        "genuine_count": int(best["genuine_count"]),
        "trust_score":   round(float(best["genuine_ratio"]) * 100, 1),
        "reason": (
            f"Based on {int(best['review_count'])} verified reviews, "
            f"**{display}** scores {round(float(best['score'])*100, 1)}/100 on our "
            f"trust-weighted ranking — {round(float(best['genuine_ratio'])*100, 1)}% "
            f"genuine reviews with an average rating of "
            f"{round(float(best['avg_rating']), 1)}/5."
        ),
    }
