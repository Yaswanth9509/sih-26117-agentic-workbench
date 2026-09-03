"""
Pydantic request/response schemas for the FastAPI endpoints.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Incoming maintenance query from engineer."""

    query: str = Field(
        ..., max_length=2000, description="Natural language maintenance question"
    )
    user_id: Optional[str] = Field(default="unknown", description="Engineer identifier")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000. When schedule?",
                    "user_id": "engineer_1",
                }
            ]
        }
    }


class RecommendationBlock(BaseModel):
    action: str
    detail: str
    timing: str
    risk_if_delayed: str
    estimated_cost_inr: float
    estimated_downtime_hours: float


class ValidationBlock(BaseModel):
    status: str
    compliance_score: int
    violations: list[str]
    warnings: list[str]


class MetadataBlock(BaseModel):
    overall_confidence: float
    total_time_ms: int
    engine_used: str
    reasoning_steps_count: int


class QueryResponse(BaseModel):
    """Full structured decision response."""

    decision_id: str
    timestamp: str
    equipment: str
    priority: str
    recommendation: RecommendationBlock
    validation: ValidationBlock
    reasoning_chain: list[str]
    metadata: MetadataBlock


class HealthResponse(BaseModel):
    """Service health plus which reasoning engine is actually serving."""

    status: str
    service: str
    version: str
    engine: str = "unknown"
    circuit_open: bool = False
    circuit_retry_in_sec: float | None = None
    providers: dict[str, bool] = {}


class ErrorResponse(BaseModel):
    error: str
    status: str
