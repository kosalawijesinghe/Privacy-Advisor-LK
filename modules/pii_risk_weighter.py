"""
PII Risk Weighting System
===========================
Assigns risk levels and scores to PII types.

Risk scores influence:
  - Severity calculation
  - Clause ranking
  - Recommendation priority

Risk Levels:
  Low      → 0.2-0.3
  Medium   → 0.4-0.6
  High     → 0.7-0.8
  Critical → 0.9-1.0
"""

from typing import Dict, List


# ── PII Risk Definitions ─────────────────────────────────────────────────────

PII_RISK_LEVELS: Dict[str, Dict] = {
    # Critical — active harm or irreversible damage
    "impersonate": {
        "risk_level": "Critical",
        "risk_score": 1.0,
        "description": "Active impersonation — someone is already pretending to be the victim",
    },
    "img_exposed": {
        "risk_level": "Critical",
        "risk_score": 0.95,
        "description": "Personal image exposed — immediate irreversible harm once shared",
    },
    "id": {
        "risk_level": "Critical",
        "risk_score": 0.85,
        "description": "National Identity Card / NIC number — permanent identifier, serious but needs other data to exploit alone",
    },
    "dob": {
        "risk_level": "High",
        "risk_score": 0.65,
        "description": "Date of birth — permanent personal fact, but semi-public and limited standalone harm",
    },
    "addr": {
        "risk_level": "High",
        "risk_score": 0.80,
        "description": "Physical address — direct physical safety threat, someone can locate you",
    },

    # Medium — moderate standalone harm
    "phone": {
        "risk_level": "Medium",
        "risk_score": 0.60,
        "description": "Phone number — enables unwanted contact, harassment, and spam",
    },
    "email": {
        "risk_level": "Medium",
        "risk_score": 0.50,
        "description": "Email address — enables spam and targeted phishing messages",
    },

    # Low — limited standalone risk
    "name": {
        "risk_level": "Low",
        "risk_score": 0.30,
        "description": "Full name — publicly knowable, limited direct harm alone",
    },
    "location": {
        "risk_level": "Medium",
        "risk_score": 0.50,
        "description": "GPS/location data — reveals whereabouts, direct privacy violation",
    },
    "username": {
        "risk_level": "Low",
        "risk_score": 0.25,
        "description": "Online username — often publicly visible, limited direct harm",
    },
}

# Risk level thresholds
RISK_LEVEL_THRESHOLDS = {
    "Critical": 0.85,
    "High":     0.65,
    "Medium":   0.35,
    "Low":      0.0,
}


class PIIRiskWeighter:
    """
    Computes PII risk scores and applies them to the pipeline.
    """

    def __init__(self):
        self._risk_data = PII_RISK_LEVELS

    def get_risk_score(self, tag: str) -> float:
        """Get risk score for a single PII tag (0-1)."""
        return self._risk_data.get(tag, {}).get("risk_score", 0.30)

    def get_risk_level(self, tag: str) -> str:
        """Get risk level string for a single PII tag."""
        return self._risk_data.get(tag, {}).get("risk_level", "Low")

    def compute_aggregate_risk(self, tags: List[str]) -> Dict:
        """
        Compute aggregate PII risk from a list of tags.

        Returns
        -------
        dict with keys:
            max_risk_score : float — highest individual risk score
            max_risk_level : str   — highest risk level present
            mean_risk_score : float — average risk across all tags
            weighted_risk : float  — weighted combination favoring highest risks
            risk_breakdown : list[dict] — per-tag risk details
            combination_bonus : float — extra risk from dangerous combinations
        """
        if not tags:
            return {
                "max_risk_score": 0.0,
                "max_risk_level": "Low",
                "mean_risk_score": 0.0,
                "weighted_risk": 0.0,
                "risk_breakdown": [],
                "combination_bonus": 0.0,
            }

        breakdown = []
        scores = []
        for tag in tags:
            data = self._risk_data.get(tag, {})
            score = data.get("risk_score", 0.30)
            scores.append(score)
            breakdown.append({
                "tag": tag,
                "risk_score": score,
                "risk_level": data.get("risk_level", "Low"),
                "description": data.get("description", ""),
            })

        max_score = max(scores)
        mean_score = sum(scores) / len(scores)

        # Combination bonus for dangerous PII combos
        tag_set = set(tags)
        combo_bonus = self._compute_combination_bonus(tag_set)

        # Weighted risk: 60% max + 30% mean + 10% combo
        weighted = 0.60 * max_score + 0.30 * mean_score + 0.10 * combo_bonus
        weighted = min(1.0, weighted)

        # Determine max risk level
        max_level = "Low"
        for level, threshold in sorted(
            RISK_LEVEL_THRESHOLDS.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            if max_score >= threshold:
                max_level = level
                break

        return {
            "max_risk_score": round(max_score, 3),
            "max_risk_level": max_level,
            "mean_risk_score": round(mean_score, 3),
            "weighted_risk": round(weighted, 3),
            "risk_breakdown": breakdown,
            "combination_bonus": round(combo_bonus, 3),
        }

    def _compute_combination_bonus(self, tag_set: set) -> float:
        """Extra risk from dangerous PII combinations."""
        bonus = 0.0
        if {"id", "name"} <= tag_set:
            bonus += 0.3  # Identity theft risk
        if {"id", "impersonate"} <= tag_set:
            bonus += 0.4  # Active identity fraud
        if {"addr", "name"} <= tag_set:
            bonus += 0.2  # Doxxing risk
        if {"email", "phone"} <= tag_set:
            bonus += 0.15  # Multi-channel exposure
        if {"img_exposed", "name"} <= tag_set:
            bonus += 0.2  # Visual identification
        if {"addr", "location"} <= tag_set:
            bonus += 0.25  # Physical safety
        return min(1.0, bonus)

    def apply_to_severity(self, severity_score: int, tags: List[str]) -> int:
        """
        Adjust severity score based on PII risk.
        Adds up to 15 points for high-risk PII.
        """
        risk = self.compute_aggregate_risk(tags)
        bonus = int(risk["weighted_risk"] * 15)
        return min(100, severity_score + bonus)

    def get_clause_ranking_boost(self, clause: Dict, tags: List[str]) -> float:
        """
        Compute a ranking boost for a clause based on PII risk.
        Higher risk PII that matches clause tags gets a larger boost.
        """
        clause_tags = set(clause.get("tags", []))
        user_tags = set(tags)
        overlap = clause_tags & user_tags

        if not overlap:
            return 0.0

        # Boost proportional to the riskiest overlapping tag
        max_overlap_risk = max(self.get_risk_score(t) for t in overlap)
        return round(max_overlap_risk * 0.08, 4)

    def get_recommendation_priority_boost(self, tags: List[str]) -> str:
        """
        Determine if recommendations should be escalated based on PII risk.
        Returns priority adjustment: 'ESCALATE', 'KEEP', or 'NONE'.
        """
        risk = self.compute_aggregate_risk(tags)
        if risk["max_risk_level"] == "Critical":
            return "ESCALATE"
        if risk["weighted_risk"] >= 0.65:
            return "ESCALATE"
        return "KEEP"
