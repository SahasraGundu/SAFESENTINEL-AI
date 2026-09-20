"""
Tools: analyze_location_trends, detect_recurring_patterns

Everything here is computed from the actual in-memory report DataFrame
with pandas — no hardcoded counts or trend figures.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from models.schemas import PrecursorSignal


def _to_datetime(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def analyze_location_trends(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"top_locations": [], "top_hazards": [], "shift_breakdown": [], "department_breakdown": []}

    top_locations = (
        df.groupby("location").size().sort_values(ascending=False).reset_index(name="count")
    ).to_dict("records")

    top_hazards = (
        df.groupby("hazard").size().sort_values(ascending=False).reset_index(name="count")
    ).to_dict("records")

    shift_breakdown = (
        df.groupby("shift").size().sort_values(ascending=False).reset_index(name="count")
    ).to_dict("records")

    department_breakdown = (
        df.groupby("department").size().sort_values(ascending=False).reset_index(name="count")
    ).to_dict("records")

    return {
        "top_locations": top_locations,
        "top_hazards": top_hazards,
        "shift_breakdown": shift_breakdown,
        "department_breakdown": department_breakdown,
    }


def location_hazard_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return pd.crosstab(df["location"], df["hazard"])


def reports_over_time(df: pd.DataFrame, freq: str = "W") -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["period", "count"])
    d = _to_datetime(df)
    d = d.dropna(subset=["_date"])
    series = d.set_index("_date").resample(freq).size()
    return series.reset_index().rename(columns={"_date": "period", 0: "count"})


def _recent_trend_pct(dates: pd.Series) -> float:
    """Compare report volume in the most recent third of the date range
    vs. the earlier two-thirds, as a % change."""
    dates = dates.dropna().sort_values()
    if len(dates) < 6:
        return 0.0
    split = int(len(dates) * (2 / 3))
    earlier, recent = dates.iloc[:split], dates.iloc[split:]
    earlier_span_days = max((earlier.max() - earlier.min()).days, 1) if len(earlier) > 1 else 1
    recent_span_days = max((recent.max() - recent.min()).days, 1) if len(recent) > 1 else 1
    earlier_rate = len(earlier) / earlier_span_days
    recent_rate = len(recent) / recent_span_days
    if earlier_rate == 0:
        return 100.0 if recent_rate > 0 else 0.0
    return round(((recent_rate - earlier_rate) / earlier_rate) * 100, 1)


def detect_recurring_patterns(df: pd.DataFrame, min_reports: int = 5) -> list[PrecursorSignal]:
    """Identifies locations with recurring hazard clusters and a report-volume
    trend, and packages them as precursor signals."""
    if df.empty:
        return []

    d = _to_datetime(df)
    signals: list[PrecursorSignal] = []

    for location, group in d.groupby("location"):
        if len(group) < min_reports:
            continue

        hazard_counts = group["hazard"].value_counts()
        recurring_hazards = [h for h, c in hazard_counts.items() if c >= 2 and "Unspecified" not in str(h)]
        if not recurring_hazards:
            continue

        trend_pct = _recent_trend_pct(group["_date"])
        distinct_hazards = len(recurring_hazards)

        # Elevated if: 2+ distinct recurring hazards AND (sufficient volume, or a
        # meaningfully rising trend backed by enough reports to be more than noise)
        elevated = distinct_hazards >= 2 and (len(group) >= 15 or (trend_pct > 25 and len(group) >= 10))
        strength = "Elevated" if elevated else "Watch"

        signals.append(
            PrecursorSignal(
                location=location,
                signal_strength=strength,
                recurring_hazards=recurring_hazards[:5],
                similar_report_count=len(group),
                recent_trend_pct=trend_pct,
                requires_investigation=elevated,
                evidence_report_ids=group["report_id"].tolist()[:10],
            )
        )

    signals.sort(key=lambda s: (s.requires_investigation, s.similar_report_count), reverse=True)
    return signals
