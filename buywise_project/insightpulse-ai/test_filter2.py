import re

_STOPWORDS = {"the", "a", "an", "and", "or", "for", "with", "of", "in", "on", "at", "to"}
_MODEL_PATTERN = re.compile(r"\b\d+\b|\bmini\b|\bpro\b|\bmax\b|\bultra\b|\bplus\b|\blite\b|\bair\b|\bfe\b|\bse\b")

def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def relevance_score(query: str, product_title: str) -> float:
    q_norm = _normalize(query)
    t_norm = _normalize(product_title)

    if q_norm in t_norm:
        return 1.0

    q_words = set(q_norm.split()) - _STOPWORDS
    if not q_words:
        return 0.5

    t_words = set(t_norm.split()) - _STOPWORDS
    word_score = len(q_words & t_words) / len(q_words)

    model_tokens = _MODEL_PATTERN.findall(q_norm)
    q_significant = [w for w in q_norm.split() if w not in _STOPWORDS and not w.isdigit()]
    brand_score = 1.0 if (q_significant and q_significant[0] in t_norm) else 0.0

    if model_tokens:
        model_matched = sum(1 for tok in model_tokens if tok in t_norm)
        model_score = model_matched / len(model_tokens)
        if model_score == 0:
            return 0.1  # highly penalize missing models
        return round(word_score * 0.3 + model_score * 0.5 + brand_score * 0.2, 3)
    else:
        return round(word_score * 0.6 + brand_score * 0.4, 3)

pairs = [
    ("ordinary serum", "Foxtale Vitamin C Serum"),
    ("ordinary serum", "The Ordinary Niacinamide 10% + Zinc 1% Serum"),
    ("the ordinary serum", "The Ordinary Niacinamide 10% + Zinc 1% Serum"),
    ("iphone 14", "Apple iPhone 14 128GB"),
    ("iphone 14", "Apple iPhone 15 128GB"),
    ("aqualogica sunscreen", "Aqualogica Detan+ Dewy Sunscreen"),
    ("aqualogica sunscreen", "Mamaearth Aqua Glow Sunscreen"),
    ("samsung s23", "Samsung Galaxy S22 Ultra"),
    ("samsung s23", "Samsung Galaxy S23 Ultra"),
]

for q, t in pairs:
    print(f"Q: '{q:<20}' | T: '{t:<45}' -> Score: {relevance_score(q, t)}")
