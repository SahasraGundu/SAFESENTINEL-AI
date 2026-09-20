import pandas as pd
import streamlit as st

from rag.loaders import (
    infer_report_from_free_text,
    load_guidance_file,
    load_reports_from_csv,
    load_text_from_docx,
    load_text_from_pdf,
)
from rag.vectorstore import VectorStore
from ui import copilot, dashboard, investigation, patterns
from ui.components import footer_disclaimer, top_nav
from utils.config import APP_NAME, DEFAULT_CSV_PATH, GUIDANCE_DIR, TAGLINE
from utils.llm import llm_available, llm_status_message
from utils.style import CUSTOM_CSS

st.set_page_config(page_title=f"{APP_NAME} — Incident Precursor Intelligence", page_icon="◆", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
if "reports" not in st.session_state:
    st.session_state["reports"] = []  # list[dict]
if "data_version" not in st.session_state:
    st.session_state["data_version"] = 0
if "nav" not in st.session_state:
    st.session_state["nav"] = "Overview"
if "warnings" not in st.session_state:
    st.session_state["warnings"] = []


@st.cache_data(show_spinner=False)
def _load_guidance_texts() -> dict[str, str]:
    import os

    texts = {}
    if os.path.isdir(GUIDANCE_DIR):
        for fname in sorted(os.listdir(GUIDANCE_DIR)):
            if fname.endswith(".txt"):
                texts[fname] = load_guidance_file(os.path.join(GUIDANCE_DIR, fname))
    return texts


@st.cache_data(show_spinner=False)
def _load_demo_reports() -> list[dict]:
    reports, _ = load_reports_from_csv(DEFAULT_CSV_PATH, source_name="sample_reports.csv")
    return reports


def _build_store(reports: list[dict]) -> VectorStore:
    store = VectorStore()
    for r in reports:
        store.add_report(r)
    for fname, text in _load_guidance_texts().items():
        store.add_guidance_document(fname, text)
    return store


@st.cache_resource(show_spinner=False)
def _cached_store(reports_tuple, version: int) -> VectorStore:
    # reports_tuple is a hashable representation used purely as a cache key
    reports = st.session_state["reports"]
    return _build_store(reports)


def get_store() -> VectorStore:
    key = (len(st.session_state["reports"]), st.session_state["data_version"])
    return _cached_store(key, st.session_state["data_version"])


def get_df() -> pd.DataFrame:
    if not st.session_state["reports"]:
        return pd.DataFrame(columns=["report_id", "date", "location", "department", "shift", "report_type", "severity", "hazard", "description"])
    return pd.DataFrame(st.session_state["reports"])


def load_demo_data():
    st.session_state["reports"] = _load_demo_reports()
    st.session_state["data_version"] += 1
    st.session_state["warnings"] = []


def add_reports(new_reports: list[dict], warnings: list[str]):
    st.session_state["reports"] = st.session_state["reports"] + new_reports
    st.session_state["data_version"] += 1
    st.session_state["warnings"] = warnings


# ---------------------------------------------------------------------------
# Sidebar — data ingestion
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### DATA SOURCE")
    st.caption(llm_status_message())
    st.markdown("---")

    if st.button("⚡ Load Demo Data", use_container_width=True):
        load_demo_data()
        st.rerun()

    st.caption("Loads 100+ reports from the synthetic demonstration dataset.")
    st.markdown("---")

    st.markdown("**Upload reports**")
    uploaded = st.file_uploader(
        "CSV, PDF, TXT, or DOCX", type=["csv", "pdf", "txt", "docx"], accept_multiple_files=True
    )
    if uploaded and st.button("Ingest uploaded files", use_container_width=True):
        new_reports, warnings = [], []
        for f in uploaded:
            try:
                if f.name.lower().endswith(".csv"):
                    reports, w = load_reports_from_csv(f, source_name=f.name)
                    new_reports.extend(reports)
                    warnings.extend(w)
                elif f.name.lower().endswith(".pdf"):
                    text = load_text_from_pdf(f.read())
                    new_reports.append(infer_report_from_free_text(text, f.name, len(new_reports)))
                elif f.name.lower().endswith(".docx"):
                    text = load_text_from_docx(f.read())
                    new_reports.append(infer_report_from_free_text(text, f.name, len(new_reports)))
                elif f.name.lower().endswith(".txt"):
                    text = f.read().decode("utf-8", errors="ignore")
                    new_reports.append(infer_report_from_free_text(text, f.name, len(new_reports)))
            except Exception as e:
                warnings.append(f"Failed to process {f.name}: {e}")
        add_reports(new_reports, warnings)
        st.rerun()

    st.markdown("---")
    st.markdown("**Manual entry**")
    with st.form("manual_entry_sidebar"):
        text = st.text_area("Quick report text", height=80)
        if st.form_submit_button("Add report", use_container_width=True) and text.strip():
            r = infer_report_from_free_text(text, "manual", len(st.session_state["reports"]))
            add_reports([r], [])
            st.rerun()

    if st.session_state["warnings"]:
        st.markdown("---")
        for w in st.session_state["warnings"]:
            st.warning(w)

    st.markdown("---")
    st.caption(f"{len(st.session_state['reports'])} reports currently loaded.")
    st.caption("Synthetic demonstration dataset — not real incident data.")


# ---------------------------------------------------------------------------
# Top nav
# ---------------------------------------------------------------------------
top_nav(st.session_state["nav"], llm_available())

PAGES = ["Overview", "Investigate", "Patterns", "Copilot"]
nav_cols = st.columns(len(PAGES))
for col, page in zip(nav_cols, PAGES):
    if col.button(page, use_container_width=True, type=("primary" if st.session_state["nav"] == page else "secondary")):
        st.session_state["nav"] = page
        st.rerun()

st.write("")

df = get_df()

# ---------------------------------------------------------------------------
# First-time experience
# ---------------------------------------------------------------------------
if df.empty and st.session_state["nav"] == "Overview":
    st.markdown(
        f"""
        <div class="ss-welcome-hero">
            <div class="ss-hero-label" style="justify-content:center; display:flex;">Welcome to</div>
            <div class="ss-hero-number">SAFE<span class="accent">SENTINEL</span></div>
            <div class="ss-hero-sub">{TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="ss-step-card"><div class="ss-step-num">01</div><b>INGEST</b><br><span style="color:var(--text-secondary); font-size:0.85rem;">Load demo data or upload your own safety reports (CSV, PDF, TXT, DOCX).</span></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="ss-step-card"><div class="ss-step-num">02</div><b>INVESTIGATE</b><br><span style="color:var(--text-secondary); font-size:0.85rem;">The agent retrieves evidence, scores risk, and detects recurring patterns.</span></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="ss-step-card"><div class="ss-step-num">03</div><b>ACT</b><br><span style="color:var(--text-secondary); font-size:0.85rem;">Review evidence-grounded, prioritized investigation actions.</span></div>', unsafe_allow_html=True)
    st.write("")
    b1, b2 = st.columns(2)
    if b1.button("▶ Load Demo Data", use_container_width=True):
        load_demo_data()
        st.rerun()
    if b2.button("Upload Reports (see sidebar)", use_container_width=True, type="secondary"):
        pass
    footer_disclaimer()
    st.stop()

store = get_store()

if st.session_state["nav"] == "Overview":
    dashboard.render(df)
elif st.session_state["nav"] == "Investigate":
    investigation.render(df, store)
elif st.session_state["nav"] == "Patterns":
    patterns.render(df)
elif st.session_state["nav"] == "Copilot":
    copilot.render(df, store)

footer_disclaimer()
