"""
Agent 2: RetrievalAgent
Searches the configured vector store for relevant MRPL documents.
Backend-agnostic: it talks to BaseVectorStore, so swapping TF-IDF for
FAISS post-MVP needs no change here (see docs/MIGRATION.md).
Loads and indexes documents on first call (lazy init, cached after).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import settings
from core.document_loader import DocumentLoader
from core.vector_store import BaseVectorStore, get_vector_store

logger = logging.getLogger(__name__)

# Module-level singleton so index is built only once
_vector_store: BaseVectorStore | None = None


def _get_store() -> BaseVectorStore:
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    vs = get_vector_store()
    cache_path = settings.VECTOR_STORE_PATH

    # Try loading cached index first
    if vs.load(cache_path):
        logger.info(f"Loaded index from cache: {cache_path}")
        _vector_store = vs
        return vs

    # Build from scratch
    logger.info("Building index from sample docs...")
    loader = DocumentLoader(docs_path=settings.SAMPLE_DOCS_PATH)
    docs = loader.load_all()
    if not docs:
        raise RuntimeError(
            "No documents found in sample_docs. Run generate_sample_data.py first."
        )
    vs.build_index(docs)
    vs.save(cache_path)
    logger.info(f"Index built and cached ({vs.doc_count} docs)")

    _vector_store = vs
    return vs


class RetrievalAgent(BaseAgent):
    """Retrieves top-K relevant documents from the configured vector store."""

    def __init__(self) -> None:
        super().__init__(name="retrieval", timeout_sec=settings.AGENT_TIMEOUT_SEC)

    async def _run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        equipment: str = input_data.get("equipment", "")
        queries: list[str] = input_data.get("queries", [])
        top_k: int = input_data.get("top_k", settings.VECTOR_SEARCH_TOP_K)

        if not queries and not equipment:
            return {"documents": [], "documents_found": 0, "status": "PARTIAL"}

        store = _get_store()

        # Build combined search queries
        search_queries: list[str] = []
        if equipment:
            search_queries.append(f"{equipment} maintenance schedule specification")
        search_queries.extend(queries)

        # Run all queries and merge results (dedup by source)
        seen: dict[str, dict[str, Any]] = {}
        for sq in search_queries:
            results = store.search(sq, top_k=top_k)
            for doc in results:
                key = str(doc.get("source", "")) + str(
                    doc.get("equipment_id", doc.get("id", ""))
                )
                if key not in seen or doc.get("similarity_score", 0) > seen[key].get(
                    "similarity_score", 0
                ):
                    seen[key] = doc

        # Sort by similarity, take top_k
        merged = sorted(
            seen.values(), key=lambda d: d.get("similarity_score", 0), reverse=True
        )[:top_k]

        # Filter to equipment-relevant docs when equipment known
        if equipment:
            eq_id = equipment.lower()
            relevant = [d for d in merged if eq_id in str(d).lower()]
            if relevant:
                # Among equipment-relevant docs, the canonical spec record
                # goes first. Several documents mention the same equipment
                # ID (maintenance_schedule.csv, service_logs.txt, ...), so
                # "equipment-relevant" alone doesn't guarantee the one
                # record ReasoningAgent's providers depend on for cost and
                # downtime survives into context_docs[:3] - reproduced live:
                # it ranked 4th of 5 by raw similarity for a real query, so
                # every provider (rule-based and a live ollama call alike)
                # saw a different, unrelated document instead and the LLM
                # returned no cost figure at all rather than guess.
                spec = [
                    d
                    for d in relevant
                    if str(d.get("source", "")) == "equipment_specs.json"
                ]
                other_relevant = [d for d in relevant if d not in spec]
                rest = [d for d in merged if d not in relevant]
                merged = (spec + other_relevant + rest)[:top_k]

        return {
            "documents": merged,
            "documents_found": len(merged),
            "retrieval_queries": search_queries,
        }
