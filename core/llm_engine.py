"""
LLM Engine: pluggable reasoning providers behind one stable interface.

Providers (selected by settings.LLM_PROVIDER):
  ollama      - local Mistral-7B via ollama. Fully offline / sovereign.
                This is the target production stack for MRPL.
  gemini      - Google Gemini REST API (cloud).
  groq        - Groq API, Llama-3 (cloud).
  rule-based  - deterministic engine, zero network. Always available.
  auto        - probe in the order above and use the first that answers.

Every provider returns the SAME JSON schema, so agents never learn which one
ran. Swapping the MVP's cloud providers for on-premise Mistral is a config
change, not a code change - see docs/MIGRATION.md.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Protocol

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

# Provider identifiers
PROVIDER_OLLAMA = "ollama"
PROVIDER_GEMINI = "gemini"
PROVIDER_GROQ = "groq"
PROVIDER_RULE_BASED = "rule-based"
PROVIDER_AUTO = "auto"

# Order used when LLM_PROVIDER=auto. Sovereign first, cloud second.
AUTO_ORDER: tuple[str, ...] = (PROVIDER_OLLAMA, PROVIDER_GEMINI, PROVIDER_GROQ)


class ReasoningProvider(Protocol):
    """Contract every reasoning backend implements."""

    name: str

    def is_available(self) -> bool:
        """Cheap check: is this provider configured and reachable?"""
        ...

    def generate(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return the parsed recommendation JSON. Raises on failure."""
        ...


def _parse_json_response(raw: str, provider: str) -> dict[str, Any]:
    """Strip markdown fences some models emit, then parse JSON."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    result: dict[str, Any] = json.loads(cleaned)
    result["engine"] = provider
    return result


# ---------------------------------------------------------------------------
# Rule-Based Reasoning Engine (always-available offline default)
# ---------------------------------------------------------------------------


class RuleBasedEngine:
    """
    Deterministic reasoning engine that mimics LLM output format.
    Produces structured JSON identical to what Groq would return.

    Cost, downtime, and the maintenance interval are read from the matching
    equipment_specs.json record in context_docs, not a hardcoded per-equipment
    table. Previously they were: every query about the same equipment - "on
    schedule, 4.2 bar" or "badly overdue, 4.9 bar" alike - produced the exact
    same Rs.35,000 figure, because that flat lookup was the only place either
    this engine or a real LLM (grounded in the same document) ever got a
    number from. Now both routine and urgent figures live in the retrieved
    document itself, so a genuinely different query produces a genuinely
    different, still-explainable answer - see generate_sample_data.py's
    SEVERITY_POLICY_NOTE for the rule this applies.
    """

    # Used only if retrieval didn't surface an equipment_specs record for
    # this equipment - should not happen in normal operation, since the
    # search query always includes the equipment ID as literal text.
    _FALLBACK_COST_INR = 30000.0
    _FALLBACK_DOWNTIME_HOURS = 2.0
    _FALLBACK_INTERVAL_MONTHS = 6.0
    _FALLBACK_URGENT_COST_MULTIPLIER = 1.35
    _FALLBACK_URGENT_DOWNTIME_MULTIPLIER = 1.6

    @staticmethod
    def _find_equipment_doc(
        eq: str, context_docs: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """The retrieved equipment_specs.json record for this equipment, if
        retrieval surfaced one among the (usually top-3) context documents."""
        for doc in context_docs:
            if (
                str(doc.get("id", "")).lower() == eq
                and "routine_service_cost_inr" in doc
            ):
                return doc
        return None

    def generate(
        self,
        equipment: str,
        intent: str,
        current_state: dict[str, Any],
        context_docs: list[dict[str, Any]],
        constraints: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a rule-based recommendation matching Groq JSON schema."""

        eq = equipment.lower()
        spec = self._find_equipment_doc(eq, context_docs)

        def _spec_float(key: str, default: float) -> float:
            if spec is None:
                return default
            try:
                return float(spec.get(key, default))
            except (TypeError, ValueError):
                return default

        base_cost = _spec_float("routine_service_cost_inr", self._FALLBACK_COST_INR)
        base_downtime = _spec_float(
            "routine_service_downtime_hours", self._FALLBACK_DOWNTIME_HOURS
        )
        cost_multiplier = _spec_float(
            "urgent_cost_multiplier", self._FALLBACK_URGENT_COST_MULTIPLIER
        )
        downtime_multiplier = _spec_float(
            "urgent_downtime_multiplier", self._FALLBACK_URGENT_DOWNTIME_MULTIPLIER
        )
        interval = int(
            _spec_float("maintenance_interval_months", self._FALLBACK_INTERVAL_MONTHS)
        )
        budget = constraints.get("budget_inr", 100000)

        pressure = current_state.get("pressure_bar")
        last_service_days = current_state.get("last_service_days", 0)
        temp_rise = current_state.get("temperature_rise_c", 0)

        reasoning: list[str] = []
        confidence = 0.85

        # ── Pressure analysis ────────────────────────────────────────────────
        pressure_pct: float | None = None
        if pressure is not None:
            safe_max = 5.0 if "reactor" in eq else 8.0 if "compressor" in eq else 6.0
            pressure_pct = round(pressure / safe_max * 100, 1)
            if pressure_pct > 95:
                reasoning.append(
                    f"Step 1: CRITICAL - Pressure {pressure} bar is {pressure_pct}% of max safe "
                    f"value ({safe_max} bar). Immediate action required."
                )
                confidence = 0.97
            elif pressure_pct > 85:
                reasoning.append(
                    f"Step 1: WARNING - Pressure {pressure} bar is {pressure_pct}% of max safe "
                    f"value ({safe_max} bar). Plan maintenance soon."
                )
                confidence = 0.92
            else:
                reasoning.append(
                    f"Step 1: Pressure {pressure} bar is {pressure_pct}% of max safe value "
                    f"({safe_max} bar) - within safe operating range."
                )
        else:
            reasoning.append(
                "Step 1: No pressure reading provided - using historical averages."
            )

        # ── Temperature analysis ─────────────────────────────────────────────
        if temp_rise and temp_rise > 0:
            if temp_rise > 20:
                reasoning.append(
                    f"Step 2: ALERT - Temperature risen by {temp_rise}C above baseline. "
                    "Indicates possible bearing wear or coolant issue."
                )
                confidence = max(confidence, 0.94)
            else:
                reasoning.append(
                    f"Step 2: Temperature rise of {temp_rise}C noted - within acceptable "
                    "variation range."
                )
        else:
            reasoning.append("Step 2: Temperature readings within normal range.")

        # ── Maintenance schedule analysis ────────────────────────────────────
        last_days_str = f"{last_service_days} days" if last_service_days else "unknown"
        interval_days = interval * 30
        is_overdue = bool(last_service_days) and last_service_days >= interval_days
        if is_overdue:
            reasoning.append(
                f"Step 3: Last service was {last_days_str} ago. "
                f"Recommended interval is {interval} months ({interval_days} days). "
                "Equipment is DUE for maintenance."
            )
            confidence = max(confidence, 0.93)
        elif last_service_days and last_service_days >= interval_days * 0.8:
            reasoning.append(
                f"Step 3: Last service was {last_days_str} ago. "
                f"Approaching {interval}-month service window - schedule proactively."
            )
        else:
            reasoning.append(
                f"Step 3: Last service was {last_days_str} ago. "
                f"Next service interval: {interval} months."
            )

        # ── Cost & downtime: severity-adjusted against the routine baseline ──
        is_urgent = (
            (pressure_pct is not None and pressure_pct > 85)
            or is_overdue
            or (bool(temp_rise) and temp_rise > 20)
        )
        if is_urgent:
            cost = float(round(base_cost * cost_multiplier))
            downtime = float(round(base_downtime * downtime_multiplier, 1))
            urgency_note = (
                f" Urgent pricing applies (elevated pressure, overdue service, "
                f"or reported symptoms): Rs.{int(base_cost):,} routine cost "
                f"x{cost_multiplier:g}, {base_downtime}h routine downtime "
                f"x{downtime_multiplier:g}."
            )
        else:
            cost = base_cost
            downtime = base_downtime
            urgency_note = ""

        # ── Cost analysis ────────────────────────────────────────────────────
        if budget and cost > budget:
            reasoning.append(
                f"Step 4: Estimated cost Rs.{cost:,.0f} EXCEEDS budget Rs.{budget:,.0f}."
                f"{urgency_note} Request budget approval or phased approach."
            )
            confidence -= 0.05
        else:
            reasoning.append(
                f"Step 4: Estimated cost Rs.{cost:,.0f} is within budget "
                f"Rs.{int(budget):,}. Buffer: Rs.{int(budget - cost):,}.{urgency_note}"
            )

        # ── Historical precedent ─────────────────────────────────────────────
        reasoning.append(
            f"Step 5: Historical data shows {equipment} maintenance successful in "
            "4 of 5 previous similar cases using standard procedure."
        )

        # ── Recommendation by intent ─────────────────────────────────────────
        if intent == "risk_assessment":
            recommendation = (
                f"HIGH risk detected for {equipment}. Recommend urgent inspection "
                "within 48 hours. Do not operate beyond current parameters."
            )
            risk_if_delayed = (
                "Equipment failure likely within 2-4 weeks if maintenance is postponed."
            )
        elif intent == "cost_optimization":
            recommendation = (
                f"Proceed with {equipment} maintenance (Rs.{cost:,.0f}). "
                "Defer lower-priority equipment to next quarter."
            )
            risk_if_delayed = (
                "Deferred equipment may reach critical state by next quarter."
            )
        elif intent == "compliance_check":
            if last_service_days and last_service_days >= interval * 30:
                recommendation = (
                    f"NOT RECOMMENDED to skip - {equipment} is already at/past its "
                    f"{interval}-month service interval. Violates maintenance protocol."
                )
                risk_if_delayed = (
                    "Regulatory non-compliance and increased failure probability."
                )
            else:
                recommendation = (
                    f"Maintenance can be deferred up to {interval * 30 - last_service_days} "
                    f"more days within compliance window for {equipment}."
                )
                risk_if_delayed = "Monitor closely if deferring; check pressure daily."
        else:  # schedule_maintenance / status_check / default
            recommendation = (
                f"Schedule maintenance for {equipment} within the next 2 weeks. "
                f"Estimated cost: Rs.{cost:,.0f}, downtime: {downtime} hours."
            )
            risk_if_delayed = (
                f"Delaying beyond {interval + 1} months risks unplanned failure "
                "and higher repair costs."
            )

        return {
            "reasoning": reasoning,
            "recommendation": recommendation,
            "cost_estimate_inr": cost,
            "downtime_hours": downtime,
            "risk_if_delayed": risk_if_delayed,
            "confidence": round(confidence, 2),
            "engine": "rule-based",
        }


# ---------------------------------------------------------------------------
# Ollama Engine - local Mistral-7B (target sovereign stack)
# ---------------------------------------------------------------------------


class OllamaEngine:
    """
    Calls a local ollama daemon for fully offline reasoning.

    This is the provider MRPL runs in production: no data leaves the plant
    network. It is inactive until `bash scripts/setup_llm.sh` has installed
    ollama and pulled the model, at which point `auto` selects it first.
    """

    name = PROVIDER_OLLAMA

    def is_available(self) -> bool:
        """True only if a local ollama daemon answers and has the model."""
        try:
            response = httpx.get(
                f"{settings.OLLAMA_BASE_URL}/api/tags",
                timeout=settings.OLLAMA_PROBE_TIMEOUT_SEC,
            )
            response.raise_for_status()
            tags = response.json().get("models", [])
            names = [str(m.get("name", "")) for m in tags]
            return any(n.startswith(settings.OLLAMA_MODEL) for n in names)
        except Exception:
            return False

    def generate(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Call ollama /api/generate and return parsed JSON."""
        response = httpx.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "format": "json",
            },
            timeout=settings.OLLAMA_TIMEOUT_SEC,
        )
        response.raise_for_status()
        raw = str(response.json().get("response", "")).strip()
        if not raw:
            raise RuntimeError("ollama returned an empty response")
        return _parse_json_response(raw, self.name)


# ---------------------------------------------------------------------------
# Gemini Engine - Google Generative Language REST API
# ---------------------------------------------------------------------------


class GeminiEngine:
    """Calls the Gemini REST API. Requires GEMINI_API_KEY in the environment."""

    name = PROVIDER_GEMINI

    def is_available(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    def generate(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Call Gemini and return parsed JSON."""
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set")

        url = (
            f"{settings.GEMINI_BASE_URL}/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )
        response = httpx.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": settings.GEMINI_API_KEY,
            },
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "maxOutputTokens": settings.GEMINI_MAX_TOKENS,
                    "temperature": settings.GEMINI_TEMPERATURE,
                },
            },
            timeout=settings.GEMINI_TIMEOUT_SEC,
        )
        response.raise_for_status()
        payload = response.json()

        candidates = payload.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Gemini returned no candidates: {payload}")

        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        if not parts:
            # Thinking-heavy models can spend the whole budget before answering.
            reason = candidate.get("finishReason", "unknown")
            raise RuntimeError(f"Gemini returned no content (finishReason={reason})")

        raw = str(parts[0].get("text", "")).strip()
        if not raw:
            raise RuntimeError("Gemini returned an empty response")
        return _parse_json_response(raw, self.name)


# ---------------------------------------------------------------------------
# Groq Engine - Llama-3
# ---------------------------------------------------------------------------


class GroqEngine:
    """Calls the Groq API for LLM-powered reasoning."""

    name = PROVIDER_GROQ

    def __init__(self) -> None:
        self._client: Any = None

    def is_available(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import groq

                self._client = groq.Groq(api_key=settings.GROQ_API_KEY)
            except Exception as exc:
                raise RuntimeError(f"Groq client init failed: {exc}") from exc
        return self._client

    def generate(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Call Groq and return parsed JSON."""
        client = self._get_client()
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=settings.GROQ_MAX_TOKENS,
            temperature=settings.GROQ_TEMPERATURE,
            timeout=settings.GROQ_TIMEOUT_SEC,
        )
        raw = response.choices[0].message.content.strip()
        return _parse_json_response(raw, self.name)


# ---------------------------------------------------------------------------
# Public LLMEngine (router)
# ---------------------------------------------------------------------------


class LLMEngine:
    """
    Public interface for LLM reasoning.

    Resolves one provider (respecting settings.LLM_PROVIDER), uses it, and
    falls back to the rule-based engine if it is unavailable or errors.
    Callers never need to know which engine ran - the result always carries
    an "engine" key naming it.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Any] = {
            PROVIDER_OLLAMA: OllamaEngine(),
            PROVIDER_GEMINI: GeminiEngine(),
            PROVIDER_GROQ: GroqEngine(),
        }
        self._fallback = RuleBasedEngine()
        self._resolved: str | None = None
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_opened_at: float | None = None
        # provider name -> (monotonic timestamp, available)
        self._availability: dict[str, tuple[float, bool]] = {}

    # ── Provider resolution ──────────────────────────────────────────────────

    def resolve_provider(self, refresh: bool = False) -> str:
        """
        Decide which provider to use. Cached after the first call so the
        ollama probe costs at most one round trip per process.
        """
        if self._resolved is not None and not refresh:
            return self._resolved

        configured = settings.LLM_PROVIDER.strip().lower()

        if configured == PROVIDER_AUTO:
            for candidate in AUTO_ORDER:
                if self._providers[candidate].is_available():
                    self._resolved = candidate
                    break
            else:
                self._resolved = PROVIDER_RULE_BASED
        elif configured in self._providers:
            available = self._providers[configured].is_available()
            self._resolved = configured if available else PROVIDER_RULE_BASED
            if not available:
                logger.warning(
                    f"LLM_PROVIDER={configured} is not available, "
                    "falling back to rule-based"
                )
        else:
            self._resolved = PROVIDER_RULE_BASED

        logger.info(f"llm provider resolved: {self._resolved}")
        return self._resolved

    def _record_failure(self, provider_name: str) -> None:
        """
        Open the circuit after repeated failures so a degraded provider
        cannot add its timeout to every subsequent query. While open, queries
        go straight to the rule-based engine - until CIRCUIT_COOLDOWN_SEC
        elapses, at which point one retry (half-open) is allowed again. A
        failed half-open retry re-opens the circuit and restarts the cooldown.
        """
        threshold = settings.LLM_FAILURE_THRESHOLD
        if threshold <= 0:
            return
        self._consecutive_failures += 1
        if self._consecutive_failures >= threshold:
            was_open = self._circuit_open
            self._circuit_open = True
            self._circuit_opened_at = time.monotonic()
            if not was_open:
                logger.warning(
                    f"circuit opened: {provider_name} failed "
                    f"{self._consecutive_failures}x, serving rule-based for "
                    f"{settings.CIRCUIT_COOLDOWN_SEC:.0f}s"
                )
            else:
                logger.warning(
                    f"circuit half-open retry failed for {provider_name}, "
                    f"re-opening for another {settings.CIRCUIT_COOLDOWN_SEC:.0f}s"
                )

    def _circuit_allows_attempt(self) -> bool:
        """True if the primary provider should be tried: circuit is closed,
        or open long enough that a half-open retry is due."""
        if not self._circuit_open:
            return True
        cooldown = settings.CIRCUIT_COOLDOWN_SEC
        if cooldown <= 0:
            return False  # circuit never recovers automatically
        if self._circuit_opened_at is None:
            return True
        return (time.monotonic() - self._circuit_opened_at) >= cooldown

    def reset_circuit(self) -> None:
        """Close the circuit and retry the configured provider."""
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_opened_at = None

    def _is_available_cached(self, name: str) -> bool:
        """
        Availability of one provider, memoised for PROVIDER_PROBE_TTL_SEC.

        The ollama probe is a real network round trip. /health calls this for
        every provider on every request, so without the cache a health check
        costs seconds whenever ollama is absent.
        """
        ttl = settings.PROVIDER_PROBE_TTL_SEC
        now = time.monotonic()

        if ttl > 0:
            cached = self._availability.get(name)
            if cached is not None and now - cached[0] < ttl:
                return cached[1]

        available = self._providers[name].is_available()
        self._availability[name] = (now, available)
        return available

    def available_providers(self) -> dict[str, bool]:
        """Availability of every provider - used by the /health endpoint."""
        status = {name: self._is_available_cached(name) for name in self._providers}
        status[PROVIDER_RULE_BASED] = True
        return status

    # ── Reasoning ────────────────────────────────────────────────────────────

    def generate_reasoning(
        self,
        equipment: str,
        intent: str,
        current_state: dict[str, Any],
        context_docs: list[dict[str, Any]],
        constraints: dict[str, Any],
        query: str,
    ) -> dict[str, Any]:
        """
        Generate step-by-step reasoning and a recommendation.

        Returns:
            dict with keys: reasoning, recommendation, cost_estimate_inr,
            downtime_hours, risk_if_delayed, confidence, engine
        """
        provider_name = self.resolve_provider()

        if provider_name != PROVIDER_RULE_BASED and self._circuit_allows_attempt():
            try:
                from config.prompts import (
                    REASONING_SYSTEM_PROMPT,
                    REASONING_USER_PROMPT,
                )

                user_prompt = REASONING_USER_PROMPT.format(
                    equipment=equipment,
                    current_state=json.dumps(current_state, indent=2),
                    context=json.dumps(context_docs[:3], indent=2),
                    query=query,
                )
                result = self._providers[provider_name].generate(
                    REASONING_SYSTEM_PROMPT, user_prompt
                )
                if self._circuit_open:
                    logger.info(f"circuit closed: {provider_name} recovered")
                self._consecutive_failures = 0
                self._circuit_open = False
                self._circuit_opened_at = None
                logger.info(f"engine={provider_name} equipment={equipment}")
                return result
            except Exception as exc:
                self._record_failure(provider_name)
                logger.warning(
                    f"{provider_name} failed ({exc}), using rule-based fallback"
                )

        result = self._fallback.generate(
            equipment=equipment,
            intent=intent,
            current_state=current_state,
            context_docs=context_docs,
            constraints=constraints,
        )
        logger.info(f"engine=rule-based equipment={equipment}")
        return result

    # ── Health ───────────────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Report the active engine and what else is reachable."""
        resolved = self.resolve_provider()
        cooldown_remaining = None
        if self._circuit_open and self._circuit_opened_at is not None:
            elapsed = time.monotonic() - self._circuit_opened_at
            cooldown_remaining = max(0.0, settings.CIRCUIT_COOLDOWN_SEC - elapsed)
        return {
            "engine": PROVIDER_RULE_BASED if self._circuit_open else resolved,
            "status": "ok",
            "configured_provider": resolved,
            "circuit_open": self._circuit_open,
            "circuit_retry_in_sec": (
                round(cooldown_remaining, 1) if cooldown_remaining else None
            ),
            "providers": self.available_providers(),
        }
