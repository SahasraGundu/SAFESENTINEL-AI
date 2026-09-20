"""
Tool: generate_investigation_actions

Actions are always grounded in the actual evidence passed in (similar
reports, guidance snippets, risk factors) — never generic filler like
"improve safety." The rule-based generator runs first and is what ships
if the LLM is unavailable; the LLM (if available) is used only to
smooth phrasing of the same grounded facts, not to invent new ones.
"""
from __future__ import annotations

from typing import Any

from models.schemas import InvestigationAction, RiskAnalysis, RiskFactors
from utils.llm import chat, llm_available


def _rule_based_actions(
    report: dict[str, Any],
    risk_factors: RiskFactors,
    risk: RiskAnalysis,
    similar_reports: list[dict[str, Any]],
    guidance: list[dict[str, Any]],
) -> list[InvestigationAction]:
    actions: list[InvestigationAction] = []
    location = report.get("location", "the reported location")

    if len(similar_reports) >= 3:
        ids = ", ".join(r["report_id"] for r in similar_reports[:5])
        actions.append(InvestigationAction(
            priority="HIGH" if risk.risk_level == "HIGH" else "MEDIUM",
            action=f"Schedule a physical inspection of {location} — {len(similar_reports)} similar prior reports ({ids}) point to a recurring, not isolated, issue.",
            grounded_in=f"{len(similar_reports)} similar historical reports",
        ))

    if risk_factors.missing_controls:
        gap = risk_factors.missing_controls[0]
        actions.append(InvestigationAction(
            priority="HIGH" if risk.risk_level in ("HIGH", "MEDIUM") else "LOW",
            action=f"Close the control gap identified in the report text ('{gap}') before the next shift change.",
            grounded_in="Missing-control language extracted from report",
        ))

    if guidance:
        g = guidance[0]
        actions.append(InvestigationAction(
            priority="MEDIUM",
            action=f"Apply the response procedure in {g.get('source_document', 'the relevant SOP')} (matched at {g.get('similarity', 0):.0%} relevance) to this specific case.",
            grounded_in=f"Retrieved guidance: {g.get('source_document', 'SOP')}",
        ))

    if "night" in str(report.get("shift", "")).lower():
        actions.append(InvestigationAction(
            priority="MEDIUM",
            action=f"Review night-shift staffing and response times for {location}, since this and related reports cluster on the night shift.",
            grounded_in="Shift field on report + similar reports",
        ))

    if risk_factors.equipment:
        eq = ", ".join(risk_factors.equipment[:3])
        actions.append(InvestigationAction(
            priority="HIGH" if risk.risk_level == "HIGH" else "MEDIUM",
            action=f"Tag out and inspect the equipment referenced ({eq}) rather than resetting/cleaning and returning it to service.",
            grounded_in="Equipment keywords extracted from report text",
        ))

    if not actions:
        actions.append(InvestigationAction(
            priority="LOW",
            action=f"Log this report against {location} for trend monitoring; no corroborating evidence yet found to warrant immediate escalation.",
            grounded_in="No similar reports or guidance matched above threshold",
        ))

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    actions.sort(key=lambda a: priority_order.get(a.priority, 3))
    return actions[:5]


def generate_investigation_actions(
    report: dict[str, Any],
    risk_factors: RiskFactors,
    risk: RiskAnalysis,
    similar_reports: list[dict[str, Any]],
    guidance: list[dict[str, Any]],
) -> list[InvestigationAction]:
    actions = _rule_based_actions(report, risk_factors, risk, similar_reports, guidance)

    if not llm_available():
        return actions

    facts = "\n".join(f"- [{a.priority}] {a.action} (grounded in: {a.grounded_in})" for a in actions)
    system_prompt = (
        "You are a safety investigation writer. Rewrite the given grounded action items to be "
        "clearer and more specific in tone, in the same order, same count, same priorities, and "
        "without adding any new facts, locations, IDs, or claims not present in the input. "
        "Return one rewritten action per line, prefixed with its priority in brackets, e.g. '[HIGH] ...'."
    )
    rewritten = chat(system_prompt, facts, max_tokens=500)
    if not rewritten:
        return actions

    lines = [l.strip() for l in rewritten.strip().split("\n") if l.strip()]
    if len(lines) != len(actions):
        return actions  # fallback safety: don't trust a mismatched rewrite

    polished = []
    for line, original in zip(lines, actions):
        text = line
        for p in ("[HIGH]", "[MEDIUM]", "[LOW]"):
            text = text.replace(p, "").strip()
        polished.append(InvestigationAction(priority=original.priority, action=text, grounded_in=original.grounded_in))
    return polished
