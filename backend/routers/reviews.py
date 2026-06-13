"""
Reviews Router — BuyWise
REST endpoints + WebSocket for real-time review streaming.
"""

import asyncio
import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger("buywise")

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.ml_pipeline import analyze_review, analyze_review_fast
from backend.models import Review
from backend.schemas import (
    AlertOut,
    ReviewOut,
    ScrapeResult,
    SentimentTrendPoint,
    StatsOut,
    TopicCount,
)
from backend.scraper import generate_mock_reviews
from backend.scrapers.amazon import AmazonScraper
from backend.scrapers.filter import filter_reviews, compute_search_analytics
from backend.scrapers.flipkart import FlipkartScraper
from backend.scrapers.g2 import G2Scraper
from backend.scrapers.trustpilot import TrustpilotScraper

router = APIRouter()

# Larger thread pool — scrapers + ML pipeline run in parallel
_executor = ThreadPoolExecutor(max_workers=12)


# ─── Search Request Schema ─────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    product: str
    sources: Optional[List[str]] = ["amazon", "flipkart", "trustpilot", "g2"]
    max_reviews_per_source: Optional[int] = 20


class SearchResponse(BaseModel):
    total: int
    by_source: dict
    not_available: List[str]
    reviews: List[ReviewOut]
    analytics: dict


# ─── Scraper Registry ──────────────────────────────────────────────────────────

SCRAPER_MAP = {
    "amazon": AmazonScraper,
    "flipkart": FlipkartScraper,
    "trustpilot": TrustpilotScraper,
    "g2": G2Scraper,
}

# ─── WebSocket Connection Manager ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(data, default=str))
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)


manager = ConnectionManager()


# ─── REST Endpoints ────────────────────────────────────────────────────────────

@router.get("/reviews", response_model=List[ReviewOut])
async def get_reviews(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Review).order_by(Review.scraped_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/reviews/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review))
    reviews = result.scalars().all()

    total = len(reviews)
    if total == 0:
        return StatsOut(
            total=0, positive=0, negative=0, neutral=0,
            fake_count=0, fake_percent=0.0, avg_sentiment_score=0.0, avg_rating=0.0
        )

    positive = sum(1 for r in reviews if r.sentiment == "POSITIVE")
    negative = sum(1 for r in reviews if r.sentiment == "NEGATIVE")
    neutral = sum(1 for r in reviews if r.sentiment == "NEUTRAL")
    fake_count = sum(1 for r in reviews if r.is_fake)
    scores = [r.sentiment_score for r in reviews if r.sentiment_score is not None]
    ratings = [r.rating for r in reviews if r.rating is not None]

    return StatsOut(
        total=total,
        positive=positive,
        negative=negative,
        neutral=neutral,
        fake_count=fake_count,
        fake_percent=round(fake_count / total * 100, 1) if total else 0.0,
        avg_sentiment_score=round(sum(scores) / len(scores), 3) if scores else 0.0,
        avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
    )


@router.get("/reviews/sentiment-trend", response_model=List[SentimentTrendPoint])
async def get_sentiment_trend(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).order_by(Review.scraped_at.asc()))
    reviews = result.scalars().all()

    daily: dict[str, dict] = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
    for r in reviews:
        if r.scraped_at and r.sentiment:
            date_str = r.scraped_at.strftime("%Y-%m-%d")
            sentiment_key = r.sentiment.lower()
            if sentiment_key in daily[date_str]:
                daily[date_str][sentiment_key] += 1

    return [
        SentimentTrendPoint(date=date, **counts)
        for date, counts in sorted(daily.items())
    ]


@router.get("/reviews/topics", response_model=List[TopicCount])
async def get_topics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review.topics))
    rows = result.scalars().all()

    topic_counts: dict[str, int] = defaultdict(int)
    for topics_json in rows:
        if topics_json:
            try:
                topics = json.loads(topics_json)
                for t in topics:
                    topic_counts[t.lower().strip()] += 1
            except Exception:
                pass

    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    return [TopicCount(topic=t, count=c) for t, c in sorted_topics[:15]]


@router.get("/alerts", response_model=List[AlertOut])
async def get_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review)
        .where((Review.sentiment == "NEGATIVE") | (Review.is_fake == True))  # noqa: E712
        .order_by(Review.scraped_at.desc())
        .limit(20)
    )
    return result.scalars().all()


@router.post("/scrape", response_model=ScrapeResult)
async def trigger_scrape(
    count: int = 30,
    db: AsyncSession = Depends(get_db),
):
    raw_reviews = generate_mock_reviews(count=count)
    added = 0

    for raw in raw_reviews:
        ml_results = analyze_review(raw["text"], raw.get("rating"))

        review = Review(
            source=raw["source"],
            product=raw["product"],
            author=raw["author"],
            text=raw["text"],
            rating=raw["rating"],
            scraped_at=raw["scraped_at"],
            images=raw.get("images"),
            **ml_results,
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)

        # Broadcast to all connected WebSocket clients
        await manager.broadcast({
            "type": "new_review",
            "data": {
                "id": review.id,
                "source": review.source,
                "product": review.product,
                "author": review.author,
                "text": review.text,
                "rating": review.rating,
                "sentiment": review.sentiment,
                "sentiment_score": review.sentiment_score,
                "topics": review.topics,
                "is_fake": review.is_fake,
                "fake_confidence": review.fake_confidence,
                "summary": review.summary,
                "scraped_at": review.scraped_at.isoformat() if review.scraped_at else None,
            },
        })
        added += 1

    await db.commit()
    return ScrapeResult(message="Scrape complete", reviews_added=added)


# ─── Product Search Endpoint ───────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
async def search_product_reviews(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Instant search: scrape → instant ML → return in ~2s.
    HuggingFace enrichment runs in background via WebSocket.
    """
    from backend.instant_ml import analyze_instant

    loop = asyncio.get_event_loop()
    sources = [s.lower() for s in (request.sources or list(SCRAPER_MAP.keys()))]
    product = request.product.strip()
    n = request.max_reviews_per_source or 6

    await manager.broadcast({"type": "search_started", "data": {"product": product, "sources": sources}})

    # ── Scrape all sources in parallel ────────────────────────────────────────
    from backend.scrapers.base import ScrapeResult

    async def run_scraper(source_key: str) -> ScrapeResult:
        if source_key not in SCRAPER_MAP:
            return ScrapeResult(available=None, reviews=[])
        scraper = SCRAPER_MAP[source_key]()
        scraper.max_reviews = n
        result: ScrapeResult = await loop.run_in_executor(_executor, scraper.safe_scrape, product)
        if result.available is not False:
            filtered = filter_reviews(product, result.reviews, min_score=0.20)
            logger.info(f"[Search] {source_key}: {len(result.reviews)} raw → {len(filtered)} after filter")
            return ScrapeResult(available=result.available, reviews=filtered)
        return result  # NOT_AVAILABLE — pass through unchanged

    scrape_results: list[ScrapeResult] = await asyncio.gather(*[run_scraper(s) for s in sources])

    # ── Categorise: available vs not_available ────────────────────────────────
    all_raw: list[dict] = []
    by_source: dict[str, int] = {}
    not_available: list[str] = []

    source_display = {s: SCRAPER_MAP[s].source_name if hasattr(SCRAPER_MAP[s], 'source_name') else s.capitalize()
                      for s in SCRAPER_MAP}

    for source_key, result in zip(sources, scrape_results):
        display = source_display.get(source_key, source_key.capitalize())
        if result.available is False:
            not_available.append(display)
            by_source[display] = 0
        else:
            by_source[display] = len(result.reviews)
            all_raw.extend(result.reviews)

    # ── Deduplicate raw reviews against each other ────────────────────────────
    seen_texts: set[str] = set()
    deduped_raw: list[dict] = []
    for raw in all_raw:
        key = raw["text"][:120].strip().lower()
        if key not in seen_texts:
            seen_texts.add(key)
            deduped_raw.append(raw)
    all_raw = deduped_raw

    # ── Instant ML + DB insert (with duplicate detection) ────────────────────
    # For duplicates we COLLECT the existing row so the response always has data.
    all_reviews: list[Review] = []
    newly_inserted: list[Review] = []

    for raw in all_raw:
        try:
            text_prefix = raw["text"][:60].strip()
            # Check if this review already exists
            dup_result = await db.execute(
                select(Review).where(
                    Review.source == raw["source"],
                    Review.text.like(text_prefix + "%")
                ).limit(1)
            )
            existing = dup_result.scalar()
            if existing:
                all_reviews.append(existing)  # Collect existing — don't re-insert
                continue

            # New review — run ML and insert
            ml = analyze_instant(raw["text"], raw.get("rating"))
            review = Review(
                source=raw["source"], product=raw["product"],
                author=raw.get("author", "Anonymous"), text=raw["text"],
                rating=raw.get("rating"),
                scraped_at=raw.get("scraped_at", datetime.utcnow()),
                images=raw.get("images"),
                **ml,
            )
            db.add(review)
            await db.flush()
            await db.refresh(review)
            all_reviews.append(review)
            newly_inserted.append(review)
        except Exception as e:
            logger.warning(f"[Search] Review error: {e}")

    await db.commit()

    # Final dedup on review id (safety net)
    seen_ids: set[int] = set()
    final_reviews: list[Review] = []
    for r in all_reviews:
        if r.id not in seen_ids:
            seen_ids.add(r.id)
            final_reviews.append(r)

    # Broadcast only newly inserted reviews
    for review in newly_inserted:
        await manager.broadcast({"type": "new_review", "data": {
            "id": review.id, "source": review.source, "product": review.product,
            "author": review.author, "text": review.text, "rating": review.rating,
            "sentiment": review.sentiment, "sentiment_score": review.sentiment_score,
            "topics": review.topics, "is_fake": review.is_fake,
            "fake_confidence": review.fake_confidence, "summary": review.summary,
            "scraped_at": review.scraped_at.isoformat() if review.scraped_at else None,
        }})

    # ── Fetch ALL reviews for this product from DB (Fallback/Cache) ───────────
    # This ensures that even if live scraping fails/blocks, we return existing data
    product_lower = product.lower()
    all_result = await db.execute(
        select(Review)
        .where(Review.product.ilike(f"%{product_lower[:30]}%"))
        .order_by(Review.scraped_at.desc())
        .limit(100)
    )
    db_reviews = all_result.scalars().all()

    # Combine newly scraped/identified reviews with DB fallback, deduplicating by ID
    for r in db_reviews:
        if r.id not in seen_ids:
            seen_ids.add(r.id)
            final_reviews.append(r)

    # ── Compute analytics ─────────────────────────────────────────────────────
    analytics = compute_search_analytics(product, final_reviews, by_source)

    await manager.broadcast({"type": "search_complete", "data": {
        "product": product, "total": len(final_reviews),
        "by_source": by_source, "not_available": not_available, "analytics": analytics,
    }})

    # ── Background HuggingFace enrichment (new reviews only) ─────────────────
    new_ids = [r.id for r in newly_inserted]
    asyncio.create_task(_enrich_reviews_background(new_ids, product))

    return SearchResponse(
        total=len(final_reviews),
        by_source=by_source,
        not_available=not_available,
        reviews=final_reviews,
        analytics=analytics,
    )


async def _enrich_reviews_background(review_ids: list[int], product: str):
    """
    Background task: re-runs HuggingFace models on saved reviews after search returns.
    Pushes enriched_review WebSocket events so the UI updates automatically.
    """
    if not review_ids:
        return
    try:
        from backend.database import AsyncSessionLocal
        from backend.ml_pipeline import analyze_review_fast
        loop = asyncio.get_event_loop()

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Review).where(Review.id.in_(review_ids)))
            reviews = result.scalars().all()

            for review in reviews:
                try:
                    ml = await loop.run_in_executor(
                        _executor, analyze_review_fast, review.text, review.rating
                    )
                    review.sentiment = ml["sentiment"]
                    review.sentiment_score = ml["sentiment_score"]
                    review.topics = ml["topics"]
                    review.is_fake = ml["is_fake"]
                    review.fake_confidence = ml["fake_confidence"]
                    review.summary = ml["summary"]
                    await manager.broadcast({"type": "enriched_review", "data": {
                        "id": review.id,
                        "sentiment": review.sentiment,
                        "sentiment_score": review.sentiment_score,
                        "topics": review.topics,
                        "is_fake": review.is_fake,
                        "summary": review.summary,
                    }})
                except Exception as e:
                    logger.warning(f"[Enrich] Review {review.id} failed: {e}")

            await db.commit()
            logger.info(f"[Enrich] Enriched {len(reviews)} reviews for '{product}'")
    except Exception as e:
        logger.warning(f"[Enrich] Background enrichment failed: {e}")


# ─── AI Report Endpoint ────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    product: str
    review_ids: List[int]


@router.post("/report")
async def generate_product_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a full AI Product Intelligence Report for a product.
    Fetches reviews by IDs from DB, runs the ML report engine, returns structured report.
    """
    from backend.report_engine import generate_report

    if not request.review_ids:
        return {"error": "No review IDs provided"}

    # Fetch reviews from DB
    result = await db.execute(
        select(Review).where(Review.id.in_(request.review_ids))
    )
    reviews = result.scalars().all()

    if not reviews:
        return {"error": "No reviews found for given IDs"}

    logger.info(f"[Report] Generating report for '{request.product}' — {len(reviews)} reviews")

    # Run in thread pool (blocking ML ops)
    loop = asyncio.get_event_loop()
    report = await loop.run_in_executor(
        _executor, generate_report, request.product, list(reviews)
    )

    # Broadcast report ready event
    await manager.broadcast({
        "type": "report_ready",
        "data": {"product": request.product, "score": report.get("score"), "verdict": report.get("verdict")},
    })

    return report


# ─── Model Train / Status Endpoints ───────────────────────────────────────────

@router.get("/model/status")
async def model_status():
    """Return current ML model training status."""
    try:
        from backend.ml_model.classifier import get_model_status
        return get_model_status()
    except Exception as e:
        return {"trained": False, "error": str(e)}


@router.post("/model/train")
async def trigger_model_training(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger ML model training on all reviews in DB.
    Runs in background thread pool so it doesn't block the API.
    """
    from backend.ml_model.classifier import train_model

    result_holder = await db.execute(select(Review))
    all_reviews = result_holder.scalars().all()

    if len(all_reviews) < 10:
        return {
            "success": False,
            "reason": f"Only {len(all_reviews)} reviews in DB. Need at least 10 to train.",
        }

    logger.info(f"[ModelTrain] Training on {len(all_reviews)} reviews...")
    loop = asyncio.get_event_loop()
    stats = await loop.run_in_executor(_executor, train_model, list(all_reviews))

    await manager.broadcast({
        "type": "model_trained",
        "data": stats,
    })
    return stats


async def _auto_train_model(db_session_factory, min_reviews: int = 20):
    """Background auto-training triggered after each search."""
    try:
        from backend.database import AsyncSessionLocal
        from backend.ml_model.classifier import train_model, get_model_status
        import asyncio

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Review))
            all_reviews = result.scalars().all()

        if len(all_reviews) < min_reviews:
            return

        status = get_model_status()
        trained_count = status.get("review_count", 0)
        # Only retrain if we have 20+ new reviews since last training
        if len(all_reviews) - trained_count < 20 and status.get("trained"):
            return

        logger.info(f"[AutoTrain] Auto-training on {len(all_reviews)} reviews...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, train_model, list(all_reviews))
        logger.info("[AutoTrain] Auto-training complete")
    except Exception as e:
        logger.warning(f"[AutoTrain] Failed: {e}")


# ─── WebSocket ─────────────────────────────────────────────────────────────────

@router.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
