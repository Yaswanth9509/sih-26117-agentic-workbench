"""
Audit Logger: append-only JSONL decision log.
Every workflow run appends one JSON line - never overwrites.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)


def log_decision(decision: dict[str, Any], user_id: str = "unknown") -> None:
    """
    Append one audit entry to decisions.jsonl (immutable, append-only).

    Args:
        decision: Final decision dict from DecisionAgent
        user_id:  Engineer identifier
    """
    log_path = Path(settings.AUDIT_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "decision_id": decision.get("decision_id", "UNKNOWN"),
        "user_id": user_id,
        "equipment": decision.get("equipment", "unknown"),
        "intent": decision.get("intent", "unknown"),
        "recommendation_action": decision.get("recommendation", {}).get("action", ""),
        "recommendation_detail": decision.get("recommendation", {}).get("detail", "")[
            :120
        ],
        "cost_estimate_inr": decision.get("analysis", {}).get("cost_estimate_inr", 0),
        "validation_status": decision.get("validation", {}).get("status", "UNKNOWN"),
        "compliance_score": decision.get("validation", {}).get("compliance_score", 0),
        "overall_confidence": decision.get("metadata", {}).get("overall_confidence", 0),
        "total_time_ms": decision.get("metadata", {}).get("total_time_ms", 0),
        "engine_used": decision.get("metadata", {}).get("engine_used", "unknown"),
        "priority": decision.get("priority", "NORMAL"),
        "violations": decision.get("validation", {}).get("violations", []),
        "warnings_count": len(decision.get("validation", {}).get("warnings", [])),
    }

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info(
            f"audit_log decision_id={entry['decision_id']} equipment={entry['equipment']}"
        )
    except Exception as exc:
        logger.error(f"Failed to write audit log: {exc}")


def read_recent(n: int = 10) -> list[dict[str, Any]]:
    """Read the last n entries from the audit log."""
    log_path = Path(settings.AUDIT_LOG_PATH)
    if not log_path.exists():
        return []
    try:
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        recent = lines[-n:] if len(lines) >= n else lines
        return [json.loads(line) for line in reversed(recent)]
    except Exception as exc:
        logger.error(f"Failed to read audit log: {exc}")
        return []
