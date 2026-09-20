# SafeSentinel AI — Incident Precursor Intelligence Agent

**Track C — Perception, Voice & Document Reasoning Agents**

> "From scattered safety reports to early incident intelligence."

An agentic RAG system that turns unstructured safety reports (near-misses,
observations, incidents) into evidence-grounded early-warning intelligence
for safety officers — with a full agent trace, transparent risk scoring,
and cross-report pattern detection.

---

## Problem

Organizations collect hundreds of safety reports that quietly contain
recurring warning signals — the same leak, the same missing signage, the
same forklift near-miss — but no one has time to read all of them closely
enough to notice the pattern before it becomes an incident.

## Solution

SafeSentinel ingests reports, retrieves relevant history and safety
guidance, extracts risk factors, computes a transparent risk score,
detects recurring hazard clusters across locations/shifts, and surfaces
**precursor signals** — locations with rising, recurring hazard activity
that warrant investigation. Every claim the system makes is traceable to
a specific retrieved report, guidance document, or computed statistic.

---

## What's real vs. what's a deliberate scope cut

Everything shown in the UI is computed, not hardcoded:
- Risk scores come from a deterministic Python scoring function (never the LLM).
- Similarity scores come from real TF-IDF + cosine-similarity retrieval.
- Pattern/precursor statistics come from pandas aggregation over the loaded dataset.
- Investigation actions are grounded in the specific evidence retrieved for that report.

Two things are intentionally out of scope for this build:
- **Voice input** (Whisper) — Track C mentions this as a fit, but it was
  cut to keep the core RAG/agent pipeline solid within the time available.
- **Image input** — explicitly marked optional in the original spec.

**Embeddings note:** retrieval uses scikit-learn TF-IDF + cosine similarity
rather than a downloaded neural embedding model. This was a deliberate
choice for reliability — it needs no model download or GPU, works
instantly offline, and is still genuine vector retrieval (real embeddings,
real ranking) rather than a shortcut. Swapping in `sentence-transformers`
embeddings later is a contained change to `rag/vectorstore.py`.

---

## Architecture

```
                    SAFETY OFFICER
                          |
                          v
                INPUT / DOCUMENT LAYER  (CSV / PDF / DOCX / TXT / manual)
                          |
                          v
               DOCUMENT PROCESSING  (rag/loaders.py — robust column
                          |          detection, metadata inference)
                          v
                    RAG PIPELINE  (rag/vectorstore.py — TF-IDF dual
                          |        collections: historical_reports,
                    VECTOR STORE    safety_guidance)
                          |
                          v
                  SUPERVISOR AGENT  (agents/supervisor_agent.py)
                          |
        +-----------------+------------------+
        |                 |                  |
        v                 v                  v
    RISK TOOLS      RETRIEVAL TOOLS    PATTERN TOOLS
  (extract_risk_    (retrieve_similar  (detect_recurring_
   factors,          _reports,          patterns,
   calculate_        retrieve_safety_   analyze_location_
   risk_score)        guidance)          trends)
        |                 |                  |
        +-----------------+------------------+
                          |
                          v
                    ACTION TOOLS  (generate_investigation_actions)
                          |
                          v
                  SAFESENTINEL UI  (Overview / Investigate / Patterns / Copilot)
```

### Agent workflow (per investigation)

```
UNDERSTAND  → parse report, extract risk factors
RETRIEVE    → similar historical reports + relevant safety guidance
ANALYZE     → deterministic risk score (5 weighted components)
CONNECT     → match against detected cross-report precursor signals
INVESTIGATE → generate prioritized, evidence-grounded actions
```

Every step is logged in the visible Agent Investigation Timeline, along
with which tool produced it — nothing is a scripted animation.

### RAG pipeline

```
DOCUMENT → LOAD → CLEAN → CHUNK → TF-IDF VECTORIZE → STORE → RETRIEVE → CONTEXT → LLM (optional)
```

Two collections are kept separate throughout: `historical_reports` and
`safety_guidance`, so the agent can distinguish "similar past reports"
from "relevant SOP guidance" in its evidence.

### Tools

| Tool | File | Purpose |
|---|---|---|
| `extract_risk_factors` | `tools/risk_tools.py` | Rule-based extraction (hazards, equipment, missing controls), optionally refined by the LLM |
| `calculate_risk_score` | `tools/risk_tools.py` | Deterministic 5-component score (severity, exposure, recurrence, control gap, historical similarity) |
| `retrieve_similar_reports` | `tools/retrieval_tools.py` | TF-IDF vector search over `historical_reports` |
| `retrieve_safety_guidance` | `tools/retrieval_tools.py` | TF-IDF vector search over `safety_guidance` |
| `analyze_location_trends` | `tools/pattern_tools.py` | pandas breakdowns by location/hazard/shift/department |
| `detect_recurring_patterns` | `tools/pattern_tools.py` | Cross-report clustering into precursor signals with a trend statistic |
| `generate_investigation_actions` | `tools/action_tools.py` | Evidence-grounded action list, LLM only polishes phrasing |

### LLM failure handling

The app runs fully without `GROQ_API_KEY` — every tool has a deterministic
fallback, and the UI clearly shows **"LLM offline"** in the top bar and
sidebar rather than pretending. When the key is present, the LLM is used
to *narrate* results the Python tools already computed (risk-factor
refinement, copilot answers, action phrasing) — it is never allowed to
invent the numeric risk score or fabricate evidence.

---

## Tech stack

- **UI:** Streamlit + custom CSS (no default Streamlit look), Plotly
- **RAG:** scikit-learn TF-IDF + cosine similarity, two named collections
- **LLM:** Groq API (`llama-3.3-70b-versatile` by default), with full offline fallback
- **Data:** pandas for all aggregation/pattern analysis
- **Structured output:** Pydantic models (`models/schemas.py`)
- **Document parsing:** pypdf, python-docx

## Folder structure

```
safesentinel/
├── app.py                     # Entry point — streamlit run app.py
├── requirements.txt
├── .env.example
├── agents/
│   └── supervisor_agent.py    # Orchestration + agent trace + copilot routing
├── tools/
│   ├── risk_tools.py
│   ├── retrieval_tools.py
│   ├── pattern_tools.py
│   └── action_tools.py
├── rag/
│   ├── vectorstore.py         # TF-IDF dual-collection vector store
│   └── loaders.py             # CSV/PDF/DOCX/TXT ingestion + metadata inference
├── models/
│   └── schemas.py             # Pydantic models
├── ui/
│   ├── dashboard.py           # Overview — hero precursor signal + KPIs + charts
│   ├── investigation.py       # 3-column AI forensic workspace
│   ├── patterns.py            # Cross-report pattern intelligence
│   ├── copilot.py             # Grounded Q&A
│   └── components.py          # Shared render helpers (cards, trace, risk panel)
├── utils/
│   ├── config.py              # Env vars, risk weights, thresholds
│   ├── llm.py                 # Groq wrapper with graceful fallback
│   └── style.py               # Custom CSS — the visual identity
└── data/
    ├── generate_data.py       # Synthetic dataset generator (documented correlations)
    ├── sample_reports.csv     # 104 synthetic reports
    └── safety_guidance/       # 5 synthetic SOP reference documents
```

---

## Installation & running locally

```bash
cd safesentinel
pip install -r requirements.txt
cp .env.example .env        # optionally add your GROQ_API_KEY
streamlit run app.py
```

The app works immediately with no API key — it will show **"LLM offline"**
and use rule-based reasoning throughout. Add `GROQ_API_KEY` to `.env` to
enable LLM-narrated copilot answers and risk-factor refinement.

### Environment variables

| Variable | Required | Default |
|---|---|---|
| `GROQ_API_KEY` | No (graceful fallback) | — |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` |

---

## Dataset

`data/sample_reports.csv` is a **synthetic demonstration dataset** (104
reports) generated by `data/generate_data.py`. It is not real incident
data — but it's not random noise either. It's built with deliberate
correlations so the pattern/precursor tools have something real to find:

- **Assembly Line 3** — recurring equipment leakage, wet floors, missing
  signage, concentrated on night shift, rising trend (the flagship
  "elevated precursor signal" demo case).
- **Warehouse B** — PPE non-compliance + blocked pathways.
- **Loading Zone** — forklift/pedestrian proximity issues.
- Several smaller locations with low, steady background activity so the
  hot spots stand out rather than everything looking equally risky.

`data/safety_guidance/` contains 5 short synthetic SOP documents
(spill response, PPE, electrical safety, machine guarding, incident
reporting) — also clearly labeled as demonstration/reference material,
not an official standard.

---

## Demo flow (for judges)

1. Launch the app — see the first-time welcome screen (no ugly empty state).
2. Click **Load Demo Data** — 104 reports + guidance index instantly.
3. **Overview** — point out the hero "N ACTIVE PRECURSOR SIGNALS," then the
   Assembly Line 3 card (34 reports, rising trend, elevated signal).
4. Click **Investigate** on that card — walk through the live agent trace
   (UNDERSTAND → RETRIEVE → ANALYZE → CONNECT → INVESTIGATE), the
   transparent risk-score breakdown, and the evidence panel showing the
   actual similar reports and SOP passages that back the conclusion.
5. **Patterns** — show the location×hazard heatmap and the report-volume
   trend as extra proof the numbers are computed, not staged.
6. **Copilot** — ask "Why is Assembly Line 3 considered a safety concern?"
   and open the trace/evidence expander to show the tool calls behind
   the answer.
7. Mention the LLM-offline fallback: the whole system already ran without
   a key — adding `GROQ_API_KEY` only improves narration quality, it
   doesn't turn on functionality that was previously fake.

## Future improvements

- Swap TF-IDF for a neural embedding model + a persistent vector DB
  (Chroma) for larger datasets and cross-lingual retrieval.
- Add Whisper-based voice intake (Track C's other suggested modality).
- Add image-based hazard detection (missing PPE, spills) as a second
  evidence source alongside text.
- Persist ingested reports across sessions instead of in-memory state.
- Multi-report batch investigation view for triaging an inbox of new reports at once.

---

*SafeSentinel provides decision support and does not replace qualified
safety professionals or established safety procedures.*
