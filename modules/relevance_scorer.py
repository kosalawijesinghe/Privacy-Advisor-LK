"""
Semantic Relevance Scorer + Confidence Calibrator
===================================================
Two scoring stages in one module:

1. RelevanceScorer — multi-signal relevance ranking (no hard-coded gates)
2. ConfidenceCalibrator — calibrated confidence from cross-encoder + reasoning signals

Both use semantic-dominant weighted combinations of embedding scores,
tag overlap, penalty severity, and clause priority.
"""

import re
from typing import Dict, List, Optional

from modules.pii_risk_weighter import PIIRiskWeighter
from modules.relevance_matrix import get_relevance_tier, get_tag_clauses, clause_key

# ---- Scoring Weights (semantic-dominant) ------------------------------------

DEFAULT_WEIGHTS = {
    "cross_encoder": 0.30,
    "semantic":      0.30,
    "tag_overlap":   0.15,
    "penalty":       0.10,
    "priority":      0.10,
    "severity":      0.05,
}

MAX_CLAUSE_PRIORITY = 5.0

# ---- Penalty Parsing -------------------------------------------------------

_YEAR_RE   = re.compile(r"(\d+)\s*(?:year|yr)", re.IGNORECASE)
_MONTH_RE  = re.compile(r"(\d+)\s*(?:month)", re.IGNORECASE)
_FINE_RE   = re.compile(r"(?:LKR|Rs\.?)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
_MILLION_RE = re.compile(r"(\d+)\s*million", re.IGNORECASE)


def extract_penalty_severity(penalty_text: str) -> float:
    """
    Analyse penalty text and return a normalised severity score (0–1).
    Longer sentences / higher fines → higher severity.
    """
    if not penalty_text:
        return 0.05

    score = 0.0

    years = _YEAR_RE.findall(penalty_text)
    if years:
        max_years = max(int(y) for y in years)
        score = max(score, min(1.0, max_years / 20.0))

    if not years:
        months = _MONTH_RE.findall(penalty_text)
        if months:
            max_months = max(int(m) for m in months)
            score = max(score, min(0.4, max_months / 24.0))

    millions = _MILLION_RE.findall(penalty_text)
    if millions:
        max_m = max(float(m) for m in millions)
        score = max(score, min(1.0, max_m / 50.0))

    fines = _FINE_RE.findall(penalty_text)
    if fines:
        amounts = [float(f.replace(",", "")) for f in fines if f.replace(",", "")]
        if amounts:
            max_fine = max(amounts)
            score = max(score, min(0.8, max_fine / 10_000_000))

    lower = penalty_text.lower()
    if "double" in lower or "doubled" in lower:
        score = min(1.0, score * 1.3)
    if "rigorous imprisonment" in lower:
        score = min(1.0, score + 0.15)

    return max(0.05, round(score, 3))


# ---- Main Scorer -----------------------------------------------------------

class RelevanceScorer:
    """
    Semantic relevance scorer — no hard-coded gates or expert matrices.
    All clauses are scored using multi-signal semantic scoring.
    Relevance tier is derived from the computed score, not from a lookup.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self._weights = weights or DEFAULT_WEIGHTS

    def score(
        self,
        matched_clauses: List[Dict],
        scenario_key: str = "DATA_EXPOSURE",
        severity_score: float = 0.0,
        user_tags: Optional[List[str]] = None,
        all_scenario_keys: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Score and rank clauses using multi-signal semantic scoring
        augmented with expert relevance matrix signals.

        Returns
        -------
        list[dict]
            Scored and ranked clauses with relevance_score.
        """
        w = self._weights
        tag_set = set(user_tags or [])

        # Consider all scenario keys for the expert boost (not just the primary)
        scenario_keys_to_check = list(dict.fromkeys(
            (all_scenario_keys or []) + [scenario_key]
        ))

        # Build set of clause keys that the expert tag-clause map says
        # are specifically relevant to the user's exposed PII types
        tag_relevant_keys = set()
        for tag in tag_set:
            tag_relevant_keys |= set(get_tag_clauses(tag))

        scored: List[Dict] = []

        for clause in matched_clauses:
            # Retrieve signals from earlier pipeline stages
            sem = clause.get("semantic_score", 0.0)
            ce = clause.get("cross_encoder_score", sem)  # fallback to sem
            penalty_text = clause.get("penalty", "")

            # Tag overlap (recall-weighted: broad-coverage laws not penalised)
            clause_tags = set(clause.get("tags", []))
            if clause_tags and tag_set:
                _inter = len(clause_tags & tag_set)
                _recall = _inter / len(tag_set)
                _jaccard = _inter / max(len(clause_tags | tag_set), 1)
                tag_overlap = 0.7 * _recall + 0.3 * _jaccard
            else:
                tag_overlap = 0.0

            # Penalty severity (data-driven from clause text)
            pen_sev = extract_penalty_severity(penalty_text)

            # Clause priority (from clause JSON data, not hard-coded lookup)
            raw_priority = clause.get("law_priority", 3)
            priority = min(1.0, raw_priority / MAX_CLAUSE_PRIORITY)

            # Expert matrix signal: check ALL scenario keys for best tier
            ckey = clause_key(clause.get("law_code", ""), clause.get("section", ""))
            best_tier = "EXCLUDED"
            for sk in scenario_keys_to_check:
                tier = get_relevance_tier(sk, clause.get("law_code", ""), clause.get("section", ""))
                if tier == "PRIMARY":
                    best_tier = "PRIMARY"
                    break
                elif tier == "SECONDARY" and best_tier != "PRIMARY":
                    best_tier = "SECONDARY"

            if best_tier == "PRIMARY":
                expert_boost = 0.25
            elif best_tier == "SECONDARY":
                expert_boost = 0.12
            elif ckey in tag_relevant_keys:
                expert_boost = 0.08
            else:
                expert_boost = 0.0

            # Composite score — semantic + expert signals
            relevance = (
                w["cross_encoder"] * ce
                + w["semantic"] * sem
                + w["tag_overlap"] * tag_overlap
                + w["penalty"] * pen_sev
                + w["priority"] * priority
                + w["severity"] * severity_score
                + expert_boost
            )

            # Derive relevance tier from computed score
            if relevance >= 0.55:
                tier = "PRIMARY"
            elif relevance >= 0.35:
                tier = "SECONDARY"
            else:
                tier = "EXCLUDED"

            scored.append({
                **clause,
                "relevance_score": round(relevance, 4),
                "priority_weight": round(priority, 3),
                "penalty_severity": round(pen_sev, 3),
                "tag_overlap_score": round(tag_overlap, 4),
                "expert_boost": round(expert_boost, 4),
                "in_law_domain": True,
                "relevance_tier": tier,
                "relevance_rank": 0,
            })

        # Sort and assign ranks
        scored.sort(key=lambda r: r["relevance_score"], reverse=True)
        for rank, item in enumerate(scored):
            item["relevance_rank"] = rank + 1

        return scored


# ── Confidence Calibrator ────────────────────────────────────────────────────

CALIBRATION_WEIGHTS = {
    "cross_encoder":        0.35,
    "semantic_similarity":  0.25,
    "tag_match":            0.15,
    "reasoning_confidence": 0.15,
    "clause_priority":      0.10,
}


class ConfidenceCalibrator:
    """
    Multi-signal calibrated confidence scores for clauses.
    Uses cross-encoder and reasoning signals for richer calibration.
    """

    def __init__(self):
        self._weights = CALIBRATION_WEIGHTS
        self._pii_weighter = PIIRiskWeighter()

    def calibrate(
        self,
        clauses: List[Dict],
        user_tags: Optional[List[str]] = None,
        incident_type: str = "DATA_EXPOSURE",
    ) -> List[Dict]:
        """Compute calibrated confidence for each clause (0-1)."""
        tag_set = set(user_tags or [])
        w = self._weights

        for clause in clauses:
            semantic = clause.get("semantic_score", 0.0)
            cross_encoder = clause.get("cross_encoder_score", semantic)

            clause_tags = set(clause.get("tags", []))
            if clause_tags and tag_set:
                tag_match = len(clause_tags & tag_set) / len(clause_tags | tag_set)
            else:
                tag_match = 0.0

            reasoning_conf = clause.get("reasoning_confidence", 0.0)

            raw_priority = clause.get("law_priority", 3)
            clause_priority = min(1.0, raw_priority / MAX_CLAUSE_PRIORITY)

            confidence = (
                w["cross_encoder"] * cross_encoder
                + w["semantic_similarity"] * semantic
                + w["tag_match"] * tag_match
                + w["reasoning_confidence"] * reasoning_conf
                + w["clause_priority"] * clause_priority
            )

            confidence = max(0.0, min(1.0, confidence))

            pii_boost = self._pii_weighter.get_clause_ranking_boost(clause, user_tags or [])
            confidence = min(1.0, confidence + pii_boost)

            applicability = clause.get("applicability", "")
            if applicability == "Direct":
                confidence = min(1.0, confidence * 1.1)
            elif applicability == "Weak":
                confidence *= 0.85

            clause["confidence"] = round(confidence, 4)
            clause["confidence_signals"] = {
                "cross_encoder": round(cross_encoder, 4),
                "semantic": round(semantic, 4),
                "tag_match": round(tag_match, 4),
                "reasoning": round(reasoning_conf, 4),
                "clause_priority": round(clause_priority, 4),
                "pii_risk_boost": round(pii_boost, 4),
            }

        return clauses
