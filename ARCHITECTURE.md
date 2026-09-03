# MRPL Agentic Workbench — Architecture

## System Overview

```
Engineer (Browser)
       |  natural language query
       v
  [Streamlit UI :8501]
       |  HTTP POST /analyze
       v
  [FastAPI :8000]
  ├── RateLimiter  (10 req/min/client)
  ├── sanitize_input (SQL/XSS/prompt-injection block)
  └── AgentOrchestrator
         |
         |──▶ Agent 1: QueryUnderstandingAgent
         |        Rule-based regex/pattern NLP
         |        Output: intent, equipment, state, constraints
         |
         |──▶ Agent 2: RetrievalAgent
         |        BaseVectorStore backend (tfidf now, faiss later)
         |        Output: top-5 relevant document chunks
         |
         |──▶ Agent 3: ReasoningAgent
         |        ReasoningProvider: ollama | gemini | groq | rule-based
         |        Degrades to rule-based on any provider failure
         |        Output: reasoning chain, recommendation, confidence
         |
         |──▶ Agent 4: ValidationAgent
         |        5 deterministic business rules (pure Python)
         |        Output: APPROVED / REJECTED / ESCALATE + compliance score
         |
         └──▶ Agent 5: DecisionAgent
                  Aggregates all 4 outputs
                  Output: final structured JSON decision
         |
         v
  [Audit Logger]
  data/audit_logs/decisions.jsonl (append-only, immutable)
```

---

## Component Details

### Agent 1 — QueryUnderstandingAgent
- **File:** `agents/query_understanding.py`
- **Method:** Pure Python regex + keyword matching
- **Intent classes:** `schedule_maintenance`, `risk_assessment`, `cost_optimization`, `compliance_check`, `status_check`
- **Entity extraction:** equipment name, pressure (bar), temperature (°C), last service (days), budget (INR)
- **Timeout:** 8 seconds

### Agent 2 — RetrievalAgent
- **File:** `agents/retrieval_agent.py`
- **Interface:** `core/vector_store.py` → `BaseVectorStore` ABC, built by
  `get_vector_store()` from `settings.VECTOR_BACKEND`
- **Backend now:** `TfidfVectorStore` — scikit-learn `TfidfVectorizer` + cosine
  similarity. Index cached at `data/tfidf_index.pkl`, built once on first run.
- **Backend later:** `FaissVectorStore` — register in the factory and flip
  `VECTOR_BACKEND=faiss`. The agent holds a `BaseVectorStore` and needs no edit.
- **Fallback:** Returns empty list if the index is missing
- **Timeout:** 8 seconds

### Agent 3 — ReasoningAgent
- **File:** `agents/reasoning_agent.py`
- **Interface:** `core/llm_engine.py` → `ReasoningProvider` protocol. All
  providers emit the same JSON schema, so the agent is provider-agnostic.
- **Providers:**
  - `ollama` — local Mistral-7B, fully offline. **The production path**, already
    implemented; activates once `scripts/setup_llm.sh` has run.
  - `gemini` — Google Gemini REST (`gemini-flash-lite-latest`), cloud
  - `groq` — Groq REST (`llama-3.1-8b-instant`), cloud
  - `rule-based` — deterministic per-equipment rules, zero network. Always available.
- **Selection:** `settings.LLM_PROVIDER`; `auto` probes ollama → gemini → groq →
  rule-based and caches the result for the process.
- **Failure handling:** any provider error degrades to `RuleBasedEngine` rather
  than failing the request. A circuit breaker opens after
  `LLM_FAILURE_THRESHOLD` consecutive failures so a degraded cloud provider
  cannot add its timeout to every later query.
- **Concurrency:** the blocking HTTP call runs via `asyncio.to_thread`, so the
  agent timeout can actually interrupt a hung provider.
- **Timeout:** 8 seconds (provider timeouts are set below this so the engine's
  own fallback runs first)

### Agent 4 — ValidationAgent
- **File:** `agents/validation_agent.py`
- **Rules (5):**
  1. `cost_check` — recommendation cost ≤ budget
  2. `downtime_check` — downtime ≤ 4h (warn if over)
  3. `safety_margin` — pressure < 95% of max (escalate if critical)
  4. `compliance` — within standard maintenance interval ± 14 day grace
  5. `historical` — per-equipment historical success rate lookup
- **Output states:** `APPROVED` | `APPROVED_WITH_WARNINGS` | `REJECTED` | `ESCALATE`

### Agent 5 — DecisionAgent
- **File:** `agents/decision_agent.py`
- **Purpose:** Pure aggregation — merges all 4 outputs into final auditable JSON
- **Decision ID format:** `DEC-YYYYMMDD-HHMMSS`
- **Priority mapping:** ESCALATE→URGENT, REJECTED→HOLD, warnings→ELEVATED, else NORMAL

---

## Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **LLM (production)** | Mistral-7B via ollama | Fully offline / sovereign. Implemented. |
| **LLM (demo)** | Gemini or Groq REST | Real LLM reasoning without a 4 GB download |
| **LLM (default)** | Rule-Based Engine | Deterministic, zero network, always available |
| **Vector Search** | scikit-learn TF-IDF | Ships now; FAISS drops in behind the ABC (saves 2.5 GB) |
| **API** | FastAPI + Uvicorn | Async, OpenAPI docs built-in |
| **UI** | Streamlit | Fast dashboard, no frontend needed |
| **Settings** | pydantic-settings | Type-safe env var management |
| **Container** | Docker | Reproducible deployment |

---

## Data Flow — Detailed

```
Input: "Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000"

Agent 1 Output:
  intent=schedule_maintenance
  equipment=reactor-4
  current_state={pressure_bar: 4.2, last_service_days: 180}
  constraints={budget_inr: 50000}
  confidence=0.77

Agent 2 Output:
  documents_found=5
  documents=[safety_protocols.json, maintenance_schedule.csv, equipment_specs.json, ...]

Agent 3 Output (rule-based):
  reasoning=["Step 1: Pressure 4.2 bar is within safe range...", ...]
  recommendation="Schedule maintenance for reactor-4 within next 2 weeks"
  cost_estimate_inr=35000
  downtime_hours=2.5
  confidence=0.93
  engine_used=rule-based

Agent 4 Output:
  validation_status=APPROVED
  compliance_score=100%
  rule_results={cost_check: PASS, downtime_check: PASS, safety_margin: PASS, ...}

Agent 5 Output (Final Decision):
  decision_id=DEC-20260903-164624
  priority=NORMAL
  recommendation.action=Schedule Maintenance
  recommendation.timing=Within 2 weeks
  metadata.total_time_ms=11
  metadata.engine_used=rule-based
```

---

## File Structure

```
sih-26117-agentic-workbench/
├── agents/             5 AI agents (base + 5 implementations)
├── api/                FastAPI app (main, models, middleware)
├── config/             Settings, prompts, business rules
├── core/               LLM engine, TF-IDF vector store, document loader
├── data/
│   ├── sample_docs/    5 synthetic MRPL documents
│   ├── audit_logs/     decisions.jsonl (append-only)
│   └── tfidf_index.pkl Cached TF-IDF index
├── orchestrator/       Pipeline workflow + audit logging
├── scripts/            Data generator + test runners
├── tests/              44 tests (agent/workflow/security)
├── ui/                 Streamlit dashboard
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Security Design

1. **Input Sanitization** — 16 regex patterns block SQL, XSS, prompt injection
2. **Rate Limiting** — sliding 60-second window, 10 req/min/client
3. **Timeout** — every agent has 8s asyncio timeout; workflow 30s total
4. **No Secrets in Code** — all config via pydantic-settings + `.env`
5. **Audit Trail** — append-only JSONL, every decision logged immutably

---

## Deployment

```bash
# Option A: Direct
uvicorn api.main:app --host 0.0.0.0 --port 8000
streamlit run ui/streamlit_app.py --server.port 8501

# Option B: Docker
docker-compose up

# API docs
http://localhost:8000/docs
```
