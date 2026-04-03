"""
Incident-to-Law Mapping Engine
===============================
Maps incident types to their most relevant laws for accurate ranking.
Used as a boost signal in the relevance scorer to improve law coverage accuracy.

Maps each incident class to expected laws, with confidence scores.
Boosts clauses from expected laws during re-ranking.
"""

from typing import Dict, List, Set, Optional, Tuple


class IncidentLawMapper:
    """
    Maps incident types to their corresponding Sri Lanka statutes.
    Provides boost signals for re-ranking to improve accuracy.
    """

    # Incident type → Expected laws with confidence boost
    # Maps both pipeline incident types AND training data types
    INCIDENT_LAW_MAP = {
        # ─── Pipeline Incident Types ───
        "DATA_EXPOSURE": {
            "PDPA": 0.95,      # Data Protection Act - PRIMARY
            "TCA": 0.70,       # Telecom Act - related to exposure
            "CCA": 0.60,       # Computer Crimes Act - unauthorized access
        },
        "ACCOUNT_TAKEOVER": {
            "CCA": 0.95,       # Computer Crimes Act - unauthorized access PRIMARY
            "ETA": 0.80,       # Electronic Transactions Act - account related
            "PDPA": 0.60,      # Data Protection - if personal data involved
            "TCA": 0.50,       # Telecom - if telecom account
        },
        "IDENTITY_THEFT": {
            "CCA": 0.85,       # Computer Crimes Act - unauthorized access to identity
            "PDPA": 0.85,      # Data Protection Act - personal data abuse
            "TCA": 0.75,       # Telecom - identity used for telecom fraud
            "OSA": 0.65,       # Online Safety Act - identity misuse online
        },
        "IMPERSONATION": {
            "OSA": 0.95,       # Online Safety Act - PRIMARY for personation
            "CCA": 0.85,       # Computer Crimes Act - unauthorized access/misuse
            "TCA": 0.80,       # Telecom Act - telecom-based impersonation
            "PDPA": 0.60,      # Data Protection - personal data misuse
        },
        "IMAGE_ABUSE": {
            "OSA": 0.95,       # Online Safety Act - PRIMARY for image abuse
            "PDPA": 0.80,      # Data Protection - personal data/image
            "CCA": 0.70,       # Computer Crimes Act - authorized access
        },
        "HARASSMENT": {
            "OSA": 0.90,       # Online Safety Act - PRIMARY for harassment
            "TCA": 0.85,       # Telecom Act - harassment via telecom
            "CCA": 0.65,       # Computer Crimes Act - if computer-based
            "PDPA": 0.50,      # Data Protection - if personal data involved
        },
        "DOXXING": {
            "OSA": 0.95,       # Online Safety Act - PRIMARY for doxxing
            "PDPA": 0.85,      # Data Protection - personal information disclosed
            "CCA": 0.75,       # Computer Crimes Act - unauthorized disclosure
        },
        # ─── Training Data Incident Types (fallback mapping) ───
        "PERSONAL_DATA_BREACH": {  # Maps to DATA_EXPOSURE
            "PDPA": 0.95,
            "TCA": 0.70,
            "CCA": 0.60,
        },
        "UNAUTHORIZED_ACCESS": {  # Maps to ACCOUNT_TAKEOVER
            "CCA": 0.95,
            "ETA": 0.80,
            "PDPA": 0.60,
            "TCA": 0.50,
        },
        "TELECOMMUNICATIONS": {  # Maps to HARASSMENT
            "TCA": 0.95,
            "OSA": 0.85,
            "CCA": 0.65,
            "PDPA": 0.50,
        },
        "ELECTRONIC_TRANSACTIONS": {  # Maps to ACCOUNT_TAKEOVER
            "ETA": 0.95,
            "CCA": 0.85,
            "PDPA": 0.60,
        },
        "RIGHT_TO_INFORMATION": {  # Maps to DOXXING/DATA_EXPOSURE
            "RTI": 0.95,
            "PDPA": 0.85,
            "OSA": 0.75,
        },
        "UNKNOWN": {
            # Fallback for unclassified incidents - prioritize privacy-centric laws
            "PDPA": 0.70,      # Data protection is primary for any PII incident
            "OSA": 0.70,       # Online safety for any online incident
            "CCA": 0.55,       # Computer crimes secondary
            "TCA": 0.55,       # Telecom secondary
        },
    }

    # Law abbreviation mapping
    LAW_NAMES = {
        "PDPA": "Personal Data Protection Act",
        "CCA": "Computer Crimes Act",
        "TCA": "Telecom Act",
        "OSA": "Online Safety Act",
        "ETA": "Electronic Transactions Act",
        "RTI": "Right to Information Act",
    }

    def __init__(self):
        """Initialize mapper with incident-law relationships."""
        self._map = self.INCIDENT_LAW_MAP
        self._law_names = self.LAW_NAMES

    def get_expected_laws(
        self,
        incident_type: str,
        confidence_threshold: float = 0.5,
    ) -> Dict[str, float]:
        """
        Get expected laws for an incident type with confidence scores.

        Args:
            incident_type: Classification result (e.g., 'DATA_EXPOSURE', 'UNKNOWN')
            confidence_threshold: Minimum confidence to include (0.0-1.0)

        Returns:
            Dict mapping law abbreviations to confidence scores
        """
        incident_type = incident_type.upper()
        
        # Fallback to UNKNOWN if not in map
        if incident_type not in self._map:
            incident_type = "UNKNOWN"
        
        laws = self._map[incident_type]
        
        # Filter by confidence threshold
        filtered = {
            law: conf
            for law, conf in laws.items()
            if conf >= confidence_threshold
        }
        
        return filtered

    def get_boost_factor(
        self,
        incident_type: str,
        law_abbr: str,
        base_confidence: float = 0.5,
    ) -> float:
        """
        Calculate boost factor for a specific law in this incident context.

        Args:
            incident_type: Classification result
            law_abbr: Law abbreviation (e.g., 'PDPA')
            base_confidence: Base score to apply boost to

        Returns:
            Boosted score (0.0-1.0)
        """
        incident_type = incident_type.upper()
        law_abbr = law_abbr.upper()
        
        if incident_type not in self._map:
            incident_type = "UNKNOWN"
        
        laws = self._map[incident_type]
        
        # Get configured boost for this law
        configured_boost = laws.get(law_abbr, 0.0)
        
        # Apply as multiplicative boost
        # Higher configured_boost = stronger boost to the score
        boosted = base_confidence * (1.0 + (configured_boost - 0.5) * 0.5)
        
        return max(0.0, min(1.0, boosted))

    def get_law_priority_order(self, incident_type: str) -> List[Tuple[str, float]]:
        """
        Get laws ranked by priority for this incident type.

        Args:
            incident_type: Classification result

        Returns:
            List of (law_abbr, priority_score) tuples sorted by priority
        """
        incident_type = incident_type.upper()
        
        if incident_type not in self._map:
            incident_type = "UNKNOWN"
        
        laws = self._map[incident_type]
        ranked = sorted(laws.items(), key=lambda x: x[1], reverse=True)
        
        return ranked

    def is_law_relevant(
        self,
        incident_type: str,
        law_abbr: str,
        confidence_threshold: float = 0.6,
    ) -> bool:
        """Check if a law is relevant for this incident type."""
        expected_laws = self.get_expected_laws(incident_type, 0.0)
        law_abbr = law_abbr.upper()
        
        return expected_laws.get(law_abbr, 0.0) >= confidence_threshold

    def summarize_mapping(self, incident_type: str) -> str:
        """Return human-readable summary of law mapping."""
        incident_type = incident_type.upper()
        
        if incident_type not in self._map:
            incident_type = "UNKNOWN"
        
        laws = self.get_law_priority_order(incident_type)
        
        if not laws:
            return f"{incident_type}: No laws mapped"
        
        lines = [f"📋 {incident_type} → Expected Laws:"]
        for law_abbr, priority in laws[:3]:  # Top 3
            law_name = self._law_names.get(law_abbr, law_abbr)
            confidence = int(priority * 100)
            lines.append(f"  • {law_abbr} ({law_name}): {confidence}%")
        
        return "\n".join(lines)


# Singleton instance
_mapper = None


def get_incident_law_mapper() -> IncidentLawMapper:
    """Get or create the incident law mapper singleton."""
    global _mapper
    if _mapper is None:
        _mapper = IncidentLawMapper()
    return _mapper
