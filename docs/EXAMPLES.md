# MRPL Agentic Workbench — Sample Queries & Outputs

Five real worked examples showing input → reasoning → decision.

---

## Example 1: Maintenance Scheduling

**Query:**
```
Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000. When should I schedule?
```

**Agent 1 — Understanding:**
- Intent: `schedule_maintenance`
- Equipment: `reactor-4`
- Pressure: 4.2 bar | Last service: 180 days | Budget: Rs.50,000

**Agent 3 — Reasoning chain:**
1. Pressure 4.2 bar is within safe range 3.5–5.0 bar (84%)
2. Service interval is 6 months; 180 days = exactly at window
3. Historical trend: proactive servicing prevents failures
4. Estimated cost Rs.35,000 is within Rs.50,000 budget
5. Downtime 2.5 hours is within 4-hour limit

**Decision:**
```json
{
  "priority": "NORMAL",
  "recommendation": {
    "action": "Schedule Maintenance",
    "timing": "Within 2 weeks",
    "estimated_cost_inr": 35000,
    "estimated_downtime_hours": 2.5
  },
  "validation": {
    "status": "APPROVED",
    "compliance_score": 100
  }
}
```

---

## Example 2: Risk Assessment

**Query:**
```
Compressor-B making loud noise, temperature up 15C. What is the risk?
```

**Agent 1 — Understanding:**
- Intent: `risk_assessment`
- Equipment: `compressor-b`
- Temperature rise: 15°C

**Agent 3 — Reasoning chain:**
1. Unusual noise + temperature rise are early bearing/lubrication failure indicators
2. Compressor-B last service was 14 months ago, interval is 12 months — overdue
3. Historical precedent: 4/5 similar cases led to failure within 2-4 weeks
4. Risk level: HIGH if not inspected immediately
5. Recommended action: urgent inspection before next shift

**Decision:**
```json
{
  "priority": "ELEVATED",
  "recommendation": {
    "action": "Inspect and Assess Risk",
    "timing": "Within 1 week",
    "risk_if_delayed": "80% historical failure rate without inspection"
  },
  "validation": {
    "status": "APPROVED_WITH_WARNINGS",
    "compliance_score": 70,
    "warnings": ["Maintenance overdue"]
  }
}
```

---

## Example 3: Cost Optimization

**Query:**
```
Pump-A and Compressor-B both need service. Budget Rs.35000. Which first?
```

**Agent 1 — Understanding:**
- Intent: `cost_optimization`
- Equipment: `pump-a` (cost Rs.15,000) + `compressor-b` (cost Rs.28,000)
- Budget: Rs.35,000

**Agent 3 — Reasoning chain:**
1. Total cost Rs.43,000 exceeds Rs.35,000 budget — cannot do both
2. Pump-A: last service 200 days ago, interval 6 months — overdue by 20 days
3. Compressor-B: last service 14 months ago, showing noise symptoms
4. Risk comparison: Compressor-B has active symptoms (higher immediate risk)
5. Recommendation: service Compressor-B first (Rs.28,000), plan Pump-A next cycle

**Decision:**
```json
{
  "priority": "ELEVATED",
  "recommendation": {
    "action": "Prioritize and Schedule",
    "detail": "Service Compressor-B first (active symptoms), queue Pump-A next budget cycle",
    "estimated_cost_inr": 28000,
    "timing": "Within 1 week"
  },
  "validation": {
    "status": "APPROVED_WITH_WARNINGS",
    "compliance_score": 80,
    "warnings": ["Cost approaching budget limit"]
  }
}
```

---

## Example 4: Compliance Check

**Query:**
```
Can we skip separator-D maintenance? It was last done 26 months ago.
```

**Agent 1 — Understanding:**
- Intent: `compliance_check`
- Equipment: `separator-d`
- Last service: ~780 days (26 months)

**Agent 3 — Reasoning chain:**
1. Separator-D has a 24-month service interval
2. Last service was 26 months ago — already 2 months overdue (grace period is 14 days)
3. Safety protocols require immediate scheduling
4. Historical: 2/3 similar delayed cases resulted in emergency shutdowns
5. Skipping further risks regulatory non-compliance

**Decision:**
```json
{
  "priority": "URGENT",
  "recommendation": {
    "action": "URGENT INSPECTION REQUIRED",
    "timing": "IMMEDIATE - within 24 hours",
    "risk_if_delayed": "Regulatory violation + 67% historical emergency shutdown rate"
  },
  "validation": {
    "status": "ESCALATE",
    "compliance_score": 50,
    "escalations": ["Equipment overdue by >14 day grace period"]
  }
}
```

---

## Example 5: Equipment Status Check

**Query:**
```
What is the current status of heat exchanger-C?
```

**Agent 1 — Understanding:**
- Intent: `status_check`
- Equipment: `exchanger-c`

**Agent 3 — Reasoning chain:**
1. Exchanger-C last service: 12 months ago, interval 12 months — at scheduled window
2. No active pressure or temperature anomalies reported
3. Compliance: within standard schedule
4. Historical performance: 6/6 service cycles completed without issues
5. Status: on schedule, no immediate action required

**Decision:**
```json
{
  "priority": "NORMAL",
  "recommendation": {
    "action": "Monitor Equipment Status",
    "timing": "Within next scheduled maintenance window",
    "estimated_cost_inr": 42000,
    "estimated_downtime_hours": 4.0
  },
  "validation": {
    "status": "APPROVED",
    "compliance_score": 100,
    "violations": [],
    "warnings": []
  }
}
```

---

## Running These Examples

```bash
# Via API
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"Reactor-4 pressure 4.2 bar, budget Rs.50000. Schedule?\", \"user_id\": \"eng_1\"}"

# Via Streamlit UI
open http://localhost:8501
# Select an example from the sidebar or type your own query
```
