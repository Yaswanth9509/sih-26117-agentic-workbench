"""
AgentOrchestrator: manages the 5-agent workflow pipeline.
Pipeline: Understanding -> Retrieval -> Reasoning -> Validation -> Decision
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from config.settings import settings
from agents.query_understanding import QueryUnderstandingAgent
from agents.retrieval_agent import RetrievalAgent
from agents.reasoning_agent import ReasoningAgent
from agents.validation_agent import ValidationAgent
from agents.decision_agent import DecisionAgent
from orchestrator.logging import log_decision

logger = logging.getLogger("Orchestrator")


class AgentOrchestrator:
    """Runs all 5 agents in sequence and returns a final decision."""

    def __init__(self) -> None:
        self._understanding = QueryUnderstandingAgent()
        self._retrieval = RetrievalAgent()
        self._reasoning = ReasoningAgent()
        self._validation = ValidationAgent()
        self._decision = DecisionAgent()

    async def llm_health(self) -> dict[str, Any]:
        """Which reasoning engine is live, and what else is reachable."""
        from agents.reasoning_agent import _get_engine

        return await _get_engine().health_check()

    async def run_workflow(
        self, query: str, user_id: str = "unknown"
    ) -> dict[str, Any]:
        """
        Execute the complete 5-agent pipeline.

        Returns final decision dict on success.
        Returns {"error": ..., "status": "WORKFLOW_FAILED"} on failure.
        """
        workflow_start = datetime.now(tz=timezone.utc)
        logger.info(f"workflow_start user={user_id} query={query[:60]!r}")

        try:
            result = await asyncio.wait_for(
                self._pipeline(query, user_id, workflow_start),
                timeout=settings.WORKFLOW_TIMEOUT_SEC,
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"workflow TIMEOUT after {settings.WORKFLOW_TIMEOUT_SEC}s")
            return {
                "error": f"Workflow timed out after {settings.WORKFLOW_TIMEOUT_SEC}s",
                "status": "WORKFLOW_TIMEOUT",
            }
        except Exception as exc:
            logger.error(f"workflow FAILED: {exc!s}")
            return {"error": str(exc), "status": "WORKFLOW_FAILED"}

    async def _pipeline(
        self,
        query: str,
        user_id: str,
        workflow_start: datetime,
    ) -> dict[str, Any]:
        t0 = datetime.now(tz=timezone.utc)

        # ── Stage 1: Understand the query ─────────────────────────────────────
        understanding = await self._understanding.execute({"query": query})
        if understanding["status"] not in ("SUCCESS",):
            return _stage_error("understanding", understanding)

        # ── Stage 2: Retrieve relevant documents ──────────────────────────────
        retrieval = await self._retrieval.execute(
            {
                "equipment": understanding.get("equipment", ""),
                "queries": [understanding.get("intent", ""), query],
            }
        )
        if retrieval["status"] not in ("SUCCESS", "PARTIAL"):
            return _stage_error("retrieval", retrieval)

        # ── Stage 3: Reason (Groq or rule-based) ─────────────────────────────
        reasoning = await self._reasoning.execute(
            {
                "query": query,
                "understanding": understanding,
                "context_documents": retrieval.get("documents", []),
            }
        )
        if reasoning["status"] != "SUCCESS":
            return _stage_error("reasoning", reasoning)

        # ── Stage 4: Validate recommendation ─────────────────────────────────
        validation = await self._validation.execute(
            {
                "reasoning": reasoning,
                "understanding": understanding,
            }
        )
        # Validation always returns SUCCESS (violations reported inside result)

        # ── Stage 5: Synthesise final decision ───────────────────────────────
        total_ms = int((datetime.now(tz=timezone.utc) - t0).total_seconds() * 1000)
        decision = await self._decision.execute(
            {
                "understanding": understanding,
                "retrieval": retrieval,
                "reasoning": reasoning,
                "validation": validation,
                "user_id": user_id,
                "workflow_start": workflow_start.isoformat(),
                "total_time_ms": total_ms,
            }
        )

        # ── Audit log ─────────────────────────────────────────────────────────
        log_decision(decision, user_id)

        logger.info(
            f"workflow_done id={decision.get('decision_id')} "
            f"time_ms={total_ms} status={decision.get('validation', {}).get('status')}"
        )
        return decision


def _stage_error(stage: str, result: dict[str, Any]) -> dict[str, Any]:
    logger.error(
        f"stage={stage} failed status={result.get('status')} err={result.get('error')}"
    )
    return {
        "error": f"Stage '{stage}' failed: {result.get('error', 'unknown')}",
        "status": "WORKFLOW_FAILED",
        "failed_stage": stage,
    }
