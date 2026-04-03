"""
Module 12 — System Logging and Dataset Expansion
==================================================
Logs every analysis run for traceability and future dataset expansion.

Stores:
  - User-submitted scenario inputs
  - Detected scenario and severity
  - List of matched clauses and their scores
  - Recommendations generated (action + priority)
  - Timestamp and model information

Logs are written as JSON-Lines to ``data/analysis_log.jsonl``.
Retention: entries older than 180 days are automatically purged (NFR6).
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

_LOG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "analysis_log.jsonl")
)

_RETENTION_DAYS = 180


class SystemLogger:
    """Appends analysis records to a JSONL log file for dataset expansion."""

    def __init__(self, log_path: Optional[str] = None):
        self._path = log_path or _LOG_PATH

    def log_analysis(
        self,
        validated_input: Dict,
        scenario: Dict,
        severity: Dict,
        matched_clauses: List[Dict],
        model_name: str = "",
        recommendations: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Log one full analysis run.

        Returns the record that was written (for audit purposes).
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input": {
                "tags":              validated_input.get("normalized_tags", []),
                "impersonate":       validated_input.get("impersonate", False),
                "img_exposed":       validated_input.get("img_exposed", False),
                "platform":          validated_input.get("platform", ""),
                "incident_category": validated_input.get("incident_category", ""),
            },
            "scenario": {
                "description": scenario.get("scenario_description", "")[:500],
                "category":    scenario.get("incident_category", ""),
            },
            "severity": {
                "score": severity.get("score", 0),
                "level": severity.get("level", ""),
            },
            "clauses": [
                {
                    "law_code":       c.get("law_code", ""),
                    "section":        c.get("section", ""),
                    "relevance_score": c.get("relevance_score", 0.0),
                }
                for c in matched_clauses[:15]
            ],
            "recommendations": [
                {"action": r.get("action", ""), "priority": r.get("priority", "")}
                for r in (recommendations or [])[:10]
            ],
            "model": model_name,
        }

        # Ensure directory exists
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    def purge_old_entries(self, retention_days: int = _RETENTION_DAYS) -> int:
        """
        Remove log entries older than ``retention_days`` days (NFR6).

        Returns the number of entries purged.
        """
        if not os.path.exists(self._path):
            return 0

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        kept, purged = [], 0

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts    = datetime.fromisoformat(entry.get("timestamp", ""))
                        # Make naive timestamps timezone-aware (assume UTC)
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if ts >= cutoff:
                            kept.append(line)
                        else:
                            purged += 1
                    except (ValueError, KeyError):
                        kept.append(line)  # keep unparseable entries
        except OSError:
            return 0

        if purged > 0:
            with open(self._path, "w", encoding="utf-8") as f:
                f.write("\n".join(kept) + ("\n" if kept else ""))

        return purged

    def read_log(self, last_n: int = 50) -> List[Dict]:
        """Read the last N records from the log."""
        if not os.path.exists(self._path):
            return []
        records = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records[-last_n:]
