"""
Agent 1: QueryUnderstandingAgent
Parses the raw engineer query into structured intent + entities.
Pure Python - no LLM, no network calls.
"""

from __future__ import annotations

import re
import logging
from typing import Any

from agents.base_agent import BaseAgent
from config.business_rules import (
    INTENT_KEYWORDS,
    EQUIPMENT_ALIASES,
    SUPPORTED_EQUIPMENT,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class QueryUnderstandingAgent(BaseAgent):
    """Parses query -> intent, equipment, current_state, constraints, confidence."""

    def __init__(self) -> None:
        super().__init__(
            name="query_understanding", timeout_sec=settings.AGENT_TIMEOUT_SEC
        )

    async def _run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query: str = input_data.get("query", "").strip()
        if not query:
            return {"error": "Empty query", "status": "FAILED"}

        q_lower = query.lower()

        # ── 1. Detect equipment ──────────────────────────────────────────────
        equipment, loose_keyword = self._detect_equipment(q_lower)

        # ── 2. Detect intent ─────────────────────────────────────────────────
        intent, intent_conf = self._detect_intent(q_lower)

        # ── 3. Extract numerical values ───────────────────────────────────────
        current_state = self._extract_state(q_lower)

        # ── 4. Extract constraints ────────────────────────────────────────────
        constraints = self._extract_constraints(q_lower)

        # ── 5. Compute overall confidence ────────────────────────────────────
        confidence = self._compute_confidence(equipment, intent_conf, current_state)

        return {
            "intent": intent,
            "equipment": equipment or "unknown",
            # Set only when equipment was inferred from a generic type word
            # ("reactor", "pump", ...) rather than a specific ID or alias -
            # e.g. "the reactor" or "all the reactors". DecisionAgent uses
            # this to disclose that only one unit of that type is in scope,
            # rather than silently answering about a single unit when the
            # question may have meant the whole fleet or was ambiguous.
            "equipment_loose_keyword": loose_keyword,
            "current_state": current_state,
            "constraints": constraints,
            "confidence": confidence,
            "raw_query": query,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _detect_equipment(self, q: str) -> tuple[str | None, str | None]:
        """
        Returns (equipment_id, loose_keyword). loose_keyword is non-None only
        when the match came from a generic type word, not a specific ID or
        a known alias - the caller uses this to tell an honest match from a
        guessed one.
        """
        # Direct match against supported IDs
        for eq in SUPPORTED_EQUIPMENT:
            if eq in q:
                return eq, None
        # Try aliases
        for alias, canonical in EQUIPMENT_ALIASES.items():
            if alias in q:
                return canonical, None
        # Loose partial match (e.g. "reactor" -> "reactor-4")
        loose_map = {
            "reactor": "reactor-4",
            "compressor": "compressor-b",
            "pump": "pump-a",
            "exchanger": "exchanger-c",
            "separator": "separator-d",
        }
        for keyword, eq_id in loose_map.items():
            if keyword in q:
                return eq_id, keyword
        return None, None

    def _detect_intent(self, q: str) -> tuple[str, float]:
        scores: dict[str, int] = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in q)
            if hits:
                scores[intent] = hits

        if not scores:
            return "status_check", 0.5

        best_intent = max(scores, key=lambda k: scores[k])
        total_keywords = len(INTENT_KEYWORDS[best_intent])
        conf = min(0.5 + scores[best_intent] / total_keywords * 0.5, 0.99)
        return best_intent, round(conf, 2)

    def _extract_state(self, q: str) -> dict[str, Any]:
        state: dict[str, Any] = {}

        # Pressure: "4.2 bar" / "pressure 4.2"
        m = re.search(r"pressure[:\s]+(\d+\.?\d*)\s*bar", q)
        if not m:
            m = re.search(r"(\d+\.?\d*)\s*bar", q)
        if m:
            state["pressure_bar"] = float(m.group(1))

        # Temperature rise: "15 degrees" / "15C" / "temp.*15"
        m = re.search(r"temp(?:erature)?[^0-9]*(\d+)\s*(?:c|celsius|degrees?)?", q)
        if m:
            state["temperature_rise_c"] = int(m.group(1))

        # Last service: "6 months" / "180 days"
        m = re.search(r"(\d+)\s*month", q)
        if m:
            state["last_service_days"] = int(m.group(1)) * 30
        else:
            m = re.search(r"(\d+)\s*day", q)
            if m:
                state["last_service_days"] = int(m.group(1))

        # Vibration mention
        if "vibrat" in q or "noise" in q:
            state["abnormal_vibration"] = True

        return state

    def _extract_constraints(self, q: str) -> dict[str, Any]:
        constraints: dict[str, Any] = {}

        # Budget: "50K" / "50,000" / "Rs. 50000" / "INR 50000"
        m = re.search(
            r"(?:rs\.?|inr|budget)[:\s]*([0-9,]+\.?\d*)\s*(k|lakh|l)?", q, re.IGNORECASE
        )
        if not m:
            m = re.search(r"([0-9,]+)\s*(k|lakh|l)\b", q, re.IGNORECASE)

        if m:
            amount = float(m.group(1).replace(",", ""))
            suffix = (m.group(2) or "").lower()
            if suffix in ("k",):
                amount *= 1000
            elif suffix in ("lakh", "l"):
                amount *= 100000
            constraints["budget_inr"] = int(amount)

        # Time pressure: "urgent", "asap", "immediately"
        if any(w in q for w in ["urgent", "asap", "immediately", "emergency"]):
            constraints["urgency"] = "HIGH"

        return constraints

    def _compute_confidence(
        self,
        equipment: str | None,
        intent_conf: float,
        state: dict[str, Any],
    ) -> float:
        conf = intent_conf
        if equipment:
            conf += 0.1
        if state:
            conf += 0.05 * min(len(state), 3)
        return round(min(conf, 0.99), 2)
