"""
chatbot.py — BuyWise
Smart conversational endpoint: review analysis, market recommendations with
buy links, DB stats, top products, and greetings.
"""

import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import backend.reviewguard as rg
from backend.market_engine import get_market_recommendation

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


# ─── Schemas ──────────────────────────────────────────────────────────────────
class ReviewInput(BaseModel):
    text: str


class ChatMessage(BaseModel):
    role: str
    content: str


# ─── Intent detection ─────────────────────────────────────────────────────────
_RECOMMEND_WORDS = {
    "buy", "recommend", "best", "which", "suggest", "top",
    "compare", "vs", "versus", "rating", "rated", "pick", "choose",
    "should i get", "worth it", "worth buying",
}

_STATS_WORDS = {
    "how many", "total", "count", "stats", "statistics", "database",
    "data", "reviews do you", "how much", "fake", "suspicious",
    "what do you know", "tell me about",
}

_GREET_WORDS = {
    "hi", "hello", "hey", "howdy", "hiya", "good morning",
    "good evening", "good afternoon", "what can you do", "help",
    "who are you", "what are you",
}

_TOP_WORDS = {"top", "list", "show", "all", "what products", "what items"}


_LIST_TRIGGERS = {
    "list", "listing", "browse", "show", "display", "see", "view",
    "catalog", "catalogue", "products", "items", "available",
}
_LIST_QUALIFIERS = {"products", "items", "list", "catalog", "catalogue", "available"}


def _extract_filter(text: str) -> str:
    """
    Extract a product keyword filter from queries like:
      'show me iphone products'  -> 'iphone'
      'show me apple products'   -> 'apple'
      'list samsung items'       -> 'samsung'
      'product list'             -> '' (no filter)
    """
    stop = {
        "show", "me", "list", "all", "the", "a", "an", "of", "in",
        "products", "product", "items", "item", "catalog", "available",
        "browse", "see", "display", "give", "what", "is", "are", "my",
        "your", "i", "top", "best", "rated",
    }
    tokens = [t.strip("?.,!") for t in text.lower().split()
              if t.strip("?.,!") not in stop and len(t.strip("?.,!")) > 1]
    return " ".join(tokens)


def _intent(text: str) -> str:
    low    = text.lower().strip()
    tokens = set(re.findall(r"\b\w+\b", low))

    # Greet
    if tokens & _GREET_WORDS or low in {"hi", "hello", "hey"}:
        return "greet"

    # Stats
    if any(phrase in low for phrase in _STATS_WORDS):
        return "stats"

    # List / browse products — token-based (covers 'show me X products', 'product list', etc.)
    has_list_trigger    = bool(tokens & _LIST_TRIGGERS)
    has_list_qualifier  = bool(tokens & _LIST_QUALIFIERS)
    if has_list_trigger and has_list_qualifier:
        return "top_products"
    # Bare phrases: 'product list', 'all products'
    if any(phrase in low for phrase in {
        "product list", "all products", "list products",
        "show products", "show all", "top products",
    }):
        return "top_products"

    # Recommend — only if query contains a specific product hint (not just list words)
    if tokens & _RECOMMEND_WORDS:
        return "recommend"

    # Long text → review analysis
    if len(text.split()) > 4:
        return "analyze"

    return "help"


# ─── Response builders ────────────────────────────────────────────────────────
def _greet_response() -> dict:
    return {
        "type": "text",
        "content": (
            "👋 Hey! I'm **BuyWise** — your smart product review assistant.\n\n"
            "Here's what I can do:\n"
            "- 🔍 **Analyze a review** — paste any review and I'll check if it's fake\n"
            "- 🏆 **Recommend a product** — ask me *'What's the best iPhone?'*\n"
            "- 📊 **Show stats** — ask *'How many reviews do you have?'*\n"
            "- 📋 **List products** — ask *'Show me all products'*\n\n"
            "What would you like to know?"
        ),
    }


def _stats_response() -> dict:
    stats = rg.get_db_stats()
    if not stats:
        return {"type": "text", "content": "I couldn't fetch stats right now. Try again later."}

    fake_pct = round(stats["fake_count"] / max(stats["total_reviews"], 1) * 100, 1)
    return {
        "type": "stats",
        "content": (
            f"📊 **BuyWise Database Stats**\n\n"
            f"- 📝 **Total reviews:** {stats['total_reviews']:,}\n"
            f"- 📦 **Unique products:** {stats['total_products']:,}\n"
            f"- 🚨 **Suspicious reviews:** {stats['fake_count']:,} ({fake_pct}%)\n"
            f"- ⭐ **Average rating:** {stats['avg_rating']}/5\n\n"
            f"My model was trained on **80,000 real Amazon reviews** from Kaggle. "
            f"Ask me anything!"
        ),
        "data": stats,
    }


def _top_products_response(query: str = "") -> dict:
    """List products, optionally filtered by a keyword extracted from the query."""
    df = rg._load_all_products()
    if df.empty:
        return {"type": "text", "content": "No products in the database yet. Use **Search** to add some!"}

    df = df.copy()
    df["genuine_ratio"] = df["genuine_count"] / df["review_count"].clip(lower=1)
    max_r   = df["avg_rating"].max() or 5
    df["score"] = (df["avg_rating"] / max_r) * 0.6 + df["genuine_ratio"] * 0.4

    # Apply keyword filter if present
    keyword = _extract_filter(query).strip()
    filtered = df
    if keyword:
        mask = df["product"].str.lower().str.contains(
            "|".join(re.escape(k) for k in keyword.split()), na=False
        )
        filtered = df[mask]

    if filtered.empty:
        # Nothing matched — show all and explain
        header = (
            f"🔍 No products matching **'{keyword}'** found.\n"
            f"Showing all {len(df)} products instead:\n"
        )
        filtered = df
    elif keyword:
        header = f"📋 **Products matching '{keyword}'** ({len(filtered)} found):\n"
    else:
        header = f"🏆 **All Products in My Database** ({len(filtered)} total):\n"

    top = filtered.sort_values("score", ascending=False).head(10)

    lines = [header]
    for i, (_, row) in enumerate(top.iterrows(), 1):
        name = row["product"]
        name = name if len(name) <= 55 else name[:52] + "…"
        lines.append(
            f"{i}. **{name}**\n"
            f"   ⭐ {round(row['avg_rating'], 1)}/5  •  "
            f"{int(row['review_count'])} reviews  •  "
            f"{round(row['genuine_ratio']*100, 0):.0f}% genuine"
        )

    lines.append("\n💬 _Ask me 'which [product] should I buy?' for buy links & full analysis!_")
    return {"type": "top_products", "content": "\n".join(lines), "data": top.to_dict("records")}


def _recommend_response(query: str) -> dict:
    rec = get_market_recommendation(query)

    # ── Category not in database ──────────────────────────────────
    if rec.get("found") is False:
        suggestions = rec.get("suggestions", [])
        buy_links   = rec.get("buy_links", {})
        sugg_lines  = "\n".join(f"  • {s}" for s in suggestions) if suggestions else ""
        link_lines  = "\n".join(
            f"  🔗 [{src}]({url})" for src, url in buy_links.items()
        ) if buy_links else ""
        return {
            "type": "text",
            "content": (
                f"🔍 I don't have review data for **\"{query}\"** yet.\n\n"
                + (f"Here's what I **do** have data on:\n{sugg_lines}\n\n" if sugg_lines else "")
                + (f"**Search for it directly:**\n{link_lines}\n\n" if link_lines else "")
                + "💡 Use the **Search** tab to scrape reviews and I'll be able to recommend the best option!"
            ),
            "buy_links": buy_links,
        }

    # ── Matched but too few reviews ───────────────────────────────
    if rec.get("found") == "low_data":
        buy_links  = rec.get("buy_links", {})
        link_lines = "\n".join(
            f"  🔗 [{src}]({url})" for src, url in buy_links.items()
        ) if buy_links else ""
        return {
            "type": "text",
            "content": (
                f"⚠️ I found **{rec['product']}** but only have "
                f"{rec['review_count']} verified review(s) — not enough for a confident recommendation.\n\n"
                + (f"**You can search for it here:**\n{link_lines}\n\n" if link_lines else "")
                + "Use the **Search** tab to scrape more reviews for a deeper analysis!"
            ),
            "buy_links": buy_links,
        }

    # ── Full market recommendation with buy links ─────────────────
    buy_links  = rec.get("buy_links", {})
    link_lines = "\n".join(
        f"  🛒 **[Buy on {src}]({url})**" for src, url in buy_links.items()
    ) if buy_links else ""

    return {
        "type": "recommendation",
        "content": (
            f"🏆 **Best product for your search:**\n\n"
            f"**{rec['product']}**\n"
            f"- ⭐ Rating: **{rec['rating']}/5** (market average)\n"
            f"- 📝 Genuine reviews: **{rec['review_count']}**\n"
            f"- 🛡️ Trust Score: **{rec['trust_score']}/100**\n\n"
            f"{rec['reason']}\n\n"
            f"**Where to buy:**\n{link_lines}"
        ),
        "data":      rec,
        "buy_links": buy_links,
    }


def _analyze_response(text: str) -> dict:
    try:
        result = rg.analyze_review(text)
        is_fake = result["is_fake"]
        icon    = "🚨" if is_fake else "✅"
        verdict = result["fake_review_prediction"]
        sent    = result["sentiment"]
        trust   = result["trust_score"]
        fake_p  = result["fake_probability"]

        content = (
            f"{icon} **Review Analysis Result**\n\n"
            f"- **Verdict:** {verdict}\n"
            f"- **Sentiment:** {sent}\n"
            f"- **Trust Score:** {trust}/100\n"
            f"- **Fake Probability:** {fake_p}%\n\n"
        )
        if is_fake:
            content += (
                "⚠️ This review shows signs of being inauthentic. "
                "Treat it with caution before making a purchase decision."
            )
        else:
            content += (
                "This review appears to be genuine and written by a real customer. "
                "You can factor it into your decision with confidence."
            )

        return {"type": "analysis", "content": content, "data": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _help_response() -> dict:
    return {
        "type": "text",
        "content": (
            "I'm not sure what you mean. Here are some things you can ask me:\n\n"
            "- *'What's the best Samsung phone?'* → Product recommendation\n"
            "- *'Is this review fake? [paste review]'* → Review analysis\n"
            "- *'How many reviews do you have?'* → Database stats\n"
            "- *'Show me all products'* → Full product list"
        ),
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/analyze")
async def analyze_single_review(data: ReviewInput):
    """Analyze a single review text using the Kaggle-trained ReviewGuard model."""
    return _analyze_response(data.text)


@router.post("/chat")
async def chat_interaction(data: ReviewInput):
    """
    Smart conversational endpoint.
    Detects intent and routes to the appropriate handler.
    """
    text   = data.text.strip()
    intent = _intent(text)

    if intent == "greet":
        return _greet_response()
    if intent == "stats":
        return _stats_response()
    if intent == "top_products":
        return _top_products_response(text)
    if intent == "recommend":
        return _recommend_response(text)
    if intent == "analyze":
        return _analyze_response(text)

    return _help_response()
