"""
Vector store: pluggable document retrieval behind one stable interface.

Backends (selected by settings.VECTOR_BACKEND):
  tfidf - scikit-learn TF-IDF + cosine similarity. ~30 MB, no model downloads.
          This is what the MVP ships with.
  faiss - FAISS + sentence-transformers embeddings (~2.5 GB). The target
          stack; see docs/MIGRATION.md for how to add it.

Agents depend only on BaseVectorStore, so changing backend is a config change.
"""

from __future__ import annotations

import logging
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import settings

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """Contract every retrieval backend implements."""

    @abstractmethod
    def build_index(self, docs: list[dict[str, Any]]) -> None:
        """Index a list of document dicts, each with a 'text' key."""

    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return top-k documents, each with a 'similarity_score' key."""

    @abstractmethod
    def save(self, path: str) -> None:
        """Persist the index to disk."""

    @abstractmethod
    def load(self, path: str) -> bool:
        """Load an index from disk. Returns True on success."""

    @property
    @abstractmethod
    def doc_count(self) -> int:
        """Number of indexed documents."""


class TfidfVectorStore(BaseVectorStore):
    """TF-IDF document store with cosine similarity search."""

    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix: Any = None  # sparse TF-IDF matrix
        self._documents: list[dict[str, Any]] = []

    # ── Build ────────────────────────────────────────────────────────────────

    def build_index(self, docs: list[dict[str, Any]]) -> None:
        """
        Build TF-IDF index from a list of document dicts.
        Each dict must have a 'text' key used for embedding.
        """
        if not docs:
            raise ValueError("Cannot build index from empty document list")

        self._documents = docs
        texts = [str(d.get("text", "")) for d in docs]

        self._vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(texts)
        logger.info(
            f"TF-IDF index built: {len(docs)} docs, matrix={self._matrix.shape}"
        )

    # ── Search ───────────────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Return top-k most similar documents for the query.
        Each result dict has 'similarity_score' and 'source' added.
        """
        if self._vectorizer is None or self._matrix is None:
            logger.warning("VectorStore not built - returning empty results")
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0.01:  # ignore very low similarity
                doc = dict(self._documents[idx])
                doc["similarity_score"] = round(float(scores[idx]), 4)
                results.append(doc)

        logger.debug(f"search query={query[:40]!r} found={len(results)} docs")
        return results

    # ── Persistence ──────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Persist the index to disk using pickle."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "vectorizer": self._vectorizer,
                    "matrix": self._matrix,
                    "documents": self._documents,
                },
                f,
            )
        logger.info(f"VectorStore saved to {path}")

    def load(self, path: str) -> bool:
        """Load index from disk. Returns True on success."""
        p = Path(path)
        if not p.exists():
            return False
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self._vectorizer = data["vectorizer"]
            self._matrix = data["matrix"]
            self._documents = data["documents"]
            logger.info(f"VectorStore loaded from {path} ({len(self._documents)} docs)")
            return True
        except Exception as exc:
            logger.error(f"Failed to load VectorStore: {exc}")
            return False

    # ── Utility ──────────────────────────────────────────────────────────────

    def add_documents(self, docs: list[dict[str, Any]]) -> None:
        """Add documents and rebuild the index."""
        self._documents.extend(docs)
        self.build_index(self._documents)

    @property
    def doc_count(self) -> int:
        return len(self._documents)


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------

_BACKENDS: dict[str, type[BaseVectorStore]] = {
    "tfidf": TfidfVectorStore,
}


def get_vector_store(backend: str | None = None) -> BaseVectorStore:
    """
    Build the configured retrieval backend.

    Register a new backend by adding it to _BACKENDS - no agent code changes.
    """
    name = (backend or settings.VECTOR_BACKEND).strip().lower()
    if name not in _BACKENDS:
        raise ValueError(
            f"Unknown VECTOR_BACKEND={name!r}. "
            f"Available: {sorted(_BACKENDS)}. See docs/MIGRATION.md."
        )
    return _BACKENDS[name]()


# Backwards-compatible alias: existing imports of VectorStore keep working.
VectorStore = TfidfVectorStore
