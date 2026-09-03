"""
Agent 5: DecisionAgent
Synthesizes all 4 agent outputs into the final structured decision JSON.
Pure Python aggregation - no LLM, no network calls.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import settings

logger = logging.getLogger(__name__)


class DecisionAgent(BaseAgent):
    """
    Merges Understanding + Retrieval + Reasoning + Validation outputs
    into a single auditable decision document.
    """

    def __init__(self) -> None:
        super().__init__(name="decision", timeout_sec=settings.AGENT_TIMEOUT_SEC)
        self._sequence: int = 0

    async def _run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        understanding: dict[str, Any] = input_data.get("understanding", {})
        retrieval: dict[str, Any] = input_data.get("retrieval", {})
        reasoning: dict[str, Any] = input_data.get("reasoning", {})
        validation: dict[str, Any] = input_data.get("validation", {})
        user_id: str = input_data.get("user_id", "unknown")
        workflow_start: str = input_data.get("workflow_start", "")
        total_time_ms: int = input_data.get("total_time_ms", 0)

        # ── Generate decision ID ──────────────────────────────────────────────
        now = datetime.now(tz=timezone.utc)
        self._sequence += 1
        date_str = now.strftime("%Y%m%d")
        time_str = now.strftime("%H%M%S")
        decision_id = f"DEC-{date_str}-{time_str}"

        # ── Extract key fields ────────────────────────────────────────────────
        equipment = understanding.get("equipment", "unknown")
        intent = understanding.get("intent", "unknown")
        current_state = understanding.get("current_state", {})
        constraints = understanding.get("constraints", {})

        recommendation_text = reasoning.get(
            "recommendation", "No recommendation generated"
        )
        cost = reasoning.get("cost_estimate_inr", 0)
        downtime = reasoning.get("downtime_hours", 0)
        risk = reasoning.get("risk_if_delayed", "")
        reasoning_steps = reasoning.get("reasoning", [])
        engine_used = reasoning.get("engine_used", "rule-based")
        reason_confidence = reasoning.get("confidence", 0.0)

        validation_status = validation.get("validation_status", "UNKNOWN")
        compliance_score = validation.get("compliance_score", 0)
        violations = validation.get("violations", [])
        warnings = validation.get("warnings", [])
        escalations = validation.get("escalations", [])

        # ── Priority flag ─────────────────────────────────────────────────────
        priority = "NORMAL"
        if validation_status == "ESCALATE":
            priority = "URGENT"
        elif validation_status == "REJECTED":
            priority = "HOLD"
        elif warnings:
            priority = "ELEVATED"

        # ── Timing label ──────────────────────────────────────────────────────
        timing = _suggest_timing(intent, current_state, validation_status)

        # ── Build final document ──────────────────────────────────────────────
        decision = {
            "decision_id": decision_id,
            "timestamp": now.isoformat(),
            "user_query": understanding.get("raw_query", ""),
            "equipment": equipment,
            "intent": intent,
            "priority": priority,
            "current_state": {
                **current_state,
                "equipment_id": equipment,
            },
            "analysis": {
                "maintenance_urgency": _urgency_label(validation_status, current_state),
                "cost_estimate_inr": cost,
                "downtime_estimate_hours": downtime,
                "documents_consulted": retrieval.get("documents_found", 0),
            },
            "recommendation": {
                "action": _action_label(intent, validation_status),
                "detail": recommendation_text,
                "timing": timing,
                "risk_if_delayed": risk,
                "estimated_cost_inr": cost,
                "estimated_downtime_hours": downtime,
            },
            "validation": {
                "status": validation_status,
                "compliance_score": compliance_score,
                "violations": violations,
                "warnings": warnings,
                "escalations": escalations,
                "rule_results": validation.get("rule_results", {}),
            },
            "reasoning_chain": reasoning_steps,
            "metadata": {
                "overall_confidence": round(reason_confidence, 2),
                "reasoning_steps_count": len(reasoning_steps),
                "total_time_ms": total_time_ms,
                "engine_used": engine_used,
                "agents_executed": [
                    "understanding",
                    "retrieval",
                    "reasoning",
                    "validation",
                    "decision",
                ],
                "agents_failed": [],
            },
            "audit_trail": {
                "user_id": user_id,
                "request_timestamp": workflow_start,
                "response_timestamp": now.isoformat(),
                "decision_id": decision_id,
            },
            "status": "SUCCESS",
        }

        logger.info(
            f"Decision created: id={decision_id} equipment={equipment} status={validation_status}"
        )
        return decision


# ── Helpers ───────────────────────────────────────────────────────────────────


def _suggest_timing(intent: str, state: dict[str, Any], val_status: str) -> str:
    if val_status == "ESCALATE":
        return "IMMEDIATE - within 24 hours"
    if val_status == "REJECTED":
        return "ON HOLD - resolve violations first"
    last_days = state.get("last_service_days", 0)
    if intent == "risk_assessment" or (last_days and last_days > 200):
        return "Within 1 week"
    if last_days and last_days > 150:
        return "Within 2 weeks"
    return "Within next scheduled maintenance window"


def _urgency_label(val_status: str, state: dict[str, Any]) -> str:
    if val_status == "ESCALATE":
        return "CRITICAL - Immediate"
    if val_status == "REJECTED":
        return "ON HOLD"
    last_days = state.get("last_service_days", 0)
    if last_days and last_days > 200:
        return "HIGH - Overdue"
    if last_days and last_days > 150:
        return "MEDIUM - Approaching"
    return "LOW - Planned"


def _action_label(intent: str, val_status: str) -> str:
    if val_status == "ESCALATE":
        return "URGENT INSPECTION REQUIRED"
    if val_status == "REJECTED":
        return "HOLD - Budget/Safety review needed"
    labels = {
        "schedule_maintenance": "Schedule Maintenance",
        "risk_assessment": "Inspect and Assess Risk",
        "cost_optimization": "Prioritize and Schedule",
        "compliance_check": "Review Compliance Status",
        "status_check": "Monitor Equipment Status",
    }
    return labels.get(intent, "Take Appropriate Action")
