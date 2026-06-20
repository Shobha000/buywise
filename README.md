 
# 🔮 BuyWise
### AI-Based Real-Time Review Monitoring & Analysis System
 

---

## Quick Start

### 1. Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed the database with 80 sample reviews
python -m backend.seed_data

# Start the server
uvicorn backend.main:app --reload --port 8000
```

API will be live at: **http://localhost:8000**
Auto-docs at: **http://localhost:8000/docs**

---

### 2. Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Dashboard will be live at: **http://localhost:3000**

---

## ML Pipeline

| Task | Model | Fallback |
|---|---|---|
| Sentiment Analysis | `distilbert-base-uncased-finetuned-sst-2-english` | Rule-based keyword matching |
| Topic Extraction | `KeyBERT` + `all-MiniLM-L6-v2` | Domain keyword matching |
| Summarization | `sshleifer/distilbart-cnn-12-6` | First 2 sentences |
| Fake Detection | Heuristic scoring | — |

> Models are downloaded automatically on first use. Internet connection required for first run.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/reviews` | Paginated reviews |
| GET | `/api/reviews/stats` | Aggregate statistics |
| GET | `/api/reviews/sentiment-trend` | Daily sentiment trend |
| GET | `/api/reviews/topics` | Topic frequency list |
| GET | `/api/alerts` | Flagged reviews |
| POST | `/api/scrape?count=30` | Trigger new scrape |
| WS | `/api/ws/feed` | Live review stream |

---

## Project Structure

```
buywise-ai/
├── frontend/           # Next.js 15 (TypeScript)
│   ├── app/            # App Router pages
│   ├── components/     # UI components
│   └── lib/            # Shared types
└── backend/            # FastAPI (Python)
    ├── main.py         # Entry point
    ├── models.py       # DB models
    ├── ml_pipeline.py  # AI/ML logic
    ├── scraper.py      # Data generator
    └── routers/        # API routes
```

---

 
