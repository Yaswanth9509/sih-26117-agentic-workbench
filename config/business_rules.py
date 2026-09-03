"""
Business rules and keyword mappings for MRPL agents.
Edit rules here - agents import from this module.
"""

from __future__ import annotations

from typing import TypedDict


class BusinessRule(TypedDict):
    rule_id: str
    description: str
    severity: str  # "FAIL" | "WARN" | "ESCALATE"


BUSINESS_RULES: list[BusinessRule] = [
    {
        "rule_id": "RULE_1_COST_CHECK",
        "description": "Recommendation cost must not exceed the stated budget",
        "severity": "FAIL",
    },
    {
        "rule_id": "RULE_2_DOWNTIME_CHECK",
        "description": "Downtime must not exceed MAX_DOWNTIME_HOURS (4 hrs default)",
        "severity": "WARN",
    },
    {
        "rule_id": "RULE_3_SAFETY_MARGIN",
        "description": "Pressure/temperature must stay within 95% of max safe value",
        "severity": "ESCALATE",
    },
    {
        "rule_id": "RULE_4_COMPLIANCE",
        "description": "Recommendation must align with standard maintenance schedule",
        "severity": "WARN",
    },
    {
        "rule_id": "RULE_5_HISTORICAL",
        "description": "Check whether similar approach has worked in historical logs",
        "severity": "WARN",
    },
]

# Intent keywords - used by QueryUnderstandingAgent
INTENT_KEYWORDS: dict[str, list[str]] = {
    "schedule_maintenance": [
        "when should",
        "schedule",
        "when to service",
        "maintenance due",
        "plan maintenance",
        "next service",
        "overdue",
    ],
    "risk_assessment": [
        "risk",
        "danger",
        "failure",
        "noise",
        "vibration",
        "temperature up",
        "overheating",
        "leak",
        "unsafe",
    ],
    "cost_optimization": [
        "budget",
        "prioritize",
        "which first",
        "cost",
        "cheapest",
        "optimize",
        "save money",
        "most urgent",
    ],
    "compliance_check": [
        "skip",
        "delay",
        "postpone",
        "compliance",
        "violates",
        "can we skip",
        "regulatory",
        "mandatory",
    ],
    "status_check": [
        "status",
        "condition",
        "health",
        "how is",
        "check",
        "what is the",
        "current state",
    ],
}

# Supported equipment - MVP scope
SUPPORTED_EQUIPMENT: list[str] = [
    "reactor-4",
    "compressor-b",
    "pump-a",
    "exchanger-c",
    "separator-d",
]

# Equipment aliases (handle user spelling variations)
EQUIPMENT_ALIASES: dict[str, str] = {
    "reactor 4": "reactor-4",
    "reactor4": "reactor-4",
    "compressor b": "compressor-b",
    "compressorb": "compressor-b",
    "pump a": "pump-a",
    "pumpa": "pump-a",
    "exchanger c": "exchanger-c",
    "heat exchanger": "exchanger-c",
    "exchanger": "exchanger-c",
    "separator d": "separator-d",
    "separatord": "separator-d",
}
