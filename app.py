import streamlit as st
import os
import time
import json
from dotenv import load_dotenv
import plotly.graph_objects as go
load_dotenv()
from cache.memory_cache import cached_trends, cached_serper, cached_reddit, clear_all_caches
from cache.disk_cache import save_analysis, get_history, clear_api_cache
from agents.market_service import run_market_analysis, answer_followup_question
from models.output_models import MarketAnalysisResult
TIMEFRAME_MAP = {
    "Past 30 Days": "today 1-m",
    "Past 3 Months": "today 3-m",
    "Past 12 Months": "today 12-m",
    "Past 5 Years": "today 5-y"
}
COUNTRY_GEO_MAP = {
    "Global (Worldwide)": "",
    "United States": "US",
    "Turkey": "TR",
    "United Kingdom": "GB",
    "Germany": "DE",
    "France": "FR",
    "India": "IN",
    "Japan": "JP",
    "Brazil": "BR",
    "Canada": "CA",
    "Australia": "AU"
}
st.set_page_config(page_title="Market Opportunity Agent", page_icon="🌍", layout="wide")
# ──────────────────────────────────────────────
# Session State
# ──────────────────────────────────────────────
for key, default in {
    "report": None,
    "chat_history": [],
    "loaded_result": None,
    "loaded_meta": {},
    "mode": "single",          # "single" or "compare"
    "compare_a": None,         # result JSON string
    "compare_b": None,
    "compare_meta_a": {},
    "compare_meta_b": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default
# ──────────────────────────────────────────────
# Gauge Chart (compact flag for compare mode)
# ──────────────────────────────────────────────
def create_gauge(score: int, compact: bool = False):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Score", "font": {"size": 18 if compact else 24}},
        gauge={
            "axis": {"range": [None, 100], "tickwidth": 1},
            "bar": {"color": "rgba(0,0,0,0)"},
            "steps": [
                {"range": [0, 39],  "color": "#ff4b4b"},
                {"range": [40, 69], "color": "#faca2b"},
                {"range": [70, 100],"color": "#21c354"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 6},
                "thickness": 0.75,
                "value": score,
            },
        },
    ))
    h = 250 if compact else 350
    fig.update_layout(
        height=h,
        margin=dict(l=10, r=10, t=40, b=10),
        transition={"duration": 1000, "easing": "cubic-in-out"},
    )
    return fig
# ──────────────────────────────────────────────
# Full result renderer (single mode)
# ──────────────────────────────────────────────
def render_result(result, idea_raw, country_ui, timeframe_ui, trends_data=None):
    verd_color = (
        "red" if result.verdict == "DONT RECOMMEND" else
        "orange" if result.verdict == "PROCEED WITH CAUTION" else "green"
    )
    st.subheader(f"Final Verdict: :{verd_color}[{result.verdict}]", divider="rainbow")
    md_report  = f"# Market Analysis: {idea_raw}\n\n**Verdict:** {result.verdict} (Score: {result.final_score}/100)\n\n"
    md_report += f"## Metrics\n- Demand: {result.demand_score}/10\n- Competition: {result.competition_score}/10\n- Social: {result.social_score}/10\n\n"
    md_report += "## Reasons\n" + "\n".join([f"- {r}" for r in result.reasons]) + "\n\n"
    md_report += "## Risks\n"   + "\n".join([f"- {r}" for r in result.risks])   + "\n\n"
    md_report += f"## Next Move\n🚀 {result.next_move}"
    st.download_button("📥 Download Report (.md)", data=md_report,
                       file_name=f"{idea_raw.replace(' ','_')}_Analysis.md", mime="text/markdown")
    left_col, right_col = st.columns([1, 2])
    with left_col:
        ph = st.empty()
        ph.plotly_chart(create_gauge(0), use_container_width=True)
        time.sleep(0.05)
        ph.plotly_chart(create_gauge(result.final_score), use_container_width=True)
    with right_col:
        c1, c2, c3 = st.columns(3)
        c1.metric("Demand",      f"{result.demand_score}/10")
        c2.metric("Competition", f"{result.competition_score}/10")
        c3.metric("Social",      f"{result.social_score}/10")
        geo_label = f" in {country_ui}" if country_ui else " Worldwide"
        st.write(f"📈 **Trend ({timeframe_ui}{geo_label})**")
        if trends_data and trends_data.get("chart_data"):
            st.line_chart(trends_data["chart_data"])
        else:
            st.info("Trend timeline not available.")
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**✅ Top Validating Reasons:**")
        for r in result.reasons: st.info(r)
        st.write("**📍 Best Emerging Markets:**")
        for m in result.best_markets: st.markdown(f"- {m}")
    with col2:
        st.write("**⚠️ Major Risks Found:**")
        for r in result.risks: st.error(r)
        st.write("**🚀 Recommended Next Move:**")
        st.success(result.next_move)
# ──────────────────────────────────────────────
# Compact result renderer (compare mode columns)
# ──────────────────────────────────────────────
def render_compact(result, label: str, side: str = "a"):
    verd_color = (
        "red" if result.verdict == "DONT RECOMMEND" else
        "orange" if result.verdict == "PROCEED WITH CAUTION" else "green"
    )
    st.markdown(f"### {label}")
    st.markdown(f"**Verdict:** :{verd_color}[{result.verdict}]")
    ph = st.empty()
    ph.plotly_chart(create_gauge(0, compact=True), use_container_width=True, key=f"gauge_start_{side}")
    time.sleep(0.05)
    ph.plotly_chart(create_gauge(result.final_score, compact=True), use_container_width=True, key=f"gauge_end_{side}")
    st.metric("Demand",      f"{result.demand_score}/10")
    st.metric("Competition", f"{result.competition_score}/10")
    st.metric("Social",      f"{result.social_score}/10")
    st.write("**✅ Reasons:**")
    for r in result.reasons: st.info(r)
    st.write("**⚠️ Risks:**")
    for r in result.risks: st.error(r)
    st.write("**🚀 Next Move:**")
    st.success(result.next_move)
# ──────────────────────────────────────────────
# Run analysis helper (reused in both modes)
# ──────────────────────────────────────────────
def run_analysis(idea, country, city, audience, timeframe_ui, timeframe_val, geo_code):
    safe_idea  = idea.strip().lower()
    safe_query = f"{idea} {country} {city}".strip().lower()
    trends_data = cached_trends(safe_idea, timeframe_val, geo=geo_code)
    serper_data = cached_serper(safe_query)
    reddit_data = cached_reddit(safe_idea)

    # Warn the user if any data source is missing its API key
    missing_keys = []
    if trends_data.get("status") == "missing_key":
        missing_keys.append("SERPAPI_API_KEY (Google Trends)")
    if serper_data.get("status") == "missing_key":
        missing_keys.append("SERPER_API_KEY (Web Search / Reddit)")
    if missing_keys:
        st.warning(f"⚠️ Missing API keys: {', '.join(missing_keys)}. Analysis will be limited.")

    result = run_market_analysis(idea, country, city, audience,
                                trends_data, serper_data, reddit_data)
    safe_country = country.strip().lower() if country else "global"
    safe_city = city.strip().lower() if city else ""
    save_analysis(idea=safe_idea, country=safe_country, city=safe_city, timeframe=timeframe_ui,
                  score=result.final_score, verdict=result.verdict,
                  result_json=result.model_dump_json())
    return result, trends_data
# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────
st.sidebar.title("Settings")
st.sidebar.info("API Keys loaded from .env automatically.")
if st.sidebar.button("🔄 Force Clear Cache"):
    clear_all_caches()
    for k in ["report","chat_history","loaded_result","compare_a","compare_b"]:
        st.session_state[k] = None
    st.session_state.chat_history = []
    st.session_state.mode = "single"
    st.rerun()
st.sidebar.write("---")
st.sidebar.subheader("📋 Analysis History")
history = get_history(limit=15)
if not history:
    st.sidebar.caption("No analyses yet.")
else:
    for entry in history:
        icon = "🟢" if entry["verdict"] == "GO" else "🔴" if entry["verdict"] == "DONT RECOMMEND" else "🟡"
        label = f"{icon} {entry['idea']} ({entry['country']}) — {entry['score']}/100"
        if st.sidebar.button(label, key=f"hist_{entry['id']}"):
            st.session_state.loaded_result = entry["result_json"]
            st.session_state.loaded_meta = {
                "idea": entry["idea"], "country_ui": entry["country"].title(),
                "timeframe_ui": entry["timeframe"],
            }
            st.session_state.report = entry["result_json"]
            st.session_state.chat_history = []
            st.session_state.mode = "single"
            st.rerun()
# ──────────────────────────────────────────────
# Title + Mode Toggle Row
# ──────────────────────────────────────────────
title_col, btn_col = st.columns([4, 1])
with title_col:
    st.title("🌍 Market Opportunity Agent")
with btn_col:
    st.write("")  # vertical spacer
    if st.session_state.mode == "single":
        if st.button("Compare", use_container_width=True):
            st.session_state.mode = "compare"
            st.rerun()
    else:
        if st.button("↩️ Single Mode", use_container_width=True):
            st.session_state.mode = "single"
            st.session_state.compare_a = None
            st.session_state.compare_b = None
            st.rerun()
st.markdown("Evaluate market viability through live Search, Serper, and Social signals.")
# ══════════════════════════════════════════════
#  SINGLE MODE
# ══════════════════════════════════════════════
if st.session_state.mode == "single":
    with st.form("market_input_form"):
        st.subheader("Market Details")
        idea       = st.text_input("Product or Business Idea", placeholder="e.g. Protein Powder")
        country_ui = st.selectbox("Target Country", list(COUNTRY_GEO_MAP.keys()), index=2)
        country    = country_ui if country_ui != "Global (Worldwide)" else ""
        geo_code   = COUNTRY_GEO_MAP[country_ui]
        city       = st.text_input("Target City (Optional)", placeholder="e.g. Istanbul")
        audience   = st.text_input("Target Audience (Optional)", placeholder="e.g. Gym goers")
        timeframe_ui  = st.selectbox("Trend Timeframe", list(TIMEFRAME_MAP.keys()), index=1)
        timeframe_val = TIMEFRAME_MAP[timeframe_ui]
        submitted = st.form_submit_button("Analyze Opportunity")
    if submitted:
        with st.spinner(f"Investigating '{idea}' across {country_ui}..."):
            try:
                result, trends_data = run_analysis(
                    idea, country, city, audience, timeframe_ui, timeframe_val, geo_code
                )
                st.session_state.report = result.model_dump_json()
                st.session_state.chat_history = []
                st.session_state.loaded_result = None
                render_result(result, idea, country_ui, timeframe_ui, trends_data)
            except Exception as e:
                st.error(f"Failed: {str(e)}")
            safe_idea = idea.strip().lower()
            safe_query = f"{idea} {country} {city}".strip().lower()
            with st.expander("🛠️ View Raw API Signals", expanded=False):
                st.json(cached_trends(safe_idea, timeframe_val, geo=geo_code))
                st.json(cached_serper(safe_query))
                st.json(cached_reddit(safe_idea))
    elif st.session_state.loaded_result:
        meta = st.session_state.loaded_meta
        try:
            result = MarketAnalysisResult.model_validate_json(st.session_state.loaded_result)
            st.info(f"📂 Showing saved analysis for **{meta.get('idea','')}**")
            render_result(result, meta.get("idea",""), meta.get("country_ui",""),
                          meta.get("timeframe_ui",""), None)
        except Exception as e:
            st.error(f"Failed to load: {str(e)}")
    # Chatbot
    if st.session_state.report:
        st.write("---")
        st.header("💬 Discuss with your VC Agent")
        st.caption("Ask questions about the report above.")
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        with st.form("chat_form", clear_on_submit=True):
            col_input, col_btn = st.columns([8, 1])
            with col_input:
                prompt = st.text_input("", placeholder="Ask a follow-up question...", label_visibility="collapsed")
            with col_btn:
                submitted = st.form_submit_button("Send", use_container_width=True)
        if submitted and prompt.strip():
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = answer_followup_question(prompt, st.session_state.chat_history, st.session_state.report)
                    st.markdown(reply)
            st.session_state.chat_history.append({"role":"user","content":prompt})
            st.session_state.chat_history.append({"role":"assistant","content":reply})
            st.rerun()
# ══════════════════════════════════════════════
#  COMPARE MODE
# ══════════════════════════════════════════════
else:
    st.subheader("Head-to-Head Comparison")
    history_for_pick = get_history(limit=20)
    history_labels   = ["— New Search —"] + [
        f"{e['idea']} ({e['country']}) — {e['score']}/100" for e in history_for_pick
    ]
    col_a, col_b = st.columns(2)
    # ── LEFT COLUMN: IDEA A ──
    with col_a:
        st.markdown("### Idea A")
        pick_a = st.selectbox("Source", history_labels, key="pick_a")
        if pick_a == "— New Search —":
            with st.form("compare_form_a"):
                idea_a       = st.text_input("Idea A", placeholder="e.g. Fidget Spinner", key="idea_a")
                country_a_ui = st.selectbox("Country", list(COUNTRY_GEO_MAP.keys()), index=2, key="country_a")
                country_a    = country_a_ui if country_a_ui != "Global (Worldwide)" else ""
                geo_a        = COUNTRY_GEO_MAP[country_a_ui]
                tf_a_ui      = st.selectbox("Timeframe", list(TIMEFRAME_MAP.keys()), index=1, key="tf_a")
                tf_a_val     = TIMEFRAME_MAP[tf_a_ui]
                sub_a = st.form_submit_button("Analyze A")
            if sub_a:
                with st.spinner(f"Analyzing '{idea_a}'..."):
                    try:
                        res_a, _ = run_analysis(idea_a, country_a, "", "", tf_a_ui, tf_a_val, geo_a)
                        st.session_state.compare_a = res_a.model_dump_json()
                        st.session_state.compare_meta_a = {"idea": idea_a, "country": country_a_ui}
                    except Exception as e:
                        st.error(str(e))
        else:
            idx = history_labels.index(pick_a) - 1
            entry = history_for_pick[idx]
            st.session_state.compare_a = entry["result_json"]
            st.session_state.compare_meta_a = {"idea": entry["idea"], "country": entry["country"].title()}
    # ── RIGHT COLUMN: IDEA B ──
    with col_b:
        st.markdown("### Idea B")
        pick_b = st.selectbox("Source", history_labels, key="pick_b")
        if pick_b == "— New Search —":
            with st.form("compare_form_b"):
                idea_b       = st.text_input("Idea B", placeholder="e.g. Stress Ball", key="idea_b")
                country_b_ui = st.selectbox("Country", list(COUNTRY_GEO_MAP.keys()), index=2, key="country_b")
                country_b    = country_b_ui if country_b_ui != "Global (Worldwide)" else ""
                geo_b        = COUNTRY_GEO_MAP[country_b_ui]
                tf_b_ui      = st.selectbox("Timeframe", list(TIMEFRAME_MAP.keys()), index=1, key="tf_b")
                tf_b_val     = TIMEFRAME_MAP[tf_b_ui]
                sub_b = st.form_submit_button("Analyze B")
            if sub_b:
                with st.spinner(f"Analyzing '{idea_b}'..."):
                    try:
                        res_b, _ = run_analysis(idea_b, country_b, "", "", tf_b_ui, tf_b_val, geo_b)
                        st.session_state.compare_b = res_b.model_dump_json()
                        st.session_state.compare_meta_b = {"idea": idea_b, "country": country_b_ui}
                    except Exception as e:
                        st.error(str(e))
        else:
            idx = history_labels.index(pick_b) - 1
            entry = history_for_pick[idx]
            st.session_state.compare_b = entry["result_json"]
            st.session_state.compare_meta_b = {"idea": entry["idea"], "country": entry["country"].title()}
    # ── RENDER SIDE-BY-SIDE RESULTS ──
    if st.session_state.compare_a and st.session_state.compare_b:
        st.write("---")
        st.subheader("📊 Comparison Results")
        res_col_a, divider, res_col_b = st.columns([5, 1, 5])
        with res_col_a:
            try:
                result_a = MarketAnalysisResult.model_validate_json(st.session_state.compare_a)
                meta_a = st.session_state.compare_meta_a
                render_compact(result_a, f"{meta_a.get('idea','')} — {meta_a.get('country','')}", side="a")
            except Exception as e:
                st.error(str(e))
        with divider:
            st.markdown("<div style='border-left:2px solid #555; height:100%; min-height:400px; margin:auto;'></div>",
                        unsafe_allow_html=True)
        with res_col_b:
            try:
                result_b = MarketAnalysisResult.model_validate_json(st.session_state.compare_b)
                meta_b = st.session_state.compare_meta_b
                render_compact(result_b, f"{meta_b.get('idea','')} — {meta_b.get('country','')}", side="b")
            except Exception as e:
                st.error(str(e))
        # Quick winner banner — only shown if both parsed successfully
        meta_a = st.session_state.compare_meta_a
        meta_b = st.session_state.compare_meta_b
        name_a = f"{meta_a.get('idea','')} — {meta_a.get('country','')}"
        name_b = f"{meta_b.get('idea','')} — {meta_b.get('country','')}"
        try:
            result_a_parsed = MarketAnalysisResult.model_validate_json(st.session_state.compare_a)
            result_b_parsed = MarketAnalysisResult.model_validate_json(st.session_state.compare_b)
            if result_a_parsed.final_score > result_b_parsed.final_score:
                st.success(f"🏆 **{name_a}** wins with {result_a_parsed.final_score}/100 vs {result_b_parsed.final_score}/100!")
            elif result_b_parsed.final_score > result_a_parsed.final_score:
                st.success(f"🏆 **{name_b}** wins with {result_b_parsed.final_score}/100 vs {result_a_parsed.final_score}/100!")
            else:
                st.info("It's a tie!")
        except Exception:
            pass
    elif st.session_state.compare_a or st.session_state.compare_b:
        st.info("Select or analyze the second idea to see the comparison.")