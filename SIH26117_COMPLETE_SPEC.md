# SIH26117: SOVEREIGN ON-PREMISE AGENTIC AI WORKBENCH
## Complete Technical Specification (AI-Agent Friendly)

**Version:** 1.0  
**Date:** September 2026  
**Status:** Ready for Implementation  
**Target Delivery:** 36 Hours  

---

## SECTION 1: EXECUTIVE SUMMARY

### 1.1 Project Definition
- **Name:** Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs
- **Sponsor:** Mangalore Refinery & Petrochemicals Limited (MRPL)
- **SIH Track ID:** SIH26117
- **Category:** Software
- **Prize:** ₹1,00,000

### 1.2 One-Sentence Description
Build a local AI agent system where MRPL engineers ask questions about equipment maintenance and get autonomous, auditable recommendations without sending data to the cloud.

### 1.3 Success Definition
**Engineers can:**
1. Ask natural language questions (e.g., "When should I service reactor-4?")
2. Get structured recommendations with reasoning
3. See all decisions logged for compliance
4. Everything runs locally on MRPL servers

**Judges see:**
1. Multi-agent reasoning system working end-to-end
2. Production-grade code (error handling, logging, security)
3. Clear demo that takes 2 minutes to understand

### 1.4 Why This Matters
MRPL makes 200+ maintenance decisions per month. Currently manual process (hours per decision). Cloud APIs can't be used (data sovereignty). This system automates decisions while keeping everything on-premise.

### 1.5 Competitive Advantage
- **Unique:** <10 teams will attempt agentic systems at this level
- **Executable:** Reuses NexusTiQ production patterns (70% leverage)
- **Impressive:** Multi-agent orchestration shows systems thinking
- **Interview-Ready:** FAANG-level technical depth

---

## SECTION 2: PROBLEM STATEMENT (DETAILED)

### 2.1 Current State at MRPL

**Operations:**
- 3 refinery units
- 40+ critical equipment pieces
- 500+ maintenance operations/month
- 200+ engineers making operational decisions
- Current decision cycle: 2-8 hours per decision

**Current Process:**
```
Engineer observes issue
    ↓ [Manual]
Check specs, history, constraints
    ↓ [1-4 hours: searching databases]
Consult senior engineer for validation
    ↓ [Delayed if unavailable]
Manual cost-benefit analysis
    ↓ [2-4 hours: documentation]
Decision made
    ↓ [Total: 2-8 hours]
Maintenance scheduled
```

**Pain Points:**
1. **Time Waste:** Each decision takes 2-8 hours of human labor
2. **Consistency:** Different engineers make different calls on identical problems
3. **Bottleneck:** Senior engineers required to validate every decision
4. **Documentation:** Manual writeups for compliance/audit (labor-intensive)
5. **Risk:** Pressure to make fast decisions often overrides optimal decisions
6. **Scalability:** Can't handle >200 decisions/month without heroic effort

**Financial Impact:**
- Lost productivity: 8 hours/decision × 200 decisions = 1600 hours/month (~₹20 lakhs annually)
- Bad decisions: Skipped maintenance causing equipment failure (₹10-100 lakhs replacement cost)
- Compliance risk: Missing audit trail for regulatory violations (potential penalties)

### 2.2 Why Cloud AI Doesn't Work

**Constraint 1: Data Sovereignty**
- Equipment specs, maintenance logs, cost structure = trade secrets
- Cannot send to US/international cloud servers
- Regulatory requirement: certain industrial data must stay on-shore

**Constraint 2: Security**
- If cloud API compromised, MRPL's entire operational knowledge exposed
- Competitive intelligence: maintenance patterns reveal production capacity

**Constraint 3: Cost at Scale**
- Cloud APIs charge per token
- 1000+ queries/month × ₹0.05-0.10/query = ₹50K-100K/month
- Over 5-year lifecycle: ₹30-60 lakhs

**Constraint 4: Latency**
- Cloud round-trip: 2-5 seconds per decision
- Operational decisions need response in <1 second
- Sometimes network is down (petrochemical plants have outages)

**Constraint 5: Offline Operation**
- Refineries sometimes have connectivity issues
- System must work offline (no cloud fallback)

### 2.3 What MRPL Needs

**Functional Requirements:**
1. Local deployment (runs on MRPL servers, no cloud)
2. Natural language interface (engineers ask questions)
3. Autonomous reasoning (explains "why" for every decision)
4. Structured output (recommendations engineers can act on)
5. Full audit trail (every decision logged for compliance)

**Non-Functional Requirements:**
1. Speed: <6 seconds per query
2. Reliability: no crashes, graceful error handling
3. Security: prevents prompt injection, validates all inputs
4. Scalability: handles 50-100 queries/minute
5. Transparency: reasoning visible to engineers

**Use Cases:**

**Use Case 1: Maintenance Scheduling**
```
Input: "Reactor-4 pressure is 4.2 bar, last serviced 6 months ago, budget ₹50K. When service?"
Output: "Schedule next Tuesday-Wednesday, cost ₹35K, reasoning: [list]"
```

**Use Case 2: Risk Assessment**
```
Input: "Compressor-B making noise, temperature up 15°C, last service 1 year ago. Risk?"
Output: "HIGH risk, 80% historical precedent for failure in 2-4 weeks, recommend urgent inspection"
```

**Use Case 3: Cost Optimization**
```
Input: "₹2 lakh budget this quarter, need reactor-4 and pump-A service. Prioritize?"
Output: "Do pump-A first (urgent), then reactor-4 (planned), total ₹63K, leaves ₹1.37L buffer"
```

**Use Case 4: Compliance Checking**
```
Input: "Can we skip reactor maintenance this month (5 months since last service)?"
Output: "NOT RECOMMENDED: violates 6-month minimum interval, 3 of 5 previous skips resulted in failure"
```

---

## SECTION 3: SOLUTION ARCHITECTURE

### 3.1 System Overview

```
USER QUERY
    ↓
SECURITY CHECK
├─ Sanitize input
├─ Check length (<2000 chars)
├─ Validate tokens (no SQL injection)
├─ Rate limit (10 req/min)
└─ Parse JSON
    ↓
AGENT 1: QUERY UNDERSTANDING
├─ Parse intent
├─ Extract entities (equipment, constraints)
├─ Compute confidence
    ↓
AGENT 2: DOCUMENT RETRIEVAL
├─ Vector search FAISS index
├─ Return top-5 relevant documents
├─ Rank by relevance
    ↓
AGENT 3: REASONING (LLM-Powered)
├─ Load Mistral-7B
├─ Provide context (docs + query)
├─ Generate reasoning chain
├─ Output recommendation + confidence
    ↓
AGENT 4: VALIDATION
├─ Check business rules
├─ Verify constraints (cost, downtime, safety)
├─ Flag violations
├─ Compute compliance score
    ↓
AGENT 5: DECISION
├─ Synthesize all outputs
├─ Create structured JSON
├─ Add metadata (timestamp, confidence, reasoning)
    ↓
AUDIT LOG
├─ Append decision to JSONL
├─ Immutable record
    ↓
RESPONSE TO USER
└─ Display recommendation + reasoning + audit info
```

### 3.2 Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **LLM** | Mistral-7B via ollama | Fast (2s), local, good reasoning |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Lightweight, runs local |
| **Vector DB** | FAISS (local) | Fast search, no external DB |
| **Orchestration** | LangChain | Manages agents, retries, timeouts |
| **API** | FastAPI | Async, concurrent request handling |
| **UI** | Streamlit | Quick demo, no frontend needed |
| **Logging** | Python JSON logger | Structured JSONL audit trail |
| **Container** | Docker | Reproducible deployment |

### 3.3 Data Flow (Complete)

**Step 1: Input Reception**
```
Raw Query: "Reactor-4 pressure 4.2, last service 6 mo, budget 50K. When service?"
    ↓
Validation:
├─ Length check: <2000 chars ✓
├─ No malicious patterns ✓
├─ Valid JSON (if API call) ✓
└─ Under rate limit ✓
    ↓
Sanitized Input: Query ready for processing
```

**Step 2: Agent 1 Processing**
```
Agent 1: QueryUnderstandingAgent
Input: "Reactor-4 pressure 4.2..."
Processing:
├─ Tokenize text
├─ Identify entities (equipment: reactor-4, pressure: 4.2, duration: 6 months, budget: 50000)
├─ Extract intent (maintenance_scheduling)
├─ Identify constraints (budget_limit: 50000, currency: INR)
└─ Compute confidence: 0.94
Output JSON:
{
  "intent": "schedule_maintenance",
  "equipment": "reactor-4",
  "current_state": {
    "pressure_bar": 4.2,
    "last_service_days": 180
  },
  "constraints": {
    "budget_ral": 50000
  },
  "confidence": 0.94
}
```

**Step 3: Agent 2 Processing**
```
Agent 2: RetrievalAgent
Input: equipment="reactor-4", queries=["maintenance schedule", "pressure thresholds"]
Processing:
├─ Vectorize queries using sentence-transformers
├─ Search FAISS index
├─ Rank results by similarity
└─ Return top-5 documents
Output JSON:
{
  "documents_found": 4,
  "documents": [
    {
      "source": "equipment_specs.json",
      "equipment": "reactor-4",
      "safe_pressure_range": "3.5-5.0 bar",
      "max_temp": 150,
      "lifespan_years": 10
    },
    {
      "source": "maintenance_schedule.csv",
      "equipment": "reactor-4",
      "service_interval_months": 6,
      "last_service": "2026-03-15",
      "typical_cost": 35000,
      "downtime_hours": 2.5
    }
  ]
}
```

**Step 4: Agent 3 Processing**
```
Agent 3: ReasoningAgent (LLM-Powered)
Input: 
├─ Query: "Reactor-4 pressure 4.2..."
├─ Documents: [equipment_specs, maintenance_schedule, service_logs]
└─ System Prompt: "You are maintenance advisor for MRPL..."
Processing:
├─ Call Mistral-7B via ollama
├─ LLM generates step-by-step reasoning
└─ Extract recommendation + confidence
Output JSON:
{
  "reasoning": [
    "Step 1: Pressure 4.2 bar vs safe range 3.5-5.0 bar = SAFE",
    "Step 2: Service interval 6-8 months, last service 180 days = APPROACHING",
    "Step 3: Pressure trend upward (historical data), risky if delayed",
    "Step 4: Cost 35K within budget 50K"
  ],
  "recommendation": "Schedule maintenance next Tuesday-Wednesday",
  "cost_estimate": 35000,
  "downtime_hours": 2.5,
  "risk_if_delayed": "Pressure may exceed limits in 4 weeks",
  "confidence": 0.91,
  "inference_time_ms": 1847
}
```

**Step 5: Agent 4 Processing**
```
Agent 4: ValidationAgent
Input: Recommendation from Agent 3
Processing:
├─ Run against business rules:
│  ├─ Cost check: 35000 < 50000 ✓ PASS
│  ├─ Downtime check: 2.5 < 4 hours ✓ PASS
│  ├─ Safety check: 4.2 bar is 84% of max ✓ PASS
│  ├─ Compliance: follows schedule ✓ PASS
│  └─ Historical: similar approach worked 5x before ✓ PASS
└─ Compute compliance score: 98%
Output JSON:
{
  "validation_status": "APPROVED",
  "compliance_score": 98,
  "rule_results": {
    "cost_check": "PASS (35000 < 50000)",
    "downtime_check": "PASS (2.5 < 4)",
    "safety": "PASS (84% margin)",
    "compliance": "PASS (standard schedule)",
    "historical": "PASS (5 successful precedents)"
  },
  "violations": []
}
```

**Step 6: Agent 5 Processing**
```
Agent 5: DecisionAgent
Input: All 4 agent outputs
Processing:
├─ Merge results
├─ Add metadata (timestamp, decision_id, model_info)
├─ Create structured JSON
└─ Prepare for logging
Output JSON:
{
  "decision_id": "DEC-20260915-001847",
  "timestamp": "2026-09-15T14:32:01Z",
  "equipment": "reactor-4",
  
  "current_state": {
    "pressure": "4.2 bar",
    "safe_range": "3.5-5.0 bar",
    "last_service": "2026-03-15",
    "service_interval": "6-8 months"
  },
  
  "analysis": {
    "pressure_status": "SAFE",
    "maintenance_urgency": "PLANNED (not immediate)",
    "risk_level": "LOW to MEDIUM",
    "cost_estimate": 35000,
    "downtime_hours": 2.5
  },
  
  "recommendation": {
    "action": "Schedule maintenance",
    "timing": "Next Tuesday-Wednesday",
    "reason": "Proactive before pressure exceeds limits",
    "risk_if_delayed": "Pressure may exceed safe range in 4 weeks"
  },
  
  "validation": {
    "status": "APPROVED",
    "compliance_score": 98,
    "violations": []
  },
  
  "metadata": {
    "confidence": 0.91,
    "reasoning_steps": 4,
    "inference_time_ms": 1847,
    "model": "mistral-7b",
    "total_time_ms": 1952
  }
}
```

**Step 7: Audit Logging**
```
Append to: data/audit_logs/decisions.jsonl

Log Entry:
{
  "timestamp": "2026-09-15T14:32:01Z",
  "decision_id": "DEC-20260915-001847",
  "user_id": "eng_supervisor_1",
  "equipment": "reactor-4",
  "recommendation": "Schedule maintenance",
  "confidence": 0.91,
  "validation_status": "APPROVED",
  "inference_time_ms": 1847
}

(Note: Append-only, immutable audit trail)
```

**Step 8: Response to User**
```
Display in UI:
├─ Equipment: reactor-4
├─ Current State: Pressure 4.2 bar (safe)
├─ Recommendation: Schedule maintenance next Tue-Wed
├─ Cost: ₹35,000
├─ Downtime: 2.5 hours
├─ Confidence: 91%
├─ Reasoning: [step-by-step chain visible]
├─ Validation: APPROVED (98% compliance)
└─ Decision ID: DEC-20260915-001847 (for audit lookup)
```

---

## SECTION 4: MVP REQUIREMENTS (EXACT SCOPE)

### 4.1 What's Built (In Scope)

**Requirement 1.1: Query Input Processing**
- Accept natural language questions via web form
- Limit: 2000 characters max
- Support 5 sample equipment: reactor-4, compressor-B, pump-A, exchanger-C, separator-D
- Parse intent, extract entities, validate input

**Requirement 1.2: Document Management**
- 5 synthetic MRPL documents created:
  1. equipment_specs.json (technical specifications)
  2. maintenance_schedule.csv (service intervals, history)
  3. service_logs.txt (narrative maintenance records)
  4. safety_protocols.json (operational limits, rules)
  5. cost_estimates.csv (maintenance pricing)
- All data loaded into FAISS vector store (local)
- No external APIs, fully offline

**Requirement 1.3: Agent System**
- 5 specialized agents implemented:
  1. QueryUnderstandingAgent: parse intent + extract entities
  2. RetrievalAgent: vector search FAISS for relevant docs
  3. ReasoningAgent: call Mistral-7B, generate recommendations
  4. ValidationAgent: check business rules, compute compliance
  5. DecisionAgent: synthesize outputs into final recommendation
- Each agent: independent, timeout-protected, error-handling
- Orchestrator manages workflow: Understanding → Retrieval → Reasoning → Validation → Decision

**Requirement 1.4: LLM Integration**
- Mistral-7B running locally via ollama
- No cloud API calls
- Inference time: <2 seconds per query
- Model inference request format:
  ```
  POST http://localhost:11434/api/generate
  {
    "model": "mistral",
    "prompt": "<reasoning prompt>",
    "stream": false
  }
  ```

**Requirement 1.5: Business Logic**
- 5 core business rules implemented:
  1. Cost check: recommendation_cost <= budget
  2. Downtime check: downtime_hours <= 4
  3. Safety margin: pressure/temp within 95% of max
  4. Compliance check: recommendation follows standard schedule
  5. Historical validation: check if similar approach worked before
- Violations flagged, compliance score computed (0-100%)

**Requirement 1.6: Security Hardening**
- Input sanitization: XML escape, length validation, injection detection
- Rate limiting: max 10 requests/minute per client
- Timeout enforcement: 5 seconds per agent, 20 seconds total workflow
- Error handling: all exception paths return proper error JSON (never crash)
- No hardcoded secrets (environment variables only)

**Requirement 1.7: Audit Trail**
- Every decision logged to JSONL file (append-only)
- Log fields: timestamp, decision_id, user_id, equipment, recommendation, confidence, inference_time
- Audit log path: data/audit_logs/decisions.jsonl
- Immutable (append-only, no modifications)

**Requirement 1.8: User Interface**
- Streamlit web app
- Text area for query input
- Submit button to process query
- Display structured decision output (JSON)
- Show reasoning chain (visible steps)
- Display last 10 audit log entries
- No authentication required (local deployment)

**Requirement 1.9: Deployment**
- Docker container
- Dockerfile specified
- docker-compose.yml for local setup
- requirements.txt with all pinned versions
- .env.example template for configuration
- Health check endpoint: GET /health → returns OK
- API endpoint: POST /analyze → accepts query, returns decision

### 4.2 What's NOT Built (Out of Scope)

**Out of Scope 1:** Multi-user authentication
- Not needed: local MRPL deployment, single-user initially

**Out of Scope 2:** Fine-tuning Mistral
- Use base model, training data not available for MVP

**Out of Scope 3:** Cloud deployment
- Only local deployment (that's the constraint)

**Out of Scope 4:** Real MRPL database
- Use synthetic data for demo

**Out of Scope 5:** Advanced observability
- No Prometheus, Grafana, ELK stack
- Basic logging to JSONL sufficient

**Out of Scope 6:** Model quantization/optimization
- Use full Mistral-7B model (12GB RAM acceptable for MRPL)

**Out of Scope 7:** Production frontend
- Streamlit basic UI sufficient for demo

**Out of Scope 8:** Multi-language support
- English only for MVP

### 4.3 Success Acceptance Criteria

**Functional Criteria:**
- ✅ All 5 agents functioning independently, tested
- ✅ End-to-end workflow completes in <6 seconds per query
- ✅ Zero external API calls (fully offline)
- ✅ Audit log captures every decision accurately
- ✅ Input validation blocks malicious prompts (tested with injection attempts)
- ✅ Rate limiting enforced (11th request rejected)
- ✅ Timeout prevents hung requests (agent killed at 5 sec)
- ✅ Error handling: no unhandled exceptions (all errors return proper JSON)

**Code Quality Criteria:**
- ✅ requirements.txt: all packages pinned with exact versions
- ✅ No hardcoded secrets (all from environment)
- ✅ Comprehensive error handling (try-catch all async calls)
- ✅ Logging covers all decision paths (audit trail complete)
- ✅ Type hints on all functions (mypy: 100% coverage)
- ✅ No print() statements (all use logging)
- ✅ Black formatting applied (consistent code style)

**Demo Criteria:**
- ✅ Judges understand what system does in <60 seconds (no domain expertise required)
- ✅ Live demo: submit 3 sample queries → get structured recommendations
- ✅ Reasoning visible (engineers see why system recommends)
- ✅ Validation applied (recommendations checked against rules)
- ✅ Output actionable (engineers can use recommendations directly)
- ✅ No crashes during demo (rock-solid execution)

**Documentation Criteria:**
- ✅ README.md: setup instructions + architecture + examples
- ✅ ARCHITECTURE.md: detailed system design
- ✅ Inline comments: complex logic explained
- ✅ .env.example: all config variables documented

---

## SECTION 5: PROJECT STRUCTURE

```
sih-26117-agentic-workbench/
│
├── README.md                          [CRITICAL] Main documentation
├── ARCHITECTURE.md                    Detailed design
├── requirements.txt                   [CRITICAL] Pinned versions
├── .env.example                       Environment template
├── Dockerfile                         Container specification
├── docker-compose.yml                 Local development setup
├── .gitignore                         Exclude data/, logs/
│
├── config/
│   ├── __init__.py
│   ├── settings.py                    [REQUIRED] BaseSettings config
│   ├── prompts.py                     [REQUIRED] All LLM prompts
│   └── business_rules.py              [REQUIRED] Validation rules
│
├── core/
│   ├── __init__.py
│   ├── llm_engine.py                  [REQUIRED] Mistral wrapper
│   ├── document_loader.py             [REQUIRED] Load + parse docs
│   └── vector_store.py                [REQUIRED] FAISS wrapper
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py                  [REQUIRED] Abstract base class
│   ├── query_understanding.py         [REQUIRED] Agent 1
│   ├── retrieval_agent.py             [REQUIRED] Agent 2
│   ├── reasoning_agent.py             [REQUIRED] Agent 3
│   ├── validation_agent.py            [REQUIRED] Agent 4
│   └── decision_agent.py              [REQUIRED] Agent 5
│
├── orchestrator/
│   ├── __init__.py
│   ├── workflow.py                    [REQUIRED] Agent orchestration
│   └── logging.py                     [REQUIRED] Audit trail
│
├── api/
│   ├── __init__.py
│   ├── main.py                        [REQUIRED] FastAPI server
│   ├── models.py                      [REQUIRED] Pydantic schemas
│   └── middleware.py                  [REQUIRED] Rate limiting + validation
│
├── ui/
│   └── streamlit_app.py               [REQUIRED] Streamlit UI
│
├── data/
│   ├── sample_docs/
│   │   ├── equipment_specs.json       [REQUIRED] Equipment data
│   │   ├── maintenance_schedule.csv   [REQUIRED] Service intervals
│   │   ├── service_logs.txt           [REQUIRED] History
│   │   ├── safety_protocols.json      [REQUIRED] Rules
│   │   └── cost_estimates.csv         [REQUIRED] Pricing
│   ├── embeddings_index.faiss         [GENERATED] Vector store
│   └── audit_logs/
│       └── decisions.jsonl            [GENERATED] Audit trail
│
├── tests/
│   ├── __init__.py
│   ├── test_agents.py                 Unit tests for agents
│   ├── test_workflow.py               Integration tests
│   └── test_security.py               Security tests (injection)
│
├── scripts/
│   ├── setup_llm.sh                   Install ollama + model
│   ├── generate_sample_data.py        Create synthetic docs
│   └── run_checks.sh                  Pre-deployment validation
│
└── docs/
    └── EXAMPLES.md                    Sample queries + outputs
```

**File Status Legend:**
- [CRITICAL] = Must exist, system won't run without it
- [REQUIRED] = Must implement for MVP to work
- [GENERATED] = Created at runtime, not in git

---

## SECTION 6: COMPONENT SPECIFICATIONS (AI-FRIENDLY)

### 6.1 Agent 1: QueryUnderstandingAgent

**Purpose:** Parse user query and extract structured intent

**Input Format:**
```json
{
  "query": "Reactor-4 pressure is 4.2 bar. Last serviced 6 months ago. Budget is ₹50,000. When should I schedule maintenance?"
}
```

**Processing Logic:**
```
1. Tokenize query
2. Identify entities:
   - Equipment name: regex patterns for equipment types
   - Numerical values: pressures, temperatures, durations
   - Constraints: budget, time limits
3. Map to intent:
   - "when should" → schedule_maintenance
   - "what's risk" → risk_assessment
   - "can we skip" → compliance_check
   - "which to prioritize" → cost_optimization
4. Confidence scoring: how well did we understand?
```

**Output Format:**
```json
{
  "intent": "schedule_maintenance",
  "equipment": "reactor-4",
  "current_state": {
    "pressure_bar": 4.2,
    "last_service_days": 180
  },
  "constraints": {
    "budget_inr": 50000,
    "currency": "INR"
  },
  "confidence": 0.94,
  "status": "SUCCESS"
}
```

**Error Output Format:**
```json
{
  "error": "Could not parse equipment name from query",
  "status": "FAILED"
}
```

**Timeout:** 5 seconds  
**Fallback:** Return error status FAILED

---

### 6.2 Agent 2: RetrievalAgent

**Purpose:** Find relevant documents from MRPL's knowledge base

**Input Format:**
```json
{
  "equipment": "reactor-4",
  "queries": ["maintenance schedule", "pressure thresholds", "cost estimates"],
  "top_k": 5
}
```

**Processing Logic:**
```
1. Vectorize each query using sentence-transformers
2. Search FAISS index
3. Rank results by similarity score
4. Return top-K documents
5. Add retrieval metadata (similarity scores)
```

**Vector Store Contents:**
- 5 documents with embeddings pre-computed
- Index built on startup
- Search latency: <5ms per query

**Output Format:**
```json
{
  "documents_found": 4,
  "documents": [
    {
      "source": "equipment_specs.json",
      "equipment": "reactor-4",
      "safe_pressure_range": "3.5-5.0 bar",
      "max_temperature": 150,
      "lifespan_years": 10,
      "material": "stainless steel",
      "similarity_score": 0.92
    },
    {
      "source": "maintenance_schedule.csv",
      "equipment": "reactor-4",
      "service_interval_months": 6,
      "last_service_date": "2026-03-15",
      "typical_cost": 35000,
      "typical_downtime_hours": 2.5,
      "similarity_score": 0.88
    }
  ],
  "retrieval_time_ms": 42,
  "status": "SUCCESS"
}
```

**Timeout:** 5 seconds  
**Fallback:** Return empty documents array with status PARTIAL

---

### 6.3 Agent 3: ReasoningAgent (LLM-Powered)

**Purpose:** Generate step-by-step reasoning and recommendation

**Input Format:**
```json
{
  "query": "Reactor-4 pressure is 4.2 bar. Last serviced 6 months ago. Budget is ₹50,000. When schedule?",
  "context_documents": [
    {equipment_specs, maintenance_schedule, service_logs...}
  ],
  "understanding": {
    "intent": "schedule_maintenance",
    "equipment": "reactor-4",
    "constraints": {"budget_inr": 50000}
  }
}
```

**LLM Prompting Strategy:**
```
SYSTEM_PROMPT:
"You are an industrial maintenance advisor for MRPL (Mangalore Refinery).
Your role: help engineers make maintenance decisions based on equipment data.

CONSTRAINTS:
- Only use information from provided documents
- Always explain reasoning step-by-step
- Flag uncertainties or missing information
- Focus on safety, cost efficiency, compliance

PROVIDE RESPONSE IN JSON FORMAT"

USER_PROMPT:
"Equipment: {equipment}
Current State: {current_state}
Documents: {context}

Question: {query}

Respond with JSON:
{
  'reasoning': ['step1', 'step2', 'step3'],
  'recommendation': 'primary recommendation',
  'reasoning_confidence': 0.0-1.0
}"
```

**Processing Logic:**
```
1. Prepare context: format documents + query
2. Create full prompt (system + user)
3. Call Mistral-7B via ollama:
   POST http://localhost:11434/api/generate
   {model: "mistral", prompt: "...", stream: false}
4. Parse response JSON
5. Extract reasoning steps + recommendation + confidence
6. Measure inference time
```

**Output Format:**
```json
{
  "reasoning": [
    "Step 1: Current pressure 4.2 bar is within safe range (3.5-5.0 bar)",
    "Step 2: Last service exactly 6 months ago, interval is 6-8 months, approaching end",
    "Step 3: Historical pressure data shows gradual increase (risky if trend continues)",
    "Step 4: Cost ₹35K is within budget ₹50K",
    "Step 5: Downtime 2.5 hours acceptable for current schedule"
  ],
  "recommendation": "Schedule maintenance next Tuesday-Wednesday (2 weeks from now)",
  "cost_estimate_inr": 35000,
  "downtime_hours": 2.5,
  "risk_if_delayed": "Pressure may exceed safe limits in 4 weeks if trend continues",
  "confidence": 0.91,
  "inference_time_ms": 1847,
  "status": "SUCCESS"
}
```

**Error Output:**
```json
{
  "error": "Mistral inference timeout after 5 seconds",
  "status": "FAILED"
}
```

**Timeout:** 5 seconds  
**Fallback:** Return error (cannot continue without reasoning)

---

### 6.4 Agent 4: ValidationAgent

**Purpose:** Verify recommendation against business rules

**Input Format:**
```json
{
  "recommendation": {
    "action": "Schedule maintenance",
    "cost_estimate_inr": 35000,
    "downtime_hours": 2.5,
    "equipment": "reactor-4"
  },
  "context": {
    "budget_inr": 50000,
    "max_downtime_hours": 4,
    "equipment_type": "reactor"
  }
}
```

**Business Rules:**
```
RULE_1_COST_CHECK:
  Condition: recommendation.cost > context.budget
  Action: FAIL with message "Cost exceeds budget"
  
RULE_2_DOWNTIME_CHECK:
  Condition: recommendation.downtime > context.max_downtime
  Action: WARN with message "Downtime exceeds limit (requires approval)"
  
RULE_3_SAFETY_MARGIN:
  Condition: current_pressure > 95% of max_pressure
  Action: ESCALATE with message "URGENT: Safety margin critical"
  
RULE_4_COMPLIANCE:
  Condition: recommendation not in standard schedule
  Action: WARN with message "Deviation from standard schedule"
  
RULE_5_HISTORICAL:
  Condition: similar past cases found in service_logs
  Action: APPROVE with message "Similar approach succeeded N times before"
```

**Processing Logic:**
```
1. For each business rule:
   a. Check condition
   b. If violated: flag violation
   c. Record rule_result (PASS/FAIL/WARN/ESCALATE)
2. Compute compliance_score:
   score = (rules_passed / total_rules) * 100
3. Decision logic:
   if any ESCALATE: validation_status = ESCALATE
   elif any FAIL: validation_status = REJECTED
   elif any WARN: validation_status = APPROVED_WITH_WARNINGS
   else: validation_status = APPROVED
```

**Output Format:**
```json
{
  "validation_status": "APPROVED",
  "compliance_score": 98,
  "rule_results": {
    "cost_check": {
      "status": "PASS",
      "message": "Cost ₹35,000 < Budget ₹50,000"
    },
    "downtime_check": {
      "status": "PASS",
      "message": "Downtime 2.5 hours < Limit 4 hours"
    },
    "safety_margin": {
      "status": "PASS",
      "message": "Pressure 4.2 bar is 84% of max (safe)"
    },
    "compliance": {
      "status": "PASS",
      "message": "Follows standard 6-month maintenance interval"
    },
    "historical": {
      "status": "PASS",
      "message": "Similar approach succeeded 5 times before"
    }
  },
  "violations": [],
  "warnings": [],
  "status": "SUCCESS"
}
```

**Timeout:** 5 seconds  
**Fallback:** Return compliance_score = 0, validation_status = UNKNOWN

---

### 6.5 Agent 5: DecisionAgent

**Purpose:** Synthesize all agent outputs into final recommendation

**Input Format:**
```json
{
  "understanding": {Agent 1 output},
  "retrieval": {Agent 2 output},
  "reasoning": {Agent 3 output},
  "validation": {Agent 4 output},
  "workflow_metadata": {
    "total_time_ms": 1952,
    "agents_executed": ["understanding", "retrieval", "reasoning", "validation"]
  }
}
```

**Processing Logic:**
```
1. Extract key data from each agent
2. Create decision_id: "DEC-{date}-{sequence}"
3. Aggregate confidence: average of all agent confidences
4. Check validation status:
   - if ESCALATE: mark priority = URGENT
   - if REJECTED: include violation details
   - if APPROVED: proceed with recommendation
5. Add metadata: timestamp, model info, inference time
6. Structure output JSON
```

**Output Format (Final):**
```json
{
  "decision_id": "DEC-20260915-001847",
  "timestamp": "2026-09-15T14:32:01Z",
  "user_query": "Reactor-4 pressure is 4.2 bar...",
  
  "equipment": "reactor-4",
  "current_state": {
    "pressure_bar": 4.2,
    "safe_range_bar": "3.5-5.0",
    "last_service_date": "2026-03-15",
    "service_interval_months": 6,
    "status": "Approaching maintenance window"
  },
  
  "analysis": {
    "pressure_assessment": "SAFE",
    "maintenance_urgency": "PLANNED (not immediate)",
    "risk_level": "LOW to MEDIUM (trending upward)",
    "cost_estimate_inr": 35000,
    "downtime_estimate_hours": 2.5
  },
  
  "recommendation": {
    "action": "Schedule maintenance",
    "timing": "Next Tuesday-Wednesday (2 weeks)",
    "rationale": "Proactive maintenance before pressure exceeds safe limits",
    "risk_if_delayed": "Pressure may exceed safe range in 4 weeks"
  },
  
  "validation": {
    "status": "APPROVED",
    "compliance_score": 98,
    "violations": [],
    "warnings": []
  },
  
  "metadata": {
    "overall_confidence": 0.91,
    "reasoning_chain_length": 5,
    "total_inference_time_ms": 1952,
    "model_used": "mistral-7b",
    "agents_executed": ["understanding", "retrieval", "reasoning", "validation", "decision"],
    "agents_failed": []
  },
  
  "audit_trail": {
    "user_id": "eng_supervisor_1",
    "request_timestamp": "2026-09-15T14:32:00Z",
    "response_timestamp": "2026-09-15T14:32:02Z",
    "processing_time_sec": 2.0
  }
}
```

**Timeout:** None (final synthesis)  
**Status:** Always SUCCESS (if any prior agent failed, noted in audit_trail)

---

## SECTION 7: CODE TEMPLATES (Copy-Paste Ready)

### 7.1 requirements.txt (CRITICAL)

```txt
# Core ML & LLM
ollama==0.1.0
langchain==0.1.5
faiss-cpu==1.7.4
sentence-transformers==2.2.2
torch==2.0.1
numpy==1.24.3

# Web API
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.4.2
python-multipart==0.0.6

# UI
streamlit==1.28.1
pandas==2.1.1

# Data Processing
PyPDF2==3.0.1
python-docx==0.8.11
openpyxl==3.1.2
aiofiles==23.2.1

# Utilities
python-dotenv==1.0.0
requests==2.31.0
aiohttp==3.9.0

# Async
asyncio-contextmanager==1.0.0

# JSON & Validation
pyyaml==6.0.1
jsonschema==4.19.1

# Logging
python-json-logger==2.0.7

# Production
cryptography==41.0.4

# Testing
pytest==7.4.2
pytest-asyncio==0.21.1
black==23.10.1
mypy==1.6.1
```

### 7.2 config/settings.py

```python
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Centralized configuration"""
    
    # LLM Configuration
    LLM_MODEL: str = "mistral"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MAX_TOKENS: int = 500
    LLM_TEMPERATURE: float = 0.3
    LLM_TIMEOUT_SEC: int = 5
    
    # Embedding & Vector Store
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_STORE_PATH: str = "data/embeddings_index.faiss"
    VECTOR_SEARCH_TOP_K: int = 5
    
    # API Configuration
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    API_TITLE: str = "MRPL Agentic Workbench"
    API_VERSION: str = "1.0.0"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_PER_HOUR: int = 100
    
    # Security
    MAX_QUERY_LENGTH: int = 2000
    INPUT_VALIDATION_ENABLED: bool = True
    
    # Timeouts
    AGENT_TIMEOUT_SEC: int = 5
    WORKFLOW_TIMEOUT_SEC: int = 20
    REQUEST_TIMEOUT_SEC: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    AUDIT_LOG_PATH: str = "data/audit_logs/decisions.jsonl"
    
    # Business Rules
    MAX_RECOMMENDATION_COST_INR: float = 100000
    MAX_DOWNTIME_HOURS: float = 4
    SAFETY_MARGIN_PERCENT: float = 5
    
    # Data Paths
    SAMPLE_DOCS_PATH: str = "data/sample_docs"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 7.3 agents/base_agent.py

```python
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Provides: timeout enforcement, error handling, logging, structured I/O
    """
    
    def __init__(self, name: str, timeout_sec: int = 5):
        self.name = name
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent with timeout and error handling.
        Returns: structured output dict with 'status' field (SUCCESS/FAILED)
        """
        start_time = datetime.utcnow()
        
        try:
            # Run agent with timeout
            result = await asyncio.wait_for(
                self._run(input_data),
                timeout=self.timeout_sec
            )
            
            # Add metadata
            result["status"] = result.get("status", "SUCCESS")
            result["agent"] = self.name
            result["execution_time_ms"] = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            
            self.logger.info(f"✓ {self.name} succeeded ({result['execution_time_ms']}ms)")
            return result
        
        except asyncio.TimeoutError:
            self.logger.error(f"✗ {self.name} timeout after {self.timeout_sec}s")
            return {
                "error": f"{self.name} timeout after {self.timeout_sec}s",
                "status": "TIMEOUT",
                "agent": self.name
            }
        
        except Exception as e:
            self.logger.error(f"✗ {self.name} failed: {str(e)}")
            return {
                "error": str(e),
                "status": "FAILED",
                "agent": self.name
            }
    
    @abstractmethod
    async def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Override in subclass. Return dict with 'status' field."""
        pass
```

### 7.4 orchestrator/workflow.py

```python
import logging
from typing import Dict, Any
from agents.query_understanding import QueryUnderstandingAgent
from agents.retrieval_agent import RetrievalAgent
from agents.reasoning_agent import ReasoningAgent
from agents.validation_agent import ValidationAgent
from agents.decision_agent import DecisionAgent
from orchestrator.logging import log_decision

class AgentOrchestrator:
    """Manages multi-agent workflow execution"""
    
    def __init__(self):
        self.logger = logging.getLogger("Orchestrator")
        
        # Initialize agents
        self.agents = {
            "understanding": QueryUnderstandingAgent(),
            "retrieval": RetrievalAgent(),
            "reasoning": ReasoningAgent(),
            "validation": ValidationAgent(),
            "decision": DecisionAgent(),
        }
    
    async def run_workflow(self, query: str, user_id: str = "unknown") -> Dict[str, Any]:
        """
        Execute complete workflow: Understanding → Retrieval → Reasoning → Validation → Decision
        """
        
        self.logger.info(f"Starting workflow for user={user_id}, query={query[:50]}...")
        
        try:
            # Stage 1: Understanding
            understanding = await self.agents["understanding"].execute({"query": query})
            if understanding["status"] != "SUCCESS":
                return understanding
            
            # Stage 2: Retrieval
            retrieval = await self.agents["retrieval"].execute({
                "equipment": understanding.get("equipment"),
                "queries": [understanding.get("intent", ""), query]
            })
            if retrieval["status"] not in ["SUCCESS", "PARTIAL"]:
                return retrieval
            
            # Stage 3: Reasoning (LLM)
            reasoning = await self.agents["reasoning"].execute({
                "query": query,
                "context_documents": retrieval.get("documents", []),
                "understanding": understanding
            })
            if reasoning["status"] != "SUCCESS":
                return reasoning
            
            # Stage 4: Validation
            validation = await self.agents["validation"].execute({
                "recommendation": reasoning,
                "context": understanding.get("constraints", {})
            })
            # Validation always returns status SUCCESS (reports violations within)
            
            # Stage 5: Decision (Synthesis)
            decision = await self.agents["decision"].execute({
                "understanding": understanding,
                "retrieval": retrieval,
                "reasoning": reasoning,
                "validation": validation,
                "user_id": user_id
            })
            
            # Log decision
            log_decision(decision, user_id)
            
            self.logger.info(f"✓ Workflow completed: {decision.get('decision_id')}")
            return decision
        
        except Exception as e:
            self.logger.error(f"✗ Workflow failed: {str(e)}")
            return {
                "error": str(e),
                "status": "WORKFLOW_FAILED"
            }
```

### 7.5 api/main.py

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
from orchestrator.workflow import AgentOrchestrator
from api.middleware import sanitize_input, check_rate_limit
from config.settings import settings

# Setup logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION
)

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Initialize orchestrator
orchestrator = AgentOrchestrator()

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = "unknown"

class QueryResponse(BaseModel):
    decision_id: str
    recommendation: dict
    confidence: float
    inference_time_ms: int

# Endpoints
@app.post("/analyze", response_model=QueryResponse)
async def analyze_query(request: QueryRequest):
    """Analyze maintenance query and return recommendation"""
    
    try:
        # Validate input
        query = sanitize_input(request.query, settings.MAX_QUERY_LENGTH)
        
        # Check rate limit
        allowed = await check_rate_limit(request.user_id)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Run workflow
        result = await orchestrator.run_workflow(query, request.user_id)
        
        if result.get("status") != "SUCCESS":
            raise HTTPException(status_code=500, detail=result.get("error"))
        
        return QueryResponse(
            decision_id=result.get("decision_id"),
            recommendation=result.get("recommendation"),
            confidence=result.get("metadata", {}).get("overall_confidence", 0.0),
            inference_time_ms=result.get("metadata", {}).get("total_inference_time_ms", 0)
        )
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "OK", "service": "MRPL Agentic Workbench"}

# Run: uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 7.6 ui/streamlit_app.py

```python
import streamlit as st
import json
import httpx
from datetime import datetime

st.set_page_config(page_title="MRPL Agentic Workbench", layout="wide")

st.title("🛢️ MRPL Agentic Workbench")
st.markdown("Autonomous maintenance decision system for Mangalore Refinery")

# Sidebar
st.sidebar.header("Configuration")
api_url = st.sidebar.text_input("API URL", value="http://localhost:8000")
user_id = st.sidebar.text_input("User ID", value="engineer_1")

# Main area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Enter Maintenance Query")
    query = st.text_area(
        "Ask about equipment maintenance:",
        height=120,
        placeholder="Example: Reactor-4 pressure is 4.2 bar, last serviced 6 months ago. Budget is ₹50K. When should I schedule maintenance?"
    )

with col2:
    st.subheader("Equipment Reference")
    st.info("""
    Available Equipment:
    - reactor-4
    - compressor-B
    - pump-A
    - exchanger-C
    - separator-D
    """)

# Submit button
if st.button("Analyze Query", type="primary"):
    if not query.strip():
        st.error("Please enter a query")
    else:
        with st.spinner("Analyzing..."):
            try:
                # Call API
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{api_url}/analyze",
                        json={"query": query, "user_id": user_id}
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Display results
                    st.success("Analysis Complete")
                    
                    # Key metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Decision ID", result["decision_id"][:15] + "...")
                    with col2:
                        st.metric("Confidence", f"{result['confidence']*100:.0f}%")
                    with col3:
                        st.metric("Inference Time", f"{result['inference_time_ms']}ms")
                    with col4:
                        st.metric("Status", "✓ Approved")
                    
                    # Recommendation
                    st.subheader("Recommendation")
                    rec = result.get("recommendation", {})
                    st.write(f"**Action:** {rec.get('action')}")
                    st.write(f"**Timing:** {rec.get('timing')}")
                    st.write(f"**Reason:** {rec.get('rationale')}")
                    
                    # Full response (JSON)
                    st.subheader("Full Response (JSON)")
                    st.json(result)
                
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.write(response.text)
            
            except Exception as e:
                st.error(f"Connection Error: {str(e)}")
                st.info("Make sure API is running: `python api/main.py`")

# Footer
st.divider()
st.caption(f"MRPL Agentic Workbench | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
```

---

## SECTION 8: DATA FORMAT SPECIFICATIONS

### 8.1 equipment_specs.json

```json
{
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
      "typical_service_cost_inr": 35000,
      "typical_service_downtime_hours": 2.5,
      "last_major_inspection": "2026-03-15",
      "next_scheduled_service": "2026-09-15"
    },
    {
      "id": "compressor-B",
      "name": "Compressor-B",
      "type": "compressor",
      "capacity_ton_per_hour": 150,
      "material": "cast_iron",
      "design_pressure_bar": 8.0,
      "design_temperature_celsius": 80,
      "safe_operating_range_bar": [6.0, 8.0],
      "installed_date": "2019-06-20",
      "designed_lifespan_years": 15,
      "maintenance_interval_months": 12,
      "typical_service_cost_inr": 28000,
      "typical_service_downtime_hours": 3.0,
      "last_major_inspection": "2025-06-20",
      "next_scheduled_service": "2026-06-20"
    }
  ]
}
```

### 8.2 maintenance_schedule.csv

```csv
equipment_id,equipment_name,service_interval_months,last_service_date,typical_cost_inr,typical_downtime_hours,compliance_status,next_due_date
reactor-4,Reactor-4,6,2026-03-15,35000,2.5,ON_SCHEDULE,2026-09-15
compressor-B,Compressor-B,12,2025-06-20,28000,3.0,ON_SCHEDULE,2026-06-20
pump-A,Pump-A,6,2026-02-10,15000,1.5,APPROACHING,2026-08-10
exchanger-C,Heat Exchanger-C,12,2025-12-01,42000,4.0,COMING_DUE,2026-12-01
separator-D,Separator-D,24,2024-06-15,55000,5.5,OVERDUE,2026-06-15
```

### 8.3 safety_protocols.json

```json
{
  "safety_rules": [
    {
      "rule_id": "PRESSURE_LIMIT",
      "description": "Equipment pressure must not exceed design specification",
      "applies_to": ["reactor-4", "compressor-B", "pump-A"],
      "threshold_percent_of_max": 95,
      "action_if_violated": "IMMEDIATE_ESCALATION",
      "notification_level": "CRITICAL"
    },
    {
      "rule_id": "MAINTENANCE_INTERVAL",
      "description": "Equipment must receive scheduled maintenance",
      "applies_to": ["all"],
      "grace_period_days": 14,
      "action_if_violated": "ESCALATION",
      "notification_level": "HIGH"
    },
    {
      "rule_id": "DOWNTIME_LIMIT",
      "description": "Maintenance downtime cannot exceed specified limit",
      "applies_to": ["all"],
      "max_downtime_hours": 4,
      "action_if_violated": "WARNING",
      "notification_level": "MEDIUM"
    }
  ]
}
```

### 8.4 Audit Log Entry Format (decisions.jsonl)

```json
{
  "timestamp": "2026-09-15T14:32:01Z",
  "decision_id": "DEC-20260915-001847",
  "user_id": "eng_supervisor_1",
  "equipment": "reactor-4",
  "query_hash": "abc123def456",
  "recommendation_action": "Schedule maintenance",
  "recommendation_timing": "Next Tuesday-Wednesday",
  "cost_estimate_inr": 35000,
  "validation_status": "APPROVED",
  "compliance_score": 98,
  "confidence": 0.91,
  "inference_time_ms": 1952,
  "model_used": "mistral-7b",
  "agents_executed": ["understanding", "retrieval", "reasoning", "validation", "decision"],
  "agents_failed": []
}
```

---

## SECTION 9: 36-HOUR EXECUTION PLAN

### 9.1 Hour-by-Hour Breakdown

**HOURS 0-2: Foundation (Setup)**

**Goals:**
- Project created
- LLM running locally
- Can test ollama connectivity

**Deliverables:**
- GitHub repo initialized
- requirements.txt created
- Mistral-7B downloaded + running
- Health check passes

**Tasks:**
```
1. Initialize repo: git init + .gitignore
2. Create folder structure: mkdir -p config core agents orchestrator api ui data tests scripts
3. Create requirements.txt (from template in Section 7.1)
4. Install dependencies: pip install -r requirements.txt
5. Install ollama: curl https://ollama.ai/install.sh | sh
6. Pull Mistral model: ollama pull mistral
7. Start ollama server: ollama serve (background)
8. Test connectivity: curl http://localhost:11434/api/generate
9. Create config/settings.py (from template in Section 7.2)
10. Commit: "Step 1: Foundation + ollama setup"
```

**Exit Criteria:**
- Mistral responds to test query <3 seconds
- No errors in ollama logs
- All dependencies install successfully

---

**HOURS 2-6: Data Setup**

**Goals:**
- Synthetic MRPL documents created
- FAISS vector store built + working
- Can search documents

**Deliverables:**
- 5 sample documents in data/sample_docs/
- FAISS index built and saved
- Vector search working

**Tasks:**
```
1. Create data/sample_docs/ folder
2. Create generate_sample_data.py script:
   a. Generate equipment_specs.json (5 equipment types)
   b. Generate maintenance_schedule.csv (realistic data)
   c. Generate service_logs.txt (narrative format)
   d. Generate safety_protocols.json (business rules)
   e. Generate cost_estimates.csv (pricing)
3. Create core/document_loader.py:
   a. Load JSON/CSV/TXT files
   b. Parse into structured format
   c. Test: can load all 5 documents without error
4. Create core/vector_store.py:
   a. Use sentence-transformers to embed documents
   b. Build FAISS index
   c. Save index to data/embeddings_index.faiss
   d. Test: can search for "maintenance reactor-4", get relevant docs
5. Run generate_sample_data.py: python scripts/generate_sample_data.py
6. Test vector search: python -c "from core.vector_store import VectorStore; vs = VectorStore(); results = vs.search('maintenance'); print(results)"
7. Commit: "Step 2: Data setup + FAISS indexing"
```

**Exit Criteria:**
- All 5 documents load without error
- FAISS index built successfully
- Search returns relevant documents (top-1 similarity >0.85)

---

**HOURS 6-12: Core Agents (3/5)**

**Goals:**
- 3 core agents working independently
- Each has unit tests
- End-to-end pipeline: query → understanding → retrieval → reasoning

**Deliverables:**
- agents/base_agent.py (abstract base)
- agents/query_understanding.py (Agent 1)
- agents/retrieval_agent.py (Agent 2)
- agents/reasoning_agent.py (Agent 3)
- tests/test_agents.py (unit tests)

**Tasks:**
```
1. Create agents/base_agent.py (from template Section 7.5):
   a. Abstract _run() method
   b. Timeout enforcement (asyncio.wait_for)
   c. Error handling (try-catch all exceptions)
   d. Logging (all decisions to logger)
   e. Fallback behavior if timeout

2. Create agents/query_understanding.py (Agent 1):
   a. Parse query: extract intent, equipment, constraints
   b. Output: structured JSON with confidence
   c. Test: 5 sample queries → verify output format correct

3. Create agents/retrieval_agent.py (Agent 2):
   a. Take equipment + search queries
   b. Call VectorStore.search()
   c. Return top-K documents
   d. Test: search "reactor-4 maintenance" → verify docs returned

4. Create agents/reasoning_agent.py (Agent 3):
   a. Format prompt: query + context documents
   b. Call ollama (POST to http://localhost:11434/api/generate)
   c. Parse LLM response JSON
   d. Extract reasoning steps + recommendation
   e. Test: full reasoning on sample case → verify output makes sense

5. Create tests/test_agents.py:
   a. Test Agent 1: query understanding accuracy
   b. Test Agent 2: document retrieval relevance
   c. Test Agent 3: LLM response parsing
   d. Run: pytest tests/test_agents.py (all pass)

6. Test end-to-end:
   a. Sample query → Agent 1 → Agent 2 → Agent 3
   b. Verify output flows correctly between agents
   c. Measure latency (target <5 sec per agent)

7. Commit: "Step 3: Agents 1-3 (query, retrieval, reasoning)"
```

**Exit Criteria:**
- All 3 agents implemented
- Unit tests pass (pytest)
- End-to-end pipeline works
- Latency <6 seconds for full pipeline

---

**HOURS 12-18: Agents 4-5 + Orchestration**

**Goals:**
- Complete agent set (5/5)
- Orchestrator managing workflow
- Full end-to-end tested

**Deliverables:**
- agents/validation_agent.py (Agent 4)
- agents/decision_agent.py (Agent 5)
- orchestrator/workflow.py (orchestration)
- orchestrator/logging.py (audit trail)
- tests/test_workflow.py (integration tests)

**Tasks:**
```
1. Create agents/validation_agent.py (Agent 4):
   a. Input: recommendation from Agent 3
   b. Apply 5 business rules (cost, downtime, safety, compliance, historical)
   c. For each rule: check condition, flag violations
   d. Compute compliance_score: (rules_passed / total) * 100
   e. Output: approval status + violations
   f. Test: 3 sample recommendations → verify validations correct

2. Create agents/decision_agent.py (Agent 5):
   a. Input: all 4 agent outputs
   b. Merge results
   c. Create final decision JSON (from template Section 6.5)
   d. Add metadata: timestamp, decision_id, confidence
   e. Output: structured final recommendation
   f. Test: full output JSON well-formed, parseable

3. Create orchestrator/workflow.py (from template Section 7.4):
   a. Initialize all 5 agents
   b. Implement run_workflow() method:
      - Agent 1: understanding
      - Agent 2: retrieval
      - Agent 3: reasoning
      - Agent 4: validation
      - Agent 5: decision
   c. Error handling: if any agent fails, return error
   d. Timeout management: max 20 sec total workflow
   e. Test: run full workflow on 3 sample queries

4. Create orchestrator/logging.py:
   a. log_decision() function: append to JSONL
   b. Immutable log (append-only, no modifications)
   c. Log format (from Section 8.4)
   d. Test: decisions logged correctly

5. Create tests/test_workflow.py:
   a. Test full workflow end-to-end
   b. Test error handling (simulate agent failure)
   c. Test timeout enforcement
   d. Test audit logging
   e. Run: pytest tests/test_workflow.py

6. Test complete pipeline:
   a. 3 sample queries → full workflow
   b. Verify all decisions logged
   c. Measure total latency (target <6 sec per query)
   d. Verify output quality (reasoning visible, recommendations actionable)

7. Commit: "Step 4: Agents 4-5 + Orchestrator (complete chain)"
```

**Exit Criteria:**
- All 5 agents implemented + working
- Orchestrator manages workflow correctly
- Full pipeline tested end-to-end
- Audit log appends all decisions
- Latency <6 seconds per query

---

**HOURS 18-24: API + Integration**

**Goals:**
- REST API endpoint working
- Rate limiting + input validation
- Security hardening complete

**Deliverables:**
- api/main.py (FastAPI server)
- api/models.py (Pydantic schemas)
- api/middleware.py (rate limiting + validation)
- tests/test_security.py (security tests)

**Tasks:**
```
1. Create api/models.py:
   a. Pydantic QueryRequest: {query: str, user_id: str}
   b. Pydantic QueryResponse: {decision_id, recommendation, confidence, time_ms}
   c. Test: models validate input/output

2. Create api/middleware.py:
   a. sanitize_input(): XML escape, length check, injection detection
   b. check_rate_limit(): track requests per client, enforce limit
   c. Middleware for request/response logging
   d. Test: rate limiting blocks 11th request
   e. Test: injection attempts rejected

3. Create api/main.py (from template Section 7.5):
   a. FastAPI app
   b. POST /analyze endpoint: accept query, return decision
   c. GET /health endpoint: returns OK
   d. Middleware stack:
      - CORS (allow all for demo)
      - Rate limiting
      - Input validation
      - Logging
   e. Error handling: malformed requests return error JSON (never crash)
   f. Test:
      - POST /analyze with sample query → returns decision JSON
      - Rate limiter works: 11th request rejected
      - Malformed request returns error (not crash)
      - /health returns OK

4. Create tests/test_security.py:
   a. Test prompt injection blocked
   b. Test SQL injection patterns rejected
   c. Test length limits enforced
   d. Test rate limiting works
   e. Run: pytest tests/test_security.py

5. Start API server:
   a. uvicorn api.main:app --host 0.0.0.0 --port 8000
   b. Verify starts without errors
   c. Verify can POST /analyze, receive response

6. Integration testing:
   a. Query via API → orchestrator → decision → return response
   b. Verify latency: API call + processing <6 sec total
   c. Verify audit log captures all API calls

7. Commit: "Step 5: API + middleware (production-ready)"
```

**Exit Criteria:**
- FastAPI server runs on port 8000
- POST /analyze works, returns structured response
- Rate limiting enforced
- Input validation blocks malicious inputs
- No unhandled exceptions (all errors return JSON)

---

**HOURS 24-30: UI + Deployment**

**Goals:**
- Streamlit UI working
- Docker container builds + runs
- End-to-end demo ready

**Deliverables:**
- ui/streamlit_app.py (from template Section 7.6)
- Dockerfile
- docker-compose.yml
- .env.example

**Tasks:**
```
1. Create ui/streamlit_app.py (from template Section 7.6):
   a. Title + description
   b. Textarea for query input
   c. Submit button
   d. Display structured output (decision JSON)
   e. Show reasoning chain
   f. Display last 10 audit log entries
   g. Test: can submit query via UI, see response

2. Create Dockerfile:
   a. Base image: python:3.10-slim
   b. Install system dependencies (gcc, etc.)
   c. Copy requirements.txt, install pip packages
   d. Copy code
   e. Expose ports: 8000 (API) + 8501 (Streamlit)
   f. Start script: run ollama server + FastAPI + Streamlit
   g. Test: docker build succeeds

3. Create docker-compose.yml:
   a. Services: ollama, api, streamlit
   b. Volume mounts: data/ (persistence)
   c. Environment: .env file
   d. Networks: all services can communicate
   e. Test: docker-compose up (all services start)

4. Create .env.example:
   a. LLM_MODEL=mistral
   b. LLM_BASE_URL=http://localhost:11434
   c. API_PORT=8000
   d. All config variables from settings.py
   e. Usage: cp .env.example .env, then update

5. Update docker-compose to use ollama service:
   a. Don't rely on pre-installed ollama
   b. Pull official ollama image
   c. Pre-download model in Dockerfile or docker-compose

6. Test deployment:
   a. docker-compose up
   b. Wait for all services to start
   c. Open Streamlit: http://localhost:8501
   d. Submit sample query via UI
   e. Verify response appears
   f. Check API directly: curl http://localhost:8000/health

7. Test end-to-end in container:
   a. Query via Streamlit UI
   b. Verify orchestrator executes
   c. Verify audit log writes
   d. No errors in container logs

8. Commit: "Step 6: UI + Deployment (Docker ready)"
```

**Exit Criteria:**
- Streamlit app loads at http://localhost:8501
- Can submit query via UI
- Docker container builds without errors
- docker-compose up starts all services
- Full end-to-end works in container

---

**HOURS 30-36: Polish + Documentation + Pre-Flight**

**Goals:**
- Production-ready code
- Comprehensive documentation
- Pre-deployment validation complete

**Deliverables:**
- README.md (complete)
- ARCHITECTURE.md (design doc)
- Code comments + type hints
- Pre-flight checklist (all passing)
- Examples + demo docs

**Tasks:**
```
1. Code Quality:
   a. Run black: black . (format all code)
   b. Run mypy: mypy . (type checking, 100% coverage)
   c. Run pytest: pytest tests/ (all tests pass)
   d. Remove debug code + print statements
   e. Remove TODO/FIXME comments
   f. Check: no hardcoded secrets in code

2. Documentation:
   a. Write README.md:
      - What the system does (1 paragraph)
      - Setup instructions (step-by-step)
      - Architecture diagram (ASCII art)
      - Example queries + expected outputs
      - Troubleshooting section
   b. Write ARCHITECTURE.md:
      - System design diagram
      - Component descriptions
      - Data flow
      - Technology stack rationale
   c. Add inline comments:
      - Complex logic explained
      - Non-obvious decisions justified
   d. Verify all config options documented in .env.example

3. Examples:
   a. Create EXAMPLES.md with 5 sample queries:
      1. Maintenance scheduling
      2. Risk assessment
      3. Cost optimization
      4. Compliance checking
      5. Equipment status
   b. For each example: show input + expected output
   c. Add demo walkthrough (screenshot descriptions)

4. Pre-Deployment Checklist:
   ```
   Code Quality:
   [ ] black . (all formatted)
   [ ] mypy . (100% type coverage)
   [ ] pytest tests/ (all pass)
   [ ] No hardcoded secrets
   [ ] No TODO/FIXME comments
   [ ] No print() statements
   
   Dependencies:
   [ ] requirements.txt complete
   [ ] All packages pinned with versions
   [ ] pip install -r requirements.txt (no errors)
   
   Error Handling:
   [ ] All async calls have try-catch
   [ ] All endpoints return proper JSON (never crash)
   [ ] Logging covers all decision paths
   [ ] Rate limiting works (tested)
   [ ] Timeouts enforced (tested)
   
   Security:
   [ ] Input validation prevents injection
   [ ] No secrets in code or Docker
   [ ] Rate limiting enforced
   [ ] Audit log appends correctly
   
   Deployment:
   [ ] Docker builds: docker build .
   [ ] docker-compose up (all services start)
   [ ] Ollama available in container
   [ ] API responds: curl http://localhost:8000/health
   [ ] Streamlit loads: http://localhost:8501
   
   Testing:
   [ ] End-to-end test: 3 queries → all succeed
   [ ] Performance: latency <6 sec per query
   [ ] Stress test: 50 concurrent requests handled
   [ ] Security: prompt injection blocked
   [ ] Audit log: all decisions logged
   
   Documentation:
   [ ] README.md complete
   [ ] ARCHITECTURE.md detailed
   [ ] EXAMPLES.md with 5 samples
   [ ] All config documented
   [ ] Inline comments on complex logic
   
   Git:
   [ ] All code committed
   [ ] No large files in git
   [ ] .gitignore correct (excludes data/, logs/)
   [ ] History clean (no debug commits)
   [ ] Final commit: "Production ready"
   ```

5. Final Testing:
   a. End-to-end: 3 queries → responses correct
   b. Performance: measure latency per query
   c. Stress: 50 concurrent requests
   d. Security: try injection attacks → all blocked
   e. Container: docker-compose test run
   f. Documentation: README walkable by someone new

6. Git Finalization:
   a. Clean up all branches
   b. Final commit: "Production ready"
   c. Tag release: git tag v1.0.0
   d. Verify: GitHub shows all files, README prominent

7. Commit: "Step 7: Production ready (documentation + final checks)"
```

**Exit Criteria:**
- All checklist items passing
- Comprehensive documentation complete
- Code is clean + fully typed
- End-to-end demo works flawlessly
- Docker deployment tested
- Ready for submission

---

## SECTION 10: TESTING & VALIDATION

### 10.1 Unit Testing Requirements

**Test: QueryUnderstandingAgent**
```python
# tests/test_agents.py
async def test_query_understanding_maintenance():
    agent = QueryUnderstandingAgent()
    result = await agent.execute({
        "query": "Reactor-4 pressure 4.2, last serviced 6 months, budget 50K. When schedule?"
    })
    assert result["status"] == "SUCCESS"
    assert result["intent"] == "schedule_maintenance"
    assert result["equipment"] == "reactor-4"
    assert result["confidence"] > 0.8

async def test_query_understanding_risk():
    agent = QueryUnderstandingAgent()
    result = await agent.execute({
        "query": "Compressor making noise. Risk?"
    })
    assert result["intent"] == "risk_assessment"
```

**Test: RetrievalAgent**
```python
async def test_retrieval_documents():
    agent = RetrievalAgent()
    result = await agent.execute({
        "equipment": "reactor-4",
        "queries": ["maintenance schedule"]
    })
    assert result["status"] in ["SUCCESS", "PARTIAL"]
    assert len(result["documents"]) > 0
    assert result["documents"][0]["equipment"] == "reactor-4"
```

**Test: ReasoningAgent**
```python
async def test_reasoning_inference():
    agent = ReasoningAgent()
    result = await agent.execute({
        "query": "When should I service reactor-4?",
        "context_documents": [sample_equipment_specs],
        "understanding": {"equipment": "reactor-4", "intent": "schedule_maintenance"}
    })
    assert result["status"] == "SUCCESS"
    assert "reasoning" in result
    assert len(result["reasoning"]) > 0
    assert result["confidence"] > 0.7
```

**Test: Security**
```python
# tests/test_security.py
def test_input_sanitization():
    # Should reject SQL injection
    malicious = "'; DROP TABLE equipment; --"
    with pytest.raises(ValueError):
        sanitize_input(malicious)
    
    # Should reject script injection
    script = "<script>alert('xss')</script>"
    with pytest.raises(ValueError):
        sanitize_input(script)
    
    # Should accept valid query
    valid = "What's the status of reactor-4?"
    result = sanitize_input(valid)
    assert len(result) > 0

def test_rate_limiting():
    limiter = RateLimiter(max_per_minute=10)
    # Should allow 10 requests
    for i in range(10):
        assert limiter.check("client1") == True
    # Should reject 11th
    assert limiter.check("client1") == False
```

### 10.2 Integration Testing

**Test: Full Workflow**
```python
# tests/test_workflow.py
async def test_full_workflow():
    orchestrator = AgentOrchestrator()
    query = "Reactor-4 pressure 4.2, last serviced 6 months, budget ₹50K. When?"
    
    result = await orchestrator.run_workflow(query, user_id="test_user")
    
    # Verify result structure
    assert result["status"] == "SUCCESS"
    assert "decision_id" in result
    assert "recommendation" in result
    assert "metadata" in result
    assert result["metadata"]["overall_confidence"] > 0.7
    
    # Verify all agents executed
    assert len(result["metadata"]["agents_executed"]) == 5
    assert len(result["metadata"]["agents_failed"]) == 0

async def test_workflow_with_agent_failure():
    # Simulate Agent 3 (reasoning) failure
    # Should return error gracefully
    pass

async def test_workflow_timeout():
    # If workflow exceeds 20 sec, should timeout
    pass
```

### 10.3 Performance Testing

**Latency Benchmarks (Target: <6 sec per query)**
```
Agent 1 (Understanding): <500ms
Agent 2 (Retrieval): <100ms
Agent 3 (Reasoning): <1850ms  [largest: LLM inference]
Agent 4 (Validation): <50ms
Agent 5 (Decision): <100ms
Total: <2600ms (well under 6 sec target)
```

**Stress Test (50 concurrent requests)**
```
All requests should complete within timeout
No queue overflow
No memory leaks
All audit logs written correctly
```

---

## SECTION 11: DEPLOYMENT CHECKLIST

### 11.1 Pre-Submission Checklist

```
PRODUCTION READINESS CHECKLIST

[ ] CODE QUALITY
  [ ] Black formatting: black . (0 changes)
  [ ] Mypy typing: mypy . (0 errors, 100% coverage)
  [ ] Pytest: pytest tests/ (all pass, no warnings)
  [ ] No hardcoded secrets
  [ ] No TODO/FIXME comments
  [ ] No print() statements (use logging only)
  [ ] All error paths return proper JSON
  [ ] No unhandled exceptions

[ ] DEPENDENCIES
  [ ] requirements.txt exists
  [ ] All packages pinned with exact versions
  [ ] pip install -r requirements.txt (success, no warnings)
  [ ] All imports work (pip check)
  [ ] No version conflicts

[ ] SECURITY & VALIDATION
  [ ] Input sanitization: sanitize_input() tested
  [ ] Prompt injection: blocked (tested)
  [ ] SQL injection: blocked (tested)
  [ ] Length validation: <2000 chars enforced
  [ ] Rate limiting: 10 req/min enforced (tested)
  [ ] Timeout enforcement: 5 sec per agent (tested)
  [ ] No secrets in code or Docker

[ ] LOGGING & AUDIT
  [ ] Audit log path exists: data/audit_logs/
  [ ] Log format is JSONL (one JSON per line)
  [ ] Append-only (no overwrites)
  [ ] All decisions logged with metadata
  [ ] Timestamps in ISO format

[ ] DEPLOYMENT FILES
  [ ] Dockerfile exists
  [ ] docker-compose.yml exists
  [ ] .env.example exists (all config vars documented)
  [ ] .gitignore includes: data/, logs/, *.pyc, __pycache__/
  [ ] README.md complete (setup + architecture + examples)
  [ ] ARCHITECTURE.md detailed
  [ ] EXAMPLES.md with 5+ sample queries

[ ] DOCKER VERIFICATION
  [ ] Docker builds: docker build . (success, no errors)
  [ ] docker-compose up (all services start)
  [ ] Ollama model available in container
  [ ] API responds: curl http://localhost:8000/health → OK
  [ ] Streamlit loads: http://localhost:8501
  [ ] Full query works end-to-end in container

[ ] TESTING
  [ ] Unit tests pass: pytest tests/test_agents.py
  [ ] Integration tests pass: pytest tests/test_workflow.py
  [ ] Security tests pass: pytest tests/test_security.py
  [ ] End-to-end test: 3 queries → all succeed
  [ ] Performance: measure latency per query (<6 sec)
  [ ] Stress test: 50 concurrent requests handled
  [ ] Rate limiting works: 11th request rejected
  [ ] Prompt injection blocked: malicious query rejected
  [ ] Audit log correct: all decisions logged

[ ] GIT REPOSITORY
  [ ] All code committed
  [ ] .gitignore working (data/ not in git)
  [ ] No large files in repo
  [ ] History clean (no debug/temp commits)
  [ ] README at root visible on GitHub
  [ ] Final commit message: "Production ready"

[ ] DOCUMENTATION
  [ ] README.md: what, how to setup, examples
  [ ] ARCHITECTURE.md: system design, technology, data flow
  [ ] EXAMPLES.md: 5+ real query examples
  [ ] .env.example: all config variables documented
  [ ] Inline comments: complex logic explained
  [ ] Type hints: 100% function coverage

[ ] DEMO READINESS
  [ ] Can run docker-compose up (no setup needed)
  [ ] Can submit query via Streamlit UI (works)
  [ ] Output displays correctly (JSON readable)
  [ ] Reasoning visible (step-by-step shown)
  [ ] No crashes during demo
  [ ] Latency acceptable (<6 sec per query)
  [ ] Audit log working (decisions logged)

[ ] FINAL CHECKS
  [ ] All agents implemented (5/5)
  [ ] Orchestrator working
  [ ] No external cloud APIs used (fully local)
  [ ] All decisions auditable
  [ ] Code production-grade quality
  [ ] Ready to present to MRPL
```

### 11.2 Submission Artifacts

**Required Files to Submit:**
```
GitHub Repository:
├── README.md                    ← First thing judges see
├── ARCHITECTURE.md              ← System design
├── EXAMPLES.md                  ← Sample queries
├── requirements.txt             ← Exact versions
├── .env.example                 ← Config template
├── Dockerfile                   ← Container
├── docker-compose.yml           ← Local deployment
├── config/                      ← Configuration
├── core/                        ← Core logic
├── agents/                      ← 5 agents
├── orchestrator/                ← Workflow
├── api/                         ← FastAPI
├── ui/                          ← Streamlit
├── data/sample_docs/            ← Sample data
├── tests/                       ← Test suite
└── scripts/                     ← Setup scripts
```

**How to Run:**
```
git clone <your-repo>
cd sih-26117-agentic-workbench
docker-compose up
# Open http://localhost:8501
# Submit query via Streamlit
```

---

## SECTION 12: FINAL NOTES

### 12.1 Key Success Factors

1. **Judges Must Understand in <60 Seconds**
   - No NLP domain knowledge required
   - Live demo shows clear value
   - Output is actionable

2. **Production-Grade Execution**
   - Error handling bulletproof
   - Logging comprehensive
   - Security hardened
   - Docker deployment works

3. **Uniqueness Stands Out**
   - <10 teams attempt this
   - Multi-agent reasoning is rare
   - FAANG interviewer will be impressed

4. **You Can Execute in 36 Hours**
   - Reuses NexusTiQ patterns (70%)
   - Clear milestones (7 stages)
   - No learning cliff at any stage

### 12.2 Common Pitfalls to Avoid

**Pitfall 1:** Complex AI, poor UX
- Solution: Simple Streamlit UI is fine
- Demo should be 2 minutes to understand

**Pitfall 2:** Code quality issues
- Solution: Run black, mypy, pytest before submit
- Production code = judges respect it

**Pitfall 3:** Incomplete documentation
- Solution: Write README, ARCHITECTURE, EXAMPLES
- Judges need to understand system without code review

**Pitfall 4:** Hardcoded secrets
- Solution: All config via .env
- Double-check before pushing to GitHub

**Pitfall 5:** Cloud API dependency
- Solution: Ensure everything runs locally
- No ollama connectivity = system down

### 12.3 Post-Submission

**After Submitting to SIH:**
- Monitor GitHub for any issues judges report
- Be ready to explain architecture to judges
- Prepare 2-3 min demo video (optional)
- Document any edge cases encountered

**For FAANG Interview:**
- Story: "Built multi-agent reasoning system for industrial operations"
- Show code quality + production thinking
- Discuss trade-offs (accuracy vs speed, scale considerations)
- Be ready to dive deep into any component

---

## END OF SPECIFICATION

**Document Version:** 1.0  
**Last Updated:** September 2026  
**Status:** Ready for Implementation  
**Estimated Effort:** 36 Hours  
**Target Submission:** September 20, 2026  

**This document is AI-agent friendly:**
- Structured sections with clear hierarchy
- Specific requirements (not vague)
- Code templates copy-paste ready
- Acceptance criteria objective
- Checklists verifiable

**Questions?** Re-read Section 3 (Architecture) or Section 6 (Components).

---

**Good luck. You've got this. 🚀**
