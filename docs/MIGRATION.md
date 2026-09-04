# Migration: MVP → On-Premise Production Stack

This document is the contract between what ships for the initial SIH submission
and the sovereign on-premise architecture in the problem statement.

The MVP makes two substitutions, both for install size. **Neither is baked into
the agents.** Both sit behind an interface, so the production stack replaces
them through configuration, not a rewrite.

| Layer | MVP (ships now) | Production target | Size delta |
|---|---|---|---|
| Reasoning | Rule-based engine + optional Gemini/Groq cloud | Mistral-7B via ollama, local | +4 GB model |
| Retrieval | scikit-learn TF-IDF + cosine similarity | FAISS + sentence-transformers | +2.5 GB (PyTorch) |

Total install today: **~270 MB, no model downloads.** The full stack is ~3 GB.

---

## Why these seams exist

Both substitutions are hidden behind an interface that the agents depend on:

- `core/llm_engine.py` → `ReasoningProvider` protocol. Every provider returns
  the identical JSON schema, so `agents/reasoning_agent.py` cannot tell which
  one ran.
- `core/vector_store.py` → `BaseVectorStore` ABC + `get_vector_store()` factory.
  `agents/retrieval_agent.py` holds a `BaseVectorStore`, never a concrete class.

The consequence: **swapping to the production stack touches zero agent code,
zero orchestrator code, and zero API code.**

---

## Step 1: Local Mistral-7B (already implemented)

The sovereign reasoning path is **written and wired**, not stubbed - and
already active on the primary dev machine (confirmed live: `/health` reports
`engine: ollama`, real Mistral answers in ~6-7s on an RTX 4060). On a machine
where ollama isn't installed yet, it stays inactive until it is:

```bash
bash scripts/setup_llm.sh     # installs ollama, pulls mistral, verifies
```

Then either leave `LLM_PROVIDER=auto` (ollama is probed first and wins), or pin
it explicitly in `.env`:

```
LLM_PROVIDER=ollama
```

Confirm with `curl http://localhost:8000/health` — the `engine` field reads
`ollama`, and no request leaves the machine. Delete `GEMINI_API_KEY` and
`GROQ_API_KEY` from `.env` to make that structurally impossible.

Code involved: `OllamaEngine` in `core/llm_engine.py`. It posts to
`/api/generate` with `format: "json"` and parses the same schema as every other
provider.

## Step 2: FAISS + sentence-transformers (to implement)

This is the one piece genuinely not written, because it costs 2.5 GB.

1. Add to `requirements.txt`:
   ```
   faiss-cpu==1.9.0
   sentence-transformers==3.3.1
   torch==2.5.1
   ```

2. Add `FaissVectorStore(BaseVectorStore)` to `core/vector_store.py`,
   implementing the five abstract methods: `build_index`, `search`, `save`,
   `load`, `doc_count`. Embed with `settings.EMBEDDING_MODEL`
   (`all-MiniLM-L6-v2`); `search` must return documents carrying a
   `similarity_score` key, exactly as the TF-IDF backend does.

3. Register it in the factory:
   ```python
   _BACKENDS: dict[str, type[BaseVectorStore]] = {
       "tfidf": TfidfVectorStore,
       "faiss": FaissVectorStore,
   }
   ```

4. Flip the config in `.env`:
   ```
   VECTOR_BACKEND=faiss
   VECTOR_STORE_PATH=data/embeddings_index.faiss
   ```

No other file changes. `tests/test_agents.py` retrieval tests should pass
unmodified against the new backend — that is the acceptance check.

---

## What stays the same either way

These are already built to the production specification and need no migration:

- All 5 agents, and the orchestrator sequencing them
- Per-agent and per-workflow timeout enforcement
- Input sanitisation, injection screening, length validation
- Rate limiting (10 req/min per client)
- Append-only JSONL audit trail
- FastAPI endpoints and the Streamlit UI
- The 5 business rules and compliance scoring

---

## Honest status of the offline claim

Read this before demoing.

- With **ollama installed**: fully offline. No external calls. The claim holds
  literally.
- With **no provider configured**: fully offline. The rule-based engine makes
  no network calls at all. The claim holds, but the reasoning is deterministic
  rather than generative.
- With **a Gemini or Groq key set**: query text goes to that provider. The
  claim does *not* hold, and the audit log records `engine: gemini` or
  `engine: groq` on every affected decision so this is never ambiguous.

The cloud providers exist so the MVP can demonstrate real LLM reasoning on a
laptop without a 4 GB download. They are a development convenience, not the
deployment model. `/health` always reports which engine is live.
