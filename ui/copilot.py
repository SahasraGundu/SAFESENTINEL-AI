import pandas as pd
import streamlit as st

from agents.supervisor_agent import answer_copilot_query
from rag.vectorstore import VectorStore
from ui.components import agent_trace, evidence_card, section_title

SUGGESTED = [
    "Why is Assembly Line 3 considered a safety concern?",
    "What hazards are increasing?",
    "Which location needs investigation?",
    "Compare night shift and day shift.",
]


def render(df: pd.DataFrame, store: VectorStore):
    st.markdown('<div class="ss-hero-label">AI Copilot</div>', unsafe_allow_html=True)
    st.markdown('<div class="ss-hero-number" style="font-size:2.4rem;">SAFETY INVESTIGATION COPILOT</div>', unsafe_allow_html=True)
    st.markdown('<div class="ss-hero-sub">Ask about risk, evidence, or patterns — every answer is grounded in retrieved reports and guidance.</div>', unsafe_allow_html=True)
    st.write("")

    cols = st.columns(len(SUGGESTED))
    picked = None
    for c, q in zip(cols, SUGGESTED):
        if c.button(q, use_container_width=True):
            picked = q

    query = st.chat_input("Ask the safety investigation copilot...")
    query = picked or query

    if "copilot_history" not in st.session_state:
        st.session_state["copilot_history"] = []

    if query:
        with st.spinner("Investigating..."):
            result = answer_copilot_query(query, store, df)
        st.session_state["copilot_history"].insert(0, {"query": query, "result": result})

    for turn in st.session_state["copilot_history"]:
        st.markdown('<hr class="ss-divider">', unsafe_allow_html=True)
        st.markdown(f'<div style="color:var(--accent-yellow); font-weight:700; font-size:0.95rem;">▸ {turn["query"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ss-panel" style="margin-top:10px;">{turn["result"]["answer"]}</div>', unsafe_allow_html=True)

        with st.expander("Agent trace & evidence"):
            agent_trace(turn["result"]["trace"], turn["result"]["tools_used"])
            ev = turn["result"]["evidence"]
            if ev.get("similar_reports"):
                section_title("Evidence — Reports")
                for r in ev["similar_reports"][:5]:
                    evidence_card(r["report_id"], r["similarity"], r["snippet"])
            if ev.get("guidance"):
                section_title("Evidence — Guidance")
                for g in ev["guidance"][:3]:
                    evidence_card(g["source_document"], g["similarity"], g["snippet"])
