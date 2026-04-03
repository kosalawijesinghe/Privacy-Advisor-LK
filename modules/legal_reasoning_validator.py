"""
Legal Reasoning Validation Layer (v2 — Semantic-Driven)
========================================================
Validates clause applicability using semantic signals instead of
hard-coded keyword lists and category affinity mappings.

Signals:
  1. Cross-encoder relevance (from re-ranking stage)
  2. Semantic similarity (bi-encoder cosine)
  3. Tag overlap (data-driven Jaccard)
  4. Contextual keyword similarity (TF-IDF learned from clause corpus)

Output: applicability (Direct, Partial, Weak), reasoning_confidence, explanation
"""

from typing import Dict, List, Set

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as _cos_sim
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


# ── Applicability thresholds ─────────────────────────────────────────────────
DIRECT_THRESHOLD = 0.50
PARTIAL_THRESHOLD = 0.28


class LegalReasoningValidator:
    """
    Validates the legal applicability of each clause to the scenario
    using purely semantic signals. No hard-coded keyword lists or
    category affinity mappings.
    """

    def __init__(self):
        pass

    def validate(
        self,
        clauses: List[Dict],
        scenario_text: str,
        scenario_key: str = "DATA_EXPOSURE",
        user_tags: List[str] = None,
    ) -> List[Dict]:
        """
        Validate each clause's applicability using semantic signals.
        """
        if not clauses or not scenario_text.strip():
            return clauses

        tag_set = set(user_tags or [])

        # Compute TF-IDF contextual similarity (learned from clause texts)
        tfidf_scores = self._compute_tfidf_scores(scenario_text, clauses)

        results = []
        for i, clause in enumerate(clauses):
            tfidf_score = tfidf_scores[i] if tfidf_scores else 0.0
            validation = self._validate_single(
                clause, scenario_text, tag_set, tfidf_score,
            )
            results.append({**clause, **validation})

        return results

    def _compute_tfidf_scores(self, scenario_text: str, clauses: List[Dict]):
        """Compute TF-IDF cosine similarity between scenario and each clause."""
        if not _HAS_SKLEARN:
            return None
        try:
            clause_texts = []
            for c in clauses:
                text = " ".join(filter(None, [
                    c.get("title", ""),
                    c.get("description", ""),
                    c.get("full_text", ""),
                    " ".join(c.get("keywords", [])),
                ])).strip()
                clause_texts.append(text if text else "unknown")
            all_texts = [scenario_text] + clause_texts
            tfidf = TfidfVectorizer(max_features=2000, stop_words="english")
            matrix = tfidf.fit_transform(all_texts)
            sims = _cos_sim(matrix[0:1], matrix[1:]).flatten()
            return [float(s) for s in sims]
        except Exception:
            return None

    def _validate_single(
        self,
        clause: Dict,
        scenario_text: str,
        tag_set: Set[str],
        tfidf_score: float,
    ) -> Dict:
        """Validate a single clause using semantic signals."""
        signals = []

        # Signal 1: Tag overlap (recall-weighted to avoid penalising broad laws)
        clause_tags = set(clause.get("tags", []))
        tag_overlap = clause_tags & tag_set
        if clause_tags and tag_set:
            _inter = len(tag_overlap)
            _recall = _inter / len(tag_set)
            _jaccard = _inter / max(len(clause_tags | tag_set), 1)
            tag_score = 0.7 * _recall + 0.3 * _jaccard
        else:
            tag_score = 0.0
        signals.append(("tag_overlap", tag_score))

        # Signal 2: Semantic similarity (from embedding pipeline)
        semantic_score = clause.get("semantic_score", 0.0)
        signals.append(("semantic_relevance", semantic_score))

        # Signal 3: Cross-encoder relevance (from re-ranking pipeline)
        cross_encoder_score = clause.get("cross_encoder_score", semantic_score)
        signals.append(("cross_encoder_relevance", cross_encoder_score))

        # Signal 4: TF-IDF contextual similarity (learned, not hard-coded)
        contextual_score = max(0.0, min(1.0, tfidf_score))
        signals.append(("contextual_similarity", contextual_score))

        # Weighted combination — semantic-dominant
        reasoning_confidence = (
            0.30 * cross_encoder_score
            + 0.30 * semantic_score
            + 0.20 * tag_score
            + 0.20 * contextual_score
        )
        reasoning_confidence = min(1.0, reasoning_confidence)

        # Determine applicability level
        if reasoning_confidence >= DIRECT_THRESHOLD:
            applicability = "Direct"
        elif reasoning_confidence >= PARTIAL_THRESHOLD:
            applicability = "Partial"
        else:
            applicability = "Weak"

        # Build explanation
        explanation = self._build_explanation(
            clause, tag_overlap, semantic_score, cross_encoder_score,
            contextual_score, applicability,
        )

        return {
            "applicability": applicability,
            "reasoning_confidence": round(reasoning_confidence, 4),
            "reasoning_explanation": explanation,
            "reasoning_signals": {name: round(val, 4) for name, val in signals},
        }

    def _build_explanation(
        self,
        clause: Dict,
        tag_overlap: Set[str],
        semantic_score: float,
        cross_encoder_score: float,
        contextual_score: float,
        applicability: str,
    ) -> str:
        """Build a human-readable reasoning explanation."""
        law_code = clause.get("law_code", "")
        section = clause.get("section", "")
        parts = []

        if applicability == "Direct":
            parts.append(
                f"{law_code} Section {section} is directly applicable based on "
                f"strong semantic alignment and contextual relevance."
            )
        elif applicability == "Partial":
            parts.append(
                f"{law_code} Section {section} provides partial coverage "
                f"based on moderate semantic alignment."
            )
        else:
            parts.append(
                f"{law_code} Section {section} has limited applicability "
                f"to this specific scenario."
            )

        if tag_overlap:
            tag_names = ", ".join(sorted(tag_overlap))
            parts.append(f"Protects exposed data: {tag_names}.")

        if cross_encoder_score >= 0.5:
            parts.append("Strong deep-semantic relevance to the incident description.")
        elif semantic_score >= 0.4:
            parts.append("Moderate semantic alignment with the incident description.")

        if contextual_score >= 0.4:
            parts.append("Contextual keyword analysis supports applicability.")

        return " ".join(parts)

    def filter_weak_clauses(
        self,
        validated_clauses: List[Dict],
        min_applicability: str = "Partial",
    ) -> List[Dict]:
        """
        Remove clauses below the specified applicability threshold.
        """
        levels = {"Direct": 3, "Partial": 2, "Weak": 1}
        min_level = levels.get(min_applicability, 1)
        return [
            c for c in validated_clauses
            if levels.get(c.get("applicability", "Weak"), 1) >= min_level
        ]
