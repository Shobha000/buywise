from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReviewOut(BaseModel):
    id: int
    source: str
    product: str
    author: str
    text: str
    rating: Optional[float] = None
    scraped_at: datetime
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    topics: Optional[str] = None
    is_fake: Optional[bool] = None
    fake_confidence: Optional[float] = None
    summary: Optional[str] = None
    images: Optional[str] = None   # JSON list of image URLs e.g. '["https://..."]'

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    total: int
    positive: int
    negative: int
    neutral: int
    fake_count: int
    fake_percent: float
    avg_sentiment_score: float
    avg_rating: float


class SentimentTrendPoint(BaseModel):
    date: str
    positive: int
    negative: int
    neutral: int


class TopicCount(BaseModel):
    topic: str
    count: int


class ScrapeResult(BaseModel):
    message: str
    reviews_added: int


class AlertOut(BaseModel):
    id: int
    text: str
    sentiment: str
    is_fake: bool
    source: str
    product: str
    scraped_at: datetime
    model_config = {"from_attributes": True}
