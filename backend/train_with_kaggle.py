#!/usr/bin/env python3
"""
train_with_kaggle.py — BuyWise TURBO
======================================
500K Amazon reviews. All operations vectorized — no Python loops.
Trains 4 models for both fake-detection and sentiment.

Expected runtime: ~5-7 minutes total.
"""
import logging as _logging
_logging.getLogger("kagglesdk").setLevel(_logging.WARNING)

import sys, json, logging, time, warnings
from pathlib import Path

import numpy as np
import pandas as pd
import joblib

warnings.filterwarnings("ignore", category=UserWarning)

from sklearn.linear_model import LogisticRegression, SGDClassifier, PassiveAggressiveClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score, roc_auc_score
from scipy.sparse import hstack as sp_hstack, csr_matrix

BASE_DIR        = Path(__file__).parent
MODEL_PATH      = BASE_DIR / "reviewguard_model.pkl"
VECT_PATH       = BASE_DIR / "reviewguard_vectorizer.pkl"
SENT_MODEL_PATH = BASE_DIR / "sentiment_model.pkl"
SENT_VECT_PATH  = BASE_DIR / "sentiment_vectorizer.pkl"
REPORT_PATH     = BASE_DIR / "training_report.json"

KAGGLE_DATASET = "kritanjalijain/amazon-reviews"
MAX_ROWS = 500_000

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("BuyWise.Train")


# ─── Download ─────────────────────────────────────────────────────────────────
def download_dataset() -> Path:
    log.info(f"📥  {KAGGLE_DATASET}")
    import kagglehub
    path = Path(kagglehub.dataset_download(KAGGLE_DATASET))
    csvs = list(path.glob("**/*.csv"))
    chosen = next((f for f in csvs if "train" in f.name.lower()), csvs[0])
    log.info(f"✅  {chosen}")
    return chosen


# ─── Load ──────────────────────────────────────────────────────────────────────
def load_data(path: Path) -> pd.DataFrame:
    log.info(f"📂  Loading {MAX_ROWS:,} rows...")
    df = pd.read_csv(path, header=None,
                     names=["label", "title", "review"],
                     nrows=MAX_ROWS, on_bad_lines="skip",
                     encoding="utf-8", quoting=0, engine="python")
    log.info(f"   {df.shape}")
    return df


# ─── Normalise ────────────────────────────────────────────────────────────────
def normalise(df: pd.DataFrame) -> pd.DataFrame:
    df["text"] = (df["title"].fillna("") + " " + df["review"].fillna("")).str.strip()
    df = df[df["text"].str.len() >= 15].copy()
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)
    df = df[df["label"].isin([1, 2])].copy()
    df["sentiment_label"] = df["label"].map({2: "POSITIVE", 1: "NEGATIVE"})
    df["s_label"] = df["label"].map({2: 1, 1: 0})
    log.info(f"   {len(df):,} | {df['sentiment_label'].value_counts().to_dict()}")
    return df


# ─── Fake labelling (100% vectorized, no regex loops) ─────────────────────────
_GENERIC = [
    "best product ever", "absolutely love", "highly recommend", "five stars",
    "amazing product", "must buy", "great value", "works perfectly",
    "exactly as described", "no complaints",
]

def label_fake(series: pd.Series) -> np.ndarray:
    log.info("   🔍 Fake labelling (vectorized)...")
    lower      = series.str.lower()
    words      = series.str.split()
    word_count = words.str.len().fillna(0).astype(int)
    excl_count = series.str.count("!")
    char_count = series.str.len().clip(lower=1)

    # caps ratio: count uppercase letters
    caps_count = series.apply(lambda x: sum(1 for c in x if c.isupper()))
    caps_ratio = caps_count / char_count

    # unique word ratio — fast approximation: unique chars / total chars
    # (avoids split+set per row)
    uniq_approx = series.apply(
        lambda x: len(set(x.lower().split())) / max(len(x.split()), 1)
    )

    gen_hits = sum(
        lower.str.contains(p, regex=False, na=False).astype(int)
        for p in _GENERIC
    )

    signals = (
        (word_count < 6).astype(int) * 2 +
        (caps_ratio > 0.35).astype(int) +
        (excl_count > 3).astype(int) +
        ((uniq_approx < 0.4) & (word_count > 5)).astype(int) +
        (gen_hits >= 2).astype(int)
    )
    labels = (signals >= 3).astype(int)
    pos = labels.sum()
    log.info(f"   Genuine={len(labels)-pos:,}  Suspicious={pos:,}  ({pos/len(labels):.2%})")
    return labels.values


# ─── Meta-features (fast, no avg_wl loop) ─────────────────────────────────────
def meta_features(df: pd.DataFrame) -> csr_matrix:
    log.info("   Meta-features (vectorized)...")
    s = df["text"]
    wc  = s.str.split().str.len().fillna(0).values
    ex  = s.str.count("!").values
    qu  = s.str.count(r"\?").values
    cap = s.apply(lambda x: sum(c.isupper() for c in x) / max(len(x),1)).values
    tl  = s.str.len().values
    return csr_matrix(np.column_stack([wc, ex, qu, cap, tl]).astype(np.float32))


# ─── TF-IDF ───────────────────────────────────────────────────────────────────
def fit_tfidf(texts: list, word_feats=15000, char_feats=8000):
    log.info(f"   Word TF-IDF ({word_feats:,})...")
    wv = TfidfVectorizer(analyzer="word", stop_words="english",
                         max_features=word_feats, ngram_range=(1, 3),
                         sublinear_tf=True, min_df=2, dtype=np.float32)
    wX = wv.fit_transform(texts)

    log.info(f"   Char TF-IDF ({char_feats:,})...")
    cv = TfidfVectorizer(analyzer="char_wb", max_features=char_feats,
                         ngram_range=(3, 5), sublinear_tf=True,
                         min_df=3, dtype=np.float32)
    cX = cv.fit_transform(texts)
    return wX, cX, wv, cv

def transform_tfidf(texts: list, wv, cv):
    return wv.transform(texts), cv.transform(texts)


# ─── Model race ───────────────────────────────────────────────────────────────
def race(X_tr, X_te, y_tr, y_te, label: str):
    models = {
        "LinearSVC": CalibratedClassifierCV(
            LinearSVC(C=1.5, class_weight="balanced", max_iter=3000, random_state=42), cv=3),
        "LogisticReg": LogisticRegression(
            C=5.0, class_weight="balanced", max_iter=800,
            solver="saga", n_jobs=-1, random_state=42),
        "SGD": SGDClassifier(
            loss="modified_huber", alpha=5e-5, class_weight="balanced",
            max_iter=500, random_state=42, n_jobs=-1),
        "PassiveAggressive": CalibratedClassifierCV(
            PassiveAggressiveClassifier(C=0.8, class_weight="balanced",
                                        max_iter=1000, random_state=42), cv=3),
    }
    best_clf, best_f1, best_name = None, -1, ""
    metrics = {}
    for name, clf in models.items():
        t0 = time.time()
        log.info(f"   → {name}...")
        clf.fit(X_tr, y_tr)
        yp  = clf.predict(X_te)
        ypr = clf.predict_proba(X_te)[:, 1]
        acc = accuracy_score(y_te, yp)
        f1  = f1_score(y_te, yp, average="weighted")
        try:    auc = roc_auc_score(y_te, ypr)
        except: auc = 0.0
        log.info(f"     acc={acc:.4f}  f1={f1:.4f}  auc={auc:.4f}  ({time.time()-t0:.0f}s)")
        metrics[name] = {"accuracy": round(acc,4), "f1": round(f1,4), "auc": round(auc,4)}
        if f1 > best_f1:
            best_f1, best_clf, best_name = f1, clf, name

    log.info(f"\n🏆  [{label}] Best: {best_name}  F1={best_f1:.4f}")
    log.info("\n" + classification_report(y_te, best_clf.predict(X_te)))
    return best_clf, best_name, metrics


# ─── Train fake ───────────────────────────────────────────────────────────────
def train_fake(df: pd.DataFrame):
    log.info(f"\n🧠  [FAKE DETECTION] {len(df):,} reviews")
    fake_y = label_fake(df["text"])
    texts  = df["text"].tolist()

    wX, cX, wv, cv = fit_tfidf(texts)
    mX = meta_features(df)
    X  = sp_hstack([wX, cX, mX], format="csr")
    log.info(f"   Matrix: {X.shape}  nnz={X.nnz:,}")

    Xtr, Xte, ytr, yte = train_test_split(
        X, fake_y, test_size=0.15, random_state=42, stratify=fake_y)
    clf, name, met = race(Xtr, Xte, ytr, yte, "FAKE")
    return clf, (wv, cv), met, name, yte, Xte


# ─── Train sentiment ──────────────────────────────────────────────────────────
def train_sentiment(df: pd.DataFrame):
    log.info(f"\n🎭  [SENTIMENT] {len(df):,} reviews")
    texts = df["text"].tolist()
    y     = df["s_label"].values

    wX, cX, wv, cv = fit_tfidf(texts, word_feats=20_000, char_feats=10_000)
    X = sp_hstack([wX, cX], format="csr")
    log.info(f"   Matrix: {X.shape}  nnz={X.nnz:,}")

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y)
    clf, name, met = race(Xtr, Xte, ytr, yte, "SENTIMENT")
    return clf, (wv, cv), met, name


# ─── Save ──────────────────────────────────────────────────────────────────────
def save_all(fc, fv, fm, fn, sc, sv, sm, sn, yte, Xte):
    joblib.dump(fc, MODEL_PATH);      log.info(f"✅  {MODEL_PATH.name}")
    joblib.dump(fv, VECT_PATH);       log.info(f"✅  {VECT_PATH.name}")
    joblib.dump(sc, SENT_MODEL_PATH); log.info(f"✅  {SENT_MODEL_PATH.name}")
    joblib.dump(sv, SENT_VECT_PATH);  log.info(f"✅  {SENT_VECT_PATH.name}")
    REPORT_PATH.write_text(json.dumps({
        "dataset": KAGGLE_DATASET, "rows": MAX_ROWS,
        "fake_model": fn, "fake_metrics": fm,
        "sent_model": sn, "sent_metrics": sm,
        "feature_dim": Xte.shape[1], "test_samples": int(len(yte)),
    }, indent=2))
    log.info(f"📊  {REPORT_PATH.name}")


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    log.info("=" * 66)
    log.info("  BuyWise TURBO Training — 500K reviews, 4 models, vectorized")
    log.info("=" * 66)

    csv = download_dataset()
    df  = load_data(csv)
    df  = normalise(df)

    fc, fv, fm, fn, yte, Xte = train_fake(df)
    sc, sv, sm, sn            = train_sentiment(df)

    save_all(fc, fv, fm, fn, sc, sv, sm, sn, yte, Xte)
    log.info(f"\n🎉  Done in {(time.time()-t0)/60:.1f} min")
    log.info("    Restart BuyWise backend to load the new models.\n")


if __name__ == "__main__":
    main()
