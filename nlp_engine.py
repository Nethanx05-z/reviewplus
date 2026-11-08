"""
ReviewPulse - core NLP engine
Aspect-Based Sentiment Analysis of Product Reviews

Pipeline:
 1. Clean text and split into sentences      (spaCy)
 2. Split sentences into opinion segments    (contrast words: but, however...)
 3. Extract aspects (nouns)                  (spaCy POS tagging + lemmatization)
 4. Score sentiment of each segment          (VADER + domain lexicon)
 5. Aggregate per aspect
"""
import re
from collections import Counter, defaultdict

import pandas as pd
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ---------------------------------------------------------------- config
# Different words that mean the same aspect -> one canonical name
ASPECT_SYNONYMS = {
    "display": "screen", "screen": "screen",
    "cost": "price", "price": "price", "value": "price", "money": "price",
    "shipping": "delivery", "delivery": "delivery", "packaging": "packaging",
    "package": "packaging",
    "cam": "camera", "camera": "camera", "photo": "camera", "picture": "camera",
    "battery": "battery", "charging": "battery", "charger": "battery",
    "performance": "performance", "speed": "performance",
    "sound": "sound", "speaker": "sound", "audio": "sound",
    "build": "build quality", "quality": "build quality", "design": "design",
    "service": "customer service", "support": "customer service",
    "storage": "storage", "memory": "storage",
    "software": "software", "app": "software", "ui": "software",
}

# Generic nouns that are NOT product aspects
STOP_ASPECTS = {
    "phone", "product", "thing", "item", "day", "time", "week", "month", "year",
    "one", "lot", "bit", "way", "people", "everything", "something", "anything",
    "nothing", "order", "purchase", "buy", "star", "review", "reason", "end",
    "hour", "minute", "stuff", "need", "family", "friend", "work", "use",
    "drain", "night", "device", "model", "brand", "customer", "life", "light", "case", "side",
}

# Domain words VADER does not know (score -4 .. +4)
CUSTOM_LEXICON = {
    "drains": -2.5, "drain": -2.0, "blurry": -2.5, "laggy": -2.5, "lags": -2.5,
    "lag": -2.0, "overheats": -3.0, "overheating": -3.0, "sluggish": -2.5,
    "flimsy": -2.5, "cheaply": -1.5, "late": -1.8, "delayed": -2.0,
    "damaged": -3.0, "broken": -3.0, "dim": -1.5, "tinny": -2.0, "muffled": -2.0,
    "durable": 2.5, "sturdy": 2.5, "crisp": 2.5, "snappy": 2.5, "smooth": 2.2,
    "sleek": 2.2, "vibrant": 2.5, "affordable": 2.5, "overpriced": -2.5,
    "pricey": -1.5, "worth": 2.0, "lasts": 1.5, "unresponsive": -2.5, "fast": 1.5, "slow": -1.8, "quick": 1.5,
}

CONTRAST_SPLIT = re.compile(r"\b(?:but|however|although|though|yet|while|whereas)\b", re.I)


# ---------------------------------------------------------------- loaders
def load_models():
    """Load spaCy model + VADER analyzer (call once)."""
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        try:
            from spacy.cli import download as spacy_download
            spacy_download("en_core_web_sm")
            nlp = spacy.load("en_core_web_sm")
        except Exception:
            raise RuntimeError(
                "spaCy model missing. Run: python -m spacy download en_core_web_sm"
            )
    sia = SentimentIntensityAnalyzer()
    sia.lexicon.update(CUSTOM_LEXICON)
    return nlp, sia


# ---------------------------------------------------------------- steps
def clean_text(text: str) -> str:
    text = str(text)
    text = re.sub(r"http\S+|www\.\S+", " ", text)   # urls
    text = re.sub(r"<.*?>", " ", text)               # html tags
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_aspects(segment_doc):
    """Return canonical aspect names found in a spaCy doc/span."""
    found = []
    for tok in segment_doc:
        if tok.pos_ in ("NOUN", "PROPN"):
            lemma = tok.lemma_.lower()
            if lemma in STOP_ASPECTS or len(lemma) < 3 or not lemma.isalpha():
                continue
            found.append(ASPECT_SYNONYMS.get(lemma, lemma))
    return list(dict.fromkeys(found))  # unique, keep order


def label_from_score(score: float) -> str:
    if score >= 0.05:
        return "Positive"
    if score <= -0.05:
        return "Negative"
    return "Neutral"


def analyze_reviews(reviews, nlp, sia, min_mentions=2):
    """
    reviews: list[str]
    returns (details_df, summary_df)
    details_df: one row per (review, sentence segment, aspect)
    summary_df: one row per aspect with counts and verdict
    """
    rows = []
    for rid, review in enumerate(reviews, start=1):
        doc = nlp(clean_text(review))
        for sent in doc.sents:
            # split sentence into opinion segments at contrast words
            pieces = CONTRAST_SPLIT.split(sent.text)
            for piece in pieces:
                piece = piece.strip(" ,;.-")
                if len(piece) < 3:
                    continue
                seg = nlp(piece)
                aspects = extract_aspects(seg)
                if not aspects:
                    continue
                score = sia.polarity_scores(piece)["compound"]
                for asp in aspects:
                    rows.append({
                        "review_id": rid,
                        "aspect": asp,
                        "segment": piece,
                        "score": round(score, 3),
                        "sentiment": label_from_score(score),
                    })

    details = pd.DataFrame(rows, columns=["review_id", "aspect", "segment", "score", "sentiment"])
    if details.empty:
        return details, pd.DataFrame(columns=["aspect", "Positive", "Negative", "Neutral",
                                              "mentions", "avg_score", "verdict"])

    summary = (details.pivot_table(index="aspect", columns="sentiment",
                                   values="score", aggfunc="count", fill_value=0)
               .reindex(columns=["Positive", "Negative", "Neutral"], fill_value=0))
    summary["mentions"] = summary.sum(axis=1)
    summary["avg_score"] = details.groupby("aspect")["score"].mean().round(3)
    summary = summary[summary["mentions"] >= min_mentions].reset_index()
    summary["verdict"] = summary.apply(verdict, axis=1)
    summary = summary.sort_values("mentions", ascending=False).reset_index(drop=True)
    return details, summary


def verdict(row) -> str:
    if row["mentions"] == 0:
        return "No data"
    pos_ratio = row["Positive"] / row["mentions"]
    neg_ratio = row["Negative"] / row["mentions"]
    if pos_ratio >= 0.6:
        return "Good"
    if neg_ratio >= 0.6:
        return "Poor"
    return "Mixed"


def generate_summary(summary_df, top_n=3) -> str:
    """Plain-English pros/cons summary."""
    if summary_df.empty:
        return "Not enough aspect mentions to summarise."
    good = summary_df[summary_df.verdict == "Good"].sort_values("avg_score", ascending=False)
    poor = summary_df[summary_df.verdict == "Poor"].sort_values("avg_score")
    mixed = summary_df[summary_df.verdict == "Mixed"]
    parts = []
    if not good.empty:
        parts.append("Users love the " + ", ".join(good.aspect.head(top_n)) + ".")
    if not poor.empty:
        parts.append("Common complaints are about the " + ", ".join(poor.aspect.head(top_n)) + ".")
    if not mixed.empty:
        parts.append("Opinions are mixed on " + ", ".join(mixed.aspect.head(top_n)) + ".")
    return " ".join(parts)


def overall_sentiment(reviews, sia):
    scores = [sia.polarity_scores(clean_text(r))["compound"] for r in reviews]
    labels = [label_from_score(s) for s in scores]
    return Counter(labels), sum(scores) / max(len(scores), 1)
