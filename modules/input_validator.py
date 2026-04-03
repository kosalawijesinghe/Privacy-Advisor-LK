"""
Module 2 — Input Validation and Normalization
===============================================
Validates and normalizes user-submitted incident data before any analysis.

Responsibilities:
  - Check for empty or missing fields
  - Normalize input formats
  - Verify at least one relevant indicator exists
  - Categorize inputs into: PII exposure, identity misuse, or platform-based
  - Return "no legal relevance" when no indicators are present
"""

from typing import List, Dict

# Recognized PII tag keys (includes incident indicators treated as high-priority tags)
VALID_TAGS = {"name", "id", "phone", "email", "addr", "dob", "username", "location",
              "impersonate", "img_exposed"}

# Human-readable labels for PII tags
TAG_LABELS = {
    "name": "Full Name",
    "id": "National ID / NIC",
    "phone": "Phone Number",
    "email": "Email Address",
    "addr": "Physical Address",
    "dob": "Date of Birth",
    "username": "Username / Handle",
    "location": "Location Data",
    "impersonate": "Impersonation",
    "img_exposed": "Image / Photo Exposed",
}


class InputValidator:
    """Validates, normalizes, and categorizes user incident inputs."""

    def validate(
        self,
        tags: List[str],
        impersonate: bool = False,
        img_exposed: bool = False,
        platform: str = "",
    ) -> Dict:
        """
        Validate and normalize user inputs.

        Returns
        -------
        dict with keys:
            is_valid : bool — True if at least one relevant indicator exists
            normalized_tags : list[str] — cleaned, deduplicated tag list
            impersonate : bool
            img_exposed : bool
            platform : str — cleaned platform name
            incident_category : str — scenario key (IDENTITY_IMPERSONATION | IMAGE_ABUSE | ACCOUNT_MISUSE | DATABASE_BREACH | UNAUTHORIZED_DATA_PROCESSING | DATA_EXPOSURE | no_relevance)
            warnings : list[str] — issues found during validation
            pii_count : int — number of PII fields selected
        """
        warnings: List[str] = []

        # Normalize tags: lowercase, strip, deduplicate, filter invalid
        normalized = []
        seen = set()
        for tag in tags:
            t = tag.strip().lower()
            if t and t in VALID_TAGS and t not in seen:
                normalized.append(t)
                seen.add(t)
            elif t and t not in VALID_TAGS:
                warnings.append(f"Unrecognized input tag: '{t}'")

        # Fold boolean indicators into the tag list (high-priority tags)
        if impersonate and "impersonate" not in seen:
            normalized.append("impersonate")
            seen.add("impersonate")
        if img_exposed and "img_exposed" not in seen:
            normalized.append("img_exposed")
            seen.add("img_exposed")

        # Derive booleans from the authoritative tag list
        impersonate = "impersonate" in seen
        img_exposed = "img_exposed" in seen

        # Normalize platform
        platform_clean = platform.strip() if platform else ""

        # Check if any relevant indicator exists
        has_any = len(normalized) > 0

        if not has_any:
            return {
                "is_valid": False,
                "normalized_tags": [],
                "impersonate": False,
                "img_exposed": False,
                "platform": "",
                "incident_category": "no_relevance",
                "warnings": ["No PII tags or incident indicators provided. Cannot perform legal analysis."],
                "pii_count": 0,
            }

        # Categorize the incident
        category = self._categorize(normalized, impersonate, img_exposed, platform_clean)

        # Additional validation warnings
        if img_exposed and not platform_clean:
            warnings.append("Image exposure indicated but no platform specified.")

        # PII count excludes indicator tags
        pii_count = sum(1 for t in normalized if t not in ("impersonate", "img_exposed"))

        return {
            "is_valid": True,
            "normalized_tags": normalized,
            "impersonate": impersonate,
            "img_exposed": img_exposed,
            "platform": platform_clean,
            "incident_category": category,
            "warnings": warnings,
            "pii_count": pii_count,
        }

    def _categorize(
        self,
        tags: List[str],
        impersonate: bool,
        img_exposed: bool,
        platform: str,
    ) -> str:
        """
        Classify incident into one of 6 scenario categories:
          - IDENTITY_IMPERSONATION: active impersonation/fraud
          - IMAGE_ABUSE: unauthorized image sharing
          - ACCOUNT_MISUSE: account credentials at risk
          - DATABASE_BREACH: mass data exposure (5+ PII types)
          - UNAUTHORIZED_DATA_PROCESSING: data processing without consent
          - DATA_EXPOSURE: general PII exposure
        """
        tag_set = set(tags)
        # Exclude indicator tags from PII-count-based rules
        pii_tags = tag_set - {"impersonate", "img_exposed"}

        if impersonate:
            return "IDENTITY_IMPERSONATION"

        if img_exposed:
            return "IMAGE_ABUSE"

        if "username" in pii_tags and pii_tags & {"email", "phone"}:
            return "ACCOUNT_MISUSE"

        if len(pii_tags) >= 5:
            return "DATABASE_BREACH"

        if pii_tags & {"addr", "location"} and pii_tags & {"name", "id"}:
            return "UNAUTHORIZED_DATA_PROCESSING"

        return "DATA_EXPOSURE"
