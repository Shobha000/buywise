"""
Report Engine — BuyWise (v2 — Custom ML Model)
Generates a structured AI Product Intelligence Report from aggregated review data.
Now uses custom-trained ML model for enriched scoring + new report parameters.
"""

import json
import logging
import re
from collections import Counter, defaultdict

logger = logging.getLogger("buywise")


# ─── Lazy model imports ───────────────────────────────────────────────────────

def _get_sentiment_pipeline():
    try:
        from backend.ml_pipeline import _load_sentiment
        return _load_sentiment()
    except Exception:
        return None


def _get_summarizer():
    try:
        from backend.ml_pipeline import _load_summarizer
        return _load_summarizer()
    except Exception:
        return None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 15]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _safe_summarize(summarizer, text: str, max_len: int = 80, min_len: int = 30) -> str:
    try:
        word_count = len(text.split())
        if word_count < 40:
            return text[:300]
        actual_max = min(max_len, max(min_len + 1, word_count // 2))
        actual_min = min(min_len, actual_max - 1)
        result = summarizer(text[:1500], max_length=actual_max, min_length=actual_min, do_sample=False)
        return result[0]["summary_text"] if result else text[:300]
    except Exception as e:
        logger.warning(f"[ReportEngine] Summarizer error: {e}")
        return text[:300]


# ─── Pros / Cons Extraction ───────────────────────────────────────────────────

def _extract_pros_cons(reviews: list, sentiment_pipeline) -> tuple[list[str], list[str]]:
    pros_pool: Counter = Counter()
    cons_pool: Counter = Counter()

    for review in reviews:
        text = getattr(review, "text", "") or ""
        sentences = _split_sentences(text)
        for sent in sentences[:6]:
            if not sentiment_pipeline:
                sentiment = getattr(review, "sentiment", None)
                if sentiment == "POSITIVE":
                    pros_pool[_clean(sent)] += 1
                elif sentiment == "NEGATIVE":
                    cons_pool[_clean(sent)] += 1
                continue
            try:
                result = sentiment_pipeline(sent[:256])[0]
                label = result["label"].upper()
                score = result["score"]
                if label == "POSITIVE" and score > 0.75:
                    pros_pool[_clean(sent)] += 1
                elif label == "NEGATIVE" and score > 0.75:
                    cons_pool[_clean(sent)] += 1
            except Exception:
                pass

    def _deduplicate(pool: Counter, n: int) -> list[str]:
        seen: set[str] = set()
        result = []
        for sent, _ in pool.most_common(n * 3):
            words = set(sent.lower().split())
            if len(words & seen) / max(len(words), 1) < 0.6:
                result.append(sent)
                seen |= words
            if len(result) >= n:
                break
        return result

    pros = _deduplicate(pros_pool, 5)
    cons = _deduplicate(cons_pool, 5)

    if not pros:
        for r in reviews[:5]:
            if getattr(r, "sentiment", None) == "POSITIVE":
                t = getattr(r, "text", "") or ""
                if t:
                    pros.append(_clean(t[:120]) + "...")
            if len(pros) >= 3:
                break

    if not cons:
        for r in reviews[:5]:
            if getattr(r, "sentiment", None) == "NEGATIVE":
                t = getattr(r, "text", "") or ""
                if t:
                    cons.append(_clean(t[:120]) + "...")
            if len(cons) >= 3:
                break

    return pros[:5], cons[:5]


# ─── Score & Verdict ─────────────────────────────────────────────────────────

def _compute_score(positive: int, total: int, avg_rating: float, fake_percent: float,
                   quality_score: int = 50, authenticity_score: int = 50) -> int:
    if total == 0:
        return 50
    pos_rate   = positive / total
    rating_n   = avg_rating / 5.0
    trust      = 1.0 - (fake_percent / 100.0)
    quality_n  = quality_score / 100.0
    auth_n     = authenticity_score / 100.0
    # Weighted formula using ML-derived quality + authenticity
    raw = (pos_rate * 0.35) + (rating_n * 0.30) + (trust * 0.15) + (quality_n * 0.10) + (auth_n * 0.10)
    return round(raw * 100)


def _verdict(score: int) -> tuple[str, str, str]:
    if score >= 75:
        return "Recommended", "✅", "#22c55e"
    elif score >= 55:
        return "Proceed with Caution", "⚠️", "#f59e0b"
    elif score >= 35:
        return "Mixed Reviews", "🤔", "#ff6b35"
    return "Not Recommended", "❌", "#f43f5e"


def _confidence_label(total: int) -> str:
    if total >= 30: return "High"
    elif total >= 15: return "Medium"
    return "Low"


# ─── Main Report Generator ───────────────────────────────────────────────────

def generate_report(product: str, reviews: list) -> dict:
    """
    Generate a full AI Product Intelligence Report.
    Uses custom ML model + HuggingFace models for maximum accuracy.
    """
    logger.info(f"[ReportEngine] Generating report for '{product}' ({len(reviews)} reviews)")

    if not reviews:
        return _empty_report(product)

    # ── Basic Stats ───────────────────────────────────────────────────────────
    total          = len(reviews)
    pos_reviews    = [r for r in reviews if getattr(r, "sentiment", None) == "POSITIVE"]
    neg_reviews    = [r for r in reviews if getattr(r, "sentiment", None) == "NEGATIVE"]
    neu_reviews    = [r for r in reviews if getattr(r, "sentiment", None) == "NEUTRAL"]
    fake_reviews   = [r for r in reviews if getattr(r, "is_fake", False)]
    ratings        = [r.rating for r in reviews if r.rating is not None]
    avg_rating     = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
    fake_percent   = round(len(fake_reviews) / total * 100, 1)

    # ── Custom ML Model Scores ────────────────────────────────────────────────
    logger.info("[ReportEngine] Computing ML model scores...")
    try:
        from backend.ml_model.classifier import compute_report_scores, get_model_status
        ml_scores = compute_report_scores(reviews)
        model_status = get_model_status()
    except Exception as e:
        logger.warning(f"[ReportEngine] ML model error: {e}")
        ml_scores = _default_ml_scores()
        model_status = {"trained": False}

    quality_score      = ml_scores.get("review_quality_score", 50)
    authenticity_score = ml_scores.get("authenticity_score", 50)
    aspect_sentiment   = ml_scores.get("aspect_sentiment", {})
    price_value_score  = ml_scores.get("price_value_score")
    rec_confidence     = ml_scores.get("recommendation_confidence", 0)
    against_conf       = ml_scores.get("against_confidence", 0)
    trend              = ml_scores.get("review_trend", "Stable")

    # ── Score & Verdict ───────────────────────────────────────────────────────
    score = _compute_score(len(pos_reviews), total, avg_rating, fake_percent,
                           quality_score, authenticity_score)
    verdict_label, verdict_emoji, verdict_color = _verdict(score)

    # ── HuggingFace Models ────────────────────────────────────────────────────
    sentiment_pipeline = _get_sentiment_pipeline()
    summarizer         = _get_summarizer()

    # ── Pros / Cons ───────────────────────────────────────────────────────────
    logger.info("[ReportEngine] Extracting pros/cons...")
    pros, cons = _extract_pros_cons(reviews, sentiment_pipeline)

    # ── AI Summaries ─────────────────────────────────────────────────────────
    logger.info("[ReportEngine] Generating AI summaries...")
    love_text    = "Customers appreciate this product."
    dislike_text = "Some customers have reported issues."

    if pos_reviews:
        pos_texts = " ".join(r.text for r in pos_reviews[:8] if r.text)
        if summarizer and len(pos_texts.split()) > 30:
            love_text = _safe_summarize(summarizer, pos_texts, 100, 40)
        elif pos_texts:
            love_text = _clean(pos_texts[:400])

    if neg_reviews:
        neg_texts = " ".join(r.text for r in neg_reviews[:8] if r.text)
        if summarizer and len(neg_texts.split()) > 30:
            dislike_text = _safe_summarize(summarizer, neg_texts, 100, 40)
        elif neg_texts:
            dislike_text = _clean(neg_texts[:400])

    # ── Key Themes ────────────────────────────────────────────────────────────
    topic_counts: Counter = Counter()
    for r in reviews:
        if r.topics:
            try:
                for t in json.loads(r.topics):
                    topic_counts[t.lower().strip()] += 1
            except Exception:
                pass
    key_themes = [t for t, _ in topic_counts.most_common(8)]

    # ── Fake Risk ─────────────────────────────────────────────────────────────
    if fake_percent < 10:
        fake_risk = "Low"
    elif fake_percent < 25:
        fake_risk = "Medium"
    else:
        fake_risk = "High"

    # ── Per-Source Breakdown ──────────────────────────────────────────────────
    source_groups: dict[str, list] = defaultdict(list)
    for r in reviews:
        source_groups[r.source].append(r)

    source_breakdown = {}
    for src, rlist in source_groups.items():
        sp = sum(1 for r in rlist if getattr(r, "sentiment", None) == "POSITIVE")
        sn = sum(1 for r in rlist if getattr(r, "sentiment", None) == "NEGATIVE")
        sr = [r.rating for r in rlist if r.rating is not None]
        sf = sum(1 for r in rlist if getattr(r, "is_fake", False))
        source_breakdown[src] = {
            "total": len(rlist), "positive": sp, "negative": sn,
            "neutral": len(rlist) - sp - sn, "fake": sf,
            "avg_rating": round(sum(sr) / len(sr), 2) if sr else 0.0,
        }

    # ── Rating Distribution ───────────────────────────────────────────────────
    rating_dist: Counter = Counter()
    for r in reviews:
        if r.rating is not None:
            rating_dist[str(round(r.rating))] += 1
    rating_distribution = dict(sorted(rating_dist.items()))

    logger.info(f"[ReportEngine] Done. Score={score}, Verdict={verdict_label}, Trend={trend}")

    return {
        # ── Core ──
        "product":                  product,
        "score":                    score,
        "verdict":                  verdict_label,
        "verdict_emoji":            verdict_emoji,
        "verdict_color":            verdict_color,
        "total_reviews_analyzed":   total,
        "positive_count":           len(pos_reviews),
        "negative_count":           len(neg_reviews),
        "neutral_count":            len(neu_reviews),
        "avg_rating":               avg_rating,
        "confidence":               _confidence_label(total),
        # ── AI Text ──
        "pros":                     pros,
        "cons":                     cons,
        "what_customers_love":      love_text,
        "what_customers_dislike":   dislike_text,
        "key_themes":               key_themes,
        # ── Fake Analysis ──
        "fake_analysis": {
            "fake_count":    len(fake_reviews),
            "fake_percent":  fake_percent,
            "risk":          fake_risk,
        },
        # ── ML Model Scores (NEW) ──
        "aspect_sentiment":          aspect_sentiment,
        "review_quality_score":      quality_score,
        "authenticity_score":        authenticity_score,
        "price_value_score":         price_value_score,
        "recommendation_confidence": rec_confidence,
        "against_confidence":        against_conf,
        "review_trend":              trend,
        # ── Source & Distribution ──
        "source_breakdown":          source_breakdown,
        "rating_distribution":       rating_distribution,
        # ── Model Metadata ──
        "model_info": {
            "trained":       model_status.get("trained", False),
            "accuracy":      model_status.get("accuracy"),
            "review_count":  model_status.get("review_count", total),
            "version":       model_status.get("model_version", "v1"),
        },
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _empty_report(product: str) -> dict:
    return {
        "product": product, "score": 0, "verdict": "No Data",
        "verdict_emoji": "❓", "verdict_color": "#4a5568",
        "total_reviews_analyzed": 0, "confidence": "Low",
        "pros": [], "cons": [],
        "what_customers_love": "No reviews available.",
        "what_customers_dislike": "No reviews available.",
        "key_themes": [],
        "fake_analysis": {"fake_count": 0, "fake_percent": 0.0, "risk": "Unknown"},
        "aspect_sentiment": {}, "review_quality_score": 0, "authenticity_score": 0,
        "price_value_score": None, "recommendation_confidence": 0,
        "against_confidence": 0, "review_trend": "Stable",
        "source_breakdown": {}, "rating_distribution": {},
        "model_info": {"trained": False, "accuracy": None, "review_count": 0, "version": "v1"},
    }


def _default_ml_scores() -> dict:
    return {
        "aspect_sentiment": {}, "review_quality_score": 50,
        "authenticity_score": 50, "price_value_score": None,
        "recommendation_confidence": 0, "against_confidence": 0,
        "review_trend": "Stable",
    }
