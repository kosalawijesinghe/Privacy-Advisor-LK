"""
Module 3 — Scenario Construction Engine
=========================================
Converts raw validated inputs into a meaningful natural-language incident
description. This is the core logic that makes the system scenario-based
rather than tag-based.

Instead of processing individual tags, this module builds a contextual
scenario describing the event, enabling downstream NLP/legal reasoning
to understand the full situation.

Example output:
  "Personal data including name, phone number and email address has been
   exposed online. The exposed information includes impersonation activity
   on a social media platform."
"""

from typing import List, Dict


# Natural-language fragments for each PII type
_PII_DESCRIPTIONS = {
    "name":     "full legal name",
    "id":       "national identity card (NIC) number",
    "phone":    "phone number",
    "email":    "email address",
    "addr":     "physical/residential address",
    "dob":      "date of birth",
    "username": "online username or account handle",
    "location": "location/GPS data",
}

# Context sentences for incident indicators
_INDICATOR_CONTEXT = {
    "impersonate": "There is evidence of active impersonation — someone is pretending to be the victim using their personal data.",
    "img_exposed": "A personal image or photograph of the victim has been shared publicly without consent.",
}

# Scenario-level context based on incident category
_CATEGORY_CONTEXT = {
    "IDENTITY_IMPERSONATION": (
        "This incident involves active identity impersonation, where the victim's "
        "personal information is being used to fraudulently assume their identity. "
        "This constitutes a criminal offence under Sri Lankan law."
    ),
    "IMAGE_ABUSE": (
        "This incident involves the unauthorized sharing or misuse of personal "
        "images or photographs, potentially constituting harassment or a violation "
        "of privacy rights."
    ),
    "ACCOUNT_MISUSE": (
        "This incident involves compromised account credentials and contact "
        "channels, creating risk of unauthorized access, credential stuffing, "
        "or account hijacking."
    ),
    "DATABASE_BREACH": (
        "This incident involves exposure of multiple categories of personal data "
        "simultaneously, indicating a potential database breach or large-scale "
        "data leak."
    ),
    "UNAUTHORIZED_DATA_PROCESSING": (
        "This incident involves personal data being processed, disclosed, or "
        "shared without lawful basis or consent, including potential doxxing "
        "or surveillance."
    ),
    "DATA_EXPOSURE": (
        "This incident involves the unauthorized exposure of personally "
        "identifiable information, which may be used for various forms of misuse."
    ),
    "DOXXING": (
        "This incident involves the deliberate public exposure of private "
        "personal information such as home address, phone number, or identity "
        "details, intended to facilitate harassment, intimidation, or harm."
    ),
    "HARASSMENT": (
        "This incident involves online harassment, cyberbullying, or threats "
        "using the victim's personal information, images, or private data, "
        "potentially including non-consensual sharing of intimate content."
    ),
    "IDENTITY_THEFT": (
        "This incident involves the fraudulent use of stolen personal data "
        "such as NIC numbers or identity documents to impersonate the victim "
        "for financial gain or other criminal purposes."
    ),
    "ACCOUNT_TAKEOVER": (
        "This incident involves the unauthorized access to and hijacking of "
        "online accounts, including email, social media, banking, or "
        "telecommunications accounts, through credential theft or exploitation."
    ),
}

# Combination patterns that produce richer context
_COMBINATION_CONTEXT = {
    frozenset({"name", "id"}): (
        "The combination of full name and NIC number creates a direct "
        "identity theft risk, as these together can be used to impersonate "
        "the victim in official or financial contexts."
    ),
    frozenset({"name", "id", "impersonate"}): (
        "An unauthorized party is actively using the victim's name and "
        "national ID to assume their identity, which constitutes a serious "
        "identity fraud scenario."
    ),
    frozenset({"email", "phone"}): (
        "Both primary contact channels are compromised, enabling multi-vector "
        "social engineering attacks such as phishing and pretexting."
    ),
    frozenset({"addr", "location"}): (
        "Both residential address and location data are exposed, creating a "
        "significant physical safety risk."
    ),
    frozenset({"username", "email"}): (
        "The pairing of online handle with email address facilitates credential "
        "stuffing and account recovery attacks."
    ),
    frozenset({"img_exposed", "name"}): (
        "A personal photograph linked to the victim's real name enables "
        "visual identification and targeted harassment."
    ),
    frozenset({"img_exposed", "impersonate"}): (
        "Personal images combined with impersonation activity suggests the "
        "creation of fake profiles using the victim's likeness."
    ),
}


# Legal-domain hints — vocabulary fragments that help surface clauses
# from specific laws via embedding similarity.  Triggered by tag patterns.
_LEGAL_DOMAIN_HINTS = [
    {
        # Telecom Act relevance when phone number is involved
        "check": lambda tags, imp, img: "phone" in set(tags),
        "text": (
            "The involvement of telephone or telecommunication channels "
            "may engage provisions regarding interception of messages, "
            "telecom identity fraud, and unauthorized use of "
            "telecommunication services."
        ),
    },
    {
        # Computer Crimes Act relevance for multi-PII breaches
        "check": lambda tags, imp, img: (
            sum(1 for t in tags if t not in ("impersonate", "img_exposed")) >= 2
        ),
        "text": (
            "The breadth of exposed data suggests unauthorized access to "
            "computer systems and dealing with unlawfully obtained "
            "information, which may constitute computer crimes."
        ),
    },
    {
        # Online Safety Act — harassment patterns (contact info + name)
        "check": lambda tags, imp, img: (
            bool(set(tags) & {"addr", "phone", "email"})
            and "name" in set(tags)
            and not imp
        ),
        "text": (
            "The exposure of personal contact details alongside identity "
            "information may facilitate cyberstalking, online harassment, "
            "or threatening and coercive communications."
        ),
    },
    {
        # Data-protection emphasis for impersonation with many PII tags
        "check": lambda tags, imp, img: (
            imp
            and sum(1 for t in tags if t not in ("impersonate", "img_exposed")) >= 3
        ),
        "text": (
            "Despite the impersonation element, the volume of exposed "
            "personal data also raises data protection concerns regarding "
            "purpose limitation, data security, and the data subject's "
            "right of access and erasure."
        ),
    },
]


# ── Scenario detection rules (priority-ordered) ─────────────────────────────
# Each rule has a check function that returns True/False and a confidence
# weighting function.  A single incident can match multiple scenarios.

_SCENARIO_RULES: List[Dict] = [
    {
        "key": "IDENTITY_IMPERSONATION",
        "check": lambda tags, imp, img, plat: "impersonate" in tags,
        "confidence": lambda tags, imp, img, plat: (
            0.95 if {"name", "id"} & set(tags) else 0.82
        ),
    },
    {
        "key": "IMAGE_ABUSE",
        "check": lambda tags, imp, img, plat: "img_exposed" in tags,
        "confidence": lambda tags, imp, img, plat: (
            0.90 if plat else 0.78
        ),
    },
    {
        "key": "DATABASE_BREACH",
        "check": lambda tags, imp, img, plat: (
            sum(1 for t in tags if t not in ("impersonate", "img_exposed")) >= 5
        ),
        "confidence": lambda tags, imp, img, plat: (
            min(0.95, 0.60 + len(tags) * 0.05)
        ),
    },
    {
        "key": "ACCOUNT_MISUSE",
        "check": lambda tags, imp, img, plat: (
            "username" in set(tags) and set(tags) & {"email", "phone"}
        ),
        "confidence": lambda tags, imp, img, plat: (
            0.88 if plat else 0.75
        ),
    },
    {
        "key": "UNAUTHORIZED_DATA_PROCESSING",
        "check": lambda tags, imp, img, plat: bool(
            set(tags) & {"addr", "location"} and set(tags) & {"name", "id"}
        ),
        "confidence": lambda tags, imp, img, plat: 0.72,
    },
    {
        "key": "DATA_EXPOSURE",
        "check": lambda tags, imp, img, plat: len(tags) > 0,
        "confidence": lambda tags, imp, img, plat: (
            min(0.80, 0.40 + len(tags) * 0.08)
        ),
    },
]


class ScenarioBuilder:
    """
    Builds a contextual incident scenario description from structured inputs.
    This enables AI/NLP models and legal reasoning to understand the full
    situation rather than processing individual tags.

    Supports detecting multiple concurrent scenarios with individual
    confidence scores.
    """

    def build_scenario(
        self,
        validated_input: Dict,
        user_description: str = "",
    ) -> Dict:
        """
        Construct a scenario description from validated input.

        Parameters
        ----------
        validated_input : dict
            Output from InputValidator.validate()
        user_description : str, optional
            Free-text incident description provided by the user.
            Appended to the generated scenario to enrich semantic matching.

        Returns
        -------
        dict with keys:
            scenario_description : str — full natural-language incident description
            incident_category : str — primary category from validation
            pii_summary : str — human-readable list of exposed data
            indicator_summary : str — summary of flags/indicators
            key_combinations : list[str] — detected high-risk combinations
            detected_scenarios : list[dict] — all matching scenarios with confidence
                Each entry: {"key": str, "confidence": float, "title": str}
        """
        tags = validated_input.get("normalized_tags", [])
        impersonate = "impersonate" in tags
        img_exposed = "img_exposed" in tags
        platform = validated_input.get("platform", "")
        category = validated_input.get("incident_category", "pii_exposure")

        # Build the set of all active inputs for combination matching
        all_active = set(tags)

        parts: List[str] = []

        # 1. Opening statement with PII summary
        pii_summary = self._build_pii_summary(tags)
        if pii_summary:
            parts.append(f"Personal data including {pii_summary} has been exposed without authorization.")

        # 2. Indicator context
        indicator_parts = []
        if impersonate:
            parts.append(_INDICATOR_CONTEXT["impersonate"])
            indicator_parts.append("impersonation activity")
        if img_exposed:
            plat_str = f" on {platform}" if platform else ""
            parts.append(f"A personal image or photograph has been shared publicly{plat_str} without consent.")
            indicator_parts.append("image exposure")

        # 3. Platform context
        if platform:
            parts.append(f"The incident occurred on or was disseminated via {platform}.")

        # 4. Combination-specific context
        key_combos = []
        for combo_set, context in _COMBINATION_CONTEXT.items():
            if combo_set.issubset(all_active):
                parts.append(context)
                key_combos.append(", ".join(sorted(combo_set)))

        # 5. Category-level context (add context for ALL matching scenarios)
        detected = self.detect_scenarios(validated_input)
        for sc in detected:
            sc_key = sc["key"]
            if sc_key in _CATEGORY_CONTEXT and sc_key != category:
                parts.append(_CATEGORY_CONTEXT[sc_key])
        if category in _CATEGORY_CONTEXT:
            parts.append(_CATEGORY_CONTEXT[category])

        # 6. Legal domain hints — add vocabulary for TCA / CCA / OSA / PDPA
        for hint in _LEGAL_DOMAIN_HINTS:
            if hint["check"](tags, impersonate, img_exposed):
                parts.append(hint["text"])

        # Fallback if somehow empty
        if not parts:
            parts.append("A data exposure incident has been reported. Details are pending assessment.")

        # Blend user's free-text description for richer semantic matching
        if user_description and user_description.strip():
            parts.append(f"Victim's account: {user_description.strip()}")

        scenario_description = " ".join(parts)
        indicator_summary = " and ".join(indicator_parts) if indicator_parts else "none detected"

        return {
            "scenario_description": scenario_description,
            "incident_category": category,
            "pii_summary": pii_summary or "no specific PII identified",
            "indicator_summary": indicator_summary,
            "key_combinations": key_combos,
            "detected_scenarios": detected,
        }

    def detect_scenarios(self, validated_input: Dict) -> List[Dict]:
        """
        Detect all applicable scenario categories for the given inputs.

        Returns a list of dicts sorted by confidence (highest first):
            [{"key": "IDENTITY_IMPERSONATION", "confidence": 0.95}, ...]
        """
        tags = validated_input.get("normalized_tags", [])
        impersonate = "impersonate" in tags
        img_exposed = "img_exposed" in tags
        platform = validated_input.get("platform", "")

        matched = []
        for rule in _SCENARIO_RULES:
            if rule["check"](tags, impersonate, img_exposed, platform):
                conf = rule["confidence"](tags, impersonate, img_exposed, platform)
                matched.append({
                    "key": rule["key"],
                    "confidence": round(conf, 2),
                })

        # Always include DATA_EXPOSURE as base if nothing else matched
        if not matched and tags:
            matched.append({"key": "DATA_EXPOSURE", "confidence": 0.50})

        matched.sort(key=lambda s: s["confidence"], reverse=True)
        return matched

    def _build_pii_summary(self, tags: List[str]) -> str:
        """Build a human-readable comma-separated list of exposed PII types."""
        if not tags:
            return ""
        descriptions = [_PII_DESCRIPTIONS.get(t, t) for t in tags]
        if len(descriptions) == 1:
            return descriptions[0]
        return ", ".join(descriptions[:-1]) + " and " + descriptions[-1]
