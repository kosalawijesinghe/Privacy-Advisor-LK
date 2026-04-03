"""
Module 4 — Scenario Severity Evaluation
=========================================
Evaluates the severity level of a data exposure incident based on multiple
risk indicators.

Severity indicators:
  - Number of exposed PII items
  - Identity impersonation
  - Exposure of personal images
  - Use of an online platform
  - Combination of multiple risk indicators

Classification:
  - Critical (70+)
  - High (50-69)
  - Moderate (30-49)
  - Low (0-29)
"""

from typing import List, Dict


# Weight assigned to each tag (PII + incident indicators)
_TAG_WEIGHTS = {
    "impersonate": 25,   # highest risk — active identity fraud
    "img_exposed": 20,   # high risk — image/photo abuse
    "id": 25,
    "phone": 20,
    "addr": 15,
    "dob": 15,
    "email": 10,
    "name": 10,
    "location": 10,
    "username": 5,
}

# Multiple PII bonus (+3 per extra after first)
_MULTI_PII_BONUS_PER_TAG = 3
_MULTI_PII_THRESHOLD = 2  # bonus starts after this many tags

# Platform exposure bonus
_PLATFORM_BONUS = 12

# Bonus for dangerous combinations
_COMBINATION_BONUSES = [
    {"requires_all": ["id", "name"], "bonus": 10, "label": "Identity Theft Combo (ID + Name)"},
    {"requires_all": ["id", "impersonate"], "bonus": 15, "label": "Active Identity Fraud (ID + Impersonation)"},
    {"requires_all": ["name", "impersonate"], "bonus": 10, "label": "Name-based Impersonation"},
    {"requires_all": ["email", "phone"], "bonus": 5, "label": "Multi-Channel Contact Exposure"},
    {"requires_all": ["addr", "name"], "bonus": 8, "label": "Named Address Exposure (Doxxing Risk)"},
]

# Volume bonus when many PII types are exposed
_VOLUME_THRESHOLD = 5
_VOLUME_BONUS = 10

# Severity classification thresholds (checked in order, first match wins)
_SEVERITY_LEVELS = [
    {"min_score": 70, "level": "Critical", "color": "#ef4444"},
    {"min_score": 50, "level": "High", "color": "#f97316"},
    {"min_score": 30, "level": "Moderate", "color": "#FFD700"},
    {"min_score": 0,  "level": "Low", "color": "#22c55e"},
]


class SeverityAnalyzer:
    """Evaluates incident severity from validated inputs and scenario data."""

    def analyze(self, validated_input: Dict) -> Dict:
        """
        Calculate severity score and classify the incident.

        Parameters
        ----------
        validated_input : dict
            Output from InputValidator.validate()

        Returns
        -------
        dict with keys:
            score : int — 0 to 100
            level : str — "Critical" | "High" | "Moderate" | "Low"
            color : str — hex color for UI
            contributors : list[dict] — each factor's weight and label
            normalized : float — score / 100 for use in ranking formula
        """
        tags = validated_input.get("normalized_tags", [])
        platform = validated_input.get("platform", "")

        score = 0
        contributors: List[Dict] = []

        # Tag weights (PII + indicators are unified)
        for tag in tags:
            weight = _TAG_WEIGHTS.get(tag, 0)
            if weight > 0:
                score += weight
                contributors.append({"factor": f"Exposed {tag}", "weight": weight})

        # Platform exposure bonus — public platform increases risk
        if platform:
            score += _PLATFORM_BONUS
            contributors.append({"factor": f"Public platform exposure ({platform})", "weight": _PLATFORM_BONUS})

        # Multiple PII bonus (count only actual PII, not indicator tags)
        pii_tags = [t for t in tags if t not in ("impersonate", "img_exposed")]
        if len(pii_tags) >= _MULTI_PII_THRESHOLD:
            extra_tags = len(pii_tags) - _MULTI_PII_THRESHOLD + 1
            multi_bonus = extra_tags * _MULTI_PII_BONUS_PER_TAG
            score += multi_bonus
            contributors.append({"factor": f"Multiple PII types exposed ({len(pii_tags)})", "weight": multi_bonus})

        # Combination bonuses
        all_active = set(tags)
        if validated_input.get("impersonate"):
            all_active.add("impersonate")
        if validated_input.get("img_exposed"):
            all_active.add("img_exposed")

        for combo in _COMBINATION_BONUSES:
            if all(t in all_active for t in combo["requires_all"]):
                score += combo["bonus"]
                contributors.append({"factor": combo["label"], "weight": combo["bonus"]})

        # Volume bonus (PII tags only)
        if len(pii_tags) >= _VOLUME_THRESHOLD:
            score += _VOLUME_BONUS
            contributors.append({"factor": f"High volume of data types ({len(tags)}+)", "weight": _VOLUME_BONUS})

        # Minimum severity floors for indicator-only scenarios
        # (active threats like impersonation should never score Low)
        if "impersonate" in tags:
            score = max(score, 40)   # at least High when alone
        if "img_exposed" in tags:
            score = max(score, 35)   # at least Moderate when alone

        # Cap at 100
        final_score = min(score, 100)

        # Classify severity
        level = "Low"
        color = "#22c55e"
        for threshold in _SEVERITY_LEVELS:
            if final_score >= threshold["min_score"]:
                level = threshold["level"]
                color = threshold["color"]
                break

        return {
            "score": final_score,
            "level": level,
            "color": color,
            "contributors": contributors,
            "normalized": round(final_score / 100.0, 2),
        }
