"""
Generate synthetic MRPL sample documents.
Run: python scripts/generate_sample_data.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

OUT = Path("data/sample_docs")
OUT.mkdir(parents=True, exist_ok=True)

# Shared across every equipment record so it reaches an LLM's context
# regardless of which specific record retrieval surfaces. Named fields
# (routine_service_cost_inr, urgent_cost_multiplier) let both the rule-based
# engine and a real LLM compute a severity-adjusted figure instead of quoting
# one flat number for every query - the single, previous root cause of cost
# and downtime never varying: a query with "pressure 4.9 bar, badly overdue"
# got exactly the same Rs.35,000 as one with "pressure 4.2 bar, on schedule",
# because the routine figure was the only number either engine ever saw.
SEVERITY_POLICY_NOTE = (
    "Urgent pricing applies when operating pressure exceeds 85% of the safe "
    "maximum, service is overdue beyond the compliance grace period, or "
    "abnormal vibration/temperature symptoms are reported - reflecting "
    "expedited parts sourcing, overtime labor, and more extensive inspection "
    "under those conditions. Otherwise the routine figure applies."
)


# ── 1. equipment_specs.json ──────────────────────────────────────────────────


def gen_equipment_specs() -> None:
    data = {
        "equipment": [
            {
                "id": "reactor-4",
                "name": "Reactor-4",
                "type": "reactor",
                "capacity_liters": 500000,
                "material": "stainless_steel_316",
                "design_pressure_bar": 5.0,
                "design_temperature_celsius": 150,
                "safe_operating_range_bar": [3.5, 5.0],
                "max_safe_temperature_celsius": 150,
                "installed_date": "2018-03-15",
                "designed_lifespan_years": 10,
                "maintenance_interval_months": 6,
                "routine_service_cost_inr": 35000,
                "routine_service_downtime_hours": 2.5,
                "urgent_cost_multiplier": 1.35,
                "urgent_downtime_multiplier": 1.6,
                "urgency_policy": SEVERITY_POLICY_NOTE,
                "last_major_inspection": "2026-03-15",
                "next_scheduled_service": "2026-09-15",
            },
            {
                "id": "compressor-b",
                "name": "Compressor-B",
                "type": "compressor",
                "capacity_ton_per_hour": 150,
                "material": "cast_iron",
                "design_pressure_bar": 8.0,
                "design_temperature_celsius": 80,
                "safe_operating_range_bar": [6.0, 8.0],
                "max_safe_temperature_celsius": 80,
                "installed_date": "2019-06-20",
                "designed_lifespan_years": 15,
                "maintenance_interval_months": 12,
                "routine_service_cost_inr": 28000,
                "routine_service_downtime_hours": 3.0,
                "urgent_cost_multiplier": 1.3,
                "urgent_downtime_multiplier": 1.5,
                "urgency_policy": SEVERITY_POLICY_NOTE,
                "last_major_inspection": "2025-06-20",
                "next_scheduled_service": "2026-06-20",
            },
            {
                "id": "pump-a",
                "name": "Pump-A",
                "type": "centrifugal_pump",
                "capacity_liters_per_minute": 2000,
                "material": "duplex_stainless_steel",
                "design_pressure_bar": 6.0,
                "design_temperature_celsius": 120,
                "safe_operating_range_bar": [4.0, 6.0],
                "max_safe_temperature_celsius": 120,
                "installed_date": "2020-02-10",
                "designed_lifespan_years": 12,
                "maintenance_interval_months": 6,
                "routine_service_cost_inr": 15000,
                "routine_service_downtime_hours": 1.5,
                "urgent_cost_multiplier": 1.3,
                "urgent_downtime_multiplier": 1.5,
                "urgency_policy": SEVERITY_POLICY_NOTE,
                "last_major_inspection": "2026-02-10",
                "next_scheduled_service": "2026-08-10",
            },
            {
                "id": "exchanger-c",
                "name": "Heat-Exchanger-C",
                "type": "shell_and_tube_heat_exchanger",
                "capacity_mw": 12,
                "material": "titanium_grade_2",
                "design_pressure_bar": 10.0,
                "design_temperature_celsius": 200,
                "safe_operating_range_bar": [7.0, 10.0],
                "max_safe_temperature_celsius": 200,
                "installed_date": "2017-12-01",
                "designed_lifespan_years": 20,
                "maintenance_interval_months": 12,
                "routine_service_cost_inr": 42000,
                "routine_service_downtime_hours": 4.0,
                "urgent_cost_multiplier": 1.4,
                "urgent_downtime_multiplier": 1.75,
                "urgency_policy": SEVERITY_POLICY_NOTE,
                "last_major_inspection": "2025-12-01",
                "next_scheduled_service": "2026-12-01",
            },
            {
                "id": "separator-d",
                "name": "Separator-D",
                "type": "three_phase_separator",
                "capacity_barrels_per_day": 10000,
                "material": "carbon_steel_coated",
                "design_pressure_bar": 12.0,
                "design_temperature_celsius": 90,
                "safe_operating_range_bar": [8.0, 12.0],
                "max_safe_temperature_celsius": 90,
                "installed_date": "2016-06-15",
                "designed_lifespan_years": 25,
                "maintenance_interval_months": 24,
                "routine_service_cost_inr": 55000,
                "routine_service_downtime_hours": 5.5,
                "urgent_cost_multiplier": 1.45,
                "urgent_downtime_multiplier": 1.8,
                "urgency_policy": SEVERITY_POLICY_NOTE,
                "last_major_inspection": "2024-06-15",
                "next_scheduled_service": "2026-06-15",
            },
        ]
    }
    (OUT / "equipment_specs.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    print("  equipment_specs.json done")


# ── 2. maintenance_schedule.csv ───────────────────────────────────────────────


def gen_maintenance_schedule() -> None:
    rows = [
        [
            "equipment_id",
            "equipment_name",
            "service_interval_months",
            "last_service_date",
            "typical_cost_inr",
            "typical_downtime_hours",
            "compliance_status",
            "next_due_date",
            "previous_services",
            "avg_issue_rate_percent",
        ],
        [
            "reactor-4",
            "Reactor-4",
            "6",
            "2026-03-15",
            "35000",
            "2.5",
            "ON_SCHEDULE",
            "2026-09-15",
            "8",
            "12",
        ],
        [
            "compressor-b",
            "Compressor-B",
            "12",
            "2025-06-20",
            "28000",
            "3.0",
            "ON_SCHEDULE",
            "2026-06-20",
            "5",
            "8",
        ],
        [
            "pump-a",
            "Pump-A",
            "6",
            "2026-02-10",
            "15000",
            "1.5",
            "APPROACHING",
            "2026-08-10",
            "10",
            "6",
        ],
        [
            "exchanger-c",
            "Heat-Exchanger-C",
            "12",
            "2025-12-01",
            "42000",
            "4.0",
            "COMING_DUE",
            "2026-12-01",
            "6",
            "15",
        ],
        [
            "separator-d",
            "Separator-D",
            "24",
            "2024-06-15",
            "55000",
            "5.5",
            "OVERDUE",
            "2026-06-15",
            "3",
            "20",
        ],
    ]
    with open(OUT / "maintenance_schedule.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print("  maintenance_schedule.csv done")


# ── 3. service_logs.txt ───────────────────────────────────────────────────────


def gen_service_logs() -> None:
    content = """SERVICE LOG - MRPL Refinery Unit Operations
Generated: September 2026

LOG ENTRY: Reactor-4 | Date: 2026-03-15 | Engineer: S. Kumar
Performed scheduled 6-month maintenance on Reactor-4. Replaced gaskets and seals. Pressure tested to 5.0 bar - PASS. Catalyst bed inspected - minor fouling cleared. Temperature sensors calibrated. System returned to service at 14:30. Total downtime: 2.5 hours. Cost: Rs.34,500. Status: COMPLETED SUCCESSFULLY.

LOG ENTRY: Compressor-B | Date: 2025-06-20 | Engineer: R. Pillai
Annual maintenance on Compressor-B. Replaced bearings (2 sets). Lubrication system flushed and refilled. Vibration analysis - readings within normal range post-service. Pressure relief valve tested and calibrated. Motor insulation resistance checked: 850 MOhm (PASS). Total downtime: 3 hours. Cost: Rs.27,200. Status: COMPLETED SUCCESSFULLY.

LOG ENTRY: Pump-A | Date: 2026-02-10 | Engineer: M. Shetty
6-month service on Pump-A centrifugal pump. Impeller wear within tolerance (8% wear). Mechanical seal replaced. Shaft alignment checked and corrected (0.05mm deviation corrected to 0.01mm). Cavitation test: no issues detected. Total downtime: 1.5 hours. Cost: Rs.14,800. Status: COMPLETED SUCCESSFULLY.

LOG ENTRY: Separator-D | Date: 2024-06-15 | Engineer: P. Nair
Biennial maintenance on Separator-D. Internal inspection revealed minor corrosion on inlet nozzle - treated with epoxy coating. Demister pads replaced. Level control sensors recalibrated. Pressure safety valve tested: opens at 12.2 bar (within spec). Total downtime: 5.5 hours. Cost: Rs.53,000. Status: COMPLETED WITH MINOR FINDINGS.

LOG ENTRY: Reactor-4 | Date: 2025-09-10 | Engineer: S. Kumar
Emergency inspection triggered by pressure spike to 4.8 bar (96% of max). Root cause: partial blockage in feed line. Blockage cleared. Pressure normalized to 4.1 bar within 2 hours. No damage to reactor vessel. Preventive: increased monitoring frequency for 30 days. Cost: Rs.8,000. Status: EMERGENCY - RESOLVED.

LOG ENTRY: Compressor-B | Date: 2025-12-01 | Engineer: R. Pillai
Unscheduled maintenance - abnormal noise reported. Found: loose impeller retaining nut (vibration-induced). Nut re-torqued to spec. Vibration levels returned to normal (2.1 mm/s). No other issues found. Downtime: 4 hours. Cost: Rs.5,500. Status: RESOLVED.

LOG ENTRY: Pump-A | Date: 2025-08-05 | Engineer: M. Shetty
Routine 6-month service. All parameters nominal. Seal showing 70% remaining life. Bearing temperature: 42C (normal). No corrective action needed. Total downtime: 1.25 hours. Cost: Rs.13,200. Status: COMPLETED - NO ISSUES.

HISTORICAL FAILURE ANALYSIS SUMMARY:
- Reactor-4: 1 pressure exceedance in 8 services (12.5% incident rate)
- Compressor-B: 1 unscheduled stop in 5 services (20% incident rate)
- Pump-A: 0 failures in 10 services (0% incident rate) - most reliable equipment
- Separator-D: Corrosion found in last inspection - monitor closely
- Heat-Exchanger-C: No failures since installation (15 years - excellent record)
"""
    (OUT / "service_logs.txt").write_text(content, encoding="utf-8")
    print("  service_logs.txt done")


# ── 4. safety_protocols.json ──────────────────────────────────────────────────


def gen_safety_protocols() -> None:
    data = {
        "version": "2.1",
        "last_updated": "2026-01-01",
        "authority": "MRPL Safety & Environment Department",
        "safety_rules": [
            {
                "rule_id": "PRESSURE_LIMIT",
                "description": "Equipment operating pressure must not exceed 95% of design pressure",
                "applies_to": ["reactor-4", "compressor-b", "pump-a", "separator-d"],
                "threshold_percent_of_max": 95,
                "action_if_violated": "IMMEDIATE_ESCALATION",
                "notification_level": "CRITICAL",
                "response_time_minutes": 15,
            },
            {
                "rule_id": "TEMPERATURE_LIMIT",
                "description": "Operating temperature must not exceed 95% of max safe temperature",
                "applies_to": ["all"],
                "threshold_percent_of_max": 95,
                "action_if_violated": "IMMEDIATE_ESCALATION",
                "notification_level": "CRITICAL",
                "response_time_minutes": 15,
            },
            {
                "rule_id": "MAINTENANCE_INTERVAL",
                "description": "Equipment must receive scheduled maintenance within grace period",
                "applies_to": ["all"],
                "grace_period_days": 14,
                "action_if_violated": "ESCALATION",
                "notification_level": "HIGH",
                "response_time_hours": 48,
            },
            {
                "rule_id": "DOWNTIME_LIMIT",
                "description": "Planned maintenance downtime cannot exceed limit without approval",
                "applies_to": ["all"],
                "max_downtime_hours": 4,
                "exception_process": "Written approval from Unit Superintendent required",
                "action_if_violated": "WARNING",
                "notification_level": "MEDIUM",
            },
            {
                "rule_id": "BUDGET_APPROVAL",
                "description": "Maintenance costs above threshold require prior budget approval",
                "cost_threshold_inr": 50000,
                "approval_authority": "Plant Manager",
                "action_if_violated": "HOLD",
                "notification_level": "HIGH",
            },
            {
                "rule_id": "VENDOR_CERTIFICATION",
                "description": "All maintenance work must be performed by certified vendors only",
                "certification_required": "MRPL_VENDOR_CLASS_A_or_B",
                "action_if_violated": "IMMEDIATE_HOLD",
                "notification_level": "CRITICAL",
            },
        ],
        "emergency_contacts": {
            "safety_officer": "+91-824-2270400",
            "plant_manager": "+91-824-2270401",
            "fire_station": "+91-824-2270402",
        },
    }
    (OUT / "safety_protocols.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    print("  safety_protocols.json done")


# ── 5. cost_estimates.csv ─────────────────────────────────────────────────────


def gen_cost_estimates() -> None:
    rows = [
        [
            "equipment_id",
            "service_type",
            "labor_cost_inr",
            "material_cost_inr",
            "total_cost_inr",
            "vendor_name",
            "vendor_rating",
            "last_updated",
            "includes_parts",
            "warranty_days",
        ],
        [
            "reactor-4",
            "routine_6m",
            "12000",
            "22000",
            "34500",
            "Thermax_Services",
            "A",
            "2026-03-15",
            "Yes",
            "90",
        ],
        [
            "reactor-4",
            "major_overhaul",
            "35000",
            "65000",
            "100000",
            "Thermax_Services",
            "A",
            "2025-09-10",
            "Yes",
            "180",
        ],
        [
            "compressor-b",
            "routine_12m",
            "10000",
            "17500",
            "27500",
            "Atlas_Copco_India",
            "A",
            "2025-06-20",
            "Yes",
            "90",
        ],
        [
            "compressor-b",
            "bearing_replacement",
            "8000",
            "12000",
            "20000",
            "Atlas_Copco_India",
            "A",
            "2025-12-01",
            "Yes",
            "60",
        ],
        [
            "pump-a",
            "routine_6m",
            "5000",
            "9800",
            "14800",
            "KSB_India",
            "B",
            "2026-02-10",
            "Yes",
            "60",
        ],
        [
            "pump-a",
            "seal_replacement",
            "3000",
            "6000",
            "9000",
            "KSB_India",
            "B",
            "2025-08-05",
            "Yes",
            "30",
        ],
        [
            "exchanger-c",
            "routine_12m",
            "18000",
            "24000",
            "42000",
            "HRS_Process_Systems",
            "A",
            "2025-12-01",
            "Yes",
            "90",
        ],
        [
            "exchanger-c",
            "tube_bundle_replace",
            "40000",
            "80000",
            "120000",
            "HRS_Process_Systems",
            "A",
            "2023-12-01",
            "Yes",
            "365",
        ],
        [
            "separator-d",
            "routine_24m",
            "20000",
            "33000",
            "53000",
            "Descon_Engineering",
            "B",
            "2024-06-15",
            "Yes",
            "120",
        ],
        [
            "separator-d",
            "corrosion_treatment",
            "15000",
            "25000",
            "40000",
            "Descon_Engineering",
            "B",
            "2024-06-15",
            "Yes",
            "180",
        ],
    ]
    with open(OUT / "cost_estimates.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print("  cost_estimates.csv done")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating MRPL sample data...")
    gen_equipment_specs()
    gen_maintenance_schedule()
    gen_service_logs()
    gen_safety_protocols()
    gen_cost_estimates()
    print(f"Done. Files written to: {OUT.resolve()}")
