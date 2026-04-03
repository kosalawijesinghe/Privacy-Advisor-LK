"""
Compliance Alert Generator — FR8
===================================
Converts pipeline output into structured compliance alert objects.

Each alert captures violation details, applicable laws, severity,
recommendations count, and an explainability summary — providing
a machine-readable and human-readable incident report.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List

_SEVERITY_TO_RISK: Dict[str, str] = {
    "Critical": "HIGH_RISK",
    "High":     "HIGH_RISK",
    "Moderate": "MEDIUM_RISK",
    "Low":      "LOW_RISK",
}

_RISK_DESCRIPTIONS: Dict[str, str] = {
    "HIGH_RISK":   "Immediate action required. Serious legal exposure under Sri Lankan law.",
    "MEDIUM_RISK": "Significant privacy concerns detected. Prompt action recommended.",
    "LOW_RISK":    "Minor privacy considerations. Review recommended.",
    "NO_RISK":     "No violations detected based on provided information.",
}


class ComplianceAlert:
    """
    Generates structured compliance alert objects from pipeline results.
    Fulfils FR8: Compliance Alert Generation.
    """

    def generate(self, pipeline_result: Dict) -> Dict:
        """
        Convert a pipeline result dict into a compliance alert.

        Returns
        -------
        dict with keys:
            alert_id            : str UUID
            timestamp           : ISO 8601
            risk_level          : str (HIGH_RISK / MEDIUM_RISK / LOW_RISK / NO_RISK)
            risk_description    : str
            severity_score      : int (0–100)
            severity_level      : str
            exposed_data_types  : list[str]
            violations          : list of violation dicts
            applicable_laws     : list[str] of law codes
            recommendations_count : int
            detected_scenarios  : list[str]
            explainability_summary : str
            coverage            : int (number of violated clauses)
        """
        alert_id  = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        if not pipeline_result.get("valid"):
            return {
                "alert_id":               alert_id,
                "timestamp":              timestamp,
                "risk_level":             "NO_RISK",
                "risk_description":       _RISK_DESCRIPTIONS["NO_RISK"],
                "severity_score":         0,
                "severity_level":         "Low",
                "exposed_data_types":     [],
                "violations":             [],
                "applicable_laws":        [],
                "recommendations_count":  0,
                "detected_scenarios":     [],
                "explainability_summary": "Insufficient data to generate a compliance alert.",
                "coverage":               0,
            }

        severity  = pipeline_result.get("severity", {})
        clauses   = pipeline_result.get("matched_clauses", [])
        recs      = pipeline_result.get("recommendations", [])
        scenarios = pipeline_result.get("detected_scenarios", [])
        validated = pipeline_result.get("validated_input", {})
        tags      = validated.get("normalized_tags", [])

        violations: List[Dict] = [
            {
                "law_code":    c.get("law_code"),
                "law_name":    c.get("law_name"),
                "section":     c.get("section"),
                "title":       c.get("title"),
                "penalty":     c.get("penalty"),
                "confidence":  round(c.get("confidence", 0.0), 3),
                "matched_tags": c.get("matched_tags", []),
            }
            for c in clauses
        ]

        applicable_laws = sorted({c.get("law_code") for c in clauses if c.get("law_code")})
        risk_level      = _SEVERITY_TO_RISK.get(severity.get("level", "Low"), "LOW_RISK")

        # Build explainability summary from top clause
        top_clause = clauses[0] if clauses else {}
        expl       = top_clause.get("explanation_text", {})
        summary    = (
            expl.get("why_relevant")
            or top_clause.get("reason")
            or top_clause.get("explanation")
            or (f"{len(violations)} legal provision(s) triggered across {len(applicable_laws)} act(s)."
                if violations else "No violations detected.")
        )

        return {
            "alert_id":               alert_id,
            "timestamp":              timestamp,
            "risk_level":             risk_level,
            "risk_description":       _RISK_DESCRIPTIONS.get(risk_level, ""),
            "severity_score":         severity.get("score", 0),
            "severity_level":         severity.get("level", "Low"),
            "exposed_data_types":     tags,
            "violations":             violations,
            "applicable_laws":        applicable_laws,
            "recommendations_count":  len(recs),
            "detected_scenarios":     [s.get("key") for s in scenarios],
            "explainability_summary": summary,
            "coverage":               len(violations),
        }
