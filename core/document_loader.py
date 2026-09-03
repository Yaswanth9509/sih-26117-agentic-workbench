"""
Document Loader: loads and flattens MRPL sample documents.
Supports JSON, CSV, TXT. Returns list[dict] with 'text' field for TF-IDF.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads MRPL knowledge-base documents from data/sample_docs/."""

    def __init__(self, docs_path: str = "data/sample_docs") -> None:
        self.docs_path = Path(docs_path)

    # ── Public ───────────────────────────────────────────────────────────────

    def load_all(self) -> list[dict[str, Any]]:
        """Load all 5 sample documents. Returns flat list[dict] with 'text' key."""
        all_docs: list[dict[str, Any]] = []

        loaders = [
            ("equipment_specs.json", self._load_json),
            ("maintenance_schedule.csv", self._load_csv),
            ("service_logs.txt", self._load_txt),
            ("safety_protocols.json", self._load_json),
            ("cost_estimates.csv", self._load_csv),
        ]

        for filename, loader_fn in loaders:
            path = self.docs_path / filename
            if not path.exists():
                logger.warning(f"Missing sample doc: {filename} - skipping")
                continue
            try:
                docs = loader_fn(str(path))
                for d in docs:
                    d["source"] = filename
                all_docs.extend(docs)
                logger.info(f"Loaded {len(docs)} records from {filename}")
            except Exception as exc:
                logger.error(f"Failed to load {filename}: {exc}")

        logger.info(f"Total documents loaded: {len(all_docs)}")
        return all_docs

    # ── Private loaders ──────────────────────────────────────────────────────

    def _load_json(self, path: str) -> list[dict[str, Any]]:
        """Load a JSON file. Handles both list and dict with a list under any key."""
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        records: list[dict[str, Any]] = []
        if isinstance(raw, list):
            records = raw
        elif isinstance(raw, dict):
            # Flatten: pick the first list-valued key
            for v in raw.values():
                if isinstance(v, list):
                    records = v
                    break
            if not records:
                records = [raw]  # treat whole dict as single record

        result = []
        for rec in records:
            flat = self._flatten(rec)
            flat["text"] = " ".join(str(v) for v in flat.values())
            result.append(flat)
        return result

    def _load_csv(self, path: str) -> list[dict[str, Any]]:
        """Load a CSV file into list of row dicts."""
        rows = []
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rec = dict(row)
                rec["text"] = " ".join(str(v) for v in rec.values())
                rows.append(rec)
        return rows

    def _load_txt(self, path: str) -> list[dict[str, Any]]:
        """Split TXT into paragraphs; each paragraph = one document."""
        with open(path, encoding="utf-8") as f:
            content = f.read()

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        return [{"text": para, "content": para} for para in paragraphs]

    @staticmethod
    def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """Recursively flatten nested dict."""
        out: dict[str, Any] = {}
        for k, v in d.items():
            key = f"{prefix}{k}" if not prefix else f"{prefix}_{k}"
            if isinstance(v, dict):
                out.update(DocumentLoader._flatten(v, key))
            elif isinstance(v, list):
                out[key] = " ".join(str(i) for i in v)
            else:
                out[key] = v
        return out
