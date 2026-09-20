import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tools.pattern_tools import analyze_location_trends, detect_recurring_patterns, reports_over_time
from ui.components import precursor_card, section_title

PLOTLY_TEMPLATE = dict(
    paper_bgcolor="#0a0a0b", plot_bgcolor="#0a0a0b",
    font=dict(color="#a1a1aa", family="Inter"),
    margin=dict(l=10, r=10, t=30, b=10),
)


def _style_fig(fig):
    fig.update_layout(**PLOTLY_TEMPLATE)
    fig.update_xaxes(gridcolor="#2a2a2e", zeroline=False)
    fig.update_yaxes(gridcolor="#2a2a2e", zeroline=False)
    return fig


def render(df: pd.DataFrame):
    signals = detect_recurring_patterns(df)
    elevated = [s for s in signals if s.requires_investigation]
    trends = analyze_location_trends(df)

    # ---- HERO ----
    c1, c2 = st.columns([2.2, 1])
    with c1:
        st.markdown('<div class="ss-hero-label">Incident Precursor Intelligence</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="ss-hero-number">{len(signals)} <span class="accent">ACTIVE</span> PRECURSOR SIGNALS</div>',
            unsafe_allow_html=True,
        )
        warn = f'<span class="warn">{len(elevated)} require immediate investigation</span>' if elevated else "No signals currently require immediate investigation"
        st.markdown(f'<div class="ss-hero-sub">{warn}</div>', unsafe_allow_html=True)
    with c2:
        m1, m2 = st.columns(2)
        m1.metric("Reports analyzed", len(df))
        m2.metric("Locations monitored", df["location"].nunique() if not df.empty else 0)
        m3, m4 = st.columns(2)
        high_risk_reports = int((df["severity"] >= 4).sum()) if not df.empty else 0
        m3.metric("High-severity reports", high_risk_reports)
        m4.metric("Elevated signals", len(elevated))

    st.markdown('<hr class="ss-divider">', unsafe_allow_html=True)

    # ---- RISK TREND ----
    section_title("Report Volume Trend")
    ts = reports_over_time(df, freq="W")
    if not ts.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ts["period"], y=ts["count"], mode="lines", fill="tozeroy",
            line=dict(color="#f5c518", width=2), fillcolor="rgba(245,197,24,0.08)",
        ))
        _style_fig(fig)
        fig.update_layout(height=220, showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No dated reports available to plot a trend yet.")

    # ---- PRECURSOR SIGNALS ----
    section_title("Precursor Signals")
    if not signals:
        st.markdown(
            '<div class="ss-panel">No recurring hazard patterns detected yet — load more reports to surface signals.</div>',
            unsafe_allow_html=True,
        )
    else:
        for s in signals[:6]:
            clicked = precursor_card(s, key_prefix="dash")
            if clicked:
                st.session_state["investigate_location"] = s.location
                st.session_state["nav"] = "Investigate"
                st.rerun()

    st.markdown('<hr class="ss-divider">', unsafe_allow_html=True)

    # ---- TOP HAZARDS / LOCATIONS / SHIFTS ----
    col1, col2, col3 = st.columns(3)
    with col1:
        section_title("Top Hazards")
        haz_df = pd.DataFrame(trends["top_hazards"][:6])
        if not haz_df.empty:
            fig = go.Figure(go.Bar(
                x=haz_df["count"], y=haz_df["hazard"], orientation="h",
                marker_color="#f5c518",
            ))
            _style_fig(fig)
            fig.update_layout(height=260, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col2:
        section_title("Top Locations")
        loc_df = pd.DataFrame(trends["top_locations"][:6])
        if not loc_df.empty:
            fig = go.Figure(go.Bar(
                x=loc_df["count"], y=loc_df["location"], orientation="h",
                marker_color="#ef4444",
            ))
            _style_fig(fig)
            fig.update_layout(height=260, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col3:
        section_title("Shift Patterns")
        shift_df = pd.DataFrame(trends["shift_breakdown"])
        if not shift_df.empty:
            fig = go.Figure(go.Pie(
                labels=shift_df["shift"], values=shift_df["count"], hole=0.55,
                marker=dict(colors=["#f5c518", "#f97316", "#6b6b70", "#3a1414"]),
            ))
            _style_fig(fig)
            fig.update_layout(height=260, showlegend=True, legend=dict(font=dict(size=10)))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
