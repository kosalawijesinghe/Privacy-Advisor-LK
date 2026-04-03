"""
Scenario–Clause Relevance Matrix
==================================
Expert-defined mapping from each incident scenario category to the specific
legal clauses that are directly applicable.

For each scenario category, clauses are divided into:
  - PRIMARY   : directly and specifically targets this scenario type
  - SECONDARY : broadly applicable or supportive clause
  - EXCLUDED  : (everything not listed) — irrelevant to this scenario

This matrix is the ground truth for strict legal relevance filtering.
It replaces loose tag-matching with expert-curated legal reasoning.
"""

from typing import Dict, FrozenSet


# Type alias: each entry is a frozenset of "LAW_CODE:Section" keys
_ClauseSet = FrozenSet[str]


def _fs(*keys: str) -> _ClauseSet:
    return frozenset(keys)


# ═══════════════════════════════════════════════════════════════════════════════
# PRIMARY clauses: directly and specifically applicable to the scenario
# ═══════════════════════════════════════════════════════════════════════════════

PRIMARY: Dict[str, _ClauseSet] = {

    "IDENTITY_IMPERSONATION": _fs(
        # OSA — Online cheating by personation (all 3 sub-sections)
        "OSA:18(a)", "OSA:18(b)", "OSA:18(c)",
        # OSA — Communicating statements to cause harassment
        "OSA:20(1)",
        # CCA — Unauthorized access with intent to commit offence
        "CCA:4(a)", "CCA:4(b)",
        # CCA — Unauthorized disclosure of access info
        "CCA:10",
        # TCA — Deceiving persons using telecom
        "TCA:46B",
        # TCA — False information to obtain telecom service
        "TCA:46C",
        # ETA — Attribution of electronic records
        "ETA:12(1)(a)",
    ),

    "IMAGE_ABUSE": _fs(
        # OSA — Communicating statements to cause harassment (image/private info)
        "OSA:20(1)",
        # OSA — Online cheating by personation (if image used for impersonation)
        "OSA:18(a)", "OSA:18(c)",
        # PDPA — Integrity and confidentiality obligation
        "PDPA:10(a)", "PDPA:10(b)",
        # PDPA — Confine processing to defined purpose
        "PDPA:7(a)", "PDPA:7(c)",
        # CCA — Dealing with unlawfully obtained info
        "CCA:7(a)", "CCA:7(c)",
    ),

    "ACCOUNT_MISUSE": _fs(
        # CCA — Unauthorized access
        "CCA:3(a)", "CCA:3(b)",
        # CCA — Unauthorized access with intent
        "CCA:4(a)", "CCA:4(b)",
        # CCA — Unauthorized function
        "CCA:5",
        # CCA — Unauthorized disclosure
        "CCA:10",
        # ETA — Attribution of electronic records (identity verification)
        "ETA:12(1)(a)", "ETA:12(1)(b)", "ETA:12(1)(c)",
        # ETA — Electronic signatures
        "ETA:7(a)", "ETA:7(b)(ii)",
    ),

    "DATABASE_BREACH": _fs(
        # PDPA — Purpose limitation
        "PDPA:6(1)a)", "PDPA:6(1)b)", "PDPA:6(1)c)",
        # PDPA — Proportionality
        "PDPA:7(a)", "PDPA:7(b)", "PDPA:7(c)",
        # PDPA — Integrity and confidentiality
        "PDPA:10(a)", "PDPA:10(b)",
        # PDPA — Right of access
        "PDPA:13(1)",
        # PDPA — Accountability
        "PDPA:12(1)(a)", "PDPA:12(1)(f)",
        # CCA — Dealing with unlawfully obtained data
        "CCA:7(a)", "CCA:7(b)", "CCA:7(c)",
        # CCA — Unauthorized access
        "CCA:3(a)", "CCA:3(b)",
    ),

    "UNAUTHORIZED_DATA_PROCESSING": _fs(
        # PDPA — Purpose limitation (all sub-sections)
        "PDPA:6(1)a)", "PDPA:6(1)b)", "PDPA:6(1)c)",
        # PDPA — Confine to purpose
        "PDPA:7(a)", "PDPA:7(b)", "PDPA:7(c)",
        # PDPA — Retention limits
        "PDPA:9",
        # PDPA — Transparency
        "PDPA:11(a)", "PDPA:11(b)",
        # PDPA — Right to object
        "PDPA:14(1)", "PDPA:14(2)",
        # PDPA — Right to erasure
        "PDPA:16(a)", "PDPA:16(b)",
        # RTI — Denial of access for privacy
        "RTI:5(1)(a)",
    ),

    "DATA_EXPOSURE": _fs(
        # PDPA — Purpose limitation
        "PDPA:6(1)a)", "PDPA:6(1)b)",
        # PDPA — Confine to purpose
        "PDPA:7(a)", "PDPA:7(c)",
        # PDPA — Integrity and confidentiality
        "PDPA:10(a)", "PDPA:10(b)",
        # PDPA — Prevent loss/damage
        "PDPA:8(a)",
        # PDPA — Right of access
        "PDPA:13(1)",
        # PDPA — Transparency
        "PDPA:11(a)",
        # PDPA — Right to object
        "PDPA:14(1)",
        # PDPA — Accountability
        "PDPA:12(1)(a)",
        # CCA — Dealing with unlawfully obtained info
        "CCA:7(a)", "CCA:7(b)", "CCA:7(c)",
    ),

    "DOXXING": _fs(
        # OSA — Communicating statements to cause harassment
        "OSA:20(1)",
        # OSA — Online cheating by personation
        "OSA:18(a)", "OSA:18(c)",
        # PDPA — Integrity and confidentiality
        "PDPA:10(a)", "PDPA:10(b)",
        # PDPA — Confine processing to purpose
        "PDPA:7(a)",
        # CCA — Dealing with unlawfully obtained info
        "CCA:7(a)", "CCA:7(b)",
    ),

    "HARASSMENT": _fs(
        # OSA — Communicating statements to cause harassment
        "OSA:20(1)",
        # OSA — Online cheating by personation
        "OSA:18(a)",
        # PDPA — Integrity and confidentiality
        "PDPA:10(a)", "PDPA:10(b)",
        # PDPA — Confine processing to purpose
        "PDPA:7(a)",
        # CCA — Dealing with unlawfully obtained info
        "CCA:7(a)",
        # TCA — Deceiving persons using telecom
        "TCA:46B",
    ),

    "IDENTITY_THEFT": _fs(
        # CCA — Unauthorized access with intent to commit offence
        "CCA:4(a)", "CCA:4(b)",
        # CCA — Unauthorized access
        "CCA:3(a)",
        # CCA — Unauthorized disclosure
        "CCA:10",
        # TCA — Deceiving / misleading via telecom
        "TCA:46B",
        # TCA — False info to obtain telecom service
        "TCA:46C",
        # TCA — Unauthorized intrusion
        "TCA:52(a)",
        # PDPA — Integrity and confidentiality
        "PDPA:10(a)",
        # PDPA — Confine processing
        "PDPA:7(a)",
        # ETA — Attribution of electronic records
        "ETA:12(1)(a)",
    ),

    "ACCOUNT_TAKEOVER": _fs(
        # CCA — Unauthorized access
        "CCA:3(a)", "CCA:3(b)",
        # CCA — Unauthorized access with intent
        "CCA:4(a)", "CCA:4(b)",
        # CCA — Unauthorized function
        "CCA:5",
        # CCA — Unauthorized disclosure
        "CCA:10",
        # TCA — Unauthorized intrusion
        "TCA:52(a)", "TCA:52(d)",
        # TCA — Deceiving via telecom
        "TCA:46B",
        # TCA — False info to obtain telecom service
        "TCA:46C",
        # ETA — Attribution of electronic records
        "ETA:12(1)(a)", "ETA:12(1)(b)",
        # ETA — Electronic signatures
        "ETA:7(a)",
        # PDPA — Integrity and confidentiality
        "PDPA:10(a)",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# SECONDARY clauses: broadly applicable, supportive, or contextually relevant
# ═══════════════════════════════════════════════════════════════════════════════

SECONDARY: Dict[str, _ClauseSet] = {

    "IDENTITY_IMPERSONATION": _fs(
        # PDPA — Integrity & confidentiality (data that enabled impersonation)
        "PDPA:10(a)",
        # PDPA — Right of access (victim's right to know)
        "PDPA:13(1)",
        # CCA — Dealing with unlawfully obtained info
        "CCA:7(a)",
        # ETA — Attribution concerns
        "ETA:12(2)(a)",
        # TCA — Unauthorized intrusion with intent
        "TCA:52(d)",
        # OSA — Circulating false report
        "OSA:19",
    ),

    "IMAGE_ABUSE": _fs(
        # PDPA — Transparency
        "PDPA:11(a)",
        # PDPA — Right to erasure
        "PDPA:16(a)",
        # PDPA — Right to object
        "PDPA:14(1)",
        # RTI — Privacy protection
        "RTI:5(1)(a)",
        # TCA — Unauthorized disclosure
        "TCA:49(c)",
        # OSA — Circulating false report
        "OSA:19",
        # OSA — Online cheating by personation
        "OSA:18(b)",
    ),

    "ACCOUNT_MISUSE": _fs(
        # PDPA — Integrity and confidentiality
        "PDPA:10(a)", "PDPA:10(b)",
        # TCA — Deceiving persons
        "TCA:46B",
        # TCA — Unauthorized intrusion
        "TCA:52(a)", "TCA:52(d)",
        # ETA — Reliance on attributed records
        "ETA:12(2)(a)", "ETA:12(2)(b)",
    ),

    "DATABASE_BREACH": _fs(
        # PDPA — Transparency
        "PDPA:11(a)",
        # PDPA — Retention limit
        "PDPA:9",
        # PDPA — Right to erasure
        "PDPA:16(a)",
        # PDPA — Accountability (broader)
        "PDPA:12(1)(b)", "PDPA:12(1)(c)",
        # RTI — Privacy protection
        "RTI:5(1)(a)",
    ),

    "UNAUTHORIZED_DATA_PROCESSING": _fs(
        # PDPA — Accountability
        "PDPA:12(1)(a)", "PDPA:12(1)(f)",
        # PDPA — Integrity
        "PDPA:10(a)", "PDPA:10(b)",
        # PDPA — Right to erasure (additional)
        "PDPA:16(c)",
        # PDPA — Right of access
        "PDPA:13(1)",
        # RTI — Medical records privacy
        "RTI:5(1)(e)",
    ),

    "DATA_EXPOSURE": _fs(
        # PDPA — Retention
        "PDPA:9",
        # PDPA — Right to erasure
        "PDPA:16(a)",
        # TCA — Unauthorized disclosure
        "TCA:49(c)",
        # TCA — Interception
        "TCA:52(a)",
    ),

    "DOXXING": _fs(
        # PDPA — Transparency
        "PDPA:11(a)",
        # PDPA — Right to erasure
        "PDPA:16(a)",
        # PDPA — Right to object
        "PDPA:14(1)",
        # PDPA — Purpose limitation
        "PDPA:6(1)a)",
        # RTI — Privacy protection
        "RTI:5(1)(a)",
        # OSA — Circulating false report
        "OSA:19",
    ),

    "HARASSMENT": _fs(
        # PDPA — Transparency
        "PDPA:11(a)",
        # PDPA — Right to erasure
        "PDPA:16(a)",
        # PDPA — Right to object
        "PDPA:14(1)",
        # RTI — Privacy protection
        "RTI:5(1)(a)",
        # TCA — Unauthorized disclosure
        "TCA:49(c)",
        # OSA — Circulating false report
        "OSA:19",
    ),

    "IDENTITY_THEFT": _fs(
        # PDPA — Purpose limitation
        "PDPA:6(1)a)", "PDPA:6(1)b)",
        # PDPA — Integrity and confidentiality
        "PDPA:10(b)",
        # PDPA — Right of access
        "PDPA:13(1)",
        # CCA — Dealing with unlawfully obtained info
        "CCA:7(a)",
        # ETA — Attribution
        "ETA:12(1)(b)", "ETA:12(2)(a)",
        # TCA — Authorized intrusion with intent
        "TCA:52(d)",
    ),

    "ACCOUNT_TAKEOVER": _fs(
        # PDPA — Integrity
        "PDPA:10(b)",
        # PDPA — Right of access
        "PDPA:13(1)",
        # CCA — Dealing with unlawfully obtained info
        "CCA:7(a)", "CCA:7(b)",
        # ETA — Attribution of electronic records
        "ETA:12(1)(c)", "ETA:12(2)(a)", "ETA:12(2)(b)",
        # ETA — Electronic signatures
        "ETA:7(b)(ii)",
        # OSA — Communicating statements to cause harassment
        "OSA:20(1)",
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Lookup helpers
# ═══════════════════════════════════════════════════════════════════════════════

def clause_key(law_code: str, section: str) -> str:
    """Build the canonical lookup key for a clause."""
    return f"{law_code}:{section}"


def get_relevance_tier(scenario_key: str, law_code: str, section: str) -> str:
    """
    Determine the relevance tier of a clause for a given scenario.

    Returns
    -------
    str : "PRIMARY", "SECONDARY", or "EXCLUDED"
    """
    key = clause_key(law_code, section)
    if key in PRIMARY.get(scenario_key, frozenset()):
        return "PRIMARY"
    if key in SECONDARY.get(scenario_key, frozenset()):
        return "SECONDARY"
    return "EXCLUDED"


# ═══════════════════════════════════════════════════════════════════════════════
# TAG → CLAUSE expert mapping
# ═══════════════════════════════════════════════════════════════════════════════
# Maps each PII data type to the specific legal provisions that most directly
# protect or regulate that type of personal data.  This is independent of
# scenario — it tells you "if THIS data is exposed, THESE are the laws that
# specifically address it."

TAG_CLAUSE_MAP: Dict[str, _ClauseSet] = {

    "name": _fs(
        "PDPA:6(1)a)",   # Purpose limitation — defined purpose for PII
        "PDPA:10(a)",    # Integrity and confidentiality
        "PDPA:13(1)",    # Right of access to personal data
        "PDPA:8(a)",     # Obligation to ensure accuracy
        "PDPA:7(a)",     # Confine processing to purpose
    ),

    "id": _fs(
        "PDPA:6(1)b)",   # Explicit purpose definition
        "PDPA:7(a)",     # Confine processing
        "PDPA:10(a)",    # Integrity and confidentiality
        "PDPA:12(1)(a)", # Accountability
        "CCA:7(a)",      # Unlawfully obtained data
        "PDPA:7(b)",     # Proportionality of processing
    ),

    "email": _fs(
        "PDPA:7(c)",     # Confine processing
        "PDPA:11(a)",    # Transparency — provide info to subject
        "PDPA:14(1)",    # Right to withdraw consent / object
        "CCA:3(a)",      # Unauthorized access (email accounts)
        "TCA:49(c)",     # Unauthorized disclosure via telecom
        "PDPA:10(a)",    # Integrity
    ),

    "phone": _fs(
        "TCA:46B",       # Deceiving/misleading via telecom
        "TCA:46C",       # False info to obtain telecom service
        "TCA:49(c)",     # Unauthorized disclosure
        "PDPA:10(a)",    # Integrity and confidentiality
        "PDPA:7(a)",     # Confine processing
    ),

    "addr": _fs(
        "PDPA:6(1)a)",   # Purpose limitation
        "PDPA:10(b)",    # Prevent loss, destruction, damage
        "PDPA:8(a)",     # Accuracy obligation
        "PDPA:9",        # Retention limits
        "PDPA:7(a)",     # Confine processing
    ),

    "dob": _fs(
        "PDPA:6(1)c)",   # Legitimate purpose
        "PDPA:7(b)",     # Proportionality
        "PDPA:9",        # Retention limits
        "PDPA:16(a)",    # Right to erasure
    ),

    "username": _fs(
        "CCA:3(a)",      # Unauthorized access
        "CCA:3(b)",      # Unauthorized access to info
        "CCA:4(a)",      # Unauthorized access with intent
        "CCA:10",        # Disclosure enabling access
        "ETA:12(1)(a)",  # Attribution of electronic records
        "ETA:7(a)",      # Electronic signatures
    ),

    "location": _fs(
        "PDPA:6(1)a)",   # Purpose limitation
        "PDPA:7(a)",     # Confine to purpose
        "PDPA:10(a)",    # Integrity
        "TCA:52(a)",     # Unauthorized intrusion
        "TCA:52(d)",     # Intrusion with intent
    ),

    "impersonate": _fs(
        "OSA:18(a)",     # Cheating by personation
        "OSA:18(b)",     # Cheating by personation
        "OSA:18(c)",     # Cheating by personation
        "CCA:4(a)",      # Unauthorized access with intent
        "CCA:4(b)",      # Unauthorized access with intent
        "TCA:46B",       # Deceiving via telecom
    ),

    "img_exposed": _fs(
        "OSA:20(1)",     # Harassment via statements/images
        "OSA:18(a)",     # Online cheating by personation
        "OSA:18(c)",     # Personation using someone's image
        "PDPA:10(a)",    # Integrity — image as personal data
        "PDPA:16(a)",    # Right to erasure
        "CCA:7(a)",      # Unlawfully obtained info
        "CCA:7(c)",      # Acquiring unlawfully obtained info
    ),
}


def get_tag_clauses(tag: str) -> FrozenSet[str]:
    """Return the set of clause keys specifically relevant to a PII tag."""
    return TAG_CLAUSE_MAP.get(tag, frozenset())


def get_clauses_for_tag(tag: str, matched_clauses: list) -> list:
    """
    From a list of matched clause dicts, return those specifically
    relevant to the given tag, sorted by relevance_score descending.
    """
    relevant_keys = TAG_CLAUSE_MAP.get(tag, frozenset())
    result = []
    for c in matched_clauses:
        key = clause_key(c.get("law_code", ""), c.get("section", ""))
        if key in relevant_keys:
            result.append(c)
    result.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return result


def get_tags_for_clause(law_code: str, section: str, user_tags: list) -> list:
    """
    Given a clause and the user's selected tags, return which tags
    this clause specifically protects.
    """
    key = clause_key(law_code, section)
    matched = []
    for tag in user_tags:
        if key in TAG_CLAUSE_MAP.get(tag, frozenset()):
            matched.append(tag)
    return matched
