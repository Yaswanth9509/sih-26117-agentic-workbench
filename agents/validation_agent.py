"""
Agent 4: ValidationAgent
Checks the ReasoningAgent recommendation against 5 business rules.
Pure Python - deterministic, no LLM, no network calls.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import settings

logger = logging.getLogger(__name__)


class ValidationAgent(BaseAgent):
    """
    Applies 5 business rules to a recommendation and returns:
    - validation_status: APPROVED | APPROVED_WITH_WARNINGS | REJECTED | ESCALATE
    - compliance_score: 0-100
    - rule_results: per-rule pass/fail details
    - violations: list of critical failures
    - warnings: list of non-critical issues
    """

    def __init__(self) -> None:
        super().__init__(name="validation", timeout_sec=settings.AGENT_TIMEOUT_SEC)

    async def _run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        reasoning: dict[str, Any] = input_data.get("reasoning", {})
        understanding: dict[str, Any] = input_data.get("understanding", {})

        cost: float = float(reasoning.get("cost_estimate_inr", 0))
        downtime: float = float(reasoning.get("downtime_hours", 0))
        confidence: float = float(reasoning.get("confidence", 0))
        current_state: dict[str, Any] = understanding.get("current_state", {})
        constraints: dict[str, Any] = understanding.get("constraints", {})
        equipment: str = understanding.get("equipment", "unknown")

        budget: float = float(
            constraints.get("budget_inr", settings.MAX_RECOMMENDATION_COST_INR)
        )
        pressure: float | None = current_state.get("pressure_bar")
        temp_rise: float | None = current_state.get("temperature_rise_c")
        last_service_days: int = current_state.get("last_service_days", 0)

        rule_results: dict[str, dict[str, str]] = {}
        violations: list[str] = []
        warnings: list[str] = []
        escalations: list[str] = []

        # ── RULE 1: Cost check ────────────────────────────────────────────────
        if cost > budget:
            rule_results["cost_check"] = {
                "status": "FAIL",
                "message": f"Cost Rs.{cost:,.0f} exceeds budget Rs.{budget:,.0f}",
            }
            violations.append(f"Cost Rs.{cost:,.0f} exceeds budget Rs.{budget:,.0f}")
        elif cost > budget * 0.9:
            rule_results["cost_check"] = {
                "status": "WARN",
                "message": f"Cost Rs.{cost:,.0f} is >90% of budget Rs.{budget:,.0f}",
            }
            warnings.append("Cost approaching budget limit")
        else:
            rule_results["cost_check"] = {
                "status": "PASS",
                "message": f"Cost Rs.{cost:,.0f} within budget Rs.{budget:,.0f} (buffer Rs.{budget-cost:,.0f})",
            }

        # ── RULE 2: Downtime check ────────────────────────────────────────────
        max_dt = settings.MAX_DOWNTIME_HOURS
        if downtime > max_dt:
            rule_results["downtime_check"] = {
                "status": "WARN",
                "message": f"Downtime {downtime}h exceeds limit {max_dt}h - requires superintendent approval",
            }
            warnings.append(f"Downtime {downtime}h exceeds {max_dt}h limit")
        else:
            rule_results["downtime_check"] = {
                "status": "PASS",
                "message": f"Downtime {downtime}h within limit {max_dt}h",
            }

        # ── RULE 3: Safety margin ─────────────────────────────────────────────
        if pressure is not None:
            safe_max_map = {
                "reactor-4": 5.0,
                "compressor-b": 8.0,
                "pump-a": 6.0,
                "exchanger-c": 10.0,
                "separator-d": 12.0,
            }
            safe_max = safe_max_map.get(equipment.lower(), 6.0)
            pct = round(pressure / safe_max * 100, 1)
            margin = settings.SAFETY_MARGIN_PERCENT
            if pct > (100 - margin):
                rule_results["safety_margin"] = {
                    "status": "ESCALATE",
                    "message": f"CRITICAL: Pressure {pressure} bar is {pct}% of max {safe_max} bar",
                }
                escalations.append(
                    f"Pressure {pct}% of max - IMMEDIATE ACTION REQUIRED"
                )
            elif pct > 85:
                rule_results["safety_margin"] = {
                    "status": "WARN",
                    "message": f"Pressure {pressure} bar is {pct}% of max {safe_max} bar - monitor closely",
                }
                warnings.append(f"Pressure at {pct}% - approaching limit")
            else:
                rule_results["safety_margin"] = {
                    "status": "PASS",
                    "message": f"Pressure {pressure} bar is {pct}% of max {safe_max} bar - safe",
                }
        elif temp_rise and temp_rise > 20:
            rule_results["safety_margin"] = {
                "status": "WARN",
                "message": f"Temperature rise {temp_rise}C noted - monitor for overheating",
            }
            warnings.append(f"High temperature rise: {temp_rise}C")
        else:
            rule_results["safety_margin"] = {
                "status": "PASS",
                "message": "No critical pressure/temperature readings detected",
            }

        # ── RULE 4: Compliance check ──────────────────────────────────────────
        interval_map = {
            "reactor-4": 6,
            "compressor-b": 12,
            "pump-a": 6,
            "exchanger-c": 12,
            "separator-d": 24,
        }
        interval_months = interval_map.get(equipment.lower(), 12)
        interval_days = interval_months * 30
        grace_days = 14

        if last_service_days > interval_days + grace_days:
            rule_results["compliance"] = {
                "status": "WARN",
                "message": (
                    f"Last service {last_service_days}d ago exceeds {interval_months}-month "
                    f"interval by {last_service_days - interval_days}d - schedule immediately"
                ),
            }
            warnings.append("Maintenance overdue")
        elif last_service_days >= interval_days * 0.8:
            rule_results["compliance"] = {
                "status": "PASS",
                "message": f"Approaching {interval_months}-month service window - proactive scheduling recommended",
            }
        else:
            rule_results["compliance"] = {
                "status": "PASS",
                "message": f"Within standard {interval_months}-month maintenance schedule",
            }

        # ── RULE 5: Historical validation ─────────────────────────────────────
        success_rate_map = {
            "reactor-4": (7, 8),
            "compressor-b": (4, 5),
            "pump-a": (10, 10),
            "exchanger-c": (6, 6),
            "separator-d": (2, 3),
        }
        successes, total = success_rate_map.get(equipment.lower(), (4, 5))
        rate = round(successes / total * 100)
        if rate >= 80:
            rule_results["historical"] = {
                "status": "PASS",
                "message": f"Similar approach succeeded {successes}/{total} times ({rate}%) historically",
            }
        else:
            rule_results["historical"] = {
                "status": "WARN",
                "message": f"Historical success rate only {rate}% ({successes}/{total}) - review approach",
            }
            warnings.append(f"Low historical success rate: {rate}%")

        # ── Compute status + score ────────────────────────────────────────────
        statuses = [v["status"] for v in rule_results.values()]
        passes = statuses.count("PASS")
        warns = statuses.count("WARN")
        total_rules = len(statuses)
        compliance_score = int((passes + warns * 0.5) / total_rules * 100)

        if escalations:
            validation_status = "ESCALATE"
        elif violations:
            validation_status = "REJECTED"
        elif warnings:
            validation_status = "APPROVED_WITH_WARNINGS"
        else:
            validation_status = "APPROVED"

        return {
            "validation_status": validation_status,
            "compliance_score": compliance_score,
            "rule_results": rule_results,
            "violations": violations,
            "warnings": warnings,
            "escalations": escalations,
        }
