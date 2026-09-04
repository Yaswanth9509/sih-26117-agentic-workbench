"""
MRPL Agentic Workbench — Streamlit UI
Calls the FastAPI backend and displays structured decisions.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MRPL Agentic Workbench",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configurable so the UI can run split from the API (separate container/host).
#
# Default is 127.0.0.1, NOT localhost: on Windows "localhost" resolves to ::1
# first, and because uvicorn binds IPv4 only, httpx spends ~2s on a doomed
# IPv6 attempt before falling back - on every single call.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")


@st.cache_data(ttl=10, show_spinner=False)
def fetch_health() -> dict | None:
    """Backend health. Cached so it is not re-fetched on every rerun."""
    try:
        response = httpx.get(f"{API_URL}/health", timeout=3)
        if response.status_code == 200:
            return dict(response.json())
        return None
    except Exception:
        return None


def _safe_number(value: Any, default: float = 0.0) -> float:
    """
    ReasoningAgent normalises provider output before this page ever sees
    it, so this should never fire in practice - kept as an independent
    second layer so a future regression there degrades to a wrong-looking
    number instead of crashing the whole results view for the viewer.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# Served by Streamlit's own static-file route (server.enableStaticServing in
# .streamlit/config.toml), from ui/static/ - not read into Python at all, so
# opening it needs neither this app nor the FastAPI backend to do any work.
HOW_IT_WORKS_URL = "app/static/how_it_works.html"


@st.cache_data(ttl=5, show_spinner=False)
def fetch_recent(n: int = 10) -> list[dict] | None:
    """Recent audit entries. Cache is cleared after a new decision."""
    try:
        response = httpx.get(f"{API_URL}/recent?n={n}", timeout=5)
        if response.status_code == 200:
            return list(response.json().get("decisions", []))
        return None
    except Exception:
        return None


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  .main { background: #0f1117; }
  .stApp { background: linear-gradient(135deg, #0f1117 0%, #1a1f2e 100%); }
  .metric-card {
    background: linear-gradient(135deg, #1e2537, #252d42);
    border-radius: 12px; padding: 1.2rem;
    border: 1px solid #2e3a52; margin-bottom: 1rem;
  }
  .decision-card {
    background: linear-gradient(135deg, #1a2332, #1e2a3e);
    border-radius: 16px; padding: 1.5rem;
    border: 1px solid #2a3850; margin-top: 1rem;
  }
  .priority-URGENT { border-left: 4px solid #ff4b4b !important; }
  .priority-ELEVATED { border-left: 4px solid #ffa500 !important; }
  .priority-NORMAL { border-left: 4px solid #00c8a0 !important; }
  .priority-HOLD { border-left: 4px solid #888 !important; }
  .step-box {
    background: #1a2030; border-radius: 8px; padding: 0.8rem 1rem;
    margin: 0.4rem 0; border-left: 3px solid #3b82f6;
    font-size: 0.9rem; color: #c8d6e5;
  }
  .rule-PASS { color: #22c55e; font-weight: 600; }
  .rule-WARN { color: #f59e0b; font-weight: 600; }
  .rule-FAIL { color: #ef4444; font-weight: 600; }
  .rule-ESCALATE { color: #a855f7; font-weight: 700; }
  .rule-INFO { color: #94a3b8; font-weight: 600; }
  h1, h2, h3 { color: #e2e8f0 !important; }
  .stTextArea textarea { background: #1e2537 !important; color: #e2e8f0 !important; }
  .stButton > button {
    background: linear-gradient(135deg, #3b82f6, #1d4ed8);
    color: white; border-radius: 8px; border: none;
    padding: 0.6rem 2rem; font-weight: 600; font-size: 1rem;
    transition: all 0.2s;
  }
  .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(59,130,246,0.4); }
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏭 MRPL Workbench")
    st.caption("Sovereign On-Premise AI v1.0")
    st.divider()
    st.markdown("### Engineer Info")
    user_id = st.text_input("Your ID", value="engineer_1", placeholder="engineer_name")

    st.divider()
    st.markdown("### Quick Queries")
    examples = [
        "Reactor-4 pressure 4.2 bar, last service 6 months, budget Rs.50000. When schedule?",
        "Compressor-B making loud noise, temperature up 15C. What is the risk?",
        "Separator-D hasn't been serviced in 26 months. Can we postpone again?",
        "Pump-A and Compressor-B both need service. Budget Rs.35000. Which first?",
        "What is the current status of heat exchanger-C?",
    ]
    for i, ex in enumerate(examples, 1):
        if st.button(f"📋 Example {i}", key=f"ex_{i}", use_container_width=True):
            st.session_state["query_text"] = ex

    st.divider()
    st.markdown("### API Status")
    health = fetch_health()
    if health is None:
        st.error("API: Offline ❌")
        st.caption("Start: `uvicorn api.main:app --port 8000`")
    else:
        st.success("API: Online ✅")
        st.caption(f"Engine: `{health.get('engine', 'unknown')}`")
        if health.get("circuit_open"):
            st.caption("⚠️ Provider circuit open — serving rule-based")

# ── Main area ──────────────────────────────────────────────────────────────────
st.markdown("# 🏭 MRPL Agentic Workbench")
st.markdown("*Sovereign On-Premise AI for Maintenance Decision Support*")

hdr_l, hdr_r = st.columns([5, 2])
with hdr_r:
    # A real new tab, not an embedded panel: the explainer was designed as a
    # full-viewport experience (fixed nav bar, chapter-dot navigation, a
    # mouse-follow spotlight) and fighting a fixed-height iframe to approximate
    # that was more fragile than just letting it be its own page. Streamlit's
    # own static-file route serves it directly, so opening it needs neither
    # this script nor the FastAPI backend to do any work.
    st.link_button(
        "🎬 How This Works",
        HOW_IT_WORKS_URL,
        use_container_width=True,
        help="Opens in a new tab: a plain-English walkthrough for a "
        "non-technical audience - the problem, the solution, the system "
        "design, and why it's worth it.",
    )

st.divider()

# ── Query input ───────────────────────────────────────────────────────────────
col_q, col_btn = st.columns([5, 1])
with col_q:
    default_query = st.session_state.get("query_text", "")
    query = st.text_area(
        "Maintenance Query",
        value=default_query,
        height=100,
        placeholder="Describe the equipment state, problem, and what decision you need...",
        label_visibility="collapsed",
    )

with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze = st.button("Analyze ⚡", use_container_width=True)

st.caption(
    "Describe equipment state, readings, budget, and your question. The AI pipeline will reason through it."
)

# ── Analysis ──────────────────────────────────────────────────────────────────
if analyze and query.strip():
    with st.spinner("Running 5-agent pipeline..."):
        t0 = time.time()
        try:
            resp = httpx.post(
                f"{API_URL}/analyze",
                json={"query": query.strip(), "user_id": user_id},
                timeout=35,
            )
            elapsed = time.time() - t0

            if resp.status_code == 429:
                st.warning("Rate limit reached. Please wait a moment.")
                st.stop()
            elif resp.status_code == 400:
                err = resp.json()
                st.error(
                    f"Invalid input: {err.get('detail', {}).get('error', 'Bad request')}"
                )
                st.stop()
            elif resp.status_code != 200:
                st.error(f"API error {resp.status_code}: {resp.text[:200]}")
                st.stop()

            d = resp.json()
            # A new decision was just logged - drop the cached audit list.
            fetch_recent.clear()

        except httpx.ConnectError:
            st.error(
                "Cannot connect to API. Start the server: `uvicorn api.main:app --port 8000`"
            )
            st.stop()
        except Exception as exc:
            st.error(f"Error: {exc}")
            st.stop()

    # ── Top metrics row ──────────────────────────────────────────────────────
    st.markdown("---")
    priority = d.get("priority", "NORMAL")
    priority_emoji = {
        "URGENT": "🔴",
        "ELEVATED": "🟡",
        "NORMAL": "🟢",
        "HOLD": "⚪",
    }.get(priority, "🟢")

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Decision ID", d.get("decision_id", "—")[-13:])
    with m2:
        st.metric("Priority", f"{priority_emoji} {priority}")
    with m3:
        v_status = d.get("validation", {}).get("status", "—")
        score = d.get("validation", {}).get("compliance_score", 0)
        st.metric("Compliance", f"{score}%", delta=v_status)
    with m4:
        conf = d.get("metadata", {}).get("overall_confidence", 0)
        st.metric("Confidence", f"{conf:.0%}")
    with m5:
        ms = d.get("metadata", {}).get("total_time_ms", 0)
        engine = d.get("metadata", {}).get("engine_used", "—")
        st.metric("Response Time", f"{ms} ms", delta=engine)

    # ── Main content: recommendation + reasoning side-by-side ────────────────
    st.markdown("---")
    col_left, col_right = st.columns([3, 2])

    with col_left:
        rec = d.get("recommendation", {})
        val = d.get("validation", {})

        # Recommendation card
        p_class = f"priority-{priority}"
        st.markdown(
            f"""
        <div class="decision-card {p_class}">
          <h3 style="margin:0 0 0.5rem">🎯 Recommendation</h3>
          <p style="font-size:1.1rem;color:#e2e8f0;margin:0.2rem 0"><strong>{rec.get('action','')}</strong></p>
          <p style="color:#94a3b8;margin:0.5rem 0">{rec.get('detail','')}</p>
          <hr style="border-color:#2e3a52;margin:0.8rem 0">
          <p>⏰ <strong>Timing:</strong> {rec.get('timing','')}</p>
          <p>💰 <strong>Cost Est.:</strong> Rs.{_safe_number(rec.get('estimated_cost_inr')):,.0f}</p>
          <p>🔧 <strong>Downtime:</strong> {rec.get('estimated_downtime_hours',0)} hours</p>
          <p>⚠️ <strong>Risk if Delayed:</strong> {rec.get('risk_if_delayed','')}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Validation
        st.markdown("#### ✅ Validation Results")
        rule_results = val.get("rule_results", {})
        rule_icons = {
            "cost_check": "💰",
            "downtime_check": "⏱️",
            "safety_margin": "🛡️",
            "compliance": "📋",
            "historical": "📊",
            "scope_check": "🔍",
        }
        for rule_key, rule_data in rule_results.items():
            status = rule_data.get("status", "PASS")
            icon = rule_icons.get(rule_key, "•")
            msg = rule_data.get("message", "")
            cls = f"rule-{status}"
            label = rule_key.replace("_", " ").title()
            st.markdown(
                f'<div class="step-box">'
                f'{icon} <span class="{cls}">[{status}]</span> '
                f"<strong>{label}</strong>: {msg}</div>",
                unsafe_allow_html=True,
            )

        # Most severe first: escalations outrank violations, which outrank warnings.
        escalations = val.get("escalations", [])
        violations = val.get("violations", [])
        warnings = val.get("warnings", [])
        for e in escalations:
            st.error(f"🚨 **ESCALATION:** {e}")
        for v in violations:
            st.error(f"❌ Violation: {v}")
        for w in warnings:
            st.warning(f"⚠️ Warning: {w}")
        if not (escalations or violations or warnings):
            st.success("✅ All checks passed — no violations, warnings or escalations.")

    with col_right:
        # Reasoning chain
        st.markdown("#### 🧠 Agent Reasoning Chain")
        steps = d.get("reasoning_chain", [])
        for i, step in enumerate(steps, 1):
            st.markdown(
                f'<div class="step-box">🔵 {step}</div>', unsafe_allow_html=True
            )

        # Equipment & state
        st.markdown("#### 📊 Equipment State")
        state = d.get("current_state", {})
        analysis = d.get("analysis", {})
        info = {
            "Equipment": d.get("equipment", "—"),
            "Intent Detected": d.get("intent", "—").replace("_", " ").title(),
            "Docs Consulted": analysis.get("documents_consulted", 0),
            "Reasoning Steps": d.get("metadata", {}).get("reasoning_steps_count", 0),
            "Engine Used": d.get("metadata", {}).get("engine_used", "—"),
        }
        if state.get("pressure_bar"):
            info["Pressure"] = f"{state['pressure_bar']} bar"
        if state.get("last_service_days"):
            info["Last Service"] = f"{state['last_service_days']} days ago"
        if state.get("temperature_rise_c"):
            info["Temp Rise"] = f"{state['temperature_rise_c']} C"

        for k, v in info.items():
            st.markdown(f"**{k}:** `{v}`")

    # ── Raw JSON expander ────────────────────────────────────────────────────
    with st.expander("📄 Full Decision JSON", expanded=False):
        st.json(d)

# ── No query message ──────────────────────────────────────────────────────────
elif not query.strip() and analyze:
    st.warning("Please enter a maintenance query.")

# ── Audit log tab ─────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📋 Recent Decisions (Audit Log)", expanded=False):
    entries = fetch_recent(10)
    if entries is None:
        st.warning("Could not load audit log — API not reachable.")
    elif not entries:
        st.info("No decisions yet. Run a query first.")
    else:
        for e in entries:
            ts = e.get("timestamp", "")[:19].replace("T", " ")
            status = e.get("validation_status", "")
            color = {
                "APPROVED": "#22c55e",
                "APPROVED_WITH_WARNINGS": "#f59e0b",
                "REJECTED": "#ef4444",
                "ESCALATE": "#a855f7",
            }.get(status, "#888")
            st.markdown(
                f"**{e.get('decision_id','')}** | `{e.get('equipment','')}` | "
                f"<span style='color:{color}'>{status}</span> | "
                f"Score: {e.get('compliance_score',0)}% | "
                f"`{e.get('engine_used','—')}` | {ts}",
                unsafe_allow_html=True,
            )
