"""
Tool: retrieve_similar_reports, retrieve_safety_guidance

Real vector retrieval against the TF-IDF-backed VectorStore — no
fabricated similarity scores or snippets.
"""
from __future__ import annotations

from typing import Any

from rag.vectorstore import VectorStore


def retrieve_similar_reports(store: VectorStore, query_text: str, top_k: int = 5, exclude_id: str | None = None) -> list[dict[str, Any]]:
    results = store.collection("historical_reports").search(query_text, top_k=top_k, exclude_id=exclude_id)
    for r in results:
        r["report_id"] = r["doc_id"]
        r["snippet"] = r["text"][:220] + ("..." if len(r["text"]) > 220 else "")
    return results


def retrieve_safety_guidance(store: VectorStore, query_text: str, top_k: int = 3) -> list[dict[str, Any]]:
    results = store.collection("safety_guidance").search(query_text, top_k=top_k)
    for r in results:
        r["source_document"] = r["metadata"].get("source", "unknown")
        r["snippet"] = r["text"][:260] + ("..." if len(r["text"]) > 260 else "")
    return results
