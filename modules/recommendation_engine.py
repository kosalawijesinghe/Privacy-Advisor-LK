"""
Module 14 - Privacy & Security Recommendation Engine (RULE-DRIVEN)
==================================================================
Generates logical, rule-based recommendations from a declarative rule system.
All recommendations are derived from explicit context rules, not hardcoded logic.

Rules are evaluated based on:
  - Exposed data (tags) & severity conditions
  - Incident scenario triggers
  - Applicable legal clauses 
  - Context-driven priority assignment
"""

from typing import Dict, List, Optional, Set, Callable


# Priority and severity mapping
_PRIORITY_ORDER = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}

# Data sensitivity weights for dynamic priority assignment
_TAG_SENSITIVITY = {
    "id": 0.95,           # National ID - highest risk
    "impersonate": 0.95,  # Active identity fraud
    "addr": 0.85,         # Physical location risk
    "phone": 0.80,        # Account takeover + SIM swap
    "email": 0.75,        # Account takeover vector
    "dob": 0.75,          # Identity verification bypass
    "name": 0.65,         # Social engineering + doxxing
    "username": 0.60,     # Account linking
    "location": 0.70,     # Stalking risk
    "img_exposed": 0.90,  # Reputational harm
}

# Feature labels for explanation building
_FEATURE_LABELS = {
    "id": "your National ID / NIC",
    "name": "your full name",
    "phone": "your phone number",
    "email": "your email address",
    "addr": "your physical address",
    "dob": "your date of birth",
    "username": "your username",
    "location": "your location data",
    "impersonate": "identity impersonation",
    "img_exposed": "your personal images",
}


def _resolve_linked_clauses(linked_clause_keys: List[str], matched_clauses: List[Dict]) -> List[Dict]:
    """
    Resolve linked_clause_keys against the actual matched clauses.
    Returns clauses with law_code, section, title.
    """
    clause_by_key = {}
    for c in matched_clauses:
        k = f"{c.get('law_code', '')}:{c.get('section', '')}"
        clause_by_key[k] = c

    result = []
    for key in linked_clause_keys:
        clause = clause_by_key.get(key)
        if clause:
            result.append({
                "key": key,
                "law_code": clause.get("law_code", ""),
                "law_name": clause.get("law_name", ""),
                "section": clause.get("section", ""),
                "title": clause.get("title", ""),
            })
    return result


class ContextRule:
    """
    A declarative rule that evaluates conditions and generates a recommendation.
    
    Attributes:
        name: Unique rule identifier
        category: Recommendation category
        condition: Lambda function that returns True if rule applies
        action_template: String template for recommendation text (can use format strings)
        priority: Base priority level, or callable that takes context
        linked_clause_keys: List of law sections to link
        triggers: List of trigger descriptions for audit trail
    """
    def __init__(
        self,
        name: str,
        category: str,
        condition: Callable[[Dict], bool],
        action_template: str,
        priority,  # Can be str or Callable[[Dict], str]
        linked_clause_keys: List[str],
        triggers: List[str],
    ):
        self.name = name
        self.category = category
        self.condition = condition
        self.action_template = action_template
        self.priority = priority
        self.linked_clause_keys = linked_clause_keys
        self.triggers = triggers

    def matches(self, context: Dict) -> bool:
        """Check if this rule's condition is met in the given context."""
        try:
            return self.condition(context)
        except Exception:
            return False

    def get_priority(self, context: Dict) -> str:
        """Get priority, evaluating callable if needed."""
        if callable(self.priority):
            try:
                return self.priority(context)
            except Exception:
                return "MEDIUM"
        return self.priority

    def build_recommendation(self, context: Dict, clauses: List[Dict]) -> Optional[Dict]:
        """Build a recommendation dict if the rule matches."""
        if not self.matches(context):
            return None
        
        try:
            action = self.action_template.format(**context)
        except (KeyError, ValueError):
            action = self.action_template
        
        return {
            "action": action,
            "priority": self.get_priority(context),
            "category": self.category,
            "triggers": self.triggers,
            "linked_clauses": _resolve_linked_clauses(self.linked_clause_keys, clauses),
        }


class RecommendationEngine:
    """
    Rule-driven recommendation generator.
    All recommendations are generated from explicit context rules.
    """

    def __init__(self):
        """Initialize rule engine with all context-driven rules."""
        self.rules: List[ContextRule] = self._build_rules()

    def _build_rules(self) -> List[ContextRule]:
        """
        Define all recommendation rules declaratively.
        Each rule specifies conditions and actions without scattered logic.
        """
        rules = []
        
        # ─── ACCOUNT SECURITY RULES ────────────────────────────────────────
        rules.append(ContextRule(
            name="mfa_for_exposed_accounts",
            category="Account Security",
            condition=lambda ctx: bool(ctx["account_tags"]),
            action_template="Enable two-factor authentication (2FA) on all accounts using {account_tags_label}.",
            priority="URGENT",
            linked_clause_keys=["CCA:3(a)", "CCA:3(b)", "ETA:7(a)"],
            triggers=["Exposed: account data"],
        ))
        
        rules.append(ContextRule(
            name="password_reset_for_exposed_emails",
            category="Account Security",
            condition=lambda ctx: "email" in ctx["account_tags"] or "username" in ctx["account_tags"],
            action_template="Change passwords immediately for all accounts linked to {account_tags_label}.",
            priority="URGENT",
            linked_clause_keys=["CCA:3(a)", "CCA:4(a)", "ETA:12(1)(a)"],
            triggers=["Exposed: email/username"],
        ))
        
        rules.append(ContextRule(
            name="session_review",
            category="Account Security",
            condition=lambda ctx: bool(ctx["account_tags"]),
            action_template="Review and revoke active sessions and third-party app permissions on accounts linked to {account_tags_label}.",
            priority="HIGH",
            linked_clause_keys=["CCA:5", "ETA:12(2)(a)"],
            triggers=["Exposed: account tags"],
        ))
        
        rules.append(ContextRule(
            name="sim_lock_for_phone",
            category="Account Security",
            condition=lambda ctx: "phone" in ctx["account_tags"],
            action_template="Contact your mobile operator to verify no SIM swap or call forwarding is active. Request a SIM lock if available.",
            priority="HIGH",
            linked_clause_keys=["TCA:46B", "TCA:46C"],
            triggers=["Exposed: phone"],
        ))
        
        # ─── IDENTITY PROTECTION RULES ────────────────────────────────────
        rules.append(ContextRule(
            name="financial_monitoring",
            category="Identity Protection",
            condition=lambda ctx: bool(ctx["identity_tags"]),
            action_template="Monitor your financial accounts and credit reports for unauthorized activity using {identity_tags_label}.",
            priority="HIGH",
            linked_clause_keys=["PDPA:13(1)", "PDPA:10(a)"],
            triggers=["Exposed: identity data"],
        ))
        
        rules.append(ContextRule(
            name="credit_freeze",
            category="Identity Protection",
            condition=lambda ctx: "id" in ctx["identity_tags"],
            action_template="Consider placing a fraud alert or credit freeze with financial institutions to prevent identity theft.",
            priority=lambda ctx: "URGENT" if (ctx["severity_level"] == "Critical" or ctx["impersonate"]) else "HIGH",
            linked_clause_keys=["PDPA:13(1)", "CCA:7(a)", "PDPA:10(b)"],
            triggers=["Exposed: id"],
        ))
        
        rules.append(ContextRule(
            name="bank_notification_for_fraud",
            category="Identity Protection",
            condition=lambda ctx: "id" in ctx["identity_tags"] and ctx["impersonate"],
            action_template="Notify your bank and financial service providers immediately about the identity fraud.",
            priority="URGENT",
            linked_clause_keys=["OSA:18(b)", "CCA:4(a)", "CCA:4(b)"],
            triggers=["Exposed: id", "Indicator: impersonate"],
        ))
        
        rules.append(ContextRule(
            name="report_impersonation",
            category="Identity Protection",
            condition=lambda ctx: ctx["impersonate"],
            action_template="Report the identity impersonation to SLCERT and your nearest police station.",
            priority="URGENT",
            linked_clause_keys=["OSA:18(a)", "OSA:18(b)", "OSA:18(c)"],
            triggers=["Indicator: impersonate"],
        ))
        
        # ─── IMAGE REMOVAL RULES ────────────────────────────────────────
        rules.append(ContextRule(
            name="image_takedown_request",
            category="Image & Content Removal",
            condition=lambda ctx: ctx["img_exposed"],
            action_template="Submit a content removal/takedown request to the platform where your image was exposed.",
            priority="URGENT",
            linked_clause_keys=["OSA:20(1)", "PDPA:16(a)", "PDPA:7(a)"],
            triggers=["Indicator: img_exposed"],
        ))
        
        rules.append(ContextRule(
            name="preserve_image_evidence",
            category="Image & Content Removal",
            condition=lambda ctx: ctx["img_exposed"],
            action_template="Document and preserve evidence of the image exposure (screenshots with timestamps) before removal.",
            priority="MEDIUM",
            linked_clause_keys=["OSA:20(1)", "CCA:7(a)"],
            triggers=["Indicator: img_exposed"],
        ))
        
        rules.append(ContextRule(
            name="reverse_image_search",
            category="Image & Content Removal",
            condition=lambda ctx: ctx["img_exposed"],
            action_template="Use reverse image search tools to find if your image has been redistributed on other platforms.",
            priority="MEDIUM",
            linked_clause_keys=["OSA:20(1)", "PDPA:14(1)"],
            triggers=["Indicator: img_exposed"],
        ))
        
        # ─── LEGAL ACTION RULES ────────────────────────────────────────
        rules.append(ContextRule(
            name="pdpa_complaint",
            category="Legal Action",
            condition=lambda ctx: "PDPA" in ctx["law_codes"] and bool(ctx["tags"] & {"name", "id", "email", "phone"}),
            action_template="File a formal complaint with the Data Protection Authority of Sri Lanka under the Personal Data Protection Act (PDPA 2022).",
            priority=lambda ctx: "HIGH" if ctx["severity_level"] == "Critical" else "MEDIUM",
            linked_clause_keys=["PDPA:6(1)a)", "PDPA:10(a)", "PDPA:12(1)(a)"],
            triggers=["Law: PDPA", "Exposed: PII"],
        ))
        
        rules.append(ContextRule(
            name="osa_report",
            category="Legal Action",
            condition=lambda ctx: "OSA" in ctx["law_codes"] and ctx["impersonate"],
            action_template="Report the online abuse or impersonation to the Online Safety Commission under the Online Safety Act (OSA 2024).",
            priority="URGENT",
            linked_clause_keys=["OSA:18(a)", "OSA:18(b)", "OSA:18(c)", "OSA:20(1)"],
            triggers=["Law: OSA", "Indicator: impersonate"],
        ))
        
        rules.append(ContextRule(
            name="cca_complaint",
            category="Legal Action",
            condition=lambda ctx: "CCA" in ctx["law_codes"] and ctx["scenario_key"] in ["DATABASE_BREACH", "ACCOUNT_MISUSE", "ACCOUNT_TAKEOVER"],
            action_template="File a complaint under the Computer Crimes Act (CCA 2007) with the CID Cyber Crimes Division for unauthorized access.",
            priority="HIGH",
            linked_clause_keys=["CCA:3(a)", "CCA:3(b)", "CCA:7(a)"],
            triggers=["Law: CCA"],
        ))
        
        rules.append(ContextRule(
            name="tca_complaint",
            category="Legal Action",
            condition=lambda ctx: "TCA" in ctx["law_codes"] and "phone" in ctx["tags"],
            action_template="File a complaint with the Telecommunications Regulatory Commission of Sri Lanka (TRCSL) for telecom-related abuse.",
            priority="MEDIUM",
            linked_clause_keys=["TCA:46B", "TCA:52(a)"],
            triggers=["Law: TCA", "Exposed: phone"],
        ))
        
        rules.append(ContextRule(
            name="legal_counsel",
            category="Legal Action",
            condition=lambda ctx: ctx["severity_level"] in ["Critical", "High"],
            action_template="Consider seeking legal counsel to explore civil remedies for damages resulting from the data exposure.",
            priority="MEDIUM",
            linked_clause_keys=["PDPA:12(1)(a)", "PDPA:13(1)"],
            triggers=["Severity: Critical/High"],
        ))
        
        rules.append(ContextRule(
            name="subject_access_request",
            category="Legal Action",
            condition=lambda ctx: ctx["scenario_key"] in ["DATABASE_BREACH", "UNAUTHORIZED_DATA_PROCESSING"],
            action_template="Request a Subject Access Request (SAR) from the data controller under PDPA Section 13 to obtain a full account of what data they hold.",
            priority="HIGH",
            linked_clause_keys=["PDPA:13(1)", "PDPA:12(1)(a)"],
            triggers=["Scenario: data breach"],
        ))
        
        # ─── PLATFORM ACTION RULES ────────────────────────────────────────
        rules.append(ContextRule(
            name="platform_abuse_report",
            category="Platform Action",
            condition=lambda ctx: bool(ctx["platform"]),
            action_template="Report the incident to the platform's abuse/safety team and request account verification and lockdown.",
            priority="HIGH",
            linked_clause_keys=["OSA:20(1)", "PDPA:16(a)"],
            triggers=["Platform: involved"],
        ))
        
        rules.append(ContextRule(
            name="report_fake_profile",
            category="Platform Action",
            condition=lambda ctx: ctx["impersonate"] and ctx["platform"],
            action_template="Report the fake profile or impersonating account using the platform's dedicated impersonation report form.",
            priority="URGENT",
            linked_clause_keys=["OSA:18(a)", "OSA:18(b)"], 
            triggers=["Indicator: impersonate"],
        ))
        
        rules.append(ContextRule(
            name="contact_alert",
            category="Platform Action",
            condition=lambda ctx: ctx["impersonate"],
            action_template="Alert your contacts that your identity is being impersonated and warn them not to respond to requests from fake accounts.",
            priority="HIGH",
            linked_clause_keys=["OSA:18(a)", "TCA:46B"],
            triggers=["Indicator: impersonate"],
        ))
        
        # ─── PHYSICAL SAFETY RULES ────────────────────────────────────────
        rules.append(ContextRule(
            name="physical_safety_assessment",
            category="Physical Safety",
            condition=lambda ctx: bool(ctx["physical_tags"]),
            action_template="Assess your physical safety since {physical_tags_label} has been exposed. Consider temporary home security precautions.",
            priority="HIGH",
            linked_clause_keys=["PDPA:10(a)", "PDPA:10(b)"],
            triggers=["Exposed: physical data"],
        ))
        
        rules.append(ContextRule(
            name="law_enforcement_report",
            category="Physical Safety",
            condition=lambda ctx: bool(ctx["physical_tags"]) and ctx["scenario_key"] in ["DOXXING", "HARASSMENT"],
            action_template="Report the exposure of {physical_tags_label} to law enforcement. Consider a welfare check if you feel threatened.",
            priority="HIGH",
            linked_clause_keys=["PDPA:10(a)", "PDPA:10(b)"],
            triggers=["Exposed: physical data"],
        ))
        
        # ─── DATA HYGIENE RULES ────────────────────────────────────────
        rules.append(ContextRule(
            name="online_presence_audit",
            category="Data Hygiene",
            condition=lambda ctx: bool(ctx["tags"] & {"name", "email", "phone", "username"}),
            action_template="Audit your online presence and remove unnecessary personal information from social media profiles and public directories.",
            priority="MEDIUM",
            linked_clause_keys=["PDPA:11(a)", "PDPA:7(a)"],
            triggers=["Exposed: personal data"],
        ))
        
        rules.append(ContextRule(
            name="monitoring_alerts",
            category="Data Hygiene",
            condition=lambda ctx: bool(ctx["tags"] & {"name", "email"}),
            action_template="Set up monitoring alerts (e.g., Google Alerts) for your exposed information to detect further misuse.",
            priority="LOW",
            linked_clause_keys=["PDPA:13(1)", "PDPA:8(a)"],
            triggers=["Exposed: name or email"],
        ))
        
        rules.append(ContextRule(
            name="data_deletion_request",
            category="Data Hygiene",
            condition=lambda ctx: ctx["scenario_key"] in ["UNAUTHORIZED_DATA_PROCESSING", "DATABASE_BREACH"],
            action_template="Request the data controller to delete or restrict processing of your personal data under your right to erasure (PDPA Section 16).",
            priority="HIGH",
            linked_clause_keys=["PDPA:16(a)", "PDPA:16(b)", "PDPA:14(1)"],
            triggers=["Scenario: data breach"],
        ))
        
        rules.append(ContextRule(
            name="remove_from_public_sources",
            category="Data Hygiene",
            condition=lambda ctx: ctx["scenario_key"] == "DOXXING" and bool(ctx["tags"] & {"addr", "phone", "name"}),
            action_template="Request removal of your personal information from public directories, people-search sites, and forums.",
            priority="HIGH",
            linked_clause_keys=["PDPA:16(a)", "PDPA:14(1)"],
            triggers=["Scenario: DOXXING"],
        ))
        
        # ─── EVIDENCE PRESERVATION RULES ────────────────────────────────────────
        rules.append(ContextRule(
            name="universal_evidence",
            category="Evidence Preservation",
            condition=lambda ctx: True,
            action_template="Screenshot and archive all evidence (accounts, posts, messages) with full context and timestamps before deletion.",
            priority="URGENT",
            linked_clause_keys=["CCA:7(a)", "ETA:7(a)"],
            triggers=["Universal action"],
        ))
        
        rules.append(ContextRule(
            name="impersonation_forensics",
            category="Evidence Preservation",
            condition=lambda ctx: "IMPERSONATION" in ctx["scenario_key"] or "IDENTITY" in ctx["scenario_key"],
            action_template="Document user profiles, profile pictures, messages, and followers of fake accounts impersonating you.",
            priority="HIGH",
            linked_clause_keys=["OSA:18(a)", "OSA:18(b)"],
            triggers=["Scenario: impersonation"],
        ))
        
        rules.append(ContextRule(
            name="account_logs",
            category="Evidence Preservation",
            condition=lambda ctx: "TAKEOVER" in ctx["scenario_key"] or "MISUSE" in ctx["scenario_key"],
            action_template="Export complete account activity log showing unauthorized access, messages sent, and changes made.",
            priority="HIGH",
            linked_clause_keys=["CCA:3(a)", "CCA:5"],
            triggers=["Scenario: account takeover"],
        ))
        
        rules.append(ContextRule(
            name="breach_docs",
            category="Evidence Preservation",
            condition=lambda ctx: "BREACH" in ctx["scenario_key"],
            action_template="Obtain official breach notification from organization with details of exposed data, timeline, and remediation.",
            priority="HIGH",
            linked_clause_keys=["PDPA:12(1)(f)", "PDPA:12(1)(a)"],
            triggers=["Scenario: DATABASE_BREACH"],
        ))
        
        return rules

    def generate(
        self,
        validated_input: Dict,
        scenario_key: str = "DATA_EXPOSURE",
        severity_level: str = "Low",
        matched_clauses: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Generate recommendations by evaluating all context rules.
        All recommendations are driven by rule-based legal logic and context analysis.

        Parameters
        ----------
        validated_input : dict
            Output from InputValidator.validate()
        scenario_key : str
            Incident scenario (IDENTITY_IMPERSONATION, DATABASE_BREACH, etc.)
        severity_level : str
            Critical|High|Moderate|Low
        matched_clauses : list[dict], optional
            Clause objects from explanation generator

        Returns
        -------
        list[dict]
            Each dict has: action, priority, category, triggers, linked_clauses
        """
        tags = set(validated_input.get("normalized_tags", []))
        platform = validated_input.get("platform", "")
        clauses = matched_clauses or []

        # Derive context flags from tags and params
        impersonate = "impersonate" in tags
        img_exposed = "img_exposed" in tags
        account_tags = tags & {"email", "phone", "username"}
        identity_tags = tags & {"id", "name", "dob"}
        physical_tags = tags & {"addr", "location"}
        law_codes = {clause.get("law_code", "") for clause in clauses if clause.get("law_code")}
        
        # Build context dict for rule evaluation
        context = {
            "tags": tags,
            "platform": platform,
            "scenario_key": scenario_key,
            "severity_level": severity_level,
            "impersonate": impersonate,
            "img_exposed": img_exposed,
            "account_tags": account_tags,
            "account_tags_label": ", ".join(sorted([_FEATURE_LABELS[t] for t in account_tags])),
            "identity_tags": identity_tags,
            "identity_tags_label": ", ".join(sorted([_FEATURE_LABELS[t] for t in identity_tags])),
            "physical_tags": physical_tags,
            "physical_tags_label": ", ".join(sorted([_FEATURE_LABELS[t] for t in physical_tags])),
            "law_codes": law_codes,
            "dynamic_priority": "URGENT" if severity_level == "Critical" else "HIGH",
        }

        # Evaluate all rules and collect matching recommendations
        results = []
        for rule in self.rules:
            rec = rule.build_recommendation(context, clauses)
            if rec:
                results.append(rec)

        # Remove duplicates by action text
        seen_actions = set()
        deduplicated = []
        for rec in results:
            action_key = rec["action"]
            if action_key not in seen_actions:
                seen_actions.add(action_key)
                deduplicated.append(rec)

        # Sort by priority
        deduplicated.sort(key=lambda r: _PRIORITY_ORDER.get(r["priority"], 3))
        
        return deduplicated
