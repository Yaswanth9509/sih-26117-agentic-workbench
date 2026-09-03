"""
Agent 3: ReasoningAgent
The AI brain - generates step-by-step reasoning and recommendation.

Provider selection lives entirely in core.llm_engine (ollama / gemini / groq /
rule-based). This agent is deliberately provider-agnostic: every backend
returns the same JSON schema, so swapping in on-premise Mistral post-MVP
changes nothing here.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import settings
from core.llm_engine import LLMEngine

logger = logging.getLogger(__name__)

# Module-level singleton (LLMEngine is stateless, safe to share)
_llm_engine: LLMEngine | None = None


def _get_engine() -> LLMEngine:
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LLMEngine()
    return _llm_engine


def _coerce_float(value: Any, default: float) -> float:
    """
    Provider JSON is LLM-generated, not schema-enforced. A generative model
    (ollama/gemini/groq) can return a number as a string, or formatted (e.g.
    "35,000" or "Rs.35000") even when it usually doesn't - observed live:
    the identical prompt occasionally returns cost_estimate_inr as a string.
    Coerce defensively here, once, so validation math and the UI's numeric
    formatting never see anything but a real float.
    """
    if isinstance(value, bool):
        return default  # bool is an int subclass in Python; not a real number here
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[^\d.-]", "", value)
        if cleaned:
            try:
                return float(cleaned)
            except ValueError:
                pass
    return default


def _coerce_string_list(value: Any) -> list[str]:
    """Provider output should be a list of reasoning steps; degrade any
    other shape (a bare string, None, ...) into a safe list rather than
    breaking a downstream len()/iteration assumption."""
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value:
        return [value]
    return []


def normalise_reasoning_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise a raw provider result (whatever LLMEngine.generate_reasoning
    or RuleBasedEngine.generate returned) into the fixed shape every
    downstream agent depends on - both keys AND types, since provider JSON
    is LLM-generated and not schema-enforced. Shared by ReasoningAgent._run
    and the orchestrator's own last-resort fallback path (used when the
    reasoning AGENT itself times out, not just its LLM provider) so both
    apply identical rules.
    """
    return {
        "reasoning": _coerce_string_list(result.get("reasoning", [])),
        "recommendation": str(result.get("recommendation", "")),
        "cost_estimate_inr": _coerce_float(
            result.get("cost_estimate_inr"), default=0.0
        ),
        "downtime_hours": _coerce_float(result.get("downtime_hours"), default=0.0),
        "risk_if_delayed": str(result.get("risk_if_delayed", "")),
        "confidence": _coerce_float(result.get("confidence"), default=0.8),
        "engine_used": result.get("engine", "rule-based"),
    }


class ReasoningAgent(BaseAgent):
    """
    Generates reasoning chain and maintenance recommendation.
    Input: query + context_documents + understanding dict
    Output: reasoning[], recommendation, cost, downtime, risk, confidence, engine
    """

    def __init__(self) -> None:
        # Own timeout budget, not the shared AGENT_TIMEOUT_SEC: this is the
        # only agent that may call a local GPU LLM, which is slower than the
        # other four agents' typical <20ms.
        super().__init__(
            name="reasoning", timeout_sec=settings.REASONING_AGENT_TIMEOUT_SEC
        )

    async def _run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query: str = input_data.get("query", "")
        understanding: dict[str, Any] = input_data.get("understanding", {})
        context_docs: list[dict[str, Any]] = input_data.get("context_documents", [])

        equipment: str = understanding.get("equipment", "unknown")
        intent: str = understanding.get("intent", "status_check")
        current_state: dict[str, Any] = understanding.get("current_state", {})
        constraints: dict[str, Any] = understanding.get("constraints", {})

        if not query:
            return {"error": "No query provided", "status": "FAILED"}

        engine = _get_engine()
        # Provider calls are blocking HTTP. Run them off the event loop so the
        # BaseAgent timeout can actually interrupt a hung provider.
        result = await asyncio.to_thread(
            engine.generate_reasoning,
            equipment=equipment,
            intent=intent,
            current_state=current_state,
            context_docs=context_docs,
            constraints=constraints,
            query=query,
        )

        return normalise_reasoning_result(result)
