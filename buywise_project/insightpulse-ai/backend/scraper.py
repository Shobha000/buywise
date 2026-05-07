"""
Scraper — BuyWise
Generates realistic mock reviews and optionally scrapes live data.
"""

import json
import random
from datetime import datetime, timedelta

# ─── Mock Data Pool ───────────────────────────────────────────────────────────

SOURCES = ["Amazon", "Yelp", "Trustpilot", "Google Reviews", "Flipkart"]
PRODUCTS = [
    "Wireless Earbuds Pro X",
    "UltraBook Laptop 15",
    "SmartHome Hub v3",
    "Gaming Mouse Elite",
    "4K Monitor Curved",
    "Mechanical Keyboard RGB",
    "Portable SSD 1TB",
    "Bluetooth Speaker Mini",
    "Fitness Tracker Band",
    "USB-C Docking Station",
]

AUTHORS = [
    "Alex Thompson", "Priya Sharma", "James O'Brien", "Maria Garcia",
    "Li Wei", "Fatima Al-Hassan", "Rahul Verma", "Sophie Müller",
    "Carlos Mendoza", "Amara Osei", "Tyler Johnson", "Yuki Tanaka",
    "Emma Wilson", "Arjun Nair", "Chloe Dubois", "Mohammed Al-Farsi",
]

POSITIVE_TEMPLATES = [
    "Absolutely love this product! The {feature} is outstanding and exceeds all my expectations. Highly recommend to anyone looking for {quality}.",
    "This is by far the best {product_type} I have ever purchased. Setup was easy, performance is excellent, and the build quality is fantastic.",
    "Impressed with the {feature} — works perfectly right out of the box. Great value for money and the delivery was prompt.",
    "Five stars without hesitation. The {feature} is exactly what I needed. Solid build, great {quality}, and amazing customer support.",
    "Been using this for {weeks} weeks now and couldn't be happier. The {feature} really stands out compared to competitors.",
    "Excellent product! Battery life is incredible, sound quality is top-notch, and the design looks premium. Worth every penny.",
    "Surpassed my expectations! The {feature} works flawlessly and the overall experience has been nothing short of wonderful.",
    "Really happy with this purchase. Great {quality} and the {feature} makes daily use a breeze. Would definitely buy again.",
]

NEGATIVE_TEMPLATES = [
    "Terrible experience. The product stopped working after just {days} days. Customer service was unhelpful and the return process was a nightmare.",
    "Disappointed with this purchase. The {feature} is nothing like advertised. Feels cheap and the build quality is very poor.",
    "Complete waste of money. The {feature} broke within a week and the company refused to issue a refund. Avoid at all costs.",
    "The worst product I have ever bought. Poor {quality}, bad customer support, and the item arrived damaged. Never buying again.",
    "Stopped working after {days} days. The {feature} never functioned properly to begin with. Very frustrating experience overall.",
    "Not worth the price at all. The {quality} is subpar and the {feature} constantly malfunctions. Very disappointed.",
    "Poor performance and terrible build quality. The {feature} is a disaster — completely unreliable and broke easily.",
    "Had high hopes but this product is awful. The {feature} doesn't work as described and the material feels very flimsy.",
]

NEUTRAL_TEMPLATES = [
    "It's okay for the price. The {feature} works as expected but nothing special. Average {quality} overall.",
    "Decent product. Does what it says but don't expect anything extraordinary. The {feature} is functional.",
    "Neither good nor bad. The {feature} is average and the {quality} is acceptable. Might work better for some people.",
    "Mixed feelings about this one. Some aspects like {feature} are good, but the {quality} could be improved.",
    "It serves its purpose. The {feature} is satisfactory for basic use. Not the best, not the worst.",
]

FAKE_TEMPLATES = [
    "BEST PRODUCT EVER!!! ABSOLUTELY LOVE IT!! MUST BUY NOW!!! FIVE STARS!!!",
    "Amazing product!! Works perfectly!! Highly recommend!! Best buy ever!! Love love love!!",
    "Excellent!! Great value!! Best product!! No complaints!! Amazing quality!! Buy now!!",
    "WOW!! This is incredible!! BEST THING I EVER BOUGHT!! AMAZING AMAZING AMAZING!!!",
    "Best product ever. Works exactly as described. Highly recommend. Five stars. Great value. Amazing.",
]

FEATURES = ["battery life", "performance", "build quality", "display", "connectivity", "ease of use", "design", "sound quality"]
QUALITIES = ["durability", "value for money", "performance", "reliability", "build quality", "user experience"]


def _random_date(days_back: int = 30) -> datetime:
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23))


def _fill_template(template: str) -> str:
    return template.format(
        feature=random.choice(FEATURES),
        quality=random.choice(QUALITIES),
        product_type=random.choice(["gadget", "device", "product", "item"]),
        weeks=random.randint(2, 12),
        days=random.randint(3, 14),
    )


def generate_mock_reviews(count: int = 50) -> list[dict]:
    """Generate a list of mock review dicts ready for ML analysis."""
    reviews = []
    for _ in range(count):
        # Determine category: 50% positive, 25% negative, 15% neutral, 10% fake
        rand = random.random()
        if rand < 0.50:
            text = _fill_template(random.choice(POSITIVE_TEMPLATES))
            rating = round(random.uniform(4.0, 5.0), 1)
        elif rand < 0.75:
            text = _fill_template(random.choice(NEGATIVE_TEMPLATES))
            rating = round(random.uniform(1.0, 2.5), 1)
        elif rand < 0.90:
            text = _fill_template(random.choice(NEUTRAL_TEMPLATES))
            rating = round(random.uniform(2.5, 4.0), 1)
        else:
            text = random.choice(FAKE_TEMPLATES)
            rating = 5.0

        reviews.append({
            "source": random.choice(SOURCES),
            "product": random.choice(PRODUCTS),
            "author": random.choice(AUTHORS),
            "text": text,
            "rating": rating,
            "scraped_at": _random_date(days_back=30),
        })

    return reviews
