"""
Supervisor agent.

Orchestrates the real tools (retrieval, risk, pattern, action) rather
than asking the LLM to invent results. Two entry points:

  - investigate_report(): full pipeline for a single report, used by
    the Investigation page. Produces an explicit step-by-step trace.
  - answer_copilot_query(): routes a free-text question to the subset
    of tools relevant to it (keyword-based routing — deterministic and
    auditable, not a hidden LLM decision), then asks the LLM to phrase
    an answer grounded only in what those tools returned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from models.schemas import InvestigationAction, PrecursorSignal, RiskAnalysis, RiskFactors
from rag.vectorstore import VectorStore
from tools.action_tools import generate_investigation_actions
from tools.pattern_tools import analyze_location_trends, detect_recurring_patterns
from tools.retrieval_tools import retrieve_safety_guidance, retrieve_similar_reports
from tools.risk_tools import calculate_risk_score, extract_risk_factors
from utils.llm import chat, llm_available


@dataclass
class TraceStep:
    label: str
    detail: str
    tool: str | None = None


@dataclass
class InvestigationResult:
    report: dict[str, Any]
    risk_factors: RiskFactors
    risk: RiskAnalysis
    similar_reports: list[dict[str, Any]]
    guidance: list[dict[str, Any]]
    actions: list[InvestigationAction]
    precursor: PrecursorSignal | None
    trace: list[TraceStep] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)


def investigate_report(
    report: dict[str, Any],
    store: VectorStore,
    df: pd.DataFrame,
    exclude_id: str | None = None,
) -> InvestigationResult:
    trace: list[TraceStep] = []
    tools_used: list[str] = []

    trace.append(TraceStep("UNDERSTAND", f"Parsed report {report.get('report_id', '(new)')} from {report.get('location', 'unknown location')}."))

    risk_factors = extract_risk_factors(report)
    tools_used.append("extract_risk_factors")
    trace.append(TraceStep(
        "UNDERSTAND",
        f"Extracted {len(risk_factors.hazards)} hazard(s), {len(risk_factors.missing_controls)} control gap(s).",
        tool="extract_risk_factors",
    ))

    similar_reports = retrieve_similar_reports(store, report.get("description", ""), top_k=5, exclude_id=exclude_id)
    tools_used.append("retrieve_similar_reports")
    trace.append(TraceStep(
        "RETRIEVE", f"Retrieved {len(similar_reports)} similar historical report(s) via vector search.",
        tool="retrieve_similar_reports",
    ))

    guidance = retrieve_safety_guidance(store, " ".join(risk_factors.hazards + risk_factors.equipment) or report.get("description", ""), top_k=3)
    tools_used.append("retrieve_safety_guidance")
    trace.append(TraceStep(
        "RETRIEVE", f"Retrieved {len(guidance)} relevant safety guidance passage(s).",
        tool="retrieve_safety_guidance",
    ))

    location = report.get("location", "")
    location_report_count = int((df["location"] == location).sum()) if not df.empty else 0
    risk = calculate_risk_score(report, risk_factors, similar_reports, location_report_count)
    tools_used.append("calculate_risk_score")
    trace.append(TraceStep(
        "ANALYZE", f"Calculated risk score {risk.total_score:.0f}/100 ({risk.risk_level}) from 5 weighted components.",
        tool="calculate_risk_score",
    ))

    all_signals = detect_recurring_patterns(df) if not df.empty else []
    tools_used.append("detect_recurring_patterns")
    precursor = next((s for s in all_signals if s.location == location), None)
    if precursor:
        trace.append(TraceStep(
            "CONNECT",
            f"Location matches an existing precursor signal: {precursor.signal_strength} ({precursor.similar_report_count} reports, {precursor.recent_trend_pct:+.0f}% trend).",
            tool="detect_recurring_patterns",
        ))
    else:
        trace.append(TraceStep("CONNECT", "No elevated recurring pattern detected for this location yet.", tool="detect_recurring_patterns"))

    actions = generate_investigation_actions(report, risk_factors, risk, similar_reports, guidance)
    tools_used.append("generate_investigation_actions")
    trace.append(TraceStep(
        "INVESTIGATE", f"Generated {len(actions)} evidence-grounded investigation action(s).",
        tool="generate_investigation_actions",
    ))

    return InvestigationResult(
        report=report, risk_factors=risk_factors, risk=risk, similar_reports=similar_reports,
        guidance=guidance, actions=actions, precursor=precursor, trace=trace, tools_used=tools_used,
    )


# --------------------------------------------------------------------------
# Copilot: keyword-based tool routing + grounded LLM phrasing
# --------------------------------------------------------------------------

def _route_query(query: str) -> list[str]:
    q = query.lower()
    tools: list[str] = []
    if any(k in q for k in ["similar", "like this", "history", "historical"]):
        tools.append("retrieve_similar_reports")
    if any(k in q for k in ["guidance", "sop", "procedure", "policy", "applies"]):
        tools.append("retrieve_safety_guidance")
    if any(k in q for k in ["risk", "why is", "why was", "concern", "classified", "dangerous"]):
        tools.append("retrieve_similar_reports")
        tools.append("detect_recurring_patterns")
    if any(k in q for k in ["pattern", "increasing", "recurring", "trend", "hazards are"]):
        tools.append("detect_recurring_patterns")
    if any(k in q for k in ["location", "which location", "investigate", "worst", "needs investigation"]):
        tools.append("analyze_location_trends")
        tools.append("detect_recurring_patterns")
    if any(k in q for k in ["shift", "night", "day", "morning", "evening", "compare"]):
        tools.append("analyze_location_trends")
    if not tools:
        tools = ["retrieve_similar_reports", "detect_recurring_patterns"]
    # de-dup, preserve order
    seen = set()
    return [t for t in tools if not (t in seen or seen.add(t))]


def answer_copilot_query(query: str, store: VectorStore, df: pd.DataFrame) -> dict[str, Any]:
    tools_used = _route_query(query)
    trace: list[TraceStep] = [TraceStep("UNDERSTAND", f"Routed query to tools: {', '.join(tools_used)}.")]
    context_parts = []
    evidence: dict[str, Any] = {}

    if "retrieve_similar_reports" in tools_used:
        results = retrieve_similar_reports(store, query, top_k=5)
        evidence["similar_reports"] = results
        trace.append(TraceStep("RETRIEVE", f"Found {len(results)} similar reports.", tool="retrieve_similar_reports"))
        context_parts.append(
            "SIMILAR REPORTS:\n" + "\n".join(f"- {r['report_id']} ({r['similarity']:.0%}): {r['snippet']}" for r in results)
        )

    if "retrieve_safety_guidance" in tools_used:
        results = retrieve_safety_guidance(store, query, top_k=3)
        evidence["guidance"] = results
        trace.append(TraceStep("RETRIEVE", f"Found {len(results)} guidance passages.", tool="retrieve_safety_guidance"))
        context_parts.append(
            "SAFETY GUIDANCE:\n" + "\n".join(f"- {g['source_document']} ({g['similarity']:.0%}): {g['snippet']}" for g in results)
        )

    if "detect_recurring_patterns" in tools_used and not df.empty:
        signals = detect_recurring_patterns(df)
        evidence["precursor_signals"] = signals
        trace.append(TraceStep("ANALYZE", f"Detected {len(signals)} location(s) with recurring patterns.", tool="detect_recurring_patterns"))
        context_parts.append(
            "PRECURSOR SIGNALS:\n" + "\n".join(
                f"- {s.location}: {s.signal_strength}, {s.similar_report_count} reports, trend {s.recent_trend_pct:+.0f}%, hazards: {', '.join(s.recurring_hazards)}"
                for s in signals[:6]
            )
        )

    if "analyze_location_trends" in tools_used and not df.empty:
        trends = analyze_location_trends(df)
        evidence["trends"] = trends
        trace.append(TraceStep("ANALYZE", "Computed location/hazard/shift breakdowns.", tool="analyze_location_trends"))
        context_parts.append(
            "LOCATION/SHIFT DATA:\n"
            f"Top locations: {trends['top_locations'][:5]}\n"
            f"Top hazards: {trends['top_hazards'][:5]}\n"
            f"Shift breakdown: {trends['shift_breakdown']}"
        )

    context = "\n\n".join(context_parts) if context_parts else "No matching data was retrieved for this query."
    trace.append(TraceStep("INVESTIGATE", "Composed grounded answer from retrieved evidence."))

    if llm_available():
        system_prompt = (
            "You are SafeSentinel's safety investigation copilot. Answer the safety officer's "
            "question using ONLY the evidence provided below. Be concise (4-8 sentences). "
            "Cite specific report IDs, document names, or numbers from the evidence where relevant. "
            "If the evidence doesn't support a confident answer, say so plainly rather than guessing. "
            "Never claim certainty about future incidents — use language like 'elevated precursor "
            "signal' or 'investigation recommended' rather than predictions."
        )
        user_prompt = f"QUESTION: {query}\n\nEVIDENCE:\n{context}"
        answer = chat(system_prompt, user_prompt, max_tokens=500)
    else:
        answer = None

    if not answer:
        # Deterministic fallback answer built directly from the evidence, no LLM needed.
        answer = _fallback_answer(query, evidence)

    return {"answer": answer, "evidence": evidence, "tools_used": tools_used, "trace": trace}


def _fallback_answer(query: str, evidence: dict[str, Any]) -> str:
    parts = ["LLM is offline, so here is the retrieved evidence directly:"]
    if evidence.get("similar_reports"):
        top = evidence["similar_reports"][:3]
        parts.append("Similar reports: " + "; ".join(f"{r['report_id']} ({r['similarity']:.0%})" for r in top))
    if evidence.get("guidance"):
        top = evidence["guidance"][:2]
        parts.append("Relevant guidance: " + "; ".join(f"{g['source_document']} ({g['similarity']:.0%})" for g in top))
    if evidence.get("precursor_signals"):
        elevated = [s for s in evidence["precursor_signals"] if s.requires_investigation][:3]
        if elevated:
            parts.append("Elevated precursor signals: " + "; ".join(f"{s.location} ({s.similar_report_count} reports, {s.recent_trend_pct:+.0f}%)" for s in elevated))
    if evidence.get("trends"):
        t = evidence["trends"]
        if t.get("top_locations"):
            parts.append(f"Top location by report count: {t['top_locations'][0]['location']} ({t['top_locations'][0]['count']} reports).")
    if len(parts) == 1:
        parts.append("No matching evidence was found for this question in the current dataset.")
    return " ".join(parts)
