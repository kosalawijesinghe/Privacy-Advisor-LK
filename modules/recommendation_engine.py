"""
Module 14 â€” Privacy & Security Recommendation Engine
======================================================
Generates actionable, scenario-aware recommendations based on:
  - Which PII fields were exposed
  - The incident category (scenario classification)
  - Severity level
  - Impersonation / image exposure flags
  - Platform involvement

Each recommendation includes:
  - action            : str        â€” what to do
  - priority          : str        â€” "URGENT" | "HIGH" | "MEDIUM" | "LOW"
  - category          : str        â€” grouping (e.g. "Account Security", "Legal Action")
  - triggers          : list       â€” which inputs caused this recommendation
  - linked_clauses    : list[dict] — legal clauses that triggered this action
"""

from typing import Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Recommendation catalog â€” each entry defines when it fires and what it says
# linked_clause_keys lists the legal clause keys (law:section) this rec relates to
# ---------------------------------------------------------------------------

_RECOMMENDATIONS = [
    # â”€â”€ Account Security â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "action": "Enable two-factor authentication (2FA) on all accounts associated with the exposed email or phone number.",
        "priority_base": "URGENT",
        "category": "Account Security",
        "requires_any_tag": ["email", "phone", "username"],
        "requires_indicator": [],
        "linked_clause_keys": ["CCA:3(a)", "CCA:3(b)", "ETA:7(a)"],
    },
    {
        "action": "Change passwords immediately for all accounts linked to the exposed credentials.",
        "priority_base": "URGENT",
        "category": "Account Security",
        "requires_any_tag": ["email", "username"],
        "requires_indicator": [],
        "linked_clause_keys": ["CCA:3(a)", "CCA:4(a)", "ETA:12(1)(a)"],
    },
    {
        "action": "Review and revoke any active sessions or third-party app permissions on affected accounts.",
        "priority_base": "MEDIUM",
        "category": "Account Security",
        "requires_any_tag": ["email", "username"],
        "requires_indicator": [],
        "linked_clause_keys": ["CCA:5", "ETA:12(2)(a)"],
    },
    # â”€â”€ Identity Protection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "action": "Monitor your financial accounts and credit reports for unauthorized activity using your exposed identity details.",
        "priority_base": "MEDIUM",
        "category": "Identity Protection",
        "requires_any_tag": ["id", "name", "dob"],
        "requires_indicator": [],
        "linked_clause_keys": ["PDPA:13(1)", "PDPA:10(a)"],
    },
    {
        "action": "Consider placing a fraud alert or credit freeze with financial institutions to prevent identity theft.",
        "priority_base": "URGENT",
        "category": "Identity Protection",
        "requires_any_tag": ["id"],
        "requires_indicator": [],
        "boost_on_scenario": ["IDENTITY_IMPERSONATION", "DATABASE_BREACH", "IDENTITY_THEFT"],
        "linked_clause_keys": ["PDPA:13(1)", "CCA:7(a)", "PDPA:10(b)"],
    },
    {
        "action": "Report the identity impersonation to the Sri Lanka Computer Emergency Readiness Team (SLCERT) and the nearest police station.",
        "priority_base": "URGENT",
        "category": "Identity Protection",
        "requires_any_tag": [],
        "requires_indicator": ["impersonate"],
        "linked_clause_keys": ["OSA:18(a)", "OSA:18(b)", "OSA:18(c)"],
    },
    {
        "action": "Notify your bank and any relevant financial service providers about potential identity fraud using your exposed NIC/ID.",
        "priority_base": "HIGH",
        "category": "Identity Protection",
        "requires_any_tag": ["id"],
        "requires_indicator": ["impersonate"],
        "linked_clause_keys": ["OSA:18(b)", "CCA:4(a)", "CCA:4(b)"],
    },
    # â”€â”€ Image & Content Removal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "action": "Submit a content removal or takedown request to the platform where your image was exposed.",
        "priority_base": "URGENT",
        "category": "Image & Content Removal",
        "requires_any_tag": [],
        "requires_indicator": ["img_exposed"],
        "linked_clause_keys": ["OSA:20(1)", "PDPA:16(a)", "PDPA:7(a)"],
    },
    {
        "action": "Document and preserve evidence of the image exposure (screenshots with timestamps) before it is removed.",
        "priority_base": "MEDIUM",
        "category": "Image & Content Removal",
        "requires_any_tag": [],
        "requires_indicator": ["img_exposed"],
        "linked_clause_keys": ["OSA:20(1)", "CCA:7(a)"],
    },
    {
        "action": "Use reverse image search tools to check if your exposed image has been redistributed on other platforms.",
        "priority_base": "MEDIUM",
        "category": "Image & Content Removal",
        "requires_any_tag": [],
        "requires_indicator": ["img_exposed"],
        "linked_clause_keys": ["OSA:20(1)", "PDPA:14(1)"],
    },
    # â”€â”€ Legal & Regulatory Action â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "action": "File a formal complaint with the Data Protection Authority of Sri Lanka under the Personal Data Protection Act (PDPA 2022).",
        "priority_base": "MEDIUM",
        "category": "Legal Action",
        "requires_any_tag": ["name", "id", "email", "phone"],
        "requires_indicator": [],
        "boost_on_scenario": ["DATABASE_BREACH", "UNAUTHORIZED_DATA_PROCESSING"],
        "linked_clause_keys": ["PDPA:6(1)a)", "PDPA:10(a)", "PDPA:12(1)(a)"],
    },
    {
        "action": "Report the online abuse or impersonation to the Online Safety Commission under the Online Safety Act (OSA 2024).",
        "priority_base": "URGENT",
        "category": "Legal Action",
        "requires_any_tag": [],
        "requires_indicator": ["impersonate"],
        "linked_clause_keys": ["OSA:18(a)", "OSA:18(b)", "OSA:18(c)", "OSA:20(1)"],
    },
    {
        "action": "File a complaint under the Computer Crimes Act (CCA 2007) with the CID Cyber Crimes Division for unauthorized access to your data.",
        "priority_base": "HIGH",
        "category": "Legal Action",
        "requires_any_tag": [],
        "requires_indicator": [],
        "requires_scenario": ["DATABASE_BREACH", "ACCOUNT_MISUSE", "ACCOUNT_TAKEOVER"],
        "linked_clause_keys": ["CCA:3(a)", "CCA:3(b)", "CCA:7(a)"],
    },
    {
        "action": "Consider seeking legal counsel to explore civil remedies for damages resulting from the data exposure.",
        "priority_base": "LOW",
        "category": "Legal Action",
        "requires_any_tag": [],
        "requires_indicator": [],
        "min_severity": "High",
        "linked_clause_keys": ["PDPA:12(1)(a)", "PDPA:13(1)"],
    },
    # â”€â”€ Platform & Communication â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "action": "Report the exposure to the platform's abuse/safety team and request account verification or lockdown.",
        "priority_base": "MEDIUM",
        "category": "Platform Action",
        "requires_any_tag": [],
        "requires_indicator": [],
        "requires_platform": True,
        "linked_clause_keys": ["OSA:20(1)", "PDPA:16(a)"],
    },
    {
        "action": "Alert your contacts that your identity may be used fraudulently â€” warn them not to respond to requests coming from impersonating accounts.",
        "priority_base": "HIGH",
        "category": "Platform Action",
        "requires_any_tag": [],
        "requires_indicator": ["impersonate"],
        "linked_clause_keys": ["OSA:18(a)", "TCA:46B"],
    },
    # â”€â”€ Physical Safety â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "action": "Assess your physical safety if your home address or precise location has been exposed â€” consider temporary precautions.",
        "priority_base": "HIGH",
        "category": "Physical Safety",
        "requires_any_tag": ["addr", "location"],
        "requires_indicator": [],
        "linked_clause_keys": ["PDPA:10(a)", "PDPA:10(b)"],
    },
    {
        "action": "Report the exposure of your physical address to law enforcement if you feel at risk of stalking or harassment.",
        "priority_base": "MEDIUM",
        "category": "Physical Safety",
        "requires_any_tag": ["addr"],
        "requires_indicator": [],
        "boost_on_scenario": ["UNAUTHORIZED_DATA_PROCESSING", "DOXXING"],
        "linked_clause_keys": ["PDPA:10(b)", "TCA:52(d)"],
    },
    # â”€â”€ Data Hygiene â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    {
        "action": "Audit your online presence â€” remove unnecessary personal information from social media profiles and public directories.",
        "priority_base": "MEDIUM",
        "category": "Data Hygiene",
        "requires_any_tag": ["name", "email", "phone", "username"],
        "requires_indicator": [],
        "linked_clause_keys": ["PDPA:11(a)", "PDPA:7(a)"],
    },
    {
        "action": "Set up monitoring alerts (e.g. Google Alerts) for your exposed name and contact details to detect further misuse.",
        "priority_base": "LOW",
        "category": "Data Hygiene",
        "requires_any_tag": ["name", "email"],
        "requires_indicator": [],
        "linked_clause_keys": ["PDPA:13(1)", "PDPA:8(a)"],
    },
    {
        "action": "Request the data controller to delete or restrict processing of your personal data under your right to erasure (PDPA Section 16).",
        "priority_base": "HIGH",
        "category": "Data Hygiene",
        "requires_any_tag": [],
        "requires_indicator": [],
        "requires_scenario": ["UNAUTHORIZED_DATA_PROCESSING", "DATABASE_BREACH"],
        "linked_clause_keys": ["PDPA:16(a)", "PDPA:16(b)", "PDPA:14(1)"],
    },
    # ── Impersonation-specific ───────────────────────────────────────────
    {
        "action": "Report the fake profile or account to the platform using their impersonation report form — most platforms (Facebook, Instagram, WhatsApp) have a dedicated identity-theft reporting flow.",
        "priority_base": "URGENT",
        "category": "Platform Action",
        "requires_any_tag": [],
        "requires_indicator": ["impersonate"],
        "requires_platform": True,
        "linked_clause_keys": ["OSA:18(a)", "OSA:18(b)"],
    },
    {
        "action": "Collect and securely store evidence of the impersonation: screenshots of the fake profile, messages sent from it, URLs, and timestamps. This evidence is critical for police complaints and court proceedings.",
        "priority_base": "HIGH",
        "category": "Identity Protection",
        "requires_any_tag": [],
        "requires_indicator": ["impersonate"],
        "linked_clause_keys": ["OSA:18(a)", "CCA:4(b)"],
    },
    {
        "action": "Request a Subject Access Request (SAR) from the data controller under PDPA Section 13 to obtain a full account of what personal data they hold and how it was processed.",
        "priority_base": "HIGH",
        "category": "Legal Action",
        "requires_any_tag": [],
        "requires_indicator": [],
        "requires_scenario": ["DATABASE_BREACH", "UNAUTHORIZED_DATA_PROCESSING"],
        "linked_clause_keys": ["PDPA:13(1)", "PDPA:12(1)(a)"],
    },
    # ── Image abuse - specific ───────────────────────────────────────────
    {
        "action": "If intimate images were shared, contact the Online Safety Commission to request an emergency takedown order under OSA Section 19.",
        "priority_base": "URGENT",
        "category": "Image & Content Removal",
        "requires_any_tag": [],
        "requires_indicator": ["img_exposed"],
        "requires_scenario": ["IMAGE_ABUSE", "HARASSMENT"],
        "linked_clause_keys": ["OSA:20(1)", "PDPA:16(a)"],
    },
    {
        "action": "Contact a trusted support organisation (e.g., Women In Need — WIN helpline: 011 271 8585) if you are experiencing distress from non-consensual image sharing.",
        "priority_base": "MEDIUM",
        "category": "Physical Safety",
        "requires_any_tag": [],
        "requires_indicator": ["img_exposed"],
        "linked_clause_keys": [],
    },
    # ── Database breach - specific ───────────────────────────────────────
    {
        "action": "Demand a formal breach notification from the data controller detailing: what data was exposed, when the breach occurred, what remediation steps have been taken, and what compensation is available.",
        "priority_base": "MEDIUM",
        "category": "Legal Action",
        "requires_any_tag": [],
        "requires_indicator": [],
        "requires_scenario": ["DATABASE_BREACH"],
        "linked_clause_keys": ["PDPA:12(1)(f)", "PDPA:12(1)(a)"],
    },
    {
        "action": "Change passwords and security questions on all accounts where you used the same or similar credentials as those stored in the breached system.",
        "priority_base": "HIGH",
        "category": "Account Security",
        "requires_any_tag": ["email", "username"],
        "requires_indicator": [],
        "requires_scenario": ["DATABASE_BREACH"],
        "linked_clause_keys": ["CCA:3(a)", "CCA:10"],
    },
    # ── Account misuse - specific ────────────────────────────────────────
    {
        "action": "Check your account's login history and connected devices — remove any unrecognised sessions immediately and reset your recovery email and phone number.",
        "priority_base": "HIGH",
        "category": "Account Security",
        "requires_any_tag": [],
        "requires_indicator": [],
        "requires_scenario": ["ACCOUNT_MISUSE", "ACCOUNT_TAKEOVER"],
        "linked_clause_keys": ["CCA:3(a)", "CCA:5"],
    },
    {
        "action": "Contact your mobile operator to verify no SIM swap or call forwarding has been set up on your number — request a SIM lock if available.",
        "priority_base": "HIGH",
        "category": "Account Security",
        "requires_any_tag": ["phone"],
        "requires_indicator": [],
        "boost_on_scenario": ["ACCOUNT_MISUSE", "IDENTITY_IMPERSONATION", "ACCOUNT_TAKEOVER", "IDENTITY_THEFT"],
        "linked_clause_keys": ["TCA:46B", "TCA:46C"],
    },
    # ── Doxxing / unauthorized processing ────────────────────────────────
    {
        "action": "Request removal of your personal information from any public directories, people-search sites, or forums where it has been posted without consent.",
        "priority_base": "HIGH",
        "category": "Data Hygiene",
        "requires_any_tag": ["addr", "phone", "name"],
        "requires_indicator": [],
        "boost_on_scenario": ["UNAUTHORIZED_DATA_PROCESSING", "DOXXING"],
        "linked_clause_keys": ["PDPA:16(a)", "PDPA:14(1)"],
    },
    {
        "action": "If your physical address or location has been publicly posted (doxxing), assess your home security and inform local police for a welfare check if you feel threatened.",
        "priority_base": "HIGH",
        "category": "Physical Safety",
        "requires_any_tag": ["addr", "location"],
        "requires_indicator": [],
        "boost_on_scenario": ["UNAUTHORIZED_DATA_PROCESSING", "DOXXING"],
        "linked_clause_keys": ["PDPA:10(a)", "PDPA:10(b)"],
    },
    # ── NIC/ID specific ─────────────────────────────────────────────────
    {
        "action": "If your NIC number was exposed, monitor for unauthorized SIM registrations, bank account openings, or utility connections in your name — consider lodging a precautionary report at your divisional secretariat.",
        "priority_base": "MEDIUM",
        "category": "Identity Protection",
        "requires_any_tag": ["id"],
        "requires_indicator": [],
        "linked_clause_keys": ["PDPA:10(a)", "PDPA:13(1)"],
    },
    # ── Telecom-related ──────────────────────────────────────────────────
    {
        "action": "File a complaint with the Telecommunications Regulatory Commission of Sri Lanka (TRCSL) if the abuse involved phone calls, SMS, or telecom services.",
        "priority_base": "MEDIUM",
        "category": "Legal Action",
        "requires_any_tag": ["phone"],
        "requires_indicator": [],
        "linked_clause_keys": ["TCA:46B", "TCA:52(a)"],
    },
]

# Priority ordinal for sorting (lower = higher urgency)
_PRIORITY_ORDER = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

# Severity ordinal for min_severity checks
_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}

# ── Explainability constants (merged from recommendation_explainer.py) ───────
_FEATURE_LABELS = {
    "name": "your full name",
    "id": "your National ID / NIC",
    "phone": "your phone number",
    "email": "your email address",
    "addr": "your physical address",
    "dob": "your date of birth",
    "username": "your username",
    "location": "your location data",
    "impersonate": "identity impersonation",
    "img_exposed": "your personal images",
    "platform": "a public platform",
    "severity_Critical": "the critical severity of this incident",
    "severity_High": "the high severity of this incident",
    "severity_Moderate": "the moderate severity of this incident",
}

_FEATURE_WEIGHTS = {
    "impersonate": 0.95, "img_exposed": 0.85, "id": 0.90,
    "phone": 0.75, "email": 0.70, "name": 0.65, "addr": 0.80,
    "dob": 0.70, "username": 0.50, "location": 0.60, "platform": 0.55,
    "severity_Critical": 0.90, "severity_High": 0.70, "severity_Moderate": 0.45,
}

_CATEGORY_TEMPLATES = {
    "Account Security": [
        "With {features} exposed, your linked accounts could be targeted for takeover or credential-stuffing attacks.",
        "Attackers who obtain {features} often attempt to reset passwords and gain full account access.",
        "The exposure of {features} can be combined with publicly available data to bypass security questions and compromise your accounts.",
    ],
    "Identity Protection": [
        "The exposure of {features} creates a direct risk of identity theft, fraudulent transactions, or impersonation in your name.",
        "Once {features} has been leaked, bad actors can open accounts, apply for credit, or commit fraud under your identity.",
        "The compromise of {features} enables forging documents, registering services, or impersonating you to institutions.",
    ],
    "Image & Content Removal": [
        "The non-consensual distribution of {features} can cause lasting reputational and emotional harm if not addressed quickly.",
        "Once shared beyond their intended audience, {features} become exponentially harder to contain \u2014 early removal requests are critical.",
        "Preserving evidence related to {features} now strengthens any future legal or platform enforcement action.",
    ],
    "Legal Action": [
        "The circumstances involving {features} may constitute offences under Sri Lankan data protection and cyber-crime legislation.",
        "Sri Lankan law provides specific remedies for the misuse of {features} \u2014 formal complaints create an official record.",
        "Filing a legal complaint regarding {features} can trigger investigations and compel responsible parties to act.",
    ],
    "Platform Action": [
        "Platforms have dedicated processes for incidents involving {features} \u2014 reporting promptly can lead to account suspension or content removal.",
        "Notifying the platform about the compromise of {features} creates a record that strengthens both your safety and any legal proceedings.",
        "Quick platform reporting when {features} is involved helps prevent the attacker from reaching more of your contacts.",
    ],
    "Physical Safety": [
        "The exposure of {features} creates a real risk of stalking, harassment, or unwanted contact at your physical location.",
        "The leak of {features} may escalate beyond the digital sphere \u2014 assess your immediate physical safety.",
        "Proactive safety measures are warranted because {features} could be used to locate or target you offline.",
    ],
    "Data Hygiene": [
        "Reducing the online footprint of {features} limits what attackers can piece together for future misuse.",
        "Monitoring for misuse of {features} helps you detect and respond to secondary incidents early.",
        "Cleaning up traces of {features} from public sources shrinks the attack surface available to bad actors.",
    ],
}


def _resolve_linked_clauses(
    linked_clause_keys: List[str],
    matched_clauses: List[Dict],
) -> List[Dict]:
    """
    Resolve linked_clause_keys against the clauses that actually matched
    for this request.

    Returns a compact list of dicts with law_code, section, and title
    for keys that have a match; falls back to key-only for non-matches.
    """
    # Build a fast lookup: "LAW:SECTION" â†’ clause dict
    clause_by_key: Dict[str, Dict] = {}
    for c in matched_clauses:
        k = f"{c.get('law_code', '')}:{c.get('section', '')}"
        clause_by_key[k] = c

    result = []
    for key in linked_clause_keys:
        clause = clause_by_key.get(key)
        if clause:
            result.append({
                "key":      key,
                "law_code": clause.get("law_code", ""),
                "law_name": clause.get("law_name", ""),
                "section":  clause.get("section", ""),
                "title":    clause.get("title", ""),
            })
        # Only include keys that actually matched â€” keeps output clean
    return result


class RecommendationEngine:
    """Generates prioritized, scenario-aware privacy and security recommendations."""

    def generate(
        self,
        validated_input: Dict,
        scenario_key: str = "DATA_EXPOSURE",
        severity_level: str = "Low",
        matched_clauses: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Produce a ranked list of recommendations.

        Parameters
        ----------
        validated_input : dict
            Output from InputValidator.validate().
        scenario_key : str
            Classified incident category.
        severity_level : str
            Severity level string from SeverityAnalyzer.
        matched_clauses : list[dict], optional
            Filtered, explained clauses from the pipeline. Used to resolve
            linked_clause_keys → actual clause info.

        Returns
        -------
        list[dict]
            Each dict has: action, priority, category, triggers,
            linked_clauses (list of matched legal clauses backing this rec).
        """
        tags: Set[str] = set(validated_input.get("normalized_tags", []))
        platform: str = validated_input.get("platform", "")

        # Reset template rotation counters for this request
        RecommendationEngine._template_counters = {}

        # Derive indicators from tags (they are now unified)
        active_indicators: Set[str] = set()
        if "impersonate" in tags:
            active_indicators.add("impersonate")
        if "img_exposed" in tags:
            active_indicators.add("img_exposed")

        clauses = matched_clauses or []

        results: List[Dict] = []

        for rec in _RECOMMENDATIONS:
            triggers: List[str] = []

            # --- Gate: scenario restriction ---
            req_scenarios = rec.get("requires_scenario")
            if req_scenarios and scenario_key not in req_scenarios:
                continue

            # --- Gate: minimum severity ---
            min_sev = rec.get("min_severity")
            if min_sev:
                if _SEVERITY_ORDER.get(severity_level, 3) > _SEVERITY_ORDER.get(min_sev, 3):
                    continue

            # --- Gate: platform required ---
            if rec.get("requires_platform") and not platform:
                continue

            # --- Gate: indicator requirements ---
            req_indicators = rec.get("requires_indicator", [])
            if req_indicators:
                matched_indicators = active_indicators & set(req_indicators)
                if not matched_indicators:
                    continue
                for ind in sorted(matched_indicators):
                    triggers.append(f"Indicator: {ind}")

            # --- Gate: tag requirements ---
            req_tags = rec.get("requires_any_tag", [])
            if req_tags:
                matched_tags = tags & set(req_tags)
                if not matched_tags:
                    continue
                for t in sorted(matched_tags):
                    triggers.append(f"Exposed: {t}")

            # If no specific trigger was recorded but we passed all gates
            if not triggers:
                triggers.append(f"Scenario: {scenario_key}")

            # --- Priority adjustment ---
            priority = rec["priority_base"]
            boost_scenarios = rec.get("boost_on_scenario", [])
            if boost_scenarios and scenario_key in boost_scenarios:
                current_ord = _PRIORITY_ORDER.get(priority, 2)
                boosted_ord = max(0, current_ord - 1)
                for p, o in _PRIORITY_ORDER.items():
                    if o == boosted_ord:
                        priority = p
                        break

            if platform:
                triggers.append(f"Platform: {platform}")

            # Resolve linked clauses
            linked = _resolve_linked_clauses(rec.get("linked_clause_keys", []), clauses)

            results.append({
                "action":         rec["action"],
                "priority":       priority,
                "category":       rec["category"],
                "triggers":       triggers,
                "linked_clauses": linked,
            })

        # Sort: URGENT first, then HIGH, MEDIUM, LOW
        results.sort(key=lambda r: _PRIORITY_ORDER.get(r["priority"], 3))

        # ── Inline explainability (merged from recommendation_explainer) ──
        active_features: Dict[str, float] = {}
        for tag in tags:
            if tag in _FEATURE_WEIGHTS:
                active_features[tag] = _FEATURE_WEIGHTS[tag]
        if "impersonate" in active_indicators:
            active_features["impersonate"] = _FEATURE_WEIGHTS["impersonate"]
        if "img_exposed" in active_indicators:
            active_features["img_exposed"] = _FEATURE_WEIGHTS["img_exposed"]
        if platform:
            active_features["platform"] = _FEATURE_WEIGHTS["platform"]
        sev_key = f"severity_{severity_level}"
        if sev_key in _FEATURE_WEIGHTS:
            active_features[sev_key] = _FEATURE_WEIGHTS[sev_key]

        for rec in results:
            trigger_feats = self._extract_trigger_features(rec["triggers"], active_features)
            contributions = sorted(
                [{"feature": f, "label": _FEATURE_LABELS.get(f, f), "weight": w}
                 for f, w in trigger_feats.items()],
                key=lambda x: x["weight"], reverse=True,
            )
            rec["feature_contributions"] = contributions
            rec["explanation"] = self._build_explanation(rec["category"], contributions)

        return results

    # ── Explainability helpers ────────────────────────────────────────────

    @staticmethod
    def _extract_trigger_features(
        triggers: List[str],
        active_features: Dict[str, float],
    ) -> Dict[str, float]:
        features: Dict[str, float] = {}
        for trigger in triggers:
            if trigger.startswith("Exposed: "):
                tag = trigger.split("Exposed: ", 1)[1].strip()
                if tag in active_features:
                    features[tag] = active_features[tag]
            elif trigger.startswith("Indicator: "):
                ind = trigger.split("Indicator: ", 1)[1].strip()
                if ind in active_features:
                    features[ind] = active_features[ind]
            elif trigger.startswith("Platform: "):
                if "platform" in active_features:
                    features["platform"] = active_features["platform"]
            elif trigger.startswith("Scenario: "):
                for f, w in active_features.items():
                    if f.startswith("severity_"):
                        features[f] = w
        if not features and active_features:
            top = sorted(active_features.items(), key=lambda x: x[1], reverse=True)
            for f, w in top[:3]:
                features[f] = w
        return features

    # Features that add context but shouldn't appear in prose explanations
    _CONTEXTUAL_FEATURES = {"platform", "severity_Critical", "severity_High", "severity_Moderate"}

    # Per-category counter to rotate through template variants
    _template_counters: Dict[str, int] = {}

    @classmethod
    def _build_explanation(cls, category: str, contributions: List[Dict]) -> str:
        if not contributions:
            return "This recommendation applies to your overall exposure profile."
        # Only use substantive PII / indicator features in explanation prose
        prose_contribs = [c for c in contributions if c["feature"] not in cls._CONTEXTUAL_FEATURES]
        if not prose_contribs:
            # No PII features — use a generic explanation
            return "This recommendation addresses the overall risk profile of your incident."
        names = [c["label"] for c in prose_contribs[:3]]
        if len(names) == 1:
            feat_str = names[0]
        elif len(names) == 2:
            feat_str = f"{names[0]} and {names[1]}"
        else:
            feat_str = f"{', '.join(names[:-1])}, and {names[-1]}"
        templates = _CATEGORY_TEMPLATES.get(category)
        if not templates:
            return f"This recommendation was triggered because {feat_str} requires attention."
        idx = cls._template_counters.get(category, 0)
        template = templates[idx % len(templates)]
        cls._template_counters[category] = idx + 1
        return template.format(features=feat_str)
