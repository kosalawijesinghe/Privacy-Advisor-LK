"""
Module 9 — Adaptive Clause Filtering
=======================================
Produces a concise, non-redundant set of applicable legal provisions using:

1. Deduplication (same law+section)
2. Tag-overlap gate (user PII must relate to clause)
3. Adaptive score-gap cutoff — detects the natural "elbow" in the score
   distribution and discards the low-relevance tail instead of using
   a fixed cap.  This means the system returns *only* the clauses that
   are meaningfully separated from the noise floor.
4. Hard floor — nothing below a minimum relevance threshold.
5. Dynamic limit — computed from tag count, scenario count, and severity
   level so the result set scales with the complexity of the incident.
6. Confidence score — each clause gets a combined confidence value.
"""

from typing import Dict, List, Set

from modules.relevance_matrix import PRIMARY, clause_key as _clause_key


# Absolute minimum relevance to even consider
# Increased from 0.28 to 0.35 to filter out noise-level clauses
MIN_RELEVANCE = 0.35

# Minimum relative gap (as fraction of top score) to trigger cutoff
# Lowered from 0.10 to 0.05 for better gap detection sensitivity
GAP_FRACTION = 0.05

# Dynamic limit bounds
# Reduced from 4-12 to 3-8 to prevent oversupply of clauses
_MIN_CLAUSES = 3
_MAX_CLAUSES = 8

# Severity tiers that warrant showing more clauses
_HIGH_SEVERITY = {"Critical", "High"}


def _compute_dynamic_limit(
    n_tags: int,
    n_scenarios: int,
    severity_level: str,
) -> int:
    """
    Compute the maximum number of clauses to return.

    Logic (more conservative):
      base  = 3
      +1 per 3 PII tags (was per 2) — less aggressive with tags
      +0.5 per scenario — reduced from 1 per scenario
      +1 if severity is Critical or High
      Max capped at 6 (was 8)
    Capped at [_MIN_CLAUSES .. _MAX_CLAUSES].
    """
    base = 3
    tag_bonus = max(0, (n_tags - 1)) // 3  # Increased from 2 to 3
    scenario_bonus = max(0, (n_scenarios - 1)) // 2  # Divided by 2 instead of direct
    severity_bonus = 1 if severity_level in _HIGH_SEVERITY else 0
    return max(_MIN_CLAUSES, min(_MAX_CLAUSES,
               base + tag_bonus + scenario_bonus + severity_bonus))


class ClauseFilter:
    """Adaptive clause filtering with score-gap detection and dynamic limit."""

    def filter(
        self,
        scored_clauses: List[Dict],
        user_tags: List[str],
        scenario_key: str = "DATA_EXPOSURE",
        n_scenarios: int = 1,
        severity_level: str = "Low",
        all_scenario_keys: List[str] = None,
    ) -> List[Dict]:
        """
        Filter scored clauses using adaptive gap detection.

        The algorithm:
        1. Remove duplicates and below-threshold clauses.
        2. Walk the sorted scores looking for the largest relative gap.
        3. Cut the list at the gap — everything below it is noise.
        4. Apply dynamic cap based on incident complexity.
        5. Compute a confidence score for each surviving clause.

        Returns variable-length results capped at the dynamic limit.
        """
        tag_set = set(user_tags)
        seen: Set[str] = set()
        candidates: List[Dict] = []

        # ── Pass 1: Dedup + threshold + semantic gate ──
        for clause in scored_clauses:
            relevance = clause.get("relevance_score", 0.0)
            law_code = clause.get("law_code", "")
            section = clause.get("section", "")
            clause_tags = set(clause.get("tags", []))
            semantic_score = clause.get("semantic_score", 0.0)

            dedup_key = f"{law_code}:{section}"
            if dedup_key in seen:
                continue

            # Stricter primary threshold
            if relevance < MIN_RELEVANCE:
                continue

            # Semantic gate: More selective
            has_tag_overlap = bool(tag_set & clause_tags)
            
            if semantic_score >= 0.4:
                # Strong semantic relevance always passes
                reason = f"Semantically relevant to scenario"
                if has_tag_overlap:
                    matched = sorted(tag_set & clause_tags)
                    reason += f" + tag match: {', '.join(matched)}"
            elif semantic_score >= 0.25 and has_tag_overlap:
                # Moderate semantic + tag overlap
                matched = sorted(tag_set & clause_tags)
                reason = f"Tag match: {', '.join(matched)}"
            elif semantic_score < 0.25 and has_tag_overlap:
                # Weak semantic - only pass if strong tag match (multiple tags)
                matched = sorted(tag_set & clause_tags)
                if len(matched) >= 2:
                    reason = f"Strong tag match: {', '.join(matched)}"
                else:
                    continue
            else:
                continue

            seen.add(dedup_key)
            candidates.append({**clause, "filter_reason": reason})

        if len(candidates) <= 2:
            return self._add_confidence(candidates)

        # ── Pass 2: Apply dynamic limit first ──
        limit = _compute_dynamic_limit(
            n_tags=len(user_tags),
            n_scenarios=n_scenarios,
            severity_level=severity_level,
        )
        
        # ── Pass 3: Aggressive gap-based cutting ──
        scores = [c["relevance_score"] for c in candidates]
        
        # Find largest gap in top candidates
        best_gap_idx = None
        best_gap_size = 0.0
        for i in range(min(limit + 1, len(scores) - 1)):
            gap = scores[i] - scores[i + 1]
            if gap > best_gap_size:
                best_gap_size = gap
                best_gap_idx = i

        # Cut at gap if significant, otherwise use limit
        if best_gap_idx is not None and best_gap_size > 0.05:
            candidates = candidates[:best_gap_idx + 1]
        else:
            candidates = candidates[:limit]

        # ── Pass 4: Expert rescue (limited) ──
        # Only rescue PRIMARY clauses and only up to 2 more
        scenario_keys = list(dict.fromkeys((all_scenario_keys or []) + [scenario_key]))
        expert_primary: set = set()
        for sk in scenario_keys:
            expert_primary |= PRIMARY.get(sk, frozenset())

        retained_keys = {_clause_key(c.get("law_code", ""), c.get("section", "")) for c in candidates}
        rescued_count = 0
        
        for c in scored_clauses:
            ck = _clause_key(c.get("law_code", ""), c.get("section", ""))
            if ck in retained_keys or rescued_count >= 2:
                continue
            if ck not in expert_primary:
                continue
            if c.get("relevance_score", 0) < MIN_RELEVANCE:
                continue
            candidates.append({**c, "filter_reason": "Expert PRIMARY clause rescue"})
            retained_keys.add(ck)
            rescued_count += 1

        return self._add_confidence(candidates)

    def _add_confidence(self, clauses: List[Dict]) -> List[Dict]:
        """
        Compute a single confidence score (0-1) for each clause.
        This ONE score drives both ranking AND applicability classification.
        
        Formula: relevance 50% + semantic 30% + law_priority 20%
        This is based on the most important signals:
          - relevance_score (from ML cross-encoder) = semantic relevance to query
          - semantic_score (from bi-encoder) = embedding similarity
          - law_priority (from domain expertise) = legal importance for incident type
        
        Applicability is then derived from this single score:
          - confidence ≥ 0.50 = Direct (highly applicable)
          - confidence ≥ 0.28 = Partial (moderately applicable)
          - else = Weak (low applicability)
        """
        for clause in clauses:
            semantic = clause.get("semantic_score", 0.0)
            relevance = clause.get("relevance_score", 0.0)
            law_priority = clause.get("law_priority", 3)

            # Normalize law_priority to 0-1 range (max is 5)
            norm_priority = min(1.0, law_priority / 5.0)

            # Single unified confidence score
            confidence = (relevance * 0.50) + (semantic * 0.30) + (norm_priority * 0.20)
            confidence = min(1.0, max(0.0, confidence))

            clause["confidence"] = round(confidence, 2)
            
            # Applicability derived from same confidence score (consistent logic)
            if confidence >= 0.50:
                clause["applicability"] = "Direct"
            elif confidence >= 0.28:
                clause["applicability"] = "Partial"
            else:
                clause["applicability"] = "Weak"

        # Sort by confidence (highest first)
        clauses.sort(key=lambda c: c["confidence"], reverse=True)
        
        return clauses

    def group_by_law(self, filtered_clauses: List[Dict]) -> Dict[str, List[Dict]]:
        """Group filtered clauses by law_code for display."""
        groups: Dict[str, List[Dict]] = {}
        for clause in filtered_clauses:
            code = clause.get("law_code", "OTHER")
            groups.setdefault(code, []).append(clause)
        return groups
