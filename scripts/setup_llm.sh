#!/bin/bash
# =============================================================================
# Install ollama and pull Mistral-7B for fully offline (sovereign) reasoning.
#
# This is the on-premise path described in the problem statement: once this
# script has run, LLM_PROVIDER=auto selects ollama first and NO data leaves
# the machine. Until then the workbench runs on its rule-based engine, or on
# a cloud provider if a key is configured.
#
# Usage:  bash scripts/setup_llm.sh
# Needs:  ~5 GB disk, ~8 GB RAM. Linux/macOS, or WSL2 on Windows.
# =============================================================================

set -euo pipefail

MODEL="${OLLAMA_MODEL:-mistral}"
BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

echo "=== MRPL Workbench: local LLM setup ==="
echo "Model: $MODEL"
echo ""

# ── 1. Install ollama ────────────────────────────────────────────────────────
if command -v ollama >/dev/null 2>&1; then
  echo "[1/4] ollama already installed: $(ollama --version 2>/dev/null || echo present)"
else
  echo "[1/4] Installing ollama..."
  if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew >/dev/null 2>&1; then
      brew install ollama
    else
      echo "  Homebrew not found. Install from https://ollama.com/download"
      exit 1
    fi
  else
    curl -fsSL https://ollama.com/install.sh | sh
  fi
fi

# ── 2. Start the daemon ──────────────────────────────────────────────────────
echo "[2/4] Ensuring ollama daemon is running..."
if curl -sf "$BASE_URL/api/tags" >/dev/null 2>&1; then
  echo "  Daemon already responding at $BASE_URL"
else
  ollama serve >/tmp/ollama.log 2>&1 &
  for _ in $(seq 1 30); do
    if curl -sf "$BASE_URL/api/tags" >/dev/null 2>&1; then break; fi
    sleep 1
  done
  if ! curl -sf "$BASE_URL/api/tags" >/dev/null 2>&1; then
    echo "  ERROR: daemon did not start. See /tmp/ollama.log"
    exit 1
  fi
  echo "  Daemon started."
fi

# ── 3. Pull the model ────────────────────────────────────────────────────────
echo "[3/4] Pulling $MODEL (~4 GB, one time)..."
ollama pull "$MODEL"

# ── 4. Verify ────────────────────────────────────────────────────────────────
echo "[4/4] Verifying the workbench can see it..."
python - <<'PYEOF'
from core.llm_engine import LLMEngine

engine = LLMEngine()
status = engine.available_providers()
print(f"  providers: {status}")
if status.get("ollama"):
    print(f"  ACTIVE ENGINE: {engine.resolve_provider()}")
    print("  Fully offline reasoning is now available.")
else:
    print("  WARNING: ollama still not visible to the app.")
    print("  Check OLLAMA_BASE_URL and OLLAMA_MODEL in your .env")
PYEOF

echo ""
echo "Done. Set LLM_PROVIDER=ollama in .env to pin it explicitly,"
echo "or leave LLM_PROVIDER=auto to prefer it automatically."
