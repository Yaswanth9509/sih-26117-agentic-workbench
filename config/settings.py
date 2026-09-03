"""
Centralized configuration for MRPL Agentic Workbench.
All values read from environment variables or .env file.
No hardcoded secrets anywhere.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings - loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    # ── LLM provider selection ────────────────────────────────────────────────
    # auto      = probe in order: ollama -> gemini -> groq -> rule-based
    # ollama    = local Mistral-7B (sovereign / fully offline; target stack)
    # gemini    = Google Gemini REST API (cloud)
    # groq      = Groq API (cloud)
    # rule-based = deterministic offline engine, no network at all
    LLM_PROVIDER: str = "auto"

    # ── LLM: ollama (local Mistral-7B) ────────────────────────────────────────
    # 127.0.0.1 not localhost: localhost resolves ::1 first on Windows and
    # ollama binds IPv4, so every probe would stall ~2s before falling back.
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "mistral"
    # Must stay below REASONING_AGENT_TIMEOUT_SEC so the engine's own
    # rule-based fallback runs instead of the agent being killed mid-call
    # (same rule as GEMINI_TIMEOUT_SEC below). Measured on an RTX 4060 with
    # the model warm in VRAM: a full reasoning call (JSON-constrained
    # decoding, real prompt size) takes ~7.4s - CPU-only inference is far
    # slower and will routinely miss even this, correctly degrading to
    # rule-based instead of answering in time.
    OLLAMA_TIMEOUT_SEC: int = 12
    OLLAMA_PROBE_TIMEOUT_SEC: float = 1.0

    # ── LLM: Google Gemini ────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""  # Set in .env - blank = provider unavailable
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MAX_TOKENS: int = 800
    GEMINI_TEMPERATURE: float = 0.3
    # Must stay below REASONING_AGENT_TIMEOUT_SEC so the engine's own
    # rule-based fallback runs instead of the agent being killed mid-call.
    GEMINI_TIMEOUT_SEC: int = 5

    # ── LLM: Groq ─────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""  # Set in .env - blank = provider unavailable
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_MAX_TOKENS: int = 600
    GROQ_TEMPERATURE: float = 0.3
    GROQ_TIMEOUT_SEC: int = 8

    # ── LLM: fallback label (for audit logs) ──────────────────────────────────
    FALLBACK_ENGINE: str = "rule-based"

    # Consecutive provider failures before the circuit opens and the process
    # stops paying network latency on every query. 0 disables the breaker.
    LLM_FAILURE_THRESHOLD: int = 2

    # How long the circuit stays open before one retry is allowed (the
    # standard half-open step). Without this, a transient burst - e.g. many
    # concurrent requests queued behind one local GPU - permanently disables
    # that provider for the rest of the process, even after the GPU is idle
    # again seconds later. 0 disables recovery (circuit stays open forever,
    # matching the old behavior).
    CIRCUIT_COOLDOWN_SEC: float = 20.0

    # How long an availability probe result stays fresh. Without this, /health
    # re-probes the ollama port on every single request. 0 disables caching.
    PROVIDER_PROBE_TTL_SEC: float = 30.0

    # ── Retrieval backend ─────────────────────────────────────────────────────
    # tfidf = scikit-learn TF-IDF (current MVP, ~30 MB)
    # faiss = FAISS + sentence-transformers (target stack, see docs/MIGRATION.md)
    VECTOR_BACKEND: str = "tfidf"
    VECTOR_STORE_PATH: str = "data/tfidf_index.pkl"
    VECTOR_SEARCH_TOP_K: int = 5
    TFIDF_MAX_FEATURES: int = 5000
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # used by the faiss backend only

    # ── API ───────────────────────────────────────────────────────────────────
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    API_TITLE: str = "MRPL Agentic Workbench"
    API_VERSION: str = "1.0.0"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_PER_HOUR: int = 100

    # ── Security ──────────────────────────────────────────────────────────────
    MAX_QUERY_LENGTH: int = 2000
    INPUT_VALIDATION_ENABLED: bool = True

    # ── Timeouts ──────────────────────────────────────────────────────────────
    AGENT_TIMEOUT_SEC: int = 8
    # Reasoning is the one agent that may call a local GPU LLM. Separate
    # budget so this doesn't loosen the timeout on the other four agents,
    # which consistently finish in <20ms. Must stay above every provider's
    # own *_TIMEOUT_SEC above and below WORKFLOW_TIMEOUT_SEC below.
    REASONING_AGENT_TIMEOUT_SEC: int = 15
    WORKFLOW_TIMEOUT_SEC: int = 30
    REQUEST_TIMEOUT_SEC: int = 35

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    AUDIT_LOG_PATH: str = "data/audit_logs/decisions.jsonl"

    # ── Business Rules ────────────────────────────────────────────────────────
    MAX_RECOMMENDATION_COST_INR: float = 100_000
    MAX_DOWNTIME_HOURS: float = 4.0
    SAFETY_MARGIN_PERCENT: float = 5.0

    # ── Data Paths ────────────────────────────────────────────────────────────
    SAMPLE_DOCS_PATH: str = "data/sample_docs"


settings = Settings()
