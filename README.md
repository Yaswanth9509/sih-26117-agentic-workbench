# MRPL Agentic Workbench — SIH26117

**Sovereign On-Premise Agentic AI for Maintenance Decision Support**

A 5-agent AI pipeline that helps MRPL engineers make data-driven maintenance
decisions from plain-English questions — with every recommendation validated
against business rules and written to an append-only audit trail.

**~270 MB install. No model downloads. Runs with zero network access.**

---

## Quick Start (3 steps)

```bash
# 1. Install dependencies (~270 MB, no model downloads)
pip install -r requirements.txt

# 2. Generate sample MRPL data
python scripts/generate_sample_data.py

# 3. Start the API + UI (two terminals)
uvicorn api.main:app --host 0.0.0.0 --port 8000       # Terminal 1
streamlit run ui/streamlit_app.py --server.port 8501  # Terminal 2
```

Open **http://localhost:8501**. No key or configuration is required — the
workbench runs fully offline out of the box.

---

## Docker (single command)

```bash
docker-compose up
# API:  http://localhost:8000
# UI:   http://localhost:8501
# Docs: http://localhost:8000/docs
```

---

## Choosing a reasoning engine

The reasoning agent is provider-agnostic. Set `LLM_PROVIDER` in `.env`:

| Provider | Offline? | Setup | Use for |
|---|---|---|---|
| `rule-based` | **Yes** | none — always available | Guaranteed-working default |
| `ollama` | **Yes** | `bash scripts/setup_llm.sh` (~4 GB) | **Production at MRPL** |
| `gemini` | No | free key at [aistudio.google.com](https://aistudio.google.com/apikey) | Laptop demo of real LLM reasoning |
| `groq` | No | free key at [console.groq.com](https://console.groq.com) | Laptop demo of real LLM reasoning |
| `auto` *(default)* | depends | — | Probes ollama → gemini → groq → rule-based |

```bash
cp .env.example .env
# then set LLM_PROVIDER, and a key if using a cloud provider
```

Every provider returns the same JSON schema, so switching engines changes
nothing downstream. `GET /health` always reports which one is actually live,
and every audit-log entry records the `engine` that produced that decision.

**On the offline claim:** with `ollama` or `rule-based`, no data leaves the
machine — this is the deployment model for MRPL. The two cloud providers exist
so the system can demonstrate genuine LLM reasoning on a laptop without a 4 GB
download; when one is active, query text goes to that vendor and the audit log
says so. See [docs/MIGRATION.md](docs/MIGRATION.md).

---

## Architecture

```
Engineer Query (natural language)
        |
[Security: sanitize + injection screen + rate limit]
        |
Agent 1: QueryUnderstanding  -- intent, equipment, state, budget
        |
Agent 2: Retrieval           -- search over 5 MRPL documents (pluggable backend)
        |
Agent 3: Reasoning           -- ollama / gemini / groq / rule-based (pluggable)
        |
Agent 4: Validation          -- 5 business rules (cost, downtime, safety, compliance, history)
        |
Agent 5: Decision            -- final structured JSON + audit log entry
        |
FastAPI Response + Streamlit UI
```

Every agent is independently timeout-protected; a failure or timeout in any one
of them degrades the answer rather than crashing the pipeline.

---

## Technology Stack

| Component | Technology | Why |
|---|---|---|
| Retrieval | scikit-learn TF-IDF | Ships now; FAISS drops in behind `BaseVectorStore` (saves 2.5 GB) |
| Reasoning | Pluggable providers | Local Mistral for production; cloud for laptop demos |
| Offline default | Rule-Based Engine | Deterministic, zero network, always available |
| API | FastAPI | Async, OpenAPI docs built-in |
| UI | Streamlit | Fast dashboards |
| Deploy | Docker | Single-command deploy |

The MVP substitutes TF-IDF for FAISS and cloud LLMs for local Mistral, purely
to keep the install at 270 MB instead of ~3 GB. Both sit behind interfaces the
agents depend on, so the production stack is a config change — the migration
path is specified in [docs/MIGRATION.md](docs/MIGRATION.md).

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/analyze` | POST | Run the 5-agent pipeline on a query |
| `/health` | GET | Service health + which LLM engine is live |
| `/recent` | GET | Recent audit log entries |
| `/docs` | GET | Auto-generated API documentation |

### Example API Call

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000. When schedule?", "user_id": "eng_1"}'
```

### Health response

```json
{
  "status": "OK",
  "engine": "rule-based",
  "circuit_open": false,
  "providers": {"ollama": false, "gemini": false, "groq": false, "rule-based": true}
}
```

---

## Example Queries

```
Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000. When schedule?
Compressor-B making loud noise, temperature up 15C. What is the risk?
Can we skip separator-D maintenance? Last done 26 months ago.
Pump-A and Compressor-B both need service. Budget Rs.35000. Which first?
What is the current status of Heat Exchanger-C?
```

Full request/response pairs: [docs/EXAMPLES.md](docs/EXAMPLES.md).

---

## Running Tests

```bash
pytest tests/ -v                      # all 64 tests, fully offline
pytest tests/test_agents.py -v        # unit tests for all 5 agents
pytest tests/test_workflow.py -v      # end-to-end pipeline
pytest tests/test_security.py -v      # sanitization + rate limiting
pytest tests/test_llm_providers.py -v # provider routing + failover
```

The suite never touches the network: `tests/conftest.py` pins the reasoning
engine to `rule-based`, and provider transports are stubbed.

Pre-deployment gate:

```bash
bash scripts/run_checks.sh
```

### Concurrency

```bash
uvicorn api.main:app --port 8000        # terminal 1
python scripts/stress_test.py           # terminal 2
```

50 concurrent requests from 50 distinct engineer IDs. Measured results:

| Engine | Throughput | p50 | p95 | Outcome |
|---|---|---|---|---|
| `rule-based` | 210 req/s | 0.14s | 0.23s | 50/50 answered |
| `gemini` (live) | 8.7 req/s | 3.72s | 5.55s | 50/50 answered; 15 served by Gemini, 35 degraded to rule-based under vendor throttling |

Under burst, cloud throttling degrades individual answers rather than
failing requests — no 5xx, no dropped connections, service healthy after.
Note the p95 of 5.55s leaves little headroom against the 6s target when a
cloud provider is under load; the offline engines are an order of magnitude
faster.

---

## Project Structure

```
sih-26117-agentic-workbench/
   agents/          5 AI agents (understanding, retrieval, reasoning, validation, decision)
   api/             FastAPI app (main, models, middleware)
   config/          Settings, prompts, business rules
   core/            LLM providers, vector store backends, document loader
   data/            Sample MRPL docs + audit logs
   docs/            EXAMPLES.md, MIGRATION.md
   orchestrator/    Pipeline workflow + audit logging
   scripts/         Data generator, LLM setup, pre-deploy checks
   tests/           Unit + integration + security + provider tests
   ui/              Streamlit dashboard
```

---

## SIH Hackathon: Problem Statement 26117

Developed for Smart India Hackathon 2025.
Team: MRPL On-Premise AI Workbench
Constraint: decision-making must be able to run entirely on MRPL's own
infrastructure — see [docs/MIGRATION.md](docs/MIGRATION.md) for how the MVP
maps onto that deployment.
