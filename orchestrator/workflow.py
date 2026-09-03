"""
AgentOrchestrator: manages the 5-agent workflow pipeline.
Pipeline: Understanding -> Retrieval -> Reasoning -> Validation -> Decision
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from config.business_rules import SUPPORTED_EQUIPMENT
from config.settings import settings
from agents.query_understanding import QueryUnderstandingAgent
from agents.retrieval_agent import RetrievalAgent
from agents.reasoning_agent import ReasoningAgent, normalise_reasoning_result
from agents.validation_agent import ValidationAgent
from agents.decision_agent import DecisionAgent
from core.llm_engine import RuleBasedEngine
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
        # Last-resort path for when the reasoning AGENT itself fails or
        # times out - not just its LLM provider (LLMEngine already has its
        # own internal fallback for that case). Synchronous, local, cannot
        # itself fail or time out: see _reasoning_last_resort below.
        self._rule_based_fallback = RuleBasedEngine()

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

        # This system is scoped to exactly 5 known equipment items (maintenance
        # decision support, not general business intelligence). "unknown" is
        # QueryUnderstandingAgent's own signal that none matched - never a
        # legitimate value for an in-scope query. Stop here, before business
        # rules run: without this, an out-of-scope question (e.g. "what were
        # our sales in Karnataka?") still gets a maintenance recommendation
        # card with a misleading "APPROVED, 100% compliance" validation
        # result, because the 5 business rules all vacuously pass on zeroed
        # cost/downtime - reproduced live before this existed. Honest scope
        # boundary beats a confident-looking wrong answer.
        if understanding.get("equipment") == "unknown":
            return self._out_of_scope_response(query, understanding, workflow_start)

        # ── Stage 2: Retrieve relevant documents ──────────────────────────────
        retrieval = await self._retrieval.execute(
            {
                "equipment": understanding.get("equipment", ""),
                "queries": [understanding.get("intent", ""), query],
            }
        )
        if retrieval["status"] not in ("SUCCESS", "PARTIAL"):
            return _stage_error("retrieval", retrieval)

        # ── Stage 3: Reason (pluggable provider, or rule-based) ──────────────
        reasoning = await self._reasoning.execute(
            {
                "query": query,
                "understanding": understanding,
                "context_documents": retrieval.get("documents", []),
            }
        )
        if reasoning["status"] != "SUCCESS":
            # The reasoning AGENT (not just its LLM provider) failed or
            # timed out - e.g. many requests queued behind one local GPU
            # can outlive even the provider's own client-side timeout,
            # because a thread-pool-queued call hasn't started its network
            # clock yet when the agent's OUTER timeout fires. LLMEngine's
            # own internal fallback can't help here since it never got a
            # chance to run. Rather than fail the whole request (there IS
            # always a safe answer available), compute one directly.
            logger.warning(
                f"reasoning agent did not complete (status="
                f"{reasoning.get('status')}); using the always-available "
                "rule-based engine directly so the request still returns "
                "a decision"
            )
            reasoning = self._reasoning_last_resort(understanding)

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

    def _out_of_scope_response(
        self, query: str, understanding: dict[str, Any], workflow_start: datetime
    ) -> dict[str, Any]:
        """
        Clean, honest response for a query that isn't about one of the 5
        supported equipment items - skips retrieval/reasoning/validation
        entirely rather than forcing it through machinery that doesn't apply.
        Same top-level shape as a real DecisionAgent decision, so the API and
        UI need no special-casing; not logged to the audit trail, since this
        isn't a maintenance decision.
        """
        now = datetime.now(tz=timezone.utc)
        decision_id = f"DEC-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
        supported = ", ".join(SUPPORTED_EQUIPMENT)
        total_ms = int((now - workflow_start).total_seconds() * 1000)

        return {
            "decision_id": decision_id,
            "timestamp": now.isoformat(),
            "user_query": query,
            "equipment": "unknown",
            "intent": understanding.get("intent", "unknown"),
            "priority": "NORMAL",
            "current_state": {},
            "analysis": {
                "maintenance_urgency": "N/A",
                "cost_estimate_inr": 0.0,
                "downtime_estimate_hours": 0.0,
                "documents_consulted": 0,
            },
            "recommendation": {
                "action": "Outside Supported Scope",
                "detail": (
                    "This system provides maintenance decision support for "
                    f"5 specific pieces of equipment: {supported}. It does not "
                    "have access to sales, financial, HR, or other business "
                    "data. Try rephrasing your question to mention one of "
                    "the equipment above."
                ),
                "timing": "N/A",
                "risk_if_delayed": "N/A - not a maintenance decision",
                "estimated_cost_inr": 0.0,
                "estimated_downtime_hours": 0.0,
            },
            "validation": {
                "status": "OUT_OF_SCOPE",
                "compliance_score": 0,
                "violations": [],
                "warnings": [],
                "escalations": [],
                "rule_results": {
                    "scope_check": {
                        "status": "INFO",
                        "message": (
                            "No supported equipment identified in this "
                            f"query. Supported: {supported}."
                        ),
                    }
                },
            },
            "reasoning_chain": [
                "Step 1: No equipment matched from the 5 supported items "
                f"({supported}).",
                "Step 2: This system answers maintenance questions about "
                "those items only - it has no sales, financial, or other "
                "business data to draw on.",
                "Step 3: Rephrase the question naming one of the supported "
                "equipment IDs to get a real recommendation.",
            ],
            "metadata": {
                "overall_confidence": 1.0,
                "reasoning_steps_count": 3,
                "total_time_ms": total_ms,
                "engine_used": "n/a",
                "agents_executed": ["understanding"],
                "agents_failed": [],
            },
            "audit_trail": {
                "user_id": "n/a",
                "request_timestamp": workflow_start.isoformat(),
                "response_timestamp": now.isoformat(),
                "decision_id": decision_id,
            },
            "status": "SUCCESS",
        }

    def _reasoning_last_resort(self, understanding: dict[str, Any]) -> dict[str, Any]:
        """Compute a rule-based reasoning result directly, bypassing the
        ReasoningAgent/LLMEngine layer entirely. Pure Python, no network
        or thread-pool involvement, so it cannot itself time out."""
        raw = self._rule_based_fallback.generate(
            equipment=understanding.get("equipment", "unknown"),
            intent=understanding.get("intent", "status_check"),
            current_state=understanding.get("current_state", {}),
            context_docs=[],
            constraints=understanding.get("constraints", {}),
        )
        result = normalise_reasoning_result(raw)
        result["status"] = "SUCCESS"
        return result


def _stage_error(stage: str, result: dict[str, Any]) -> dict[str, Any]:
    logger.error(
        f"stage={stage} failed status={result.get('status')} err={result.get('error')}"
    )
    return {
        "error": f"Stage '{stage}' failed: {result.get('error', 'unknown')}",
        "status": "WORKFLOW_FAILED",
        "failed_stage": stage,
    }
