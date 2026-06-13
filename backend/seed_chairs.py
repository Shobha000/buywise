import sqlite3
import uuid
from datetime import datetime

DB_PATH = "buywise.db"

CHAIR_REVIEWS = [
    # ErgoMax Office Chair (The Winner)
    ("ErgoMax Office Chair", "Best chair I've ever bought. My back pain is gone after just one week.", 5, "Amazon", "John Doe"),
    ("ErgoMax Office Chair", "Very sturdy and the lumbar support is exactly where it needs to be.", 5, "Flipkart", "Jane Smith"),
    ("ErgoMax Office Chair", "A bit expensive but absolutely worth the price for the comfort.", 4, "Trustpilot", "Alice Brown"),
    
    # Gaming Pro X (Mixed)
    ("Gaming Pro X", "Looks cool but it's a bit stiff. Not great for 8+ hours of work.", 3, "Amazon", "Gamer123"),
    ("Gaming Pro X", "The leather feels cheap and it squeaks when I lean back.", 2, "Flipkart", "Bob Wilson"),
    
    # Minimalist Wooden Chair (Niche)
    ("Minimalist Wooden Chair", "Looks beautiful in my dining room, but wouldn't use it as a desk chair.", 4, "G2", "ModernDesignFan"),
]

def seed_chairs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if reviews table exists
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reviews'")
        if not cursor.fetchone():
            print("❌ Table 'reviews' does not exist. Creating it...")
            # Create a simple table if it doesn't exist for direct testing
            cursor.execute("""
                CREATE TABLE reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT,
                    text TEXT,
                    rating FLOAT,
                    source TEXT,
                    author TEXT,
                    sentiment TEXT,
                    sentiment_score FLOAT,
                    topics TEXT,
                    is_fake BOOLEAN,
                    fake_confidence FLOAT,
                    scraped_at DATETIME
                )
            """)
    except:
        pass

    print("🌱 Seeding chair reviews...")
    for product, text, rating, source, author in CHAIR_REVIEWS:
        cursor.execute("""
            INSERT INTO reviews (product, text, rating, source, author, sentiment, sentiment_score, topics, is_fake, fake_confidence, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product,
            text,
            rating,
            source,
            author,
            "POSITIVE" if rating >= 4 else "NEGATIVE",
            0.9 if rating >= 4 else 0.2,
            '["comfort", "build", "price"]',
            0,
            0.1,
            datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()
    print("✅ Seeded chair reviews successfully!")

if __name__ == "__main__":
    seed_chairs()
