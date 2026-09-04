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
import re

import httpx
import pytest

from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "streamlit_app.py")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
UI_URL = os.getenv("UI_URL", "http://127.0.0.1:8501")


def _ui_is_up() -> bool:
    try:
        return httpx.get(f"{UI_URL}/_stcore/health", timeout=5).status_code == 200
    except Exception:
        return False


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

    def test_how_it_works_link_button_targets_the_static_file(self):
        """
        The jury-facing explainer (ui/static/how_it_works.html) opens as a
        real new tab via st.link_button, not an embedded panel - it isn't a
        first-class AppTest node (surfaces as UnknownElement), so this reads
        its raw proto rather than simulating a click/navigate, which a
        headless, browser-less harness can't do anyway.
        """
        app = _run_app()
        link_buttons = app.get("link_button")
        assert link_buttons, "How This Works link_button not found"

        how = next((b for b in link_buttons if "How This Works" in b.proto.label), None)
        assert how is not None, [b.proto.label for b in link_buttons]
        assert how.proto.url == "app/static/how_it_works.html"

        # The old toggle-button/iframe/back-button flow is gone entirely -
        # the query workbench must render exactly as if this button did not
        # exist, since clicking it never touches app state (ignore_rerun).
        assert how.proto.ignore_rerun is True
        assert any("Analyze" in str(b.label) for b in app.button)
        assert len(app.text_area) == 1


@pytest.mark.skipif(not _ui_is_up(), reason="Streamlit UI not running")
class TestHowItWorksStaticFile:
    """
    Gates on the UI, not the API - this route is served entirely by
    Streamlit's own static-file handler, so it must work whether or not the
    FastAPI backend is up at all (that's the whole point of not fetching it
    through the API).
    """

    def test_static_file_is_served_and_self_contained(self):
        url = f"{UI_URL}/app/static/how_it_works.html"
        response = httpx.get(url, timeout=10)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        body = response.text
        assert "How This Works" in body
        # Must stay offline-capable: no CDN, no external fonts/scripts.
        assert "cdn." not in body.lower()
        assert not re.search(r'src="https?://', body)
        assert not re.search(r'href="https?://', body)


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
