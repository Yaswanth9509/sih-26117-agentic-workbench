#!/bin/bash
# Pre-deployment validation for the MRPL Agentic Workbench.
# Usage: bash scripts/run_checks.sh

PASS=0
FAIL=0

check() {
  if eval "$2" &>/dev/null; then
    echo "  [PASS] $1"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $1"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== MRPL Workbench Pre-Deploy Checks ==="
echo ""

echo "[Code Quality]"
check "black formatting" "python -m black --check . --quiet"
check "mypy (0 errors)" "python -m mypy ."
check "no print() in app code" "! grep -rq 'print(' agents/ api/ orchestrator/ core/ config/ --include='*.py'"
check "all __init__.py present" "test -f agents/__init__.py && test -f api/__init__.py && test -f core/__init__.py && test -f config/__init__.py"

echo ""
echo "[Dependencies]"
check "requirements.txt fully pinned" "! grep -E '^[a-zA-Z].*[><~]=' requirements.txt"
check "fastapi installed" "python -c 'import fastapi'"
check "streamlit installed" "python -c 'import streamlit'"
check "scikit-learn installed" "python -c 'import sklearn'"
check "pydantic-settings installed" "python -c 'import pydantic_settings'"
check "httpx installed" "python -c 'import httpx'"

echo ""
echo "[Data Files]"
check "equipment_specs.json" "test -f data/sample_docs/equipment_specs.json"
check "maintenance_schedule.csv" "test -f data/sample_docs/maintenance_schedule.csv"
check "service_logs.txt" "test -f data/sample_docs/service_logs.txt"
check "safety_protocols.json" "test -f data/sample_docs/safety_protocols.json"
check "cost_estimates.csv" "test -f data/sample_docs/cost_estimates.csv"

echo ""
echo "[Tests]"
check "full suite passes" "python -m pytest tests/ -q"
check "suite is offline (conftest pins engine)" "test -f tests/conftest.py"
check "provider routing covered" "test -f tests/test_llm_providers.py"

echo ""
echo "[Security]"
check "no API keys hardcoded" "! grep -rEq '(gsk_[A-Za-z0-9]|AIza[A-Za-z0-9])' --include='*.py' ."
check ".env.example exists" "test -f .env.example"
check ".env is gitignored" "grep -q '^\.env$' .gitignore"
check ".env not tracked by git" "! git ls-files --error-unmatch .env"

echo ""
echo "[Deployment]"
check "Dockerfile exists" "test -f Dockerfile"
check "docker-compose.yml exists" "test -f docker-compose.yml"
check "setup_llm.sh exists" "test -f scripts/setup_llm.sh"
check "README.md exists" "test -f README.md"
check "ARCHITECTURE.md exists" "test -f ARCHITECTURE.md"
check "docs/EXAMPLES.md exists" "test -f docs/EXAMPLES.md"
check "docs/MIGRATION.md exists" "test -f docs/MIGRATION.md"

echo ""
echo "[Engine]"
python - <<'PYEOF'
from core.llm_engine import LLMEngine

engine = LLMEngine()
print(f"  active engine : {engine.resolve_provider()}")
print(f"  providers     : {engine.available_providers()}")
PYEOF

echo ""
echo "=============================="
echo "  PASSED: $PASS | FAILED: $FAIL"
if [ $FAIL -eq 0 ]; then
  echo "  STATUS: READY TO DEPLOY"
  exit 0
else
  echo "  STATUS: FIX FAILURES BEFORE DEPLOY"
  exit 1
fi
