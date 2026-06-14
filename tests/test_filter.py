from backend.scrapers.filter import relevance_score

pairs = [
    ("ordinary serum", "Foxtale Vitamin C Serum"),
    ("the ordinary serum", "The Ordinary Niacinamide 10% + Zinc 1% Serum"),
    ("iphone 14", "Apple iPhone 14 128GB"),
    ("iphone 14", "Apple iPhone 15 128GB"),
    ("aqualogica sunscreen", "Aqualogica Detan+ Dewy Sunscreen"),
    ("aqualogica sunscreen", "Mamaearth Aqua Glow Sunscreen"),
]

for q, t in pairs:
    print(f"Q: '{q}' | T: '{t}' -> Score: {relevance_score(q, t)}")
