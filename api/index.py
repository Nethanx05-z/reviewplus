import json
import os
import re
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Try loading VADER sentiment analyzer
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
except Exception:
    sia = None

CUSTOM_LEXICON = {
    "blurry": -2.5, "overheats": -3.0, "laggy": -2.5, "stutter": -2.0, "drain": -2.0, "drains": -2.0,
    "damaged": -3.0, "broken": -3.0, "dim": -1.5, "tinny": -2.0, "muffled": -2.0,
    "durable": 2.5, "sturdy": 2.5, "crisp": 2.5, "snappy": 2.5, "smooth": 2.2,
    "sleek": 2.2, "vibrant": 2.5, "affordable": 2.5, "overpriced": -2.5,
    "pricey": -1.5, "worth": 2.0, "lasts": 1.5, "unresponsive": -2.5, "fast": 1.5, "slow": -1.8, "quick": 1.5,
}
if sia:
    sia.lexicon.update(CUSTOM_LEXICON)

# Aspect synonym canonicalization
ASPECT_SYNONYMS = {
    "display": "screen", "panel": "screen", "touchscreen": "screen", "monitor": "screen",
    "cam": "camera", "lens": "camera", "sensor": "camera", "photo": "camera", "photos": "camera", "picture": "camera", "pictures": "camera",
    "charging": "battery", "charge": "battery", "charger": "battery", "power": "battery",
    "cost": "price", "pricing": "price", "money": "price", "value": "price", "deal": "price",
    "shipping": "delivery", "courier": "delivery", "dispatch": "delivery",
    "speed": "performance", "processor": "performance", "chip": "performance", "cpu": "performance", "lag": "performance",
    "speaker": "sound", "speakers": "sound", "audio": "sound", "volume": "sound",
    "durability": "build quality", "casing": "build quality", "body": "build quality", "plastic": "build quality",
    "support": "customer service", "agent": "customer service", "service": "customer service",
    "os": "software", "ui": "software", "app": "software", "apps": "software", "update": "software", "bug": "software", "bugs": "software",
    "storage": "storage", "memory": "storage", "ram": "storage",
    "box": "packaging", "package": "packaging",
}

STOP_ASPECTS = {
    "phone", "product", "device", "item", "unit", "thing", "everything",
    "day", "week", "month", "year", "time", "amazon", "star", "stars",
    "issue", "problem", "review", "one", "bit", "lot", "way", "people",
    "money", "hand", "use", "purchase", "order", "delivery"
}

KNOWN_ASPECTS = {
    "battery", "camera", "screen", "price", "delivery", "performance",
    "sound", "build quality", "customer service", "software", "design",
    "storage", "packaging"
}

CONTRAST_SPLIT = re.compile(r"\b(?:but|however|although|though|yet|while|whereas)\b", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

def clean_text(text: str) -> str:
    text = str(text)
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_aspects(text: str):
    found = []
    text_lower = text.lower()
    
    # Check multi-word aspects first
    if "build quality" in text_lower or "build" in text_lower:
        found.append("build quality")
    if "customer service" in text_lower or "customer support" in text_lower:
        found.append("customer service")

    # Word-level matching
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text_lower)
    for w in words:
        if w in ASPECT_SYNONYMS:
            canon = ASPECT_SYNONYMS[w]
            if canon not in found:
                found.append(canon)
        elif w in KNOWN_ASPECTS and w not in found:
            found.append(w)
            
    return found

def score_segment(segment: str) -> float:
    if sia:
        return sia.polarity_scores(segment)["compound"]
    # Fallback simple polarity if VADER is somehow not initialized
    pos_words = {"great", "good", "excellent", "love", "fast", "sturdy", "smooth", "crisp", "best", "lasts"}
    neg_words = {"bad", "terrible", "poor", "slow", "blurry", "drains", "overheats", "laggy", "broken", "worst"}
    words = set(re.findall(r"\b\w+\b", segment.lower()))
    score = len(words & pos_words) * 0.4 - len(words & neg_words) * 0.4
    return max(-1.0, min(1.0, score))

def label_from_score(score: float) -> str:
    if score >= 0.05:
        return "Positive"
    if score <= -0.05:
        return "Negative"
    return "Neutral"

def verdict(pos, neg, neu):
    total = pos + neg + neu
    if total == 0:
        return "Mixed"
    if pos / total >= 0.6:
        return "Good"
    if neg / total >= 0.6:
        return "Poor"
    return "Mixed"

def generate_summary(aspects_data):
    goods = [a["aspect"] for a in aspects_data if a["verdict"] == "Good"]
    poors = [a["aspect"] for a in aspects_data if a["verdict"] == "Poor"]
    mixeds = [a["aspect"] for a in aspects_data if a["verdict"] == "Mixed"]
    
    parts = []
    if goods:
        parts.append(f"Users love the {', '.join(goods)}.")
    if poors:
        parts.append(f"Common complaints are about the {', '.join(poors)}.")
    if mixeds:
        parts.append(f"Opinions are mixed on {', '.join(mixeds)}.")
    return " ".join(parts) if parts else "Not enough mentions above threshold to synthesize a summary."

SAMPLE_REVIEWS_DEFAULT = [
    "The battery easily lasts two days, but the camera is blurry in low light.",
    "Display is super bright and vibrant! However, the customer service was awful when I called.",
    "Great price for the specs. Build quality feels a bit cheap though.",
    "Speakers are loud and crisp. Battery drains very quickly while gaming.",
    "Fast delivery by courier. Software is full of bugs and bloatware.",
    "I love the design and camera photos in daylight. But it overheats when charging.",
    "Screen is sharp and responsive. Performance lags when switching between apps.",
    "Unresponsive touch screen and terrible customer support. Returning it.",
    "Affordable price and sturdy metal chassis. Worth every penny.",
    "Battery life is amazing! Sound is tinny at high volume."
]

class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        
        if "sample" in path:
            self.wfile.write(json.dumps({
                "status": "success",
                "reviews": SAMPLE_REVIEWS_DEFAULT
            }).encode("utf-8"))
            return
            
        self.wfile.write(json.dumps({
            "status": "online",
            "service": "ReviewPulse ABSA Serverless API",
            "version": "2.0"
        }).encode("utf-8"))

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}
            
        reviews = body.get("reviews", [])
        min_mentions = int(body.get("min_mentions", 2))
        
        if not reviews:
            reviews = SAMPLE_REVIEWS_DEFAULT

        details = []
        aspect_counts = {}
        aspect_scores = {}
        
        for rid, review in enumerate(reviews, start=1):
            cleaned = clean_text(review)
            sentences = SENTENCE_SPLIT.split(cleaned)
            for s in sentences:
                segments = CONTRAST_SPLIT.split(s)
                for seg in segments:
                    seg = seg.strip(" ,;.-")
                    if len(seg) < 3:
                        continue
                    asps = extract_aspects(seg)
                    if not asps:
                        continue
                    score = round(score_segment(seg), 3)
                    label = label_from_score(score)
                    for asp in asps:
                        details.append({
                            "review_id": rid,
                            "aspect": asp,
                            "segment": seg,
                            "score": score,
                            "sentiment": label
                        })
                        if asp not in aspect_counts:
                            aspect_counts[asp] = {"Positive": 0, "Negative": 0, "Neutral": 0}
                            aspect_scores[asp] = []
                        aspect_counts[asp][label] += 1
                        aspect_scores[asp].append(score)

        # Aspect aggregation
        aspects_summary = []
        for asp, counts in aspect_counts.items():
            mentions = counts["Positive"] + counts["Negative"] + counts["Neutral"]
            if mentions >= min_mentions:
                scores = aspect_scores[asp]
                avg_sc = round(sum(scores) / len(scores), 3) if scores else 0.0
                v = verdict(counts["Positive"], counts["Negative"], counts["Neutral"])
                aspects_summary.append({
                    "aspect": asp,
                    "Positive": counts["Positive"],
                    "Negative": counts["Negative"],
                    "Neutral": counts["Neutral"],
                    "mentions": mentions,
                    "avg_score": avg_sc,
                    "verdict": v
                })

        aspects_summary.sort(key=lambda x: (x["mentions"], x["avg_score"]), reverse=True)
        summary_text = generate_summary(aspects_summary)

        # Global stats
        total_clauses = len(details)
        pos_clauses = sum(1 for d in details if d["sentiment"] == "Positive")
        positive_pct = round((pos_clauses / total_clauses * 100), 1) if total_clauses > 0 else 0.0
        avg_overall = round(sum(d["score"] for d in details) / total_clauses, 2) if total_clauses > 0 else 0.0

        response = {
            "status": "success",
            "stats": {
                "total_reviews": len(reviews),
                "total_aspects": len(aspects_summary),
                "positive_pct": positive_pct,
                "avg_score": avg_overall,
                "total_clauses": total_clauses
            },
            "summary_text": summary_text,
            "aspects": aspects_summary,
            "details": details[:100]  # first 100 rows for table display
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))
