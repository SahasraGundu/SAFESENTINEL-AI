"""
Loaders for building the working report dataset from various input types,
and for loading the safety-guidance reference documents.
"""
from __future__ import annotations

import io
import re
from datetime import date
from typing import Any

import pandas as pd

# Column-name candidates, in priority order, for robust CSV detection.
COLUMN_CANDIDATES = {
    "description": ["description", "report", "text", "observation", "incident", "details", "notes"],
    "location": ["location", "area", "site", "zone"],
    "department": ["department", "dept", "team"],
    "shift": ["shift"],
    "date": ["date", "reported_date", "timestamp"],
    "severity": ["severity", "risk_level", "priority"],
    "report_type": ["report_type", "type", "category"],
    "report_id": ["report_id", "id", "ref", "reference"],
    "hazard": ["hazard", "hazard_type"],
}


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    lower_map = {c.lower().strip(): c for c in columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    # fuzzy contains match as a fallback
    for cand in candidates:
        for lc, orig in lower_map.items():
            if cand in lc:
                return orig
    return None


def detect_columns(df: pd.DataFrame) -> dict[str, str | None]:
    cols = list(df.columns)
    return {field: _find_column(cols, cands) for field, cands in COLUMN_CANDIDATES.items()}


def load_reports_from_csv(file_like, source_name: str = "uploaded.csv") -> tuple[list[dict[str, Any]], list[str]]:
    """Returns (reports, warnings). Robust to unknown/partial column names."""
    warnings: list[str] = []
    df = pd.read_csv(file_like)
    mapping = detect_columns(df)

    if mapping["description"] is None:
        # Fall back to concatenating all text-like columns
        warnings.append(
            f"No obvious description column found in {source_name}; concatenating text columns as a fallback."
        )

    reports = []
    for i, row in df.iterrows():
        if mapping["description"]:
            desc = str(row[mapping["description"]])
        else:
            text_cols = [c for c in df.columns if df[c].dtype == object]
            desc = " | ".join(str(row[c]) for c in text_cols if pd.notna(row[c]))

        report = {
            "report_id": str(row[mapping["report_id"]]) if mapping["report_id"] else f"UP-{1000+i}",
            "date": str(row[mapping["date"]]) if mapping["date"] and pd.notna(row[mapping["date"]]) else date.today().isoformat(),
            "location": str(row[mapping["location"]]) if mapping["location"] and pd.notna(row[mapping["location"]]) else "Unspecified (inferred: not provided)",
            "department": str(row[mapping["department"]]) if mapping["department"] and pd.notna(row[mapping["department"]]) else "Unspecified (inferred: not provided)",
            "shift": str(row[mapping["shift"]]) if mapping["shift"] and pd.notna(row[mapping["shift"]]) else "Unspecified (inferred: not provided)",
            "report_type": str(row[mapping["report_type"]]) if mapping["report_type"] and pd.notna(row[mapping["report_type"]]) else "Observation (inferred default)",
            "severity": int(row[mapping["severity"]]) if mapping["severity"] and pd.notna(row[mapping["severity"]]) and str(row[mapping["severity"]]).isdigit() else 2,
            "hazard": str(row[mapping["hazard"]]) if mapping["hazard"] and pd.notna(row[mapping["hazard"]]) else "Unspecified (inferred: not provided)",
            "description": desc.strip(),
        }
        if report["description"]:
            reports.append(report)

    if not reports:
        warnings.append(f"No usable rows found in {source_name}.")
    return reports, warnings


def load_text_from_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("pypdf is not installed; cannot read PDF files.") from e
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(text_parts)


def load_text_from_docx(file_bytes: bytes) -> str:
    try:
        import docx
    except ImportError as e:
        raise RuntimeError("python-docx is not installed; cannot read DOCX files.") from e
    document = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in document.paragraphs)


def infer_report_from_free_text(text: str, source_name: str, idx: int) -> dict[str, Any]:
    """Builds a report record from a raw text/PDF/DOCX document with best-effort
    metadata inference. Inferred fields are clearly marked as such."""
    text = re.sub(r"\s+", " ", text).strip()

    location = "Unspecified (inferred: not stated in document)"
    for loc_hint in ["assembly line", "warehouse", "loading zone", "packaging", "substation", "corridor"]:
        m = re.search(rf"({loc_hint}[\w\s]{{0,15}})", text, re.IGNORECASE)
        if m:
            location = f"{m.group(1).strip().title()} (inferred from text)"
            break

    shift = "Unspecified (inferred: not stated in document)"
    for s in ["night", "morning", "evening", "day"]:
        if re.search(rf"\b{s}\b", text, re.IGNORECASE):
            shift = f"{s.title()} (inferred from text)"
            break

    return {
        "report_id": f"DOC-{source_name[:8].upper()}-{idx}",
        "date": date.today().isoformat() + " (inferred: upload date)",
        "location": location,
        "department": "Unspecified (inferred: not stated in document)",
        "shift": shift,
        "report_type": "Observation (inferred default for free-text upload)",
        "severity": 2,
        "hazard": "Unspecified (inferred: see description)",
        "description": text,
    }


def load_guidance_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
