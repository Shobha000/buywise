"""
Seed script — populate the DB with initial mock reviews for demo purposes.
Run from project root: python -m backend.seed_data
"""

import asyncio
import logging

from backend.database import AsyncSessionLocal, init_db
from backend.ml_pipeline import analyze_review
from backend.models import Review
from backend.scraper import generate_mock_reviews

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")


async def seed(count: int = 80):
    await init_db()
    raw_reviews = generate_mock_reviews(count=count)
    logger.info(f"Seeding {count} reviews...")

    async with AsyncSessionLocal() as db:
        for i, raw in enumerate(raw_reviews):
            ml = analyze_review(raw["text"], raw.get("rating"))
            review = Review(
                source=raw["source"],
                product=raw["product"],
                author=raw["author"],
                text=raw["text"],
                rating=raw["rating"],
                scraped_at=raw["scraped_at"],
                **ml,
            )
            db.add(review)
            if (i + 1) % 20 == 0:
                logger.info(f"  Processed {i + 1}/{count}")
        await db.commit()

    logger.info("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
