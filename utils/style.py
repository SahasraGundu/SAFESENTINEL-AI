CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-void: #0a0a0b;
    --bg-panel: #131315;
    --bg-panel-raised: #18181b;
    --border-thin: #2a2a2e;
    --accent-yellow: #f5c518;
    --accent-yellow-dim: #7a6210;
    --risk-high: #ef4444;
    --risk-high-dim: #3a1414;
    --risk-medium: #f97316;
    --risk-medium-dim: #3a260f;
    --risk-low: #22c55e;
    --risk-low-dim: #10321c;
    --text-primary: #f4f4f5;
    --text-secondary: #a1a1aa;
    --text-dim: #6b6b70;
}

/* ---- base app ---- */
.stApp {
    background: var(--bg-void);
    font-family: 'Inter', -apple-system, sans-serif;
    color: var(--text-primary);
}
#MainMenu, footer { visibility: hidden; height: 0; }
header[data-testid="stHeader"] { background: transparent; height: 3.5rem; }
[data-testid="stAppDeployButton"], [data-testid="stMainMenuButton"] { display: none !important; }
[data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    z-index: 999999 !important;
    background: var(--bg-panel-raised) !important;
    border: 1px solid var(--accent-yellow-dim) !important;
    border-radius: 4px !important;
    margin: 8px !important;
}
[data-testid="stExpandSidebarButton"] svg, [data-testid="collapsedControl"] svg { fill: var(--accent-yellow) !important; }
.block-container { padding-top: 1.2rem; max-width: 1280px; }

/* ---- kill default streamlit look ---- */
div[data-testid="stMetric"] {
    background: var(--bg-panel);
    border: 1px solid var(--border-thin);
    border-radius: 4px;
    padding: 14px 18px;
}
div[data-testid="stMetricValue"] { color: var(--text-primary); font-weight: 700; }
div[data-testid="stMetricLabel"] { color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; font-size: 0.72rem; }

.stButton > button {
    background: var(--accent-yellow);
    color: #0a0a0b;
    border: none;
    border-radius: 3px;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-size: 0.78rem;
    padding: 0.55rem 1.1rem;
    transition: all 0.15s ease;
}
.stButton > button:hover { background: #ffd633; box-shadow: 0 0 16px rgba(245, 197, 24, 0.35); }
.stButton > button[kind="secondary"] {
    background: transparent;
    color: var(--accent-yellow);
    border: 1px solid var(--accent-yellow-dim);
    text-transform: none;
    font-weight: 600;
}

section[data-testid="stSidebar"] {
    background: #0d0d0f;
    border-right: 1px solid var(--border-thin);
}
section[data-testid="stSidebar"] * { color: var(--text-secondary) !important; }

input, textarea, select {
    background: var(--bg-panel-raised) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-thin) !important;
    border-radius: 3px !important;
}

/* ---- top nav ---- */
.ss-topnav {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 0 18px 0; border-bottom: 1px solid var(--border-thin); margin-bottom: 22px;
}
.ss-brand { display: flex; align-items: center; gap: 10px; }
.ss-brand-mark {
    width: 30px; height: 30px; border-radius: 6px;
    background: linear-gradient(145deg, var(--accent-yellow), #b8930d);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; color: #0a0a0b; font-size: 15px;
}
.ss-brand-text { font-weight: 800; letter-spacing: 0.06em; font-size: 1.05rem; }
.ss-brand-text span { color: var(--accent-yellow); }
.ss-status { display: flex; align-items: center; gap: 8px; font-size: 0.72rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; }
.ss-status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--risk-low); box-shadow: 0 0 8px var(--risk-low); }
.ss-status-dot.offline { background: var(--text-dim); box-shadow: none; }

/* ---- editorial headings ---- */
.ss-hero-label { color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.15em; font-size: 0.72rem; font-weight: 600; margin-bottom: 6px; }
.ss-hero-number { font-size: 4.2rem; font-weight: 800; line-height: 1; letter-spacing: -0.02em; color: var(--text-primary); }
.ss-hero-number .accent { color: var(--accent-yellow); }
.ss-hero-sub { color: var(--text-secondary); font-size: 1rem; margin-top: 6px; }
.ss-hero-sub .warn { color: var(--risk-high); font-weight: 700; }

.ss-section-title {
    font-size: 0.78rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--text-dim); margin: 30px 0 14px 0; padding-bottom: 8px;
    border-bottom: 1px solid var(--border-thin);
}

/* ---- precursor cards ---- */
.ss-precursor-card {
    background: var(--bg-panel); border: 1px solid var(--border-thin); border-left: 3px solid var(--risk-medium);
    border-radius: 4px; padding: 16px 18px; margin-bottom: 12px;
}
.ss-precursor-card.high { border-left-color: var(--risk-high); }
.ss-precursor-card.low { border-left-color: var(--risk-low); }
.ss-precursor-head { display: flex; justify-content: space-between; align-items: baseline; }
.ss-precursor-loc { font-weight: 700; font-size: 1.05rem; }
.ss-badge { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; padding: 3px 8px; border-radius: 3px; }
.ss-badge.high { background: var(--risk-high-dim); color: var(--risk-high); }
.ss-badge.medium { background: var(--risk-medium-dim); color: var(--risk-medium); }
.ss-badge.low { background: var(--risk-low-dim); color: var(--risk-low); }
.ss-precursor-meta { display: flex; gap: 18px; margin-top: 10px; font-size: 0.82rem; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; }
.ss-precursor-hazards { margin-top: 8px; font-size: 0.85rem; color: var(--text-secondary); }
.ss-trend-up { color: var(--risk-high); font-weight: 700; }
.ss-trend-flat { color: var(--text-dim); font-weight: 700; }

/* ---- evidence cards ---- */
.ss-evidence-card {
    background: var(--bg-panel-raised); border: 1px solid var(--border-thin); border-radius: 4px;
    padding: 12px 14px; margin-bottom: 10px;
}
.ss-evidence-head { display: flex; justify-content: space-between; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--accent-yellow); font-weight: 600; }
.ss-evidence-sim { color: var(--text-dim); }
.ss-evidence-snippet { font-size: 0.85rem; color: var(--text-secondary); margin-top: 6px; line-height: 1.5; }

/* ---- agent trace ---- */
.ss-trace-step { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-bottom: 1px dashed var(--border-thin); }
.ss-trace-stage { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700; color: var(--accent-yellow); text-transform: uppercase; min-width: 90px; letter-spacing: 0.05em; }
.ss-trace-detail { font-size: 0.83rem; color: var(--text-secondary); }
.ss-trace-tool { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--text-dim); }

/* ---- risk score panel ---- */
.ss-risk-score-num { font-size: 3rem; font-weight: 800; line-height: 1; font-family: 'JetBrains Mono', monospace; }
.ss-risk-score-num.high { color: var(--risk-high); }
.ss-risk-score-num.medium { color: var(--risk-medium); }
.ss-risk-score-num.low { color: var(--risk-low); }
.ss-component-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid var(--border-thin); font-size: 0.85rem; }
.ss-component-bar-bg { background: var(--border-thin); height: 5px; border-radius: 3px; flex: 1; margin: 0 12px; overflow: hidden; }
.ss-component-bar-fill { background: var(--accent-yellow); height: 100%; }

.ss-panel {
    background: var(--bg-panel); border: 1px solid var(--border-thin); border-radius: 4px; padding: 18px 20px;
}
.ss-divider { border: none; border-top: 1px solid var(--border-thin); margin: 20px 0; }
.ss-report-text { font-size: 0.9rem; line-height: 1.7; color: var(--text-secondary); white-space: pre-wrap; }
.ss-tag { display: inline-block; background: var(--bg-panel-raised); border: 1px solid var(--border-thin); color: var(--text-secondary); font-size: 0.72rem; padding: 3px 9px; border-radius: 3px; margin: 2px 4px 2px 0; }
.ss-footer-disclaimer { color: var(--text-dim); font-size: 0.75rem; text-align: center; margin-top: 40px; padding-top: 16px; border-top: 1px solid var(--border-thin); }

.ss-welcome-hero { text-align: center; padding: 60px 20px 20px 20px; }
.ss-step-card { background: var(--bg-panel); border: 1px solid var(--border-thin); border-radius: 4px; padding: 20px; text-align: left; }
.ss-step-num { font-family: 'JetBrains Mono', monospace; color: var(--accent-yellow); font-weight: 800; font-size: 1.3rem; }
</style>
"""


def risk_class(level: str) -> str:
    return {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(level, "low")
