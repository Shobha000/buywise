"""
BuyWise — FastAPI Backend Entry Point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers.reviews import router as reviews_router
from backend.routers.chatbot import router as chatbot_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("buywise")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    # Prevent threading conflicts that cause segfaults on Mac
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    logger.info("Starting BuyWise backend...")
    await init_db()
    logger.info("Database initialized.")

    # DISABLED background pre-warm to fix segfaults on Mac. 
    # Models will load lazily on first request instead.
    # def _prewarm():
    #     try:
    #         from backend.ml_pipeline import _load_models
    #         _load_models()
    #         logger.info("ML models pre-warmed and ready.")
    #     except Exception as e:
    #         logger.warning(f"Model pre-warm failed: {e}")
    #
    # loop = asyncio.get_event_loop()
    # loop.run_in_executor(None, _prewarm)
    # logger.info("ML model pre-warming started in background (non-blocking)...")

    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="BuyWise",
    description="AI-Based Real-Time Review Monitoring & Analysis System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reviews_router, prefix="/api", tags=["Reviews"])
app.include_router(chatbot_router, prefix="/api", tags=["ChatBot"])


@app.get("/")
async def home():
    return {"message": "Backend running successfully"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "BuyWise"}