import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tools.pattern_tools import analyze_location_trends, detect_recurring_patterns, location_hazard_heatmap, reports_over_time
from ui.components import precursor_card, section_title
from ui.dashboard import _style_fig


def render(df: pd.DataFrame):
    st.markdown('<div class="ss-hero-label">Pattern Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="ss-hero-number" style="font-size:2.4rem;">CROSS-REPORT PATTERN ANALYSIS</div>', unsafe_allow_html=True)
    st.write("")

    if df.empty:
        st.info("Load demo data or upload reports to see pattern analysis.")
        return

    trends = analyze_location_trends(df)
    signals = detect_recurring_patterns(df)

    section_title("Location × Hazard Heatmap")
    heat = location_hazard_heatmap(df)
    if not heat.empty:
        fig = go.Figure(go.Heatmap(
            z=heat.values, x=heat.columns, y=heat.index,
            colorscale=[[0, "#131315"], [0.5, "#7a4a10"], [1, "#f5c518"]],
            showscale=False,
        ))
        _style_fig(fig)
        fig.update_layout(height=340)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    col1, col2 = st.columns(2)
    with col1:
        section_title("Reports Over Time")
        ts = reports_over_time(df, freq="W")
        if not ts.empty:
            fig = go.Figure(go.Scatter(x=ts["period"], y=ts["count"], mode="lines+markers", line=dict(color="#f5c518", width=2)))
            _style_fig(fig)
            fig.update_layout(height=280)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col2:
        section_title("Risk Distribution")
        sev_bins = pd.cut(df["severity"], bins=[0, 2, 3, 5], labels=["Low", "Medium", "High"])
        counts = sev_bins.value_counts().reindex(["Low", "Medium", "High"]).fillna(0)
        fig = go.Figure(go.Pie(
            labels=counts.index, values=counts.values, hole=0.55,
            marker=dict(colors=["#22c55e", "#f97316", "#ef4444"]),
        ))
        _style_fig(fig)
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    col3, col4 = st.columns(2)
    with col3:
        section_title("Department Breakdown")
        dep_df = pd.DataFrame(trends["department_breakdown"])
        if not dep_df.empty:
            fig = go.Figure(go.Bar(x=dep_df["department"], y=dep_df["count"], marker_color="#f5c518"))
            _style_fig(fig)
            fig.update_layout(height=260)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col4:
        section_title("Hazard Frequency")
        haz_df = pd.DataFrame(trends["top_hazards"])
        if not haz_df.empty:
            fig = go.Figure(go.Bar(x=haz_df["hazard"], y=haz_df["count"], marker_color="#ef4444"))
            _style_fig(fig)
            fig.update_layout(height=260, xaxis=dict(tickangle=-30))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown('<hr class="ss-divider">', unsafe_allow_html=True)
    section_title("Emerging Precursor Signals")
    if not signals:
        st.markdown('<div class="ss-panel">No recurring patterns detected in the current dataset.</div>', unsafe_allow_html=True)
    for s in signals:
        clicked = precursor_card(s, key_prefix="pat")
        if clicked:
            st.session_state["investigate_location"] = s.location
            st.session_state["nav"] = "Investigate"
            st.rerun()
