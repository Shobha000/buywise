import json
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped

from backend.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source: Mapped[str] = Column(String(100), nullable=False, default="Unknown")
    product: Mapped[str] = Column(String(255), nullable=False, default="General")
    author: Mapped[str] = Column(String(100), nullable=False, default="Anonymous")
    text: Mapped[str] = Column(Text, nullable=False)
    rating: Mapped[float] = Column(Float, nullable=True)
    scraped_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    source_url: Mapped[str] = Column(Text, nullable=True)   # product page URL
    images: Mapped[str] = Column(Text, nullable=True)        # JSON list of image URLs

    # ML Outputs
    sentiment: Mapped[str] = Column(String(20), nullable=True)       # POSITIVE / NEGATIVE / NEUTRAL
    sentiment_score: Mapped[float] = Column(Float, nullable=True)    # 0.0 - 1.0
    topics: Mapped[str] = Column(Text, nullable=True)                # JSON list e.g. '["price", "quality"]'
    is_fake: Mapped[bool] = Column(Boolean, nullable=True, default=False)
    fake_confidence: Mapped[float] = Column(Float, nullable=True)
    summary: Mapped[str] = Column(Text, nullable=True)

    @property
    def topics_list(self) -> list[str]:
        if self.topics:
            try:
                return json.loads(self.topics)
            except Exception:
                return []
        return []
