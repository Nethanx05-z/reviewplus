"""
ReviewPulse - Streamlit dashboard
Run:  streamlit run app.py
"""
import os
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# Ensure streamlit uses local config directory within the workspace
os.environ["STREAMLIT_CONFIG_DIR"] = str(Path(__file__).resolve().parent / ".streamlit")

from nlp_engine import analyze_reviews, generate_summary, load_models, overall_sentiment

st.set_page_config(page_title="ReviewPulse", page_icon="📊", layout="wide")


@st.cache_resource
def get_models():
    return load_models()


nlp, sia = get_models()

st.title("📊 ReviewPulse")
st.caption("Aspect-Based Sentiment Analysis of Product Reviews")

# ------------------------------------------------------------ sidebar
st.sidebar.header("⚙️ Configuration")
mode = st.sidebar.radio("Choose input method", [
    "Upload CSV",
    "Use sample data (40 reviews)",
    "Use large dataset (120 reviews)",
    "Paste reviews"
])
min_mentions = st.sidebar.slider("Minimum mentions per aspect", 1, 15, 3)

reviews = []

if mode == "Upload CSV":
    st.subheader("📂 Upload Reviews Dataset")
    f = st.file_uploader("Upload a CSV file containing reviews", type=["csv"])
    if not f:
        f = st.sidebar.file_uploader("Or upload from sidebar", type=["csv"], key="sidebar_csv")

    if f:
        try:
            # Handle possible encoding differences
            try:
                df = pd.read_csv(f, encoding="utf-8")
            except UnicodeDecodeError:
                f.seek(0)
                df = pd.read_csv(f, encoding="latin-1")

            total_rows = len(df)
            st.write(f"📋 **Data Preview:** Showing first 5 sample rows (out of **{total_rows} total rows** in your file):")
            st.dataframe(df.head(5), use_container_width=True)

            with st.expander(f"🔍 Click here to view all {total_rows} rows"):
                st.dataframe(df, use_container_width=True)

            # Auto-detect review column (case-insensitive)
            col_candidates = [c for c in df.columns if any(k in str(c).lower() for k in ["review", "text", "comment", "feedback", "content", "opinion"])]
            default_index = 0
            if col_candidates:
                default_index = list(df.columns).index(col_candidates[0])
            elif len(df.columns) > 1:
                default_index = len(df.columns) - 1

            selected_col = st.selectbox("Select the column containing the review text:", df.columns, index=default_index)
            reviews = df[selected_col].dropna().astype(str).tolist()
            st.success(f"✅ **Analyzing all {len(reviews)} reviews** from column **'{selected_col}'**.")
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            st.stop()

elif mode == "Paste reviews":
    st.subheader("📝 Paste Reviews")
    txt = st.text_area("One review per line", height=200, placeholder="The battery lasts two days but the camera is disappointing.\nGreat price, fast delivery!")
    reviews = [l.strip() for l in txt.split("\n") if l.strip()]

elif mode == "Use large dataset (120 reviews)":
    large_path = Path(__file__).resolve().parent / "large_sample_reviews.csv"
    if large_path.exists():
        df_large = pd.read_csv(large_path)
        reviews = df_large["review"].dropna().astype(str).tolist()
        st.info(f"Loaded {len(reviews)} multi-product reviews from `large_sample_reviews.csv`.")
    else:
        st.error("large_sample_reviews.csv file not found.")
        st.stop()

else:  # Use sample data (40 reviews)
    sample_path = Path(__file__).resolve().parent / "sample_reviews.csv"
    if sample_path.exists():
        df_sample = pd.read_csv(sample_path)
        reviews = df_sample["review"].dropna().astype(str).tolist()
        st.info(f"Loaded {len(reviews)} benchmark sample reviews from `sample_reviews.csv`.")
    else:
        st.error("sample_reviews.csv file not found.")
        st.stop()

if not reviews:
    st.info("👈 Upload a CSV file, paste text reviews, or select **Use sample data** to begin.")
    st.stop()

# ------------------------------------------------------------ analysis
with st.spinner("Analysing reviews..."):
    details, summary = analyze_reviews(reviews, nlp, sia, min_mentions)
    counts, avg = overall_sentiment(reviews, sia)

# ------------------------------------------------------------ KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Reviews analysed", len(reviews))
c2.metric("Aspects found", len(summary))
pos_pct = f"{(counts.get('Positive', 0) / max(len(reviews), 1)):.0%}"
c3.metric("Overall positive", pos_pct)
c4.metric("Avg sentiment score", f"{avg:.2f}")

st.success("**Summary:** " + generate_summary(summary))

if summary.empty:
    st.warning("No aspects met the minimum mention threshold. Lower the slider in the sidebar.")
    st.stop()

# ------------------------------------------------------------ charts
left, right = st.columns(2)
with left:
    st.subheader("Sentiment by aspect")
    long = summary.melt(id_vars="aspect", value_vars=["Positive", "Negative", "Neutral"],
                        var_name="Sentiment", value_name="Count")
    fig = px.bar(long, x="aspect", y="Count", color="Sentiment", barmode="group",
                 color_discrete_map={"Positive": "#2e7d32", "Negative": "#c62828", "Neutral": "#9e9e9e"})
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Average score per aspect")
    s = summary.sort_values("avg_score")
    fig2 = px.bar(s, x="avg_score", y="aspect", orientation="h", color="avg_score",
                  color_continuous_scale="RdYlGn", range_color=[-1, 1])
    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------ table
st.subheader("Aspect verdicts")
st.dataframe(summary, use_container_width=True, hide_index=True)

# ------------------------------------------------------------ drill-down
st.subheader("🔍 See what users said")
aspect = st.selectbox("Pick an aspect to view customer quotes", summary["aspect"])
sub = details[details.aspect == aspect]
a, b = st.columns(2)
with a:
    st.markdown("**👍 Positive mentions**")
    pos_quotes = sub[sub.sentiment == "Positive"].segment.head(5).tolist()
    if pos_quotes:
        for t in pos_quotes:
            st.write("• " + t)
    else:
        st.write("*(No positive mentions for this aspect)*")
with b:
    st.markdown("**👎 Negative mentions**")
    neg_quotes = sub[sub.sentiment == "Negative"].segment.head(5).tolist()
    if neg_quotes:
        for t in neg_quotes:
            st.write("• " + t)
    else:
        st.write("*(No negative mentions for this aspect)*")

# ------------------------------------------------------------ download
st.subheader("📥 Export & Download")
d_col1, d_col2, d_col3 = st.columns(3)
with d_col1:
    st.download_button("⬇️ Results (CSV)",
                       details.to_csv(index=False).encode("utf-8"),
                       "reviewpulse_results.csv", "text/csv",
                       use_container_width=True)
with d_col2:
    sample_file = Path(__file__).resolve().parent / "sample_reviews.csv"
    if sample_file.exists():
        with open(sample_file, "rb") as sf:
            st.download_button("⬇️ Sample CSV (40 Reviews)",
                               sf.read(),
                               "sample_reviews.csv", "text/csv",
                               use_container_width=True)
with d_col3:
    large_file = Path(__file__).resolve().parent / "large_sample_reviews.csv"
    if large_file.exists():
        with open(large_file, "rb") as lf:
            st.download_button("⬇️ Large CSV (120 Reviews)",
                               lf.read(),
                               "large_sample_reviews.csv", "text/csv",
                               use_container_width=True)

pdf_report = Path(__file__).resolve().parent / "ReviewPulse_Project_Report_With_Screenshots.pdf"
if not pdf_report.exists():
    pdf_report = Path(__file__).resolve().parent / "ReviewPulse_Presentation_Report.pdf"

if pdf_report.exists():
    with open(pdf_report, "rb") as pf:
        st.download_button("📄 Download Project Report with Screenshots (PDF)",
                           pf.read(),
                           "ReviewPulse_Project_Report_With_Screenshots.pdf",
                           "application/pdf",
                           use_container_width=True)



