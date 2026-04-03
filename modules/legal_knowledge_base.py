"""
Module 5 — Legal Knowledge Base
=================================
Structured access layer for Sri Lankan legal clauses stored in
``data/legal_clauses.json``.

Provides:
  - Load and cache all clauses
  - Filter by law_code, tags, or section
  - Retrieve full clause detail (title, description, full_text, penalty, etc.)
  - Build searchable text corpus for semantic matching
"""

import json
import os
from typing import Dict, List, Optional, Set


def _data_path(filename: str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", filename))


class LegalKnowledgeBase:
    """Read-only access to the Sri Lankan legal clause database."""

    def __init__(self):
        self._clauses: Optional[List[Dict]] = None

    def _load(self) -> List[Dict]:
        if self._clauses is not None:
            return self._clauses
        path = _data_path("legal_clauses.json")
        for enc in ("utf-8-sig", "utf-8", "utf-16"):
            try:
                with open(path, "r", encoding=enc) as f:
                    data = json.load(f)
                    self._clauses = data if isinstance(data, list) else []
                    return self._clauses
            except (UnicodeDecodeError, UnicodeError):
                continue
        self._clauses = []
        return self._clauses

    @property
    def clauses(self) -> List[Dict]:
        """All legal clauses."""
        return self._load()

    def get_by_law_code(self, law_code: str) -> List[Dict]:
        """Return all clauses for a given law code (e.g. 'PDPA', 'OSA')."""
        code = law_code.upper()
        return [c for c in self.clauses if c.get("law_code", "").upper() == code]

    def get_by_section(self, law_code: str, section: str) -> Optional[Dict]:
        """Return a single clause by law_code + section (e.g. 'OSA', '18(a)')."""
        code = law_code.upper()
        sec = section.strip()
        for c in self.clauses:
            if c.get("law_code", "").upper() == code and c.get("section", "").strip() == sec:
                return c
        return None

    def filter_by_tags(self, tags: List[str]) -> List[Dict]:
        """Return clauses whose tags overlap with the given set."""
        tag_set = set(tags)
        return [c for c in self.clauses if tag_set & set(c.get("tags", []))]

    def get_law_codes(self) -> List[str]:
        """Return a sorted list of unique law codes in the database."""
        codes: Set[str] = set()
        for c in self.clauses:
            code = c.get("law_code", "")
            if code:
                codes.add(code)
        return sorted(codes)

    def build_corpus(self) -> List[str]:
        """
        Build a searchable text corpus aligned with self.clauses.
        corpus[i] corresponds to self.clauses[i].
        """
        corpus = []
        for c in self.clauses:
            text = " ".join([
                c.get("title", ""),
                c.get("description", ""),
                c.get("explanation", ""),
                c.get("full_text", ""),
            ]).strip()
            corpus.append(text or f"{c.get('law_code', '')} {c.get('section', '')}")
        return corpus

    def clause_count(self) -> int:
        return len(self.clauses)
