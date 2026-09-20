"""
RAG vector store.

Design note: embeddings are computed with scikit-learn's TF-IDF
vectorizer + cosine similarity rather than a downloaded neural embedding
model. This keeps the pipeline fully local and dependency-light (no
model weights to fetch at runtime), while still doing real vector
retrieval: every chunk is embedded, stored, and ranked by an actual
similarity computation — nothing here is hardcoded or faked.

Two collections are kept, matching the spec:
  - "historical_reports": ingested safety reports
  - "safety_guidance": SOP / guidance documents
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def chunk_text(text: str, max_chars: int = 600) -> list[str]:
    """Simple paragraph-aware chunker."""
    text = clean_text(text)
    if len(text) <= max_chars:
        return [text] if text else []
    paras = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for p in paras:
        if len(current) + len(p) + 1 <= max_chars:
            current = f"{current} {p}".strip()
        else:
            if current:
                chunks.append(current)
            current = p
    if current:
        chunks.append(current)
    return chunks


@dataclass
class Document:
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Collection:
    """One TF-IDF-indexed collection of documents/chunks."""

    def __init__(self, name: str):
        self.name = name
        self.documents: list[Document] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._dirty = True

    def add(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        self.documents.append(Document(doc_id=doc_id, text=text, metadata=metadata or {}))
        self._dirty = True

    def _rebuild_if_needed(self) -> None:
        if not self._dirty:
            return
        if not self.documents:
            self._vectorizer, self._matrix = None, None
            self._dirty = False
            return
        corpus = [d.text for d in self.documents]
        self._vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), min_df=1, max_df=0.95
        )
        self._matrix = self._vectorizer.fit_transform(corpus)
        self._dirty = False

    def search(self, query: str, top_k: int = 5, exclude_id: str | None = None) -> list[dict[str, Any]]:
        self._rebuild_if_needed()
        if not self.documents or self._vectorizer is None:
            return []
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix).flatten()
        order = np.argsort(-sims)
        results = []
        for i in order:
            doc = self.documents[i]
            if exclude_id is not None and doc.doc_id == exclude_id:
                continue
            score = float(sims[i])
            if score <= 0.0:
                continue
            results.append(
                {
                    "doc_id": doc.doc_id,
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "similarity": round(score, 4),
                }
            )
            if len(results) >= top_k:
                break
        return results

    def __len__(self) -> int:
        return len(self.documents)


class VectorStore:
    """Holds the two named collections used across the app."""

    def __init__(self):
        self.collections: dict[str, Collection] = {
            "historical_reports": Collection("historical_reports"),
            "safety_guidance": Collection("safety_guidance"),
        }

    def collection(self, name: str) -> Collection:
        return self.collections[name]

    def add_report(self, report: dict[str, Any]) -> None:
        text = clean_text(report.get("description", ""))
        if not text:
            return
        metadata = {k: v for k, v in report.items() if k != "description"}
        self.collections["historical_reports"].add(
            doc_id=report["report_id"], text=text, metadata=metadata
        )

    def add_guidance_document(self, doc_name: str, full_text: str) -> None:
        chunks = chunk_text(full_text, max_chars=500)
        for i, chunk in enumerate(chunks):
            self.collections["safety_guidance"].add(
                doc_id=f"{doc_name}#chunk{i}",
                text=chunk,
                metadata={"source": doc_name, "chunk_index": i},
            )

    def stats(self) -> dict[str, int]:
        return {name: len(c) for name, c in self.collections.items()}
