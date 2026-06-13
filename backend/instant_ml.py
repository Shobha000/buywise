"""
Instant ML — BuyWise
Loads trained Kaggle model if available, falls back to rule-based heuristics.
< 1ms per review with rule-based; ~5ms with trained model.
"""

import json
import re
import logging
from pathlib import Path

log = logging.getLogger("BuyWise.ML")

# ─── Paths ────────────────────────────────────────────────────────────────────
_BASE        = Path(__file__).parent
_MODEL_PATH  = _BASE / "reviewguard_model.pkl"
_VECT_PATH   = _BASE / "reviewguard_vectorizer.pkl"
_SENT_MODEL  = _BASE / "sentiment_model.pkl"
_SENT_VECT   = _BASE / "sentiment_vectorizer.pkl"

# ─── Lazy-load trained models ─────────────────────────────────────────────────
_fake_clf   = None
_fake_vect  = None
_sent_clf   = None
_sent_vect  = None
_model_loaded = False

def _load_models():
    global _fake_clf, _fake_vect, _sent_clf, _sent_vect, _model_loaded
    if _model_loaded:
        return
    _model_loaded = True
    try:
        import joblib
        if _MODEL_PATH.exists() and _VECT_PATH.exists():
            _fake_clf  = joblib.load(_MODEL_PATH)
            _fake_vect = joblib.load(_VECT_PATH)
            log.info("✅  Loaded trained fake-detection model (Kaggle Amazon Reviews)")
        if _SENT_MODEL.exists() and _SENT_VECT.exists():
            _sent_clf  = joblib.load(_SENT_MODEL)
            _sent_vect = joblib.load(_SENT_VECT)
            log.info("✅  Loaded trained sentiment model (Kaggle Amazon Reviews)")
    except Exception as exc:
        log.warning(f"⚠️  Could not load trained models ({exc}). Using rule-based fallback.")
        _fake_clf = _fake_vect = _sent_clf = _sent_vect = None


# ─── Rule-based word lists (fallback) ────────────────────────────────────────
_POS = {
    "great","excellent","amazing","love","perfect","best","fantastic","wonderful",
    "awesome","good","happy","recommend","helpful","nice","superb","outstanding",
    "brilliant","impressed","satisfied","enjoy","smooth","fast","crisp","sharp",
    "bright","solid","premium","durable","reliable","worth","pleased","clean",
    "beautiful","flawless","impressive","quality","reasonable","affordable",
}
_NEG = {
    "terrible","awful","bad","worst","hate","poor","horrible","useless",
    "disappointed","broken","waste","refund","never","avoid","scam","faulty",
    "defective","unhappy","frustrating","fail","failed","slow","lag","laggy",
    "issue","problem","damage","cracked","stopped","overpriced","expensive",
    "heating","hot","drain","dead","scratch","return","regret","pathetic",
}
_FAKE_PHRASES = [
    "best product ever","absolutely love","highly recommend","five stars",
    "amazing product","must buy","great value","works perfectly",
    "exactly as described","no complaints",
]
_TOPICS = [
    "battery","camera","display","performance","design","price","software",
    "build","charging","speed","quality","screen","storage","sound","heat",
    "support","delivery","packaging","value","durability","update","gaming",
]


def _sentiment_rule(text: str) -> tuple[str, float]:
    words = set(re.findall(r"\b\w+\b", text.lower()))
    pos = len(words & _POS)
    neg = len(words & _NEG)
    total = pos + neg
    if total == 0:
        return "NEUTRAL", 0.55
    score = pos / total
    if score >= 0.55:
        return "POSITIVE", round(min(0.5 + score * 0.5, 0.99), 3)
    if score <= 0.45:
        return "NEGATIVE", round(min(0.5 + (1 - score) * 0.5, 0.99), 3)
    return "NEUTRAL", 0.55


def _fake_rule(text: str) -> tuple[bool, float]:
    score = 0.0
    words = text.split()
    if len(words) < 8:           score += 0.3
    if text.count("!") >= 3:     score += 0.2
    caps = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    if caps > 0.4:               score += 0.2
    lower = text.lower()
    matches = sum(1 for p in _FAKE_PHRASES if p in lower)
    if matches >= 2:             score += 0.25
    if re.search(r"(.)\1{3,}", text): score += 0.1
    score = min(score, 1.0)
    return score >= 0.45, round(score, 3)


def _topics_fast(text: str) -> list[str]:
    lower = text.lower()
    found = [t for t in _TOPICS if t in lower]
    return found[:5] if found else ["quality"]


# ─── ML-powered detection (uses trained Kaggle model) ─────────────────────────
def _fake_ml(text: str) -> tuple[bool, float]:
    """Use trained model if available, otherwise fall back to rules."""
    _load_models()
    if _fake_clf is None or _fake_vect is None:
        return _fake_rule(text)
    try:
        from scipy.sparse import hstack as sp_hstack, csr_matrix
        import numpy as np

        # Vectorizers saved as tuple (word_vect, char_vect)
        if isinstance(_fake_vect, (list, tuple)):
            word_vect, char_vect = _fake_vect
            word_X = word_vect.transform([text])
            char_X = char_vect.transform([text])
            tfidf_X = sp_hstack([word_X, char_X], format="csr")
        else:
            tfidf_X = _fake_vect.transform([text])

        # 12 meta-features
        words   = text.split()
        wcount  = max(len(words), 1)
        chars   = max(len(text), 1)
        excl    = text.count("!")
        quest   = text.count("?")
        caps_r  = sum(1 for c in text if c.isupper()) / chars
        uniq_r  = len(set(words)) / wcount
        avg_wl  = sum(len(w) for w in words) / wcount
        repeat  = 1 if re.search(r"(.{2,})\1{2,}", text.lower()) else 0
        punct_d = sum(1 for c in text if c in ".,;:!?") / chars
        sent_cnt= len(re.split(r"[.!?]+", text.strip()))
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            pol, subj = blob.sentiment.polarity, blob.sentiment.subjectivity
        except Exception:
            pol, subj = 0.0, 0.5

        meta_X = csr_matrix(np.array(
            [[wcount, excl, quest, caps_r, uniq_r, avg_wl, repeat,
              punct_d, sent_cnt, pol, subj, len(text)]],
            dtype=np.float32
        ))
        X = sp_hstack([tfidf_X, meta_X], format="csr")

        proba = _fake_clf.predict_proba(X)[0][1]
        return proba >= 0.45, round(float(proba), 3)
    except Exception as exc:
        log.debug(f"ML fake detection failed ({exc}), falling back to rules.")
        return _fake_rule(text)


def _sentiment_ml(text: str) -> tuple[str, float]:
    """Use trained sentiment model if available."""
    _load_models()
    if _sent_clf is None or _sent_vect is None:
        return _sentiment_rule(text)
    try:
        from scipy.sparse import hstack as sp_hstack

        # Handle tuple (word_vect, char_vect)
        if isinstance(_sent_vect, (list, tuple)):
            word_vect, char_vect = _sent_vect
            word_X = word_vect.transform([text])
            char_X = char_vect.transform([text])
            X = sp_hstack([word_X, char_X], format="csr")
        else:
            X = _sent_vect.transform([text])

        pred  = _sent_clf.predict(X)[0]
        proba = _sent_clf.predict_proba(X)[0]
        label = "POSITIVE" if pred == 1 else "NEGATIVE"
        confidence = round(float(max(proba)), 3)
        return label, confidence
    except Exception as exc:
        log.debug(f"ML sentiment failed ({exc}), falling back to rules.")
        return _sentiment_rule(text)


# ─── Public API ───────────────────────────────────────────────────────────────
def analyze_instant(text: str, rating: float | None = None) -> dict:
    """
    Analyze a review using the trained Kaggle model (if available)
    or rule-based heuristics. Returns in < 10ms.
    """
    sentiment, sent_score = _sentiment_ml(text)
    is_fake, fake_conf    = _fake_ml(text)
    topics                = _topics_fast(text)

    # Summary = first 2 sentences, max 200 chars
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    summary   = " ".join(sentences[:2])[:200]

    return {
        "sentiment":       sentiment,
        "sentiment_score": sent_score,
        "topics":          json.dumps(topics),
        "is_fake":         is_fake,
        "fake_confidence": fake_conf,
        "summary":         summary,
    }
