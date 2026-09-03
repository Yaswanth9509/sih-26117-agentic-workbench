"""Unit tests for all 5 agents."""

import asyncio
import pytest
import sys

sys.path.insert(0, ".")

from agents.query_understanding import QueryUnderstandingAgent
from agents.retrieval_agent import RetrievalAgent
from agents.reasoning_agent import ReasoningAgent
from agents.validation_agent import ValidationAgent
from agents.decision_agent import DecisionAgent


# ── Agent 1 ──────────────────────────────────────────────────────────────────
class TestQueryUnderstanding:
    def setup_method(self):
        self.agent = QueryUnderstandingAgent()

    def test_schedule_intent(self):
        r = asyncio.run(
            self.agent.execute(
                {
                    "query": "Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000. Schedule?"
                }
            )
        )
        assert r["status"] == "SUCCESS"
        assert r["intent"] == "schedule_maintenance"
        assert r["equipment"] == "reactor-4"
        assert r["current_state"]["pressure_bar"] == 4.2
        assert r["constraints"]["budget_inr"] == 50000

    def test_risk_intent(self):
        r = asyncio.run(
            self.agent.execute(
                {
                    "query": "Compressor-B making noise and vibrating badly. What is the risk?"
                }
            )
        )
        assert r["intent"] == "risk_assessment"
        assert r["equipment"] == "compressor-b"

    def test_compliance_intent(self):
        r = asyncio.run(
            self.agent.execute(
                {"query": "Can we skip separator-d maintenance this quarter?"}
            )
        )
        assert r["intent"] == "compliance_check"
        assert r["equipment"] == "separator-d"

    def test_empty_query_fails(self):
        r = asyncio.run(self.agent.execute({"query": ""}))
        assert r["status"] == "FAILED"

    def test_equipment_alias(self):
        r = asyncio.run(
            self.agent.execute(
                {"query": "heat exchanger pressure rising, last service 12 months"}
            )
        )
        assert r["equipment"] == "exchanger-c"

    def test_50k_budget_parsing(self):
        r = asyncio.run(self.agent.execute({"query": "pump-a service, budget Rs.50K"}))
        assert r["constraints"]["budget_inr"] == 50000


# ── Agent 2 ──────────────────────────────────────────────────────────────────
class TestRetrievalAgent:
    def setup_method(self):
        self.agent = RetrievalAgent()

    def test_retrieval_returns_docs(self):
        r = asyncio.run(
            self.agent.execute(
                {"equipment": "reactor-4", "queries": ["maintenance schedule"]}
            )
        )
        assert r["status"] == "SUCCESS"
        assert r["documents_found"] > 0

    def test_all_sources_covered(self):
        r = asyncio.run(
            self.agent.execute(
                {
                    "equipment": "compressor-b",
                    "queries": ["vibration noise bearing replacement cost"],
                    "top_k": 5,
                }
            )
        )
        sources = {d["source"] for d in r["documents"]}
        assert len(sources) >= 2  # at least 2 different sources

    def test_empty_equipment_partial(self):
        r = asyncio.run(self.agent.execute({"equipment": "", "queries": []}))
        assert r["status"] in ("SUCCESS", "PARTIAL")


# ── Agent 3 ──────────────────────────────────────────────────────────────────
class TestReasoningAgent:
    def setup_method(self):
        self.agent = ReasoningAgent()

    def test_rule_based_engine(self):
        r = asyncio.run(
            self.agent.execute(
                {
                    "query": "When to service reactor-4?",
                    "understanding": {
                        "equipment": "reactor-4",
                        "intent": "schedule_maintenance",
                        "current_state": {
                            "pressure_bar": 4.2,
                            "last_service_days": 180,
                        },
                        "constraints": {"budget_inr": 50000},
                    },
                    "context_documents": [],
                }
            )
        )
        assert r["status"] == "SUCCESS"
        assert r["engine_used"] == "rule-based"
        assert len(r["reasoning"]) >= 4
        assert r["confidence"] > 0.7
        assert r["cost_estimate_inr"] > 0

    def test_no_query_fails(self):
        r = asyncio.run(
            self.agent.execute(
                {
                    "query": "",
                    "understanding": {},
                    "context_documents": [],
                }
            )
        )
        assert r["status"] == "FAILED"


# ── Agent 4 ──────────────────────────────────────────────────────────────────
class TestValidationAgent:
    def setup_method(self):
        self.agent = ValidationAgent()

    def _make_input(
        self, cost=30000, downtime=2.5, pressure=4.2, budget=50000, last_days=180
    ):
        return {
            "reasoning": {
                "cost_estimate_inr": cost,
                "downtime_hours": downtime,
                "confidence": 0.9,
            },
            "understanding": {
                "equipment": "reactor-4",
                "current_state": {
                    "pressure_bar": pressure,
                    "last_service_days": last_days,
                },
                "constraints": {"budget_inr": budget},
            },
        }

    def test_approved_normal(self):
        r = asyncio.run(self.agent.execute(self._make_input()))
        assert r["validation_status"] == "APPROVED"
        assert r["compliance_score"] == 100
        assert len(r["violations"]) == 0

    def test_rejected_over_budget(self):
        r = asyncio.run(self.agent.execute(self._make_input(cost=60000, budget=50000)))
        assert r["validation_status"] == "REJECTED"
        assert len(r["violations"]) > 0

    def test_escalate_critical_pressure(self):
        r = asyncio.run(
            self.agent.execute(self._make_input(pressure=4.9))
        )  # 98% of 5.0 max
        assert r["validation_status"] == "ESCALATE"
        assert len(r["escalations"]) > 0

    def test_all_5_rules_checked(self):
        r = asyncio.run(self.agent.execute(self._make_input()))
        assert len(r["rule_results"]) == 5


# ── Agent 5 ──────────────────────────────────────────────────────────────────
class TestDecisionAgent:
    def setup_method(self):
        self.agent = DecisionAgent()

    def _make_input(self):
        return {
            "understanding": {
                "equipment": "reactor-4",
                "intent": "schedule_maintenance",
                "current_state": {"pressure_bar": 4.2, "last_service_days": 180},
                "constraints": {"budget_inr": 50000},
                "raw_query": "When to service reactor-4?",
            },
            "retrieval": {"documents": [], "documents_found": 3},
            "reasoning": {
                "recommendation": "Schedule maintenance within 2 weeks",
                "cost_estimate_inr": 35000,
                "downtime_hours": 2.5,
                "risk_if_delayed": "Increased failure risk",
                "reasoning": ["Step 1", "Step 2", "Step 3"],
                "confidence": 0.93,
                "engine_used": "rule-based",
            },
            "validation": {
                "validation_status": "APPROVED",
                "compliance_score": 100,
                "violations": [],
                "warnings": [],
                "escalations": [],
                "rule_results": {},
            },
            "user_id": "test_eng",
            "total_time_ms": 42,
        }

    def test_decision_structure(self):
        r = asyncio.run(self.agent.execute(self._make_input()))
        assert r["status"] == "SUCCESS"
        assert r["decision_id"].startswith("DEC-")
        assert "recommendation" in r
        assert "validation" in r
        assert "reasoning_chain" in r
        assert "metadata" in r
        assert "audit_trail" in r

    def test_priority_urgent_on_escalate(self):
        inp = self._make_input()
        inp["validation"]["validation_status"] = "ESCALATE"
        r = asyncio.run(self.agent.execute(inp))
        assert r["priority"] == "URGENT"

    def test_priority_hold_on_rejected(self):
        inp = self._make_input()
        inp["validation"]["validation_status"] = "REJECTED"
        r = asyncio.run(self.agent.execute(inp))
        assert r["priority"] == "HOLD"
