"""
Tools: extract_risk_factors, calculate_risk_score

extract_risk_factors: keyword/rule-based extraction over the report text,
optionally refined by the LLM (Groq) when available. The rule-based pass
always runs first and is used as-is if the LLM is unavailable or returns
invalid JSON — this tool never depends on the LLM to function.

calculate_risk_score: pure Python, deterministic scoring. The LLM is
never allowed to set the numeric score; it may only be asked (elsewhere)
to narrate a score that this function already computed.
"""
from __future__ import annotations

import re
from typing import Any

from models.schemas import RiskAnalysis, RiskComponent, RiskFactors
from utils.config import RISK_THRESHOLDS, RISK_WEIGHTS
from utils.llm import chat_json, llm_available

EQUIPMENT_KEYWORDS = [
    "conveyor", "motor", "press", "forklift", "gearbox", "panel", "wiring",
    "interlock", "substation", "pump", "valve", "machine",
]
ENVIRONMENT_KEYWORDS = [
    "wet floor", "slippery", "blocked", "poor lighting", "dim", "exposed",
    "puddle", "obstruct", "narrow", "loose tile",
]
MISSING_CONTROL_PATTERNS = [
    r"no (?:\w+\s){0,2}sign", r"missing sign", r"without (?:a |)(?:goggles|vest|ppe|guard)",
    r"not present", r"did not engage", r"had not been", r"no spotter",
    r"was left open", r"not been (?:mopped|cleaned|marked)",
]
HAZARD_KEYWORDS = {
    "leak": "Equipment leakage", "slip": "Slip/fall hazard", "wet": "Wet/slippery floor",
    "ppe": "PPE non-compliance", "goggles": "PPE non-compliance", "vest": "PPE non-compliance",
    "forklift": "Forklift/vehicle proximity", "electrical": "Electrical hazard",
    "wiring": "Exposed wiring", "block": "Blocked pathway/exit", "signage": "Missing signage",
    "malfunction": "Equipment malfunction", "interlock": "Safety interlock failure",
    "lighting": "Poor lighting",
}
SEVERITY_WORDS_HIGH = ["injury", "hospital", "fire", "explosion", "collapse", "severe"]


def _extract_rule_based(report: dict[str, Any]) -> RiskFactors:
    text = report.get("description", "").lower()

    hazards = sorted({label for kw, label in HAZARD_KEYWORDS.items() if kw in text})
    if report.get("hazard") and report["hazard"] not in hazards and "Unspecified" not in str(report.get("hazard", "")):
        hazards.append(report["hazard"])

    equipment = sorted({kw for kw in EQUIPMENT_KEYWORDS if kw in text})
    environment = sorted({kw for kw in ENVIRONMENT_KEYWORDS if kw in text})

    missing_controls = []
    for pattern in MISSING_CONTROL_PATTERNS:
        m = re.search(pattern, text)
        if m:
            missing_controls.append(m.group(0))

    contributing_factors = []
    if "night" in text or "night" in str(report.get("shift", "")).lower():
        contributing_factors.append("Night shift (reduced supervision/response time)")
    if "recurring" in text or "again" in text or "repeated" in text:
        contributing_factors.append("Explicit recurrence language in report")
    if missing_controls:
        contributing_factors.append("Control/safeguard gap identified in text")

    return RiskFactors(
        hazards=hazards or ["Unspecified — see description"],
        risk_factors=hazards,
        equipment=equipment,
        environment=environment,
        people_exposed="Personnel in immediate work area" if hazards else "Unknown",
        shift=str(report.get("shift", "Unknown")),
        location=str(report.get("location", "Unknown")),
        missing_controls=missing_controls,
        contributing_factors=contributing_factors,
    )


def extract_risk_factors(report: dict[str, Any]) -> RiskFactors:
    base = _extract_rule_based(report)

    if not llm_available():
        return base

    system_prompt = (
        "You are a safety analyst assistant. You will be given a safety report and a "
        "rule-based pre-extraction. Refine and de-duplicate it. Return ONLY a JSON object "
        "with keys: hazards, risk_factors, equipment, environment, people_exposed, shift, "
        "location, missing_controls, contributing_factors. Do not invent facts not "
        "supported by the report text; you may re-word or merge duplicates from the "
        "pre-extraction, but do not add unrelated hazards."
    )
    user_prompt = (
        f"REPORT TEXT:\n{report.get('description', '')}\n\n"
        f"PRE-EXTRACTION (rule-based):\n{base.model_dump_json()}"
    )
    result = chat_json(system_prompt, user_prompt)
    if not result:
        return base
    try:
        return RiskFactors(**result)
    except Exception:
        return base


def _risk_level(score: float) -> str:
    for level, (lo, hi) in RISK_THRESHOLDS.items():
        if lo <= score <= hi:
            return level
    return "HIGH" if score > 100 else "LOW"


def calculate_risk_score(
    report: dict[str, Any],
    risk_factors: RiskFactors,
    similar_reports: list[dict[str, Any]],
    location_report_count: int,
) -> RiskAnalysis:
    """Pure, deterministic Python scoring — never delegated to the LLM."""
    w = RISK_WEIGHTS
    components: list[RiskComponent] = []

    # 1. Severity: report's own severity (1-5) scaled to weight
    severity_raw = float(report.get("severity", 2))
    severity_score = min(w["severity"], (severity_raw / 5.0) * w["severity"])
    components.append(RiskComponent(
        name="Severity", score=round(severity_score, 1), max_score=w["severity"],
        explanation=f"Reported severity {severity_raw:.0f}/5 for this {report.get('report_type', 'report')}.",
    ))

    # 2. Exposure: report type + shift + people/equipment proximity
    type_weight = {"Incident": 1.0, "Near Miss": 0.7, "Observation": 0.4}.get(str(report.get("report_type", "")), 0.5)
    shift_bonus = 0.15 if "night" in str(report.get("shift", "")).lower() else 0.0
    exposure_frac = min(1.0, type_weight + shift_bonus)
    exposure_score = exposure_frac * w["exposure"]
    components.append(RiskComponent(
        name="Exposure", score=round(exposure_score, 1), max_score=w["exposure"],
        explanation=f"Report type '{report.get('report_type', 'Observation')}' on {report.get('shift', 'an unspecified')} shift.",
    ))

    # 3. Recurrence: how many reports exist at this location + similar-report count
    similarity_hits = len([r for r in similar_reports if r.get("similarity", 0) >= 0.15])
    recurrence_frac = min(1.0, (location_report_count / 20.0) * 0.6 + (similarity_hits / 5.0) * 0.4)
    recurrence_score = recurrence_frac * w["recurrence"]
    components.append(RiskComponent(
        name="Recurrence", score=round(recurrence_score, 1), max_score=w["recurrence"],
        explanation=f"{location_report_count} total reports at this location; {similarity_hits} closely similar prior reports.",
    ))

    # 4. Control gap: missing controls identified
    control_gap_frac = min(1.0, len(risk_factors.missing_controls) / 2.0)
    control_gap_score = control_gap_frac * w["control_gap"]
    components.append(RiskComponent(
        name="Control gap", score=round(control_gap_score, 1), max_score=w["control_gap"],
        explanation=(
            f"{len(risk_factors.missing_controls)} missing-control indicator(s) found in report text."
            if risk_factors.missing_controls else "No explicit missing-control language detected."
        ),
    ))

    # 5. Historical similarity: strength of the best match
    top_similarity = max((r.get("similarity", 0.0) for r in similar_reports), default=0.0)
    hist_frac = min(1.0, top_similarity / 0.6)
    hist_score = hist_frac * w["historical_similarity"]
    components.append(RiskComponent(
        name="Historical similarity", score=round(hist_score, 1), max_score=w["historical_similarity"],
        explanation=(
            f"Closest historical match at {top_similarity:.0%} similarity."
            if similar_reports else "No similar historical reports found."
        ),
    ))

    total = round(sum(c.score for c in components), 1)
    total = max(0.0, min(100.0, total))
    level = _risk_level(total)

    explanation = (
        f"Scored {total:.0f}/100 ({level}) from severity, exposure, recurrence, "
        f"control-gap and historical-similarity components — see breakdown for detail."
    )
    return RiskAnalysis(total_score=total, risk_level=level, components=components, explanation=explanation)
