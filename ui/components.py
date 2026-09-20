import streamlit as st

from models.schemas import InvestigationAction, PrecursorSignal, RiskAnalysis
from utils.style import risk_class


def top_nav(active: str, llm_online: bool):
    dot_class = "" if llm_online else "offline"
    status_text = "SYSTEM ONLINE" if llm_online else "SYSTEM ONLINE · LLM OFFLINE"
    st.markdown(
        f"""
        <div class="ss-topnav">
            <div class="ss-brand">
                <div class="ss-brand-mark">◆</div>
                <div class="ss-brand-text">SAFE<span>SENTINEL</span> AI</div>
            </div>
            <div class="ss-status"><div class="ss-status-dot {dot_class}"></div>{status_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str):
    st.markdown(f'<div class="ss-section-title">{text}</div>', unsafe_allow_html=True)


def precursor_card(signal: PrecursorSignal, key_prefix: str = "") -> bool:
    css_class = "high" if signal.requires_investigation else ("low" if signal.recent_trend_pct <= 0 else "medium")
    badge_class = "high" if signal.requires_investigation else "medium"
    badge_text = "Elevated" if signal.requires_investigation else "Watch"
    trend_class = "ss-trend-up" if signal.recent_trend_pct > 5 else "ss-trend-flat"
    trend_str = f"{signal.recent_trend_pct:+.0f}%" if signal.recent_trend_pct else "flat"
    hazards_str = ", ".join(signal.recurring_hazards[:4])

    st.markdown(
        f"""
        <div class="ss-precursor-card {css_class}">
            <div class="ss-precursor-head">
                <div class="ss-precursor-loc">{signal.location}</div>
                <div class="ss-badge {badge_class}">{badge_text} signal</div>
            </div>
            <div class="ss-precursor-hazards">Recurring: {hazards_str}</div>
            <div class="ss-precursor-meta">
                <div>{signal.similar_report_count} reports</div>
                <div class="{trend_class}">{trend_str} recent trend</div>
                <div>{len(signal.evidence_report_ids)} evidence refs</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return st.button(f"Investigate {signal.location}", key=f"{key_prefix}_{signal.location}", use_container_width=False)


def evidence_card(source_id: str, similarity: float, snippet: str, extra: str = ""):
    st.markdown(
        f"""
        <div class="ss-evidence-card">
            <div class="ss-evidence-head"><span>{source_id}</span><span class="ss-evidence-sim">{similarity:.0%} match</span></div>
            <div class="ss-evidence-snippet">{snippet}{(' · ' + extra) if extra else ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def agent_trace(trace, tools_used):
    for step in trace:
        tool_html = f'<div class="ss-trace-tool">tool: {step.tool}</div>' if getattr(step, "tool", None) else ""
        st.markdown(
            f"""
            <div class="ss-trace-step">
                <div class="ss-trace-stage">{step.label}</div>
                <div style="flex:1"><div class="ss-trace-detail">{step.detail}</div>{tool_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def risk_panel(risk: RiskAnalysis):
    cls = risk_class(risk.risk_level)
    st.markdown(
        f"""
        <div class="ss-panel">
            <div style="display:flex; align-items:baseline; gap:14px;">
                <div class="ss-risk-score-num {cls}">{risk.total_score:.0f}</div>
                <div>
                    <div class="ss-badge {cls}">{risk.risk_level} RISK</div>
                    <div style="color:var(--text-dim); font-size:0.78rem; margin-top:4px;">out of 100</div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )
    for c in risk.components:
        pct = (c.score / c.max_score * 100) if c.max_score else 0
        st.markdown(
            f"""
            <div class="ss-component-row">
                <div style="min-width:150px;">{c.name}</div>
                <div class="ss-component-bar-bg"><div class="ss-component-bar-fill" style="width:{pct:.0f}%;"></div></div>
                <div style="font-family:'JetBrains Mono',monospace; min-width:60px; text-align:right;">{c.score:.1f}/{c.max_score:.0f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown(f'<div style="color:var(--text-secondary); font-size:0.82rem; margin-top:10px;">{risk.explanation}</div></div>', unsafe_allow_html=True)


def action_list(actions: list[InvestigationAction]):
    for a in actions:
        cls = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(a.priority, "low")
        st.markdown(
            f"""
            <div class="ss-evidence-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div class="ss-badge {cls}" style="margin-right:10px;">{a.priority}</div>
                    <div style="flex:1; font-size:0.88rem; color:var(--text-primary);">{a.action}</div>
                </div>
                <div style="font-size:0.72rem; color:var(--text-dim); margin-top:6px;">Grounded in: {a.grounded_in}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def footer_disclaimer():
    st.markdown(
        '<div class="ss-footer-disclaimer">SafeSentinel provides decision support and does not replace '
        "qualified safety professionals or established safety procedures.</div>",
        unsafe_allow_html=True,
    )
