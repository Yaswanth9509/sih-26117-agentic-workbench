"""
Shared test configuration.

The suite must be deterministic and fully offline: no test may depend on a
cloud provider being reachable, or on whether a developer has a key in .env.
Every test therefore runs against the rule-based engine unless it explicitly
opts out. Provider wiring is covered by unit tests with stubbed transports in
tests/test_llm_providers.py.
"""

from __future__ import annotations

from typing import Iterator

import pytest

from config.settings import settings
from core.llm_engine import PROVIDER_RULE_BASED


@pytest.fixture(autouse=True, scope="session")
def force_offline_engine() -> Iterator[None]:
    """Pin the reasoning engine to rule-based for the whole session."""
    original_provider = settings.LLM_PROVIDER
    original_gemini = settings.GEMINI_API_KEY
    original_groq = settings.GROQ_API_KEY

    settings.LLM_PROVIDER = PROVIDER_RULE_BASED
    settings.GEMINI_API_KEY = ""
    settings.GROQ_API_KEY = ""

    # Drop any engine built before this fixture ran so the pin takes effect.
    import agents.reasoning_agent as reasoning_agent

    reasoning_agent._llm_engine = None

    yield

    settings.LLM_PROVIDER = original_provider
    settings.GEMINI_API_KEY = original_gemini
    settings.GROQ_API_KEY = original_groq
    reasoning_agent._llm_engine = None
