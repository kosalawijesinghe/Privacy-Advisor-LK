"""
Keyword-Based Clause Boosting
==============================
Directly boosts clauses based on keyword matches from incident description.
Works alongside semantic retrieval for hybrid accuracy.

Strategy:
  1. Extract keywords from incident description
  2. Match keywords to clause keywords and tags
  3. Apply multiplicative boost to matching clauses
  4. Works with all selection stages (retrieval, filtering, ranking)
"""

from typing import Dict, List, Set, Optional
import re


class KeywordClauseBooster:
    """Boost clauses based on keyword and tag matches."""

    # Incident-specific keyword patterns
    KEYWORD_PATTERNS = {
        "data_exposure": {
            "keywords": ["exposed", "leaked", "breached", "database", "dump", "publicly", "accessible", "data"],
            "boost": 0.40,
        },
        "account_takeover": {
            "keywords": ["hacked", "unauthorized access", "account", "password", "login", "compromised", "hijack"],
            "boost": 0.45,
        },
        "identity_theft": {
            "keywords": ["identity", "nic", "id number", "stolen", "fraud", "fraudulent", "loan", "credit"],
            "boost": 0.45,
        },
        "impersonation": {
            "keywords": ["fake", "impersonate", "pretend", "posing", "profile", "fake account"],
            "boost": 0.40,
        },
        "harassment": {
            "keywords": ["threatening", "harassment", "harass", "threat", "intimidat", "blackmail", "threaten"],
            "boost": 0.35,
        },
        "image_abuse": {
            "keywords": ["image", "photo", "picture", "nude", "deepfake", "morphed", "intimate", "non-consensual"],
            "boost": 0.40,
        },
        "doxxing": {
            "keywords": ["doxx", "address", "location", "personal details", "published", "exposed", "shared"],
            "boost": 0.40,
        },
    }

    COMMON_KEYWORDS = ["unauthorized", "access", "compromise", "breach", "offence", "crime", "fraud"]

    def __init__(self):
        self._compiled_patterns = self._compile_patterns()

    @staticmethod
    def _compile_patterns() -> Dict[str, tuple]:
        """Pre-compile regex patterns for efficiency."""
        compiled = {}
        for incident_type, config in KeywordClauseBooster.KEYWORD_PATTERNS.items():
            keywords = config["keywords"]
            pattern = "|".join(re.escape(kw) for kw in keywords)
            compiled[incident_type] = (re.compile(pattern, re.IGNORECASE), config["boost"])
        return compiled

    def extract_keywords(self, incident_text: str) -> Set[str]:
        """Extract keywords from incident description."""
        if not incident_text:
            return set()

        text_lower = incident_text.lower()
        keywords = set()

        # Add incident-specific keywords
        for keyword_list in [config["keywords"] for config in self.KEYWORD_PATTERNS.values()]:
            for kw in keyword_list:
                if kw.lower() in text_lower:
                    keywords.add(kw.lower())

        # Add common keywords
        for kw in self.COMMON_KEYWORDS:
            if kw.lower() in text_lower:
                keywords.add(kw.lower())

        return keywords

    def get_keyword_boost(
        self, clause: Dict, incident_text: str, base_score: float = 0.5
    ) -> float:
        """Calculate keyword-based boost for a clause."""
        if not clause or not incident_text:
            return base_score

        # Get clause keyword fields
        clause_keywords = set()
        clause_keywords.update(clause.get("keywords", []) or [])
        clause_keywords.update(clause.get("tags", []) or [])

        # Extract incident keywords
        incident_keywords = self.extract_keywords(incident_text)

        if not incident_keywords or not clause_keywords:
            return base_score

        # Calculate keyword overlap (Jaccard similarity)
        intersection = len(incident_keywords & clause_keywords)
        union = len(incident_keywords | clause_keywords)

        if union == 0:
            return base_score

        overlap_ratio = intersection / union

        # Apply boost: 0-40% boost based on overlap
        # High overlap (0.5+) → max 0.40 boost
        # Low overlap (0.1) → 0.08 boost
        boost_amount = overlap_ratio * 0.40

        return min(1.0, base_score + boost_amount)

    def boost_clauses_by_keywords(
        self, clauses: List[Dict], incident_text: str
    ) -> List[Dict]:
        """
        Apply keyword boosts to all clauses.
        Returns boosted clauses sorted by relevance_score.
        """
        if not clauses or not incident_text:
            return clauses

        boosted = []
        for clause in clauses:
            original_score = clause.get("relevance_score", 0.5)
            boosted_score = self.get_keyword_boost(clause, incident_text, original_score)
            clause_copy = clause.copy()
            clause_copy["relevance_score"] = boosted_score
            clause_copy["keyword_boost"] = round(boosted_score - original_score, 4)
            boosted.append(clause_copy)

        # Sort by boosted score
        boosted.sort(key=lambda c: c["relevance_score"], reverse=True)
        return boosted

    def boost_for_incident_type(
        self, clauses: List[Dict], incident_type: str
    ) -> List[Dict]:
        """
        Apply incident-type-specific keyword boosting.
        For known incident types, apply targeted boosts.
        """
        incident_type = (incident_type or "").lower().replace("_", " ")

        if incident_type not in self._compiled_patterns:
            return clauses

        pattern, base_boost = self._compiled_patterns[incident_type]
        boosted = []

        for clause in clauses:
            clause_copy = clause.copy()
            original_score = clause.get("relevance_score", 0.5)

            # Check if clause text/keywords match incident pattern
            clause_text = " ".join([
                clause.get("title", ""),
                clause.get("description", ""),
                " ".join(clause.get("keywords", []) or []),
                " ".join(clause.get("tags", []) or []),
            ]).lower()

            if pattern.search(clause_text):
                # Apply incident-type-specific boost
                new_score = min(1.0, original_score + base_boost)
                clause_copy["relevance_score"] = new_score
                clause_copy["incident_keyword_boost"] = round(new_score - original_score, 4)

            boosted.append(clause_copy)

        boosted.sort(key=lambda c: c["relevance_score"], reverse=True)
        return boosted
