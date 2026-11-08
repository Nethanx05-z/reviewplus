# ReviewPulse: Aspect-Based Sentiment Analysis of Product Reviews

ReviewPulse is an Aspect-Based Sentiment Analysis (ABSA) system and interactive dashboard. Rather than classifying a whole review as merely "positive" or "negative", ReviewPulse discovers exactly **what** features consumers discuss (e.g., *battery*, *camera*, *screen*, *delivery*, *price*) and **how** they feel about each individual feature.

---

## 📌 Abstract

> **ReviewPulse: Aspect-Based Sentiment Analysis of Product Reviews**  
> *ReviewPulse is an intelligent aspect-based sentiment analysis (ABSA) system designed to extract fine-grained consumer feedback from unstructured e-commerce product reviews. Rather than reducing user sentiment to a single monolithic rating, the system breaks multi-clause reviews across contrastive conjunctions, extracts specific product features (such as battery, camera, display, and delivery) using spaCy part-of-speech tagging and lemmatization, and scores localized polarity using VADER augmented with a domain-specific lexicon. The aggregated metrics, aspect verdicts (Good, Mixed, Poor), and automated pros-and-cons summaries are rendered via an interactive Streamlit dashboard. ReviewPulse enables prospective shoppers to evaluate targeted product attributes quickly and empowers manufacturers to pinpoint exact feature bottlenecks impacting customer satisfaction.*

---

## 🏗️ Architecture & Pipeline (For Viva / Demo)

| Step | Operation | Description | Implementation |
| :--- | :--- | :--- | :--- |
| **1. Cleaning** | Text Normalization | Strips URLs, HTML markup tags, and redundant whitespace. | `clean_text()` in `nlp_engine.py` |
| **2. Sentence Splitting** | Tokenization | Uses spaCy sentence boundary detection to segment long reviews into sentences. | `doc.sents` in `analyze_reviews()` |
| **3. Opinion Segmentation** | Contrastive Splitting | Splits sentences at contrast words (`but`, `however`, `although`, `yet`, `while`). Solves mixed clauses (e.g. *"Great screen **but** battery drains quickly"*). | `CONTRAST_SPLIT` regex in `nlp_engine.py` |
| **4. Aspect Extraction** | POS Tagging & Lemmatization | Identifies `NOUN` and `PROPN` tokens, lemmatizes them, removes stop-nouns, and maps synonyms to canonical aspects (`display` → `screen`). | `extract_aspects()` in `nlp_engine.py` |
| **5. Sentiment Scoring** | Lexicon & Rule-based Scoring | Calculates polarity score (-1.0 to +1.0) per segment using VADER, augmented with an electronics domain lexicon (`blurry`, `overheats`, `sluggish`, `sturdy`). | `sia.polarity_scores()` in `nlp_engine.py` |
| **6. Aggregation & Verdict** | Aspect Metrics | Aggregates mentions, computes average polarity score, and assigns a verdict: **Good** (>=60% positive), **Poor** (>=60% negative), or **Mixed**. | `verdict()` in `nlp_engine.py` |
| **7. Summary Generation** | Natural Language Summary | Automatically generates readable synthesis: *"Users love the screen, price. Common complaints are about the camera."* | `generate_summary()` in `nlp_engine.py` |
| **8. Dashboard UI** | Visualization & Drill-Down | Renders KPI cards, Plotly charts, verdict tables, customer quotes per aspect, and CSV download. | `app.py` (Streamlit) |

---

## 📁 Project Structure

```
reviewpulse/
├── app.py                 # Streamlit web dashboard
├── nlp_engine.py          # Core NLP and Aspect-Based Sentiment Analysis engine
├── sample_reviews.csv     # Benchmark dataset with 40 realistic product reviews
├── requirements.txt       # Python project dependencies
└── README.md              # Documentation, viva guide, and setup instructions
```

---

## 🚀 How to Run in Antigravity

### 1. Open Terminal & Navigate to Project
In Antigravity, open the terminal in the workspace directory:
```bash
cd /Users/nethan/.gemini/antigravity/scratch/reviewpulse
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```
*(On Windows: `venv\Scripts\activate`)*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 4. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
Streamlit will launch locally (typically at `http://localhost:8501`). In the sidebar:
- Choose **Use sample data** to instantly explore the preloaded 40 product reviews.
- Or choose **Upload CSV** to analyze any CSV with a `review` column.
- Or choose **Paste reviews** to test your own custom sentences directly.

---

## 🎯 Viva Q&A / Technical Defense Points

1. **Why not just perform overall review sentiment classification?**
   - *Answer:* Overall sentiment ignores nuances. A 3-star review often praises the screen and build while condemning battery and customer support. Aspect-based analysis provides actionable feature-level intelligence.

2. **Why split sentences at contrastive words like `but` and `however`?**
   - *Answer:* If a sentence says *"The camera is gorgeous but the battery drains fast"*, a standard sentence-level analyzer averages positive and negative scores together, yielding a neutral or misleading rating. Splitting at contrast markers separates the praise for the camera from the criticism of the battery.

3. **Why did we add a custom lexicon to VADER?**
   - *Answer:* General VADER sentiment lexicons miss domain-specific tech vocabulary. Words like *"sluggish"*, *"overheats"*, *"blurry"*, *"flimsy"*, and *"crisp"* carry strong product sentiment that off-the-shelf VADER may score as neutral.

4. **What are the limitations of this rule-based approach?**
   - *Answer:* 
     - Sarcasm (*"Great, it stopped working on day two"*) can mislead lexical sentiment analyzers.
     - Unseen aspects or informal slang might require continual updates to `ASPECT_SYNONYMS` and `STOP_ASPECTS`.

5. **What are future improvements?**
   - *Answer:* Replace or ensemble VADER with a fine-tuned transformer model (e.g. `cardiffnlp/twitter-roberta-base-sentiment-latest` or DeBERTa) and use dependency parsing or BERT-based span extraction for zero-shot aspect extraction.

---

## 🌐 Cloud Deployment (Streamlit Community Cloud)

To deploy for external presentation:
1. Push this folder to a GitHub repository.
2. In `requirements.txt`, you can add the spaCy model directly as a pip dependency:
   ```txt
   https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
   ```
3. Go to [share.streamlit.io](https://share.streamlit.io/), select your GitHub repo, and set `app.py` as the entrypoint.
