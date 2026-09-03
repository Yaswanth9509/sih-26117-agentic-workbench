"""
Abstract base class for all MRPL agents.
Provides: timeout enforcement, error handling, logging, structured I/O.
All 5 agents subclass this and implement _run().
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any


class BaseAgent(ABC):
    """
    Base for all agents. Subclasses implement _run(input_data) -> dict.
    Call execute(input_data) to run with timeout + full error handling.
    """

    def __init__(self, name: str, timeout_sec: int = 8) -> None:
        self.name = name
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Run agent with timeout and error handling.
        Always returns dict containing 'status', 'agent', 'execution_time_ms'.
        """
        start = datetime.now(tz=timezone.utc)
        try:
            result = await asyncio.wait_for(
                self._run(input_data),
                timeout=self.timeout_sec,
            )
            result.setdefault("status", "SUCCESS")
            result["agent"] = self.name
            result["execution_time_ms"] = _ms(start)
            self.logger.info(
                f"agent={self.name} status=SUCCESS time_ms={result['execution_time_ms']}"
            )
            return result

        except asyncio.TimeoutError:
            self.logger.error(f"agent={self.name} TIMEOUT after {self.timeout_sec}s")
            return {
                "error": f"{self.name} timed out after {self.timeout_sec}s",
                "status": "TIMEOUT",
                "agent": self.name,
                "execution_time_ms": self.timeout_sec * 1000,
            }
        except Exception as exc:
            self.logger.error(f"agent={self.name} FAILED error={exc!s}")
            return {
                "error": str(exc),
                "status": "FAILED",
                "agent": self.name,
                "execution_time_ms": _ms(start),
            }

    @abstractmethod
    async def _run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Core agent logic. Return dict; omit 'status' to default to SUCCESS."""


def _ms(start: datetime) -> int:
    return int((datetime.now(tz=timezone.utc) - start).total_seconds() * 1000)
