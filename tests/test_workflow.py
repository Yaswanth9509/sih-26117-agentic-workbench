"""Integration tests: full 5-agent pipeline via orchestrator."""

import asyncio
import pytest
import sys

sys.path.insert(0, ".")

from orchestrator.workflow import AgentOrchestrator


class TestWorkflow:
    def setup_method(self):
        self.orch = AgentOrchestrator()

    def _run(self, query, user="test"):
        return asyncio.run(self.orch.run_workflow(query, user))

    def test_schedule_maintenance_full_pipeline(self):
        r = self._run(
            "Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000. When schedule?"
        )
        assert r["status"] == "SUCCESS"
        assert r["decision_id"].startswith("DEC-")
        assert r["equipment"] == "reactor-4"
        assert r["intent"] == "schedule_maintenance"
        assert r["validation"]["compliance_score"] >= 0
        assert len(r["reasoning_chain"]) >= 3

    def test_risk_assessment_pipeline(self):
        r = self._run(
            "Compressor-B making loud noise, temperature up 15C. What is the risk?"
        )
        assert r["status"] == "SUCCESS"
        assert r["equipment"] == "compressor-b"
        assert r["intent"] == "risk_assessment"

    def test_cost_optimization_pipeline(self):
        r = self._run(
            "Pump-A and Separator-D both need service. Budget Rs.35000. Which first?"
        )
        assert r["status"] == "SUCCESS"
        assert r["intent"] == "cost_optimization"

    def test_compliance_pipeline(self):
        r = self._run(
            "Can we skip separator-d service this quarter? Last done 26 months ago."
        )
        assert r["status"] == "SUCCESS"
        assert r["equipment"] == "separator-d"

    def test_all_required_fields_present(self):
        r = self._run("Reactor-4 pressure 4.2 bar schedule maintenance budget 50000")
        required = [
            "decision_id",
            "timestamp",
            "equipment",
            "priority",
            "recommendation",
            "validation",
            "reasoning_chain",
            "metadata",
            "audit_trail",
        ]
        for f in required:
            assert f in r, f"Missing field: {f}"

    def test_recommendation_has_all_subfields(self):
        r = self._run("Reactor-4 service needed budget Rs.50000")
        rec = r["recommendation"]
        for f in [
            "action",
            "detail",
            "timing",
            "risk_if_delayed",
            "estimated_cost_inr",
            "estimated_downtime_hours",
        ]:
            assert f in rec, f"Missing recommendation field: {f}"

    def test_validation_has_5_rules(self):
        r = self._run("Reactor-4 pressure 4.2 bar service last 6 months budget 50000")
        rules = r["validation"]["rule_results"]
        assert len(rules) == 5

    def test_rejected_when_over_budget(self):
        r = self._run(
            "reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.5000. Schedule?"
        )
        val = r["validation"]["status"]
        assert val in ("REJECTED", "APPROVED_WITH_WARNINGS", "ESCALATE")

    def test_empty_query_fails_gracefully(self):
        r = asyncio.run(self.orch.run_workflow("", "test"))
        assert r["status"] in ("WORKFLOW_FAILED",)

    def test_metadata_engine_field(self):
        r = self._run("Reactor-4 pressure 4.2 bar maintenance needed")
        assert r["metadata"]["engine_used"] in ("rule-based", "groq")
        assert r["metadata"]["total_time_ms"] >= 0
