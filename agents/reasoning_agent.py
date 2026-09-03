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


class ReasoningAgent(BaseAgent):
    """
    Generates reasoning chain and maintenance recommendation.
    Input: query + context_documents + understanding dict
    Output: reasoning[], recommendation, cost, downtime, risk, confidence, engine
    """

    def __init__(self) -> None:
        super().__init__(name="reasoning", timeout_sec=settings.AGENT_TIMEOUT_SEC)

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

        # Normalise fields so downstream agents always get consistent keys
        return {
            "reasoning": result.get("reasoning", []),
            "recommendation": result.get("recommendation", ""),
            "cost_estimate_inr": result.get("cost_estimate_inr", 0),
            "downtime_hours": result.get("downtime_hours", 0.0),
            "risk_if_delayed": result.get("risk_if_delayed", ""),
            "confidence": result.get("confidence", 0.8),
            "engine_used": result.get("engine", "rule-based"),
        }
