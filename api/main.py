"""
FastAPI Application: main entry point for MRPL Agentic Workbench API.
Endpoints:
  POST /analyze  -> run 5-agent pipeline, return decision
  GET  /health   -> service health check
  GET  /recent   -> last 10 audit log entries
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware import RateLimiter, sanitize_input
from api.models import ErrorResponse, HealthResponse, QueryRequest, QueryResponse
from config.settings import settings
from orchestrator.logging import read_recent
from orchestrator.workflow import AgentOrchestrator

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Sovereign On-Premise Agentic AI Workbench for MRPL maintenance decisions.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singletons (created once at startup) ──────────────────────────────────────
orchestrator = AgentOrchestrator()
rate_limiter = RateLimiter(max_per_minute=settings.RATE_LIMIT_PER_MINUTE)


# ── Exception handler ─────────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception: {exc!s}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "status": "INTERNAL_ERROR"},
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.post(
    "/analyze",
    summary="Analyze a maintenance query",
    response_description="Structured maintenance decision with reasoning and validation",
)
async def analyze_query(request: QueryRequest) -> dict:
    """
    Run the full 5-agent pipeline on a maintenance query.

    - **Agent 1**: Understand intent and extract entities
    - **Agent 2**: Retrieve relevant MRPL documents
    - **Agent 3**: Generate reasoning (configured LLM provider, or rule-based)
    - **Agent 4**: Validate against 5 business rules
    - **Agent 5**: Synthesize final decision
    """
    client_id = request.user_id or "unknown"

    # ── Rate limiting ──────────────────────────────────────────────────────
    if not rate_limiter.check(client_id):
        remaining_after = rate_limiter.remaining(client_id)
        raise HTTPException(
            status_code=429,
            detail={
                "error": f"Rate limit exceeded ({settings.RATE_LIMIT_PER_MINUTE} req/min). Try again later.",
                "status": "RATE_LIMITED",
                "requests_remaining": remaining_after,
            },
        )

    # ── Input sanitization ─────────────────────────────────────────────────
    try:
        clean_query = sanitize_input(request.query, settings.MAX_QUERY_LENGTH)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"error": str(exc), "status": "INVALID_INPUT"}
        )

    # ── Run pipeline ───────────────────────────────────────────────────────
    result = await orchestrator.run_workflow(clean_query, client_id)

    if result.get("status") in ("WORKFLOW_FAILED", "WORKFLOW_TIMEOUT"):
        raise HTTPException(
            status_code=500,
            detail={"error": result.get("error"), "status": result.get("status")},
        )

    return result


@app.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """Returns OK when the service is running, plus the active LLM engine."""
    engine_status = await orchestrator.llm_health()
    return HealthResponse(
        status="OK",
        service=settings.API_TITLE,
        version=settings.API_VERSION,
        engine=str(engine_status.get("engine", "unknown")),
        circuit_open=bool(engine_status.get("circuit_open", False)),
        providers=dict(engine_status.get("providers", {})),
    )


@app.get("/recent", summary="Recent audit log entries")
async def recent_decisions(n: int = 10) -> dict:
    """Return the last n decisions from the audit log."""
    entries = read_recent(min(n, 50))
    return {"count": len(entries), "decisions": entries}


# ── Run directly ──────────────────────────────────────────────────────────────
# uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
