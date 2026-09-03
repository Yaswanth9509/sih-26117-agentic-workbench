"""
Smoke tests for the Streamlit UI, using Streamlit's own headless harness.

mypy cannot check this file's counterpart: `streamlit` ships no type
information, so `st` is typed as Any and undefined attributes or bad key
access in ui/streamlit_app.py are invisible to static analysis. These tests
actually execute the script and assert it raises nothing.

The load tests run fully offline - the app is expected to render an
"API: Offline" state when the backend is absent. The query test needs a live
backend and skips when there isn't one.
"""

from __future__ import annotations

import os

import httpx
import pytest

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "streamlit_app.py")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")


def _api_is_up() -> bool:
    # Generous timeout: /health calls available_providers(), which probes the
    # local ollama port, so it can take a couple of seconds when ollama is absent.
    try:
        return httpx.get(f"{API_URL}/health", timeout=10).status_code == 200
    except Exception:
        return False


def _run_app() -> AppTest:
    app = AppTest.from_file(APP, default_timeout=60)
    app.run()
    return app


class TestAppLoads:
    """These must pass with or without a running backend."""

    def test_no_exceptions_on_load(self):
        app = _run_app()
        assert not app.exception, [str(e.value) for e in app.exception]

    def test_renders_query_input_and_analyze_button(self):
        app = _run_app()
        assert len(app.text_area) == 1
        assert any("Analyze" in str(b.label) for b in app.button)

    def test_reports_backend_state_in_sidebar(self):
        """Either Online or Offline - never a blank or crashed sidebar."""
        app = _run_app()
        messages = [str(m.value) for m in app.sidebar.success]
        messages += [str(m.value) for m in app.sidebar.error]
        assert any("API:" in m for m in messages), messages


@pytest.mark.skipif(not _api_is_up(), reason="backend not running")
class TestQueryFlow:
    """End-to-end through the UI against a live backend."""

    def _submit(self, query: str) -> AppTest:
        app = _run_app()
        app.text_area[0].set_value(query)
        analyze = [b for b in app.button if "Analyze" in str(b.label)]
        analyze[0].click().run()
        return app

    def test_query_renders_without_exceptions(self):
        app = self._submit("Reactor-4 pressure 4.2 bar, last service 6 months.")
        assert not app.exception, [str(e.value) for e in app.exception]

    def test_decision_metrics_are_shown(self):
        app = self._submit("Reactor-4 pressure 4.2 bar, last service 6 months.")
        labels = [str(m.label) for m in app.metric]
        assert "Priority" in labels
        assert "Compliance" in labels
        assert "Confidence" in labels

    def test_escalations_are_surfaced(self):
        """
        Regression: escalations were computed by ValidationAgent but never
        rendered, so an ESCALATE decision showed URGENT with no stated reason.
        """
        app = self._submit(
            "Reactor-4 pressure 4.8 bar, last service 200 days ago. Service now?"
        )
        errors = [str(e.value) for e in app.error]
        assert any("ESCALATION" in e for e in errors), errors
