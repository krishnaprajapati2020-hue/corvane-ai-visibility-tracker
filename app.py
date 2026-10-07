import streamlit as st
import pandas as pd
from src.tracker import load_data, build_mentions_dataframe, extract_wrong_facts, compute_visibility_score

st.set_page_config(page_title="Corvane AI Visibility Tracker", layout="wide")

@st.cache_data
def get_processed_data():
    resp_df, prompts_df, facts = load_data('data')
    mentions_df = build_mentions_dataframe(resp_df)
    wrong_facts_df = extract_wrong_facts(resp_df, facts)
    scores_df = compute_visibility_score(mentions_df, resp_df, prompts_df)
    return resp_df, prompts_df, facts, mentions_df, wrong_facts_df, scores_df

resp_df, prompts_df, facts, mentions_df, wrong_facts_df, scores_df = get_processed_data()

st.title("🛰️ Corvane Fleet — AI Visibility Tracker")
tabs = st.tabs(["📊 Marcus's Monday View", "🔍 Priya's Detail View", "⚠️ Hallucination Alerts"])

with tabs[0]:
    st.subheader("Monday Morning 2-Minute Briefing")
    latest_week = int(scores_df['week'].max())
    prev_week = latest_week - 1
    
    latest_scores = scores_df[scores_df['week'] == latest_week].set_index('brand')['score'].to_dict()
    prev_scores = scores_df[scores_df['week'] == prev_week].set_index('brand')['score'].to_dict()
    
    c1, c2, c3, c4 = st.columns(4)
    brands = ['corvane', 'trakvia', 'routelyne', 'gridwell']
    cols = [c1, c2, c3, c4]
    
    for brand, col in zip(brands, cols):
        curr = latest_scores.get(brand, 0)
        prv = prev_scores.get(brand, 0)
        delta = round(curr - prv, 1)
        col.metric(label=brand.upper(), value=f"{curr} pts", delta=f"{delta} WoW")
        
    st.markdown("---")
    st.subheader("Weekly Visibility Score Trend (Weeks 1 to 6)")
    chart_data = scores_df.pivot(index='week', columns='brand', values='score')
    st.line_chart(chart_data)

with tabs[1]:
    st.subheader("Detailed Prompt Inspector")
    colA, colB = st.columns(2)
    selected_week = colA.selectbox("Select Week", options=sorted(resp_df['week'].unique(), reverse=True))
    selected_engine = colB.selectbox("Select Engine", options=['all'] + list(resp_df['engine'].unique()))
    
    filtered = resp_df[resp_df['week'] == selected_week]
    if selected_engine != 'all':
        filtered = filtered[filtered['engine'] == selected_engine]
        
    for _, item in filtered.head(15).iterrows():
        with st.expander(f"{item['prompt_id']} ({item['engine']})"):
            st.write(item['response_text'])

with tabs[2]:
    st.subheader("Wrong Claims Flagged")
    st.dataframe(wrong_facts_df, use_container_width=True)