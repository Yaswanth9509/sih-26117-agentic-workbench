# AGENTS.md - Multi-Agent Coordination File
# SIH26117: Sovereign On-Premise Agentic AI Workbench

> This file governs how all parallel agents collaborate on this project.
> Every agent MUST read this file before writing any code.

---

## Project Overview

Build a local, on-premise AI agent system for MRPL (Mangalore Refinery) engineers to make
maintenance decisions using natural language. 5 specialized internal agents.
Stack: Python + FastAPI + Streamlit + Docker, with pluggable retrieval and
reasoning backends.

**Current MVP substitutions** (install size: 270 MB vs ~3 GB) - both behind
interfaces, see `docs/MIGRATION.md`:
- Retrieval: scikit-learn TF-IDF now; FAISS + sentence-transformers is the target.
- Reasoning: rule-based engine + optional Gemini/Groq now; Mistral-7B via ollama
  is the production path and is already implemented (`OllamaEngine`).

**Full spec:** See `../SIH26117_COMPLETE_SPEC.md` for complete technical details, exact I/O formats,
code templates, and acceptance criteria.

---

## Agent Ownership Map

Each IDE agent owns specific directories. Do NOT write files outside your assigned area
without checking for conflicts first.

| IDE Agent   | Owns                                      | Description                                  |
|-------------|-------------------------------------------|----------------------------------------------|
| **Agent 1** | `config/`, `core/`, `data/`, `scripts/`   | Foundation, LLM engine, vector store, data   |
| **Agent 2** | `agents/`                                 | All 5 internal agent implementations         |
| **Agent 3** | `orchestrator/`, `api/`                   | Workflow orchestration, FastAPI server        |
| **Agent 4** | `ui/`, `tests/`, `docs/`, root files      | Streamlit UI, tests, Docker, documentation   |

**Shared files** (edit with care):
- `requirements.txt` - Agent 1 creates it; others append if needed
- `.env.example`     - Agent 1 creates it; others append their vars

---

## Dependency Order

  Agent 1 (Foundation) --> Agent 2 (Agents) --> Agent 3 (Orchestrator/API) --> Agent 4 (Tests)
                                                                           --> Agent 4 (UI/Docs) [can start immediately]

- Agent 1 must complete core/vector_store.py and core/llm_engine.py before Agent 2 can fully test
- Agent 2 must complete all agents before Agent 3 can wire the orchestrator
- Agent 3 must complete orchestrator/workflow.py and api/main.py before Agent 4 runs integration tests
- Agent 4 can begin ui/streamlit_app.py, Dockerfile, README.md, and all docs immediately (no blockers)

---

## Coding Standards (ALL agents must follow)

- Python 3.10+
- Type hints on ALL functions (100% mypy coverage required)
- Use logging module only - NO print() statements
- Docstrings on all classes and public methods
- Run black . formatting before committing
- All async functions use async/await
- ALL async calls must be wrapped in try/except
- ALL exceptions must be caught - no unhandled exceptions allowed
- All error paths return proper JSON: {"error": "...", "status": "FAILED"}
- NO hardcoded secrets - ALL config values from config/settings.py

---

## Interface Contracts Between Agents

### Agent 1 must expose (core/vector_store.py):
  class VectorStore:
    def search(self, query: str, top_k: int = 5) -> list[dict]: ...
    def add_documents(self, docs: list[dict]) -> None: ...
    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...

### Agent 1 must expose (core/llm_engine.py):
  class LLMEngine:
    async def generate(self, prompt: str, max_tokens: int = 500) -> str: ...
    async def health_check(self) -> bool: ...

### Agent 2 must expose (agents/base_agent.py):
  class BaseAgent(ABC):
    async def execute(self, input_data: dict) -> dict:
      # Always returns dict with: {"status": "SUCCESS"|"FAILED"|"TIMEOUT", "agent": str}

### Agent 3 API contract:
  POST /analyze
    Request:  {"query": str, "user_id": str (optional)}
    Response: {"decision_id": str, "recommendation": dict, "confidence": float, "inference_time_ms": int}
  GET /health
    Response: {"status": "OK", "service": str, "version": str, "engine": str,
               "circuit_open": bool, "circuit_retry_in_sec": float | None,
               "providers": dict}

---

## Key Configuration Constants

  LLM_PROVIDER              = "auto"     # ollama | gemini | groq | rule-based
  OLLAMA_MODEL              = "mistral"
  OLLAMA_BASE_URL           = "http://127.0.0.1:11434"  # host.docker.internal in the container
  OLLAMA_TIMEOUT_SEC        = 12         # below REASONING_AGENT_TIMEOUT_SEC by design
  GEMINI_MODEL              = "gemini-flash-lite-latest"
  GEMINI_TIMEOUT_SEC        = 5          # below REASONING_AGENT_TIMEOUT_SEC by design
  GROQ_MODEL                = "llama-3.1-8b-instant"
  LLM_FAILURE_THRESHOLD     = 2          # circuit breaker: opens after N consecutive failures
  CIRCUIT_COOLDOWN_SEC      = 20         # circuit auto-retries (half-open) after this long
  AGENT_TIMEOUT_SEC         = 8          # the other 4 agents; each typically <20ms
  REASONING_AGENT_TIMEOUT_SEC = 15       # reasoning only - the one agent that may call a local GPU LLM
  WORKFLOW_TIMEOUT_SEC      = 30
  MAX_QUERY_LENGTH       = 2000
  RATE_LIMIT_PER_MINUTE  = 10
  VECTOR_BACKEND         = "tfidf"       # faiss post-MVP
  VECTOR_STORE_PATH      = "data/tfidf_index.pkl"
  EMBEDDING_MODEL        = "all-MiniLM-L6-v2"   # faiss backend only
  VECTOR_SEARCH_TOP_K    = 5
  API_PORT               = 8000
  STREAMLIT_PORT         = 8501
  AUDIT_LOG_PATH         = "data/audit_logs/decisions.jsonl"
  SAMPLE_DOCS_PATH       = "data/sample_docs"

---

## Supported Equipment (MVP)

  reactor-4, compressor-B, pump-A, exchanger-C, separator-D

---

## Internal Agent Pipeline (Agent 2 builds these)

  QueryUnderstandingAgent -> RetrievalAgent -> ReasoningAgent -> ValidationAgent -> DecisionAgent

Each agent: independent, timeout-protected (8s; reasoning gets 15s - see
Key Configuration Constants above), returns {"status": "SUCCESS"|"FAILED"|"TIMEOUT"}.
If reasoning does not return SUCCESS for any reason, the orchestrator computes
a rule-based answer directly rather than failing the request - a request can
never hard-fail on this stage.

---

## File Status Tracking

Update status: [DONE] | [WIP] | [TODO] | [BLOCKED]

### Agent 1 - Foundation
  [DONE] requirements.txt
  [DONE] .env.example
  [DONE] config/__init__.py
  [DONE] config/settings.py
  [DONE] config/prompts.py
  [DONE] config/business_rules.py
  [DONE] core/__init__.py
  [DONE] core/llm_engine.py
  [DONE] core/document_loader.py
  [DONE] core/vector_store.py
  [DONE] data/sample_docs/equipment_specs.json
  [DONE] data/sample_docs/maintenance_schedule.csv
  [DONE] data/sample_docs/service_logs.txt
  [DONE] data/sample_docs/safety_protocols.json
  [DONE] data/sample_docs/cost_estimates.csv
  [DONE] scripts/generate_sample_data.py
  [DONE] scripts/setup_llm.sh
  [DONE] scripts/run_checks.sh

### Agent 2 - Agents
  [DONE] agents/__init__.py
  [DONE] agents/base_agent.py
  [DONE] agents/query_understanding.py
  [DONE] agents/retrieval_agent.py
  [DONE] agents/reasoning_agent.py
  [DONE] agents/validation_agent.py
  [DONE] agents/decision_agent.py

### Agent 3 - Orchestrator + API
  [DONE] orchestrator/__init__.py
  [DONE] orchestrator/workflow.py
  [DONE] orchestrator/logging.py
  [DONE] api/__init__.py
  [DONE] api/main.py
  [DONE] api/models.py
  [DONE] api/middleware.py

### Agent 4 - UI + Tests + Deployment + Docs
  [DONE] ui/streamlit_app.py
  [DONE] tests/__init__.py
  [DONE] tests/test_agents.py
  [DONE] tests/test_workflow.py
  [DONE] tests/test_security.py
  [DONE] tests/test_llm_providers.py
  [DONE] tests/conftest.py
  [DONE] mypy.ini
  [DONE] docs/MIGRATION.md
  [DONE] Dockerfile
  [DONE] docker-compose.yml
  [DONE] .gitignore
  [DONE] README.md
  [DONE] ARCHITECTURE.md
  [DONE] docs/EXAMPLES.md

---

## Acceptance Criteria (All agents must ensure)

  - End-to-end workflow completes in < 6 seconds per query
  - Runs with zero network access (rule-based or ollama provider).
    A configured cloud provider is a demo convenience, recorded in the
    audit log as `engine` on every affected decision.
  - Every decision logged to audit JSONL
  - Input validation blocks SQL/prompt injection
  - Rate limiting: 11th request/minute rejected
  - No unhandled exceptions (all errors return JSON)
  - Type hints: 100% mypy coverage
  - No hardcoded secrets
  - Docker container builds and runs end-to-end
