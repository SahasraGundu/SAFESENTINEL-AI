import pandas as pd
import streamlit as st

from agents.supervisor_agent import investigate_report
from rag.vectorstore import VectorStore
from ui.components import action_list, agent_trace, evidence_card, risk_panel, section_title


def _report_picker(df: pd.DataFrame) -> dict | None:
    st.markdown('<div class="ss-hero-label">Report Investigation</div>', unsafe_allow_html=True)
    st.markdown('<div class="ss-hero-number" style="font-size:2.4rem;">AI FORENSIC WORKSPACE</div>', unsafe_allow_html=True)
    st.write("")

    tab1, tab2 = st.tabs(["Select existing report", "Analyze new report text"])
    report = None

    with tab1:
        if df.empty:
            st.info("No reports loaded yet. Load demo data from the sidebar, or use the tab to analyze new text.")
        else:
            default_loc = st.session_state.get("investigate_location")
            options = df["report_id"].tolist()
            default_idx = 0
            if default_loc:
                matches = df[df["location"] == default_loc]
                if not matches.empty:
                    default_idx = options.index(matches.iloc[0]["report_id"])
            choice = st.selectbox("Report ID", options, index=default_idx)
            row = df[df["report_id"] == choice].iloc[0]
            report = row.to_dict()

    with tab2:
        with st.form("new_report_form"):
            text = st.text_area("Report description", height=120, placeholder="Describe the observation, near miss, or incident...")
            c1, c2, c3 = st.columns(3)
            location = c1.text_input("Location", value="Assembly Line 3")
            shift = c2.selectbox("Shift", ["Morning", "Evening", "Night"])
            report_type = c3.selectbox("Report type", ["Observation", "Near Miss", "Incident"])
            severity = st.slider("Severity (1-5)", 1, 5, 2)
            submitted = st.form_submit_button("Run Agent Investigation", use_container_width=True)
            if submitted and text.strip():
                report = {
                    "report_id": "NEW-REPORT",
                    "date": pd.Timestamp.today().date().isoformat(),
                    "location": location, "department": "Unspecified",
                    "shift": shift, "report_type": report_type, "severity": severity,
                    "hazard": "Unspecified (new report)", "description": text.strip(),
                }
    return report


def render(df: pd.DataFrame, store: VectorStore):
    report = _report_picker(df)
    if report is None:
        return

    exclude_id = report["report_id"] if report["report_id"] != "NEW-REPORT" else None
    with st.spinner("Agent investigating..."):
        result = investigate_report(report, store, df, exclude_id=exclude_id)

    st.markdown('<hr class="ss-divider">', unsafe_allow_html=True)
    section_title("Agent Investigation Timeline")
    st.markdown('<div class="ss-panel">', unsafe_allow_html=True)
    agent_trace(result.trace, result.tools_used)
    tools_str = " · ".join(f"`{t}`" for t in result.tools_used)
    st.markdown(f'<div style="margin-top:10px; font-size:0.75rem; color:var(--text-dim);">TOOLS USED: {tools_str}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<hr class="ss-divider">', unsafe_allow_html=True)
    left, center, right = st.columns([1, 1.1, 1.1])

    with left:
        section_title("Original Report")
        st.markdown(
            f"""
            <div class="ss-panel">
                <div style="font-family:'JetBrains Mono',monospace; color:var(--accent-yellow); font-size:0.85rem;">{report['report_id']}</div>
                <div style="color:var(--text-dim); font-size:0.78rem; margin:6px 0 12px 0;">
                    {report.get('location','')} &middot; {report.get('department','')} &middot; {report.get('shift','')} shift &middot; {report.get('date','')}
                </div>
                <div class="ss-report-text">{report.get('description','')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        section_title("Extracted Risk Factors")
        rf = result.risk_factors
        tags_html = "".join(f'<span class="ss-tag">{h}</span>' for h in rf.hazards)
        st.markdown(f'<div class="ss-panel">{tags_html}</div>', unsafe_allow_html=True)
        if rf.missing_controls:
            st.markdown('<div style="margin-top:10px;">', unsafe_allow_html=True)
            for mc in rf.missing_controls:
                st.markdown(f'<div class="ss-tag" style="border-color:var(--risk-high-dim); color:var(--risk-high);">gap: {mc}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    with center:
        section_title("Risk Assessment")
        risk_panel(result.risk)
        section_title("Recommended Investigation")
        action_list(result.actions)

    with right:
        section_title("Evidence — Similar Reports")
        if result.similar_reports:
            for r in result.similar_reports:
                evidence_card(r["report_id"], r["similarity"], r["snippet"], extra=r["metadata"].get("location", ""))
        else:
            st.markdown('<div class="ss-panel">No similar historical reports found above the relevance threshold.</div>', unsafe_allow_html=True)

        section_title("Evidence — Safety Guidance")
        if result.guidance:
            for g in result.guidance:
                evidence_card(g["source_document"], g["similarity"], g["snippet"])
        else:
            st.markdown('<div class="ss-panel">No matching safety guidance retrieved.</div>', unsafe_allow_html=True)

        if result.precursor:
            section_title("Precursor Signal")
            p = result.precursor
            badge = "Elevated" if p.requires_investigation else "Watch"
            st.markdown(
                f"""
                <div class="ss-panel">
                    <b>{badge} signal</b> at {p.location} — {p.similar_report_count} reports,
                    {p.recent_trend_pct:+.0f}% recent trend. Recurring: {', '.join(p.recurring_hazards)}.
                </div>
                """,
                unsafe_allow_html=True,
            )
