"""
Unit tests for the pluggable LLM provider layer.

These verify the routing contract that lets on-premise Mistral replace the
MVP's cloud providers without touching agent code. No network calls: every
provider transport is stubbed.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from config.settings import settings
from core import llm_engine as engine_mod
from core.llm_engine import (
    AUTO_ORDER,
    PROVIDER_GEMINI,
    PROVIDER_GROQ,
    PROVIDER_OLLAMA,
    PROVIDER_RULE_BASED,
    GeminiEngine,
    LLMEngine,
    OllamaEngine,
    RuleBasedEngine,
    _parse_json_response,
)

# Shape RetrievalAgent actually returns for the equipment_specs.json record -
# see scripts/generate_sample_data.py, the real source of these field names.
REACTOR_4_SPEC: dict[str, Any] = {
    "id": "reactor-4",
    "name": "Reactor-4",
    "type": "reactor",
    "maintenance_interval_months": 6,
    "routine_service_cost_inr": 35000,
    "routine_service_downtime_hours": 2.5,
    "urgent_cost_multiplier": 1.35,
    "urgent_downtime_multiplier": 1.6,
    "urgency_policy": "Urgent pricing applies when overdue or symptomatic.",
    "source": "equipment_specs.json",
}

VALID_PAYLOAD = {
    "reasoning": ["step 1", "step 2"],
    "recommendation": "Service reactor-4 within two weeks",
    "cost_estimate_inr": 35000,
    "downtime_hours": 2.5,
    "risk_if_delayed": "Unplanned failure",
    "confidence": 0.9,
}


class _StubResponse:
    """Minimal stand-in for an httpx.Response."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def _reasoning_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "equipment": "reactor-4",
        "intent": "schedule_maintenance",
        "current_state": {"pressure_bar": 4.2, "last_service_days": 180},
        "context_docs": [],
        "constraints": {"budget_inr": 50000},
        "query": "When should we service reactor-4?",
    }
    base.update(overrides)
    return base


# ── JSON parsing ─────────────────────────────────────────────────────────────
class TestParseJsonResponse:
    def test_plain_json(self):
        result = _parse_json_response(json.dumps(VALID_PAYLOAD), "gemini")
        assert result["engine"] == "gemini"
        assert result["cost_estimate_inr"] == 35000

    def test_strips_markdown_fences(self):
        fenced = f"```json\n{json.dumps(VALID_PAYLOAD)}\n```"
        result = _parse_json_response(fenced, "ollama")
        assert result["engine"] == "ollama"
        assert result["recommendation"].startswith("Service reactor-4")

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("not json at all", "groq")


# ── Availability probes ──────────────────────────────────────────────────────
class TestAvailability:
    def test_gemini_needs_key(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
        assert GeminiEngine().is_available() is False
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        assert GeminiEngine().is_available() is True

    def test_ollama_unreachable_is_false(self, monkeypatch):
        def boom(*args: Any, **kwargs: Any) -> None:
            raise OSError("connection refused")

        monkeypatch.setattr(engine_mod.httpx, "get", boom)
        assert OllamaEngine().is_available() is False

    def test_ollama_available_when_model_present(self, monkeypatch):
        monkeypatch.setattr(settings, "OLLAMA_MODEL", "mistral")
        monkeypatch.setattr(
            engine_mod.httpx,
            "get",
            lambda *a, **k: _StubResponse({"models": [{"name": "mistral:latest"}]}),
        )
        assert OllamaEngine().is_available() is True

    def test_ollama_false_when_model_missing(self, monkeypatch):
        monkeypatch.setattr(settings, "OLLAMA_MODEL", "mistral")
        monkeypatch.setattr(
            engine_mod.httpx,
            "get",
            lambda *a, **k: _StubResponse({"models": [{"name": "llama3:latest"}]}),
        )
        assert OllamaEngine().is_available() is False


# ── Provider transports ──────────────────────────────────────────────────────
class TestTransports:
    def test_gemini_builds_expected_request(self, monkeypatch):
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        captured: dict[str, Any] = {}

        def fake_post(url: str, **kwargs: Any) -> _StubResponse:
            captured["url"] = url
            captured["headers"] = kwargs["headers"]
            captured["json"] = kwargs["json"]
            return _StubResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": json.dumps(VALID_PAYLOAD)}]}}
                    ]
                }
            )

        monkeypatch.setattr(engine_mod.httpx, "post", fake_post)
        result = GeminiEngine().generate("system prompt", "user prompt")

        assert result["engine"] == PROVIDER_GEMINI
        assert captured["url"].endswith(":generateContent")
        assert captured["headers"]["X-goog-api-key"] == "test-key"
        assert captured["json"]["generationConfig"]["responseMimeType"] == (
            "application/json"
        )

    def test_gemini_empty_parts_raises(self, monkeypatch):
        """Thinking models can spend the whole budget before answering."""
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(
            engine_mod.httpx,
            "post",
            lambda *a, **k: _StubResponse(
                {"candidates": [{"content": {}, "finishReason": "MAX_TOKENS"}]}
            ),
        )
        with pytest.raises(RuntimeError, match="MAX_TOKENS"):
            GeminiEngine().generate("system", "user")

    def test_ollama_requests_json_format(self, monkeypatch):
        captured: dict[str, Any] = {}

        def fake_post(url: str, **kwargs: Any) -> _StubResponse:
            captured["url"] = url
            captured["json"] = kwargs["json"]
            return _StubResponse({"response": json.dumps(VALID_PAYLOAD)})

        monkeypatch.setattr(engine_mod.httpx, "post", fake_post)
        result = OllamaEngine().generate("system prompt", "user prompt")

        assert result["engine"] == PROVIDER_OLLAMA
        assert captured["url"].endswith("/api/generate")
        assert captured["json"]["stream"] is False
        assert captured["json"]["format"] == "json"


# ── Router ───────────────────────────────────────────────────────────────────
class TestRouter:
    def test_auto_order_prefers_sovereign_first(self):
        assert AUTO_ORDER[0] == PROVIDER_OLLAMA
        assert set(AUTO_ORDER) == {PROVIDER_OLLAMA, PROVIDER_GEMINI, PROVIDER_GROQ}

    def test_explicit_provider_honoured(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GEMINI)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        assert LLMEngine().resolve_provider() == PROVIDER_GEMINI

    def test_unavailable_provider_falls_back(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GROQ)
        monkeypatch.setattr(settings, "GROQ_API_KEY", "")
        assert LLMEngine().resolve_provider() == PROVIDER_RULE_BASED

    def test_unknown_provider_falls_back(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "not-a-provider")
        assert LLMEngine().resolve_provider() == PROVIDER_RULE_BASED

    def test_auto_with_nothing_available_is_rule_based(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "auto")
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
        monkeypatch.setattr(settings, "GROQ_API_KEY", "")
        monkeypatch.setattr(OllamaEngine, "is_available", lambda self: False)
        assert LLMEngine().resolve_provider() == PROVIDER_RULE_BASED

    def test_provider_failure_returns_rule_based_result(self, monkeypatch):
        """A dead provider degrades to a usable answer, never an exception."""
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GEMINI)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")

        def boom(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("503 Service Unavailable")

        monkeypatch.setattr(engine_mod.httpx, "post", boom)
        result = LLMEngine().generate_reasoning(**_reasoning_kwargs())

        assert result["engine"] == PROVIDER_RULE_BASED
        assert len(result["reasoning"]) >= 4
        assert result["cost_estimate_inr"] > 0

    def test_circuit_opens_after_threshold(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GEMINI)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(settings, "LLM_FAILURE_THRESHOLD", 2)

        calls = {"n": 0}

        def boom(*args: Any, **kwargs: Any) -> None:
            calls["n"] += 1
            raise RuntimeError("503 Service Unavailable")

        monkeypatch.setattr(engine_mod.httpx, "post", boom)
        engine = LLMEngine()
        for _ in range(4):
            engine.generate_reasoning(**_reasoning_kwargs())

        # Circuit opens after 2 failures, so the provider is not called again.
        assert calls["n"] == 2
        assert engine._circuit_open is True

    def test_reset_circuit_retries_provider(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GEMINI)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(settings, "LLM_FAILURE_THRESHOLD", 1)
        monkeypatch.setattr(
            engine_mod.httpx,
            "post",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")),
        )

        engine = LLMEngine()
        engine.generate_reasoning(**_reasoning_kwargs())
        assert engine._circuit_open is True

        engine.reset_circuit()
        assert engine._circuit_open is False

    def test_success_resets_failure_count(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GEMINI)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(settings, "LLM_FAILURE_THRESHOLD", 2)

        state = {"fail_next": True}

        def flaky(*args: Any, **kwargs: Any) -> _StubResponse:
            if state["fail_next"]:
                state["fail_next"] = False
                raise RuntimeError("transient 503")
            return _StubResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": json.dumps(VALID_PAYLOAD)}]}}
                    ]
                }
            )

        monkeypatch.setattr(engine_mod.httpx, "post", flaky)
        engine = LLMEngine()
        engine.generate_reasoning(**_reasoning_kwargs())  # fails -> rule-based
        result = engine.generate_reasoning(**_reasoning_kwargs())  # recovers

        assert result["engine"] == PROVIDER_GEMINI
        assert engine._consecutive_failures == 0
        assert engine._circuit_open is False

    def test_available_providers_always_includes_rule_based(self, monkeypatch):
        monkeypatch.setattr(OllamaEngine, "is_available", lambda self: False)
        status = LLMEngine().available_providers()
        assert status[PROVIDER_RULE_BASED] is True
        assert set(status) >= {PROVIDER_OLLAMA, PROVIDER_GEMINI, PROVIDER_GROQ}

    def test_circuit_stays_open_before_cooldown_elapses(self, monkeypatch):
        """
        Regression: a burst of concurrent requests (e.g. many queued behind
        one local GPU) used to open the circuit permanently until process
        restart. Verifies it does NOT retry before CIRCUIT_COOLDOWN_SEC.
        """
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GEMINI)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(settings, "LLM_FAILURE_THRESHOLD", 1)
        monkeypatch.setattr(settings, "CIRCUIT_COOLDOWN_SEC", 20.0)

        calls = {"n": 0}

        def boom(*args: Any, **kwargs: Any) -> None:
            calls["n"] += 1
            raise RuntimeError("503 Service Unavailable")

        monkeypatch.setattr(engine_mod.httpx, "post", boom)

        fake_now = {"t": 1000.0}
        monkeypatch.setattr(engine_mod.time, "monotonic", lambda: fake_now["t"])

        engine = LLMEngine()
        engine.generate_reasoning(**_reasoning_kwargs())  # opens circuit
        assert calls["n"] == 1
        assert engine._circuit_open is True

        fake_now["t"] += 5.0  # well inside the 20s cooldown
        engine.generate_reasoning(**_reasoning_kwargs())
        assert calls["n"] == 1, "must not retry before the cooldown elapses"

    def test_circuit_half_opens_and_recovers_after_cooldown(self, monkeypatch):
        """After CIRCUIT_COOLDOWN_SEC, exactly one retry is allowed; success
        closes the circuit fully (not just for that one call)."""
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GEMINI)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(settings, "LLM_FAILURE_THRESHOLD", 1)
        monkeypatch.setattr(settings, "CIRCUIT_COOLDOWN_SEC", 20.0)

        state = {"fail": True}

        def flaky(*args: Any, **kwargs: Any) -> _StubResponse:
            if state["fail"]:
                raise RuntimeError("503 Service Unavailable")
            return _StubResponse(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": json.dumps(VALID_PAYLOAD)}]}}
                    ]
                }
            )

        monkeypatch.setattr(engine_mod.httpx, "post", flaky)

        fake_now = {"t": 1000.0}
        monkeypatch.setattr(engine_mod.time, "monotonic", lambda: fake_now["t"])

        engine = LLMEngine()
        engine.generate_reasoning(**_reasoning_kwargs())  # opens circuit
        assert engine._circuit_open is True

        fake_now["t"] += 20.0  # cooldown elapsed exactly
        state["fail"] = False  # provider has recovered
        result = engine.generate_reasoning(**_reasoning_kwargs())

        assert result["engine"] == PROVIDER_GEMINI
        assert engine._circuit_open is False
        assert engine._circuit_opened_at is None

        # A later, ordinary failure must be able to open the circuit again -
        # confirms recovery didn't leave any latched state behind.
        state["fail"] = True
        engine.generate_reasoning(**_reasoning_kwargs())
        assert engine._circuit_open is True

    def test_failed_half_open_retry_extends_cooldown(self, monkeypatch):
        """If the retry after cooldown also fails, the circuit re-opens with
        a fresh cooldown window rather than retrying every call."""
        monkeypatch.setattr(settings, "LLM_PROVIDER", PROVIDER_GEMINI)
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(settings, "LLM_FAILURE_THRESHOLD", 1)
        monkeypatch.setattr(settings, "CIRCUIT_COOLDOWN_SEC", 20.0)

        calls = {"n": 0}

        def boom(*args: Any, **kwargs: Any) -> None:
            calls["n"] += 1
            raise RuntimeError("still down")

        monkeypatch.setattr(engine_mod.httpx, "post", boom)

        fake_now = {"t": 1000.0}
        monkeypatch.setattr(engine_mod.time, "monotonic", lambda: fake_now["t"])

        engine = LLMEngine()
        engine.generate_reasoning(**_reasoning_kwargs())  # opens circuit
        assert calls["n"] == 1

        fake_now["t"] += 20.0  # cooldown elapsed - half-open retry allowed
        engine.generate_reasoning(**_reasoning_kwargs())
        assert calls["n"] == 2, "half-open retry should have been attempted"
        assert engine._circuit_open is True

        fake_now["t"] += 5.0  # inside the NEW cooldown window
        engine.generate_reasoning(**_reasoning_kwargs())
        assert calls["n"] == 2, "must not retry again until the new cooldown elapses"


class TestRuleBasedEngineSeverityCost:
    """
    Regression: cost, downtime, and the maintenance interval used to come
    from a hardcoded per-equipment table (COST_MAP/DOWNTIME_MAP/INTERVAL_MAP),
    completely ignoring context_docs even though it was already a parameter.
    Every query about the same equipment - routine or badly overdue alike -
    produced the exact same figure, because that flat table was the only
    place the number ever came from. Fixed by reading routine/urgent figures
    from the retrieved equipment_specs.json record instead, so a genuinely
    different query produces a genuinely different, still-explainable answer.
    """

    def test_routine_query_uses_the_routine_baseline(self):
        result = RuleBasedEngine().generate(
            equipment="reactor-4",
            intent="schedule_maintenance",
            current_state={"pressure_bar": 4.2, "last_service_days": 90},
            context_docs=[REACTOR_4_SPEC],
            constraints={"budget_inr": 100000},
        )
        assert result["cost_estimate_inr"] == 35000
        assert result["downtime_hours"] == 2.5

    def test_urgent_pressure_scales_cost_and_downtime_up(self):
        """Same equipment, same call shape - only pressure changed."""
        routine = RuleBasedEngine().generate(
            equipment="reactor-4",
            intent="schedule_maintenance",
            current_state={"pressure_bar": 4.2, "last_service_days": 90},
            context_docs=[REACTOR_4_SPEC],
            constraints={"budget_inr": 100000},
        )
        urgent = RuleBasedEngine().generate(
            equipment="reactor-4",
            intent="schedule_maintenance",
            # 4.9 / 5.0 max = 98% - above the 85% urgency threshold
            current_state={"pressure_bar": 4.9, "last_service_days": 90},
            context_docs=[REACTOR_4_SPEC],
            constraints={"budget_inr": 100000},
        )
        assert urgent["cost_estimate_inr"] > routine["cost_estimate_inr"]
        assert urgent["downtime_hours"] > routine["downtime_hours"]
        assert urgent["cost_estimate_inr"] == 35000 * 1.35
        assert urgent["downtime_hours"] == round(2.5 * 1.6, 1)

    def test_overdue_service_alone_triggers_urgent_pricing(self):
        """Normal pressure, but badly overdue - must still scale up."""
        result = RuleBasedEngine().generate(
            equipment="reactor-4",
            intent="schedule_maintenance",
            current_state={"pressure_bar": 4.0, "last_service_days": 400},
            context_docs=[REACTOR_4_SPEC],
            constraints={"budget_inr": 100000},
        )
        assert result["cost_estimate_inr"] > 35000

    def test_reasoning_explains_the_urgent_multiplier(self):
        """The cost step must say WHY it's higher, not just show a number."""
        result = RuleBasedEngine().generate(
            equipment="reactor-4",
            intent="schedule_maintenance",
            current_state={"pressure_bar": 4.9, "last_service_days": 90},
            context_docs=[REACTOR_4_SPEC],
            constraints={"budget_inr": 100000},
        )
        cost_step = next(s for s in result["reasoning"] if "Estimated cost" in s)
        assert "Urgent pricing applies" in cost_step
        assert "x1.35" in cost_step

    def test_missing_equipment_doc_falls_back_without_crashing(self):
        """Retrieval found nothing for this equipment - must degrade safely,
        not crash, using the documented fallback constants."""
        result = RuleBasedEngine().generate(
            equipment="reactor-4",
            intent="schedule_maintenance",
            current_state={"pressure_bar": 4.2},
            context_docs=[],  # nothing retrieved
            constraints={"budget_inr": 100000},
        )
        assert result["cost_estimate_inr"] == RuleBasedEngine._FALLBACK_COST_INR
        assert result["downtime_hours"] == RuleBasedEngine._FALLBACK_DOWNTIME_HOURS

    def test_different_equipment_reads_its_own_spec_not_reactor4s(self):
        """Guards against _find_equipment_doc matching the wrong record."""
        pump_spec = {
            **REACTOR_4_SPEC,
            "id": "pump-a",
            "routine_service_cost_inr": 15000,
            "routine_service_downtime_hours": 1.5,
        }
        result = RuleBasedEngine().generate(
            equipment="pump-a",
            intent="schedule_maintenance",
            current_state={"pressure_bar": 4.0, "last_service_days": 30},
            context_docs=[REACTOR_4_SPEC, pump_spec],
            constraints={"budget_inr": 100000},
        )
        assert result["cost_estimate_inr"] == 15000
