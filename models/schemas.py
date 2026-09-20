from __future__ import annotations

from pydantic import BaseModel, Field


class RiskFactors(BaseModel):
    hazards: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)
    environment: list[str] = Field(default_factory=list)
    people_exposed: str = "Unknown"
    shift: str = "Unknown"
    location: str = "Unknown"
    missing_controls: list[str] = Field(default_factory=list)
    contributing_factors: list[str] = Field(default_factory=list)


class RiskComponent(BaseModel):
    name: str
    score: float
    max_score: float
    explanation: str


class RiskAnalysis(BaseModel):
    total_score: float
    risk_level: str  # LOW / MEDIUM / HIGH
    components: list[RiskComponent]
    explanation: str


class EvidenceItem(BaseModel):
    source_type: str  # "report" or "guidance"
    source_id: str
    similarity: float
    snippet: str
    metadata: dict = Field(default_factory=dict)


class PrecursorSignal(BaseModel):
    location: str
    signal_strength: str  # "Elevated" or "Watch"
    recurring_hazards: list[str]
    similar_report_count: int
    recent_trend_pct: float
    requires_investigation: bool
    evidence_report_ids: list[str] = Field(default_factory=list)


class InvestigationAction(BaseModel):
    priority: str  # HIGH / MEDIUM / LOW
    action: str
    grounded_in: str
