import random
import re
from datetime import datetime

_AUTHORS = [
    "Rahul V.", "Sneha K.", "Amit P.", "Priya R.", "Suresh M.",
    "Anjali T.", "Karan B.", "Divya S.", "Rohit N.", "Meera A.",
    "Ravi K.", "Priya S.", "Mohammed A.", "Ananya R.", "Siddharth M.",
    "Kavya P.", "Arjun T.", "Sneha L.", "Vikram B.", "Deepa N.",
]

def _categorize_product(product_name: str) -> str:
    lower = product_name.lower()
    if any(w in lower for w in ["balm", "cream", "lotion", "serum", "shampoo", "face", "skin", "hair", "wash", "moisturizer"]):
        return "beauty"
    if any(w in lower for w in ["maker", "cooker", "oven", "blender", "pan", "pot", "kitchen", "kettle"]):
        return "kitchen"
    if any(w in lower for w in ["phone", "laptop", "cable", "charger", "watch", "screen", "tv", "earbuds", "headphones", "speaker"]):
        return "tech"
    if any(w in lower for w in ["shirt", "pants", "shoe", "jacket", "dress", "jeans"]):
        return "clothing"
    return "generic"

_TEMPLATES = {
    "beauty": {
        "POS": [
            "Love this {product}! It feels great on the skin and smells amazing. Highly recommended.",
            "Best purchase! This {product} is very hydrating and gentle. Exactly what I needed.",
            "Excellent {product}! I've been using it daily and I can already see the difference. Will buy again.",
            "Really happy with this {product}. Very soothing and the quantity is good for the price. 5 stars!",
            "Superb quality! Genuine {product} and it arrived well packaged. Works perfectly for my routine."
        ],
        "NEG": [
            "Very disappointed with this {product}. It caused a mild reaction and didn't suit me at all.",
            "Not great. This {product} feels very sticky and the scent is overpowering. Expected better.",
            "Regret buying this. The {product} dried me out and didn't perform as advertised. Waste of money.",
            "Terrible experience. The {product} arrived unsealed and looks fake. Do not buy this."
        ],
        "NEU": [
            "Decent {product} but nothing special. It does the job but there are better alternatives out there.",
            "Average. This {product} is okay for daily use but I didn't see any major improvements.",
            "Mixed feelings. It moisturizes well but I don't love the texture of this {product}. Delivery was fast though."
        ]
    },
    "kitchen": {
        "POS": [
            "Excellent {product}! Makes cooking so much easier. Very easy to clean and sturdy. Highly recommended.",
            "Amazing value! This {product} heats up quickly and works perfectly. A great addition to my kitchen.",
            "Very impressed with this {product}. The non-stick surface is great and it looks premium on the counter.",
            "Great {product} at this price point. It came well packaged and all functions work as advertised. 5 stars!"
        ],
        "NEG": [
            "Very poor quality. This {product} stopped heating properly after a week. Not worth the price.",
            "Disappointed. The {product} is very hard to clean and feels cheaply made. Regret this purchase.",
            "Stopped working after a few uses. The {product} is clearly defective. Avoid this item.",
            "Terrible. This {product} arrived with a dent and the performance is poor. Complete waste of money."
        ],
        "NEU": [
            "Decent {product} but nothing special. Does the basic job but feels a bit flimsy. Average.",
            "Okay for the price. This {product} works fine for basic cooking but don't expect premium quality.",
            "Mixed experience. It works well enough but the cord is too short. Not bad but not great either."
        ]
    },
    "tech": {
        "POS": [
            "Absolutely love this {product}! The performance is outstanding and battery life is great. Highly recommended.",
            "Best purchase! The {product} arrived in perfect condition, connects easily and works flawlessly.",
            "Excellent {product}! Setup was quick and easy. Great build quality and clear display. Would buy again.",
            "Really happy with this {product}. Performance is smooth and feels very premium. Great value."
        ],
        "NEG": [
            "Very disappointed with this {product}. Stopped connecting properly after just 2 weeks.",
            "Poor quality for the price. The {product} feels cheap and battery drains very fast. Expected better.",
            "Had high hopes but this {product} failed to deliver. Heating issues and slow performance.",
            "Not worth the money at all. The {product} arrived with defects and the software is buggy."
        ],
        "NEU": [
            "The {product} is decent for the price. Does what it promises but nothing extraordinary. Performance is average.",
            "Average product. The {product} works fine for basic tasks but don't expect premium features.",
            "Mixed feelings about this {product}. Some things work great, others not so much. Software needs updates."
        ]
    },
    "clothing": {
        "POS": [
            "Love this {product}! The fit is perfect and the fabric feels very comfortable and premium.",
            "Great quality! This {product} looks exactly like the pictures. The stitching is excellent.",
            "Very happy with the {product}. It washed well without shrinking and the color is vibrant.",
            "Excellent purchase. The {product} is true to size and very stylish. Highly recommended."
        ],
        "NEG": [
            "Very disappointed. The {product} is way smaller than the size chart suggests. Fabric is scratchy.",
            "Poor quality. This {product} tore after just one wash. The material is very thin.",
            "Regret buying this. The {product} looks completely different from the photos. Terrible fit.",
            "Not worth it. The {product} has loose threads everywhere and feels very cheap."
        ],
        "NEU": [
            "Decent {product} but the fit is a bit odd. Fabric is okay for the price point.",
            "Average. The {product} looks fine but the material isn't very breathable. Okay for occasional wear.",
            "Mixed feelings. The color is nice but the sizing runs a bit small on this {product}."
        ]
    },
    "generic": {
        "POS": [
            "Excellent product! The {product} is worth every rupee. Fast delivery, great packaging and top notch quality.",
            "Amazing value for money! The {product} works exactly as described and feels very well made.",
            "Very impressed with the {product}. Works perfectly right out of the box. Highly recommended.",
            "Great product at this price point. The {product} comes well packaged and works as advertised. 5 stars!",
            "Outstanding quality! The {product} exceeded my expectations. Easy to use and great design."
        ],
        "NEG": [
            "Very poor quality. The {product} had issues from day one. Stopped functioning properly. Not worth it.",
            "Disappointed with this {product}. The description is misleading. Feels cheap and performs poorly.",
            "Defective item. The {product} is clearly flawed. Customer service did not help. Think twice before buying.",
            "Terrible experience. The {product} arrived damaged and the quality is terrible. Waste of money.",
            "Not satisfied at all. The {product} looks nothing like the photos. Avoid this product."
        ],
        "NEU": [
            "Decent product but nothing special. The {product} does the basic job but don't expect premium quality.",
            "Okay product for the price. The {product} does its job but there are better alternatives in the market.",
            "Mixed experience with the {product}. Some aspects are good, but overall it is just average.",
            "It works as expected for basic use. The {product} is fine but won't impress you. Packaging was decent."
        ]
    }
}

def generate_smart_mock(product_name: str, count: int, source: str) -> list[dict]:
    """Generates highly realistic mock reviews by classifying the product type first."""
    category = _categorize_product(product_name)
    templates = _TEMPLATES[category]
    
    reviews = []
    for _ in range(count):
        r = random.random()
        if r < 0.55:
            text = random.choice(templates["POS"]).format(product=product_name)
            rating = round(random.uniform(4.0, 5.0), 1)
        elif r < 0.80:
            text = random.choice(templates["NEG"]).format(product=product_name)
            rating = round(random.uniform(1.0, 2.5), 1)
        else:
            text = random.choice(templates["NEU"]).format(product=product_name)
            rating = round(random.uniform(2.5, 3.9), 1)
            
        reviews.append({
            "source": source,
            "product": product_name,
            "author": random.choice(_AUTHORS),
            "text": text,
            "rating": rating,
            "scraped_at": datetime.utcnow(),
        })
    return reviews
