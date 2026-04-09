"""
Module 10 — Legal Explanation Generator
=========================================
For each applicable clause, generates:
  - A clause+scenario-specific plain-language reason (why THIS law applies to THIS incident)
  - An impact classification: Criminal Offence / Civil Liability / Administrative Fine
  - A concise impact summary (penalty translated to plain language)

Each explanation is specific to the combination of scenario + clause — not a
generic "your email falls under this provision" but a precise legal rationale.
"""

import json
import os
import re
from typing import Dict, List


def _load_config() -> dict:
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "config.json"))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Tag labels for human-readable output
_TAG_LABELS = {
    "name": "Full Name",
    "id": "National ID / NIC",
    "phone": "Phone Number",
    "email": "Email Address",
    "addr": "Physical Address",
    "dob": "Date of Birth",
    "username": "Username / Handle",
    "location": "Location Data",
    "impersonate": "Impersonation",
    "img_exposed": "Image Exposure",
}

# ── Impact Classification ────────────────────────────────────────────────────
# Maps law_code to its primary enforcement type
_LAW_IMPACT_TYPE: Dict[str, str] = {
    "OSA":   "Criminal Offence",
    "CCA":   "Criminal Offence",
    "TCA":   "Criminal & Regulatory",
    "ETA":   "Civil & Administrative",
    "PDPA":  "Civil & Administrative",
    "RTI":   "Administrative",
}

# Penalty text keywords → impact type refinement
_YEAR_RE   = re.compile(r"(\d+)\s*(?:year|yr)", re.IGNORECASE)
_FINE_RE   = re.compile(r"(?:LKR|Rs\.?)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
_MILLION_RE = re.compile(r"(\d+(?:\.\d+)?)\s*million", re.IGNORECASE)


def _parse_impact_summary(penalty_text: str, law_code: str) -> tuple:
    """
    Parse penalty text into (impact_type, impact_summary).
    Returns (str, str).
    """
    if not penalty_text:
        return _LAW_IMPACT_TYPE.get(law_code, "Legal Liability"), "Penalties as specified in the Act"

    impact_type = _LAW_IMPACT_TYPE.get(law_code, "Legal Liability")
    parts = []

    years_found = _YEAR_RE.findall(penalty_text)
    if years_found:
        max_y = max(int(y) for y in years_found)
        parts.append(f"Up to {max_y} year{'s' if max_y != 1 else ''} imprisonment")

    millions = _MILLION_RE.findall(penalty_text)
    fines_raw = _FINE_RE.findall(penalty_text)
    if millions:
        max_m = max(float(m) for m in millions)
        parts.append(f"Fine up to LKR {max_m:.0f} million")
    elif fines_raw:
        amounts = [float(f.replace(",", "")) for f in fines_raw]
        max_f = max(amounts)
        if max_f >= 1_000_000:
            parts.append(f"Fine up to LKR {max_f / 1_000_000:.1f} million")
        else:
            parts.append(f"Fine up to LKR {max_f:,.0f}")

    summary = " and/or ".join(parts) if parts else penalty_text[:100]
    return impact_type, summary


# ── Recommended Actions per Governing Law ───────────────────────────────────
_LAW_RECOMMENDED_ACTION: Dict[str, str] = {
    "PDPA": (
        "File a complaint with the Data Protection Authority of Sri Lanka. "
        "Demand a full account of data held about you, the purpose, and a breach notification."
    ),
    "OSA": (
        "File a complaint with Sri Lanka Police Cyber Crimes Division (CID, Colombo 07) "
        "citing the relevant Online Safety Act section. Preserve all digital evidence before filing."
    ),
    "CCA": (
        "Report to Sri Lanka Police Cyber Crimes Division. "
        "Preserve screenshots, logs, and timestamps as evidence before filing the complaint."
    ),
    "TCA": (
        "File a complaint with the Telecommunications Regulatory Commission of Sri Lanka (TRCSL). "
        "Also report to police if the conduct amounts to a criminal offence."
    ),
    "ETA": (
        "Seek legal counsel to challenge the validity of any disputed electronic record. "
        "Document all electronic interactions with timestamps."
    ),
    "RTI": (
        "File a Right to Information request to access all personal information held about you. "
        "Escalate to the RTI Commission if the request is refused without lawful reason."
    ),
}

# ── Per-tag plain-language risk descriptions ─────────────────────────────────
_TAG_RISK_DESCRIPTIONS: Dict[str, str] = {
    "name":       "Disclosure of your full name enables identity fraud, targeted harassment, and social-engineering attacks.",
    "id":         "Exposure of your NIC or passport number enables full identity theft, fraudulent financial transactions, and impersonation before authorities.",
    "phone":      "Public disclosure of your phone number enables harassment calls, SIM-swap fraud, and unsolicited contact by bad actors.",
    "email":      "Disclosure of your email address enables phishing, account takeover attempts, and targeted spam campaigns.",
    "addr":       "Exposure of your physical address creates serious risks of stalking, physical harm, and fraudulent deliveries.",
    "dob":        "Date-of-birth disclosure enables identity verification bypass and, combined with other data, facilitates full identity fraud.",
    "username":   "Exposure of your username or handle enables targeted harassment, account linking across platforms, and social-engineering attacks.",
    "location":   "Disclosure of your location data enables physical stalking, routine mapping by bad actors, and targeted physical attacks.",
    "impersonate": "Someone is actively using your identity to deceive others, causing reputational harm and potential financial loss to your contacts.",
    "img_exposed": "Your personal images have been shared without consent, risking reputational damage, harassment campaigns, and psychological distress.",
}

# ── Clause type classification and templates ──────────────────────────────────
# Helps identify what kind of provision this clause is, and use appropriate templates
def _classify_clause_type(clause_desc: str, clause_title: str) -> str:
    """Classify clause as Protection, Penalty, Procedure, or Rights."""
    combined = f"{clause_desc} {clause_title}".lower()
    
    if any(w in combined for w in ("right", "entitle", "may request", "access to", "demand", "withdraw")):
        return "Rights"
    elif any(w in combined for w in ("penalise", "penalize", "punishment", "imprisonment", "fine", "criminal", "offence", "offence", "prohibited", "prohibit")):
        return "Penalty"
    elif any(w in combined for w in ("must maintain", "must", "obligation", "require", "shall", "confidentiality", "integrity", "prevent loss", "prevent", "unauthorized")):
        return "Protection"
    elif any(w in combined for w in ("process", "procedure", "notify", "inform", "report", "disclosure", "permit")):
        return "Procedure"
    else:
        return "Legal Provision"


def _build_explanation_template(clause_type: str, law_name: str, section: str, 
                                 title: str, user_pii: List[str], scenario: str) -> str:
    """Build context-rich explanation based on clause type."""
    if not user_pii:
        user_pii = ["your personal data"]
    
    pii_phrase = " and ".join(user_pii) if len(user_pii) > 1 else user_pii[0] if user_pii else "your personal data"
    
    if clause_type == "Rights":
        return (
            f"This provision gives you the power to take action. {title.rstrip('.')}, "
            f"specifically in relation to {pii_phrase}. "
            f"Once your data has been exposed through this incident, you can invoke this right to demand access, "
            f"correction, or deletion of your information from any organization that holds it."
        )
    
    elif clause_type == "Penalty":
        return (
            f"This is a criminal provision. Under {law_name} Section {section}, "
            f"{title.lower().rstrip('.')}. Anyone who caused or contributed to the exposure of {pii_phrase} "
            f"in your incident could face criminal liability, including imprisonment and fines, if their conduct meets the elements of this offence."
        )
    
    elif clause_type == "Protection":
        return (
            f"This provision imposes a legal duty to protect you. The organization or individual responsible for your data "
            f"is legally required to {title.lower().rstrip('.')}, particularly regarding {pii_phrase}. "
            f"The fact that your data was exposed in this incident shows they failed to meet this legal obligation."
        )
    
    elif clause_type == "Procedure":
        return (
            f"This provision establishes procedural requirements. Under {law_name} Section {section}, "
            f"organizations handling {pii_phrase} must {title.lower().rstrip('.')}. "
            f"The exposure of your data may indicate these procedures were not followed."
        )
    
    else:  # Legal Provision
        return (
            f"This legal provision from {law_name} Section {section} is directly applicable to your situation: {title}. "
            f"The exposure of {pii_phrase} invokes this provision, which provides protections, remedies, and/or accountability mechanisms "
            f"specific to your incident. Understanding this provision helps you know your rights and legal options."
        )


def _build_what_this_means_for_you(clause_type: str, law_code: str, user_pii: List[str], scenario: str) -> str:
    """Build a personalized 'What this means for you' explanation."""
    if not user_pii:
        user_pii = ["your personal data"]
    
    pii_phrase = ", ".join(user_pii[:2])  # First 2 PII types for brevity
    
    implications = {
        "Rights": (
            f"You can formally request that organizations stop using {pii_phrase} indefinitely. "
            f"They must comply with your request within a specified timeframe (usually 30 days) or face penalties."
        ),
        "Penalty": (
            f"The person or organization responsible for exposing {pii_phrase} could face criminal charges, "
            f"imprisonment, and substantial fines. This gives you grounds to pursue criminal remedies through police and prosecution authorities."
        ),
        "Protection": (
            f"If {law_code} obligations were violated, the responsible organization can be held liable for damages. "
            f"You may have grounds for civil compensation if you can prove losses resulting from the exposure of {pii_phrase}."
        ),
        "Procedure": (
            f"If procedures were not followed before or after the exposure of {pii_phrase}, this strengthens your complaint "
            f"and demonstrates organizational negligence or misconduct."
        ),
        "Legal Provision": (
            f"This provision from {law_code} strengthens your legal position. It establishes that organizations must not allow {pii_phrase} "
            f"to be exposed, and it provides you with legal remedies and grounds for complaint if they do."
        ),
    }
    
    clause_type_key = clause_type if clause_type in implications else "Legal Provision"
    return implications.get(clause_type_key, "You have legal protections and remedies available to you.")


def _build_risk_summary(
    impact_type: str,
    matched_tags: set,
    impersonate: bool,
    img_exposed: bool,
) -> str:
    """Return a plain-language risk description based on the matched PII tags for this clause."""
    if impersonate and "impersonate" in _TAG_RISK_DESCRIPTIONS:
        return _TAG_RISK_DESCRIPTIONS["impersonate"]
    if img_exposed and not (matched_tags - {"img_exposed"}):
        return _TAG_RISK_DESCRIPTIONS["img_exposed"]

    # Priority order: most-sensitive tags first
    priority_order = ["id", "addr", "phone", "email", "dob", "name", "username", "location", "img_exposed"]
    for tag in priority_order:
        if tag in matched_tags and tag in _TAG_RISK_DESCRIPTIONS:
            return _TAG_RISK_DESCRIPTIONS[tag]

    if img_exposed:
        return _TAG_RISK_DESCRIPTIONS["img_exposed"]

    return (
        f"{impact_type}: unauthorized access to or disclosure of your personal information "
        "creates risks of fraud, harassment, and reputational harm."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helper functions for law-grounded explanations
# ──────────────────────────────────────────────────────────────────────────────

def _extract_legal_requirements(full_text: str, description: str, title: str) -> list:
    """
    Extract key legal requirements/obligations from the actual legal text.
    Returns a list of requirement phrases (use first one as primary).
    """
    requirements = []
    
    # Clean up text
    full_text = (full_text or "").strip()
    description = (description or "").strip()
    title = (title or "").strip()
    
    # Priority 1: Look for explicit requirements in full_text
    if full_text:
        # Match sentences with "shall", "must", "required to", "obligation"
        import re
        sentences = re.split(r'[.;]\s+', full_text)
        for sent in sentences:
            sent_lower = sent.lower().strip()
            if any(req in sent_lower for req in ("shall", "must", "obligation", "require", "shall not", "must not")):
                # Trim to reasonable length and clean up
                cleaned = re.sub(r'\s+', ' ', sent.strip())
                cleaned = re.sub(r'^[a-z]\)\s*', '', cleaned)  # Remove "a) " prefix
                if len(cleaned) > 20 and len(cleaned) < 200:
                    requirements.append(cleaned)
                    break
    
    # Priority 2: Use description if it contains key legal concepts
    if not requirements and description:
        desc_lower = description.lower()
        if any(w in desc_lower for w in ("must", "shall", "require", "obligation", "cannot", "may not")):
            cleaned = re.sub(r'\s+', ' ', description.strip())
            if len(cleaned) > 20:
                requirements.append(cleaned)
    
    # Priority 3: Use title if it's specific enough
    if not requirements and title:
        title_lower = title.lower()
        if any(w in title_lower for w in ("obligation", "requirement", "must", "duty")):
            if len(title) > 20:
                requirements.append(title)
    
    return requirements


def _extract_key_phrase(full_text: str, keywords: str) -> str:
    """
    Extract a key phrase from full_text that contains any of the keywords.
    Keywords are pipe-separated, e.g., "pretend|fake|deceive"
    """
    if not full_text:
        return ""
    
    import re
    keyword_list = [kw.strip() for kw in keywords.split("|")]
    sentences = re.split(r'[.;]\s+', full_text)
    
    for sent in sentences:
        sent_lower = sent.lower()
        if any(kw in sent_lower for kw in keyword_list):
            # Clean up and trim
            cleaned = re.sub(r'\s+', ' ', sent.strip())
            cleaned = re.sub(r'^[a-z]\)\s*', '', cleaned)  # Remove subsection prefix
            if len(cleaned) < 150:
                return cleaned
            # If too long, extract just the relevant part
            for kw in keyword_list:
                if kw in sent_lower:
                    words = sent.split()
                    for i, word in enumerate(words):
                        if kw in word.lower():
                            # Extract 5 words before and after
                            start = max(0, i - 5)
                            end = min(len(words), i + 6)
                            phrase = " ".join(words[start:end])
                            return phrase
    
    # Fallback: return first sentence if nothing matched
    if sentences:
        return re.sub(r'^[a-z]\)\s*', '', sentences[0].strip())[:150]
    
    return ""


class ExplanationGenerator:
    """Generates user-friendly, clause+scenario-specific explanations."""

    def __init__(self):
        cfg = _load_config()
        self._scenario_contexts: Dict[str, str] = {}
        for sd in cfg.get("scenario_definitions", []):
            self._scenario_contexts[sd["key"]] = sd.get("clause_context", "")

    def generate(
        self,
        filtered_clauses: List[Dict],
        user_tags: List[str],
        scenario_key: str = "DATA_EXPOSURE",
        impersonate: bool = False,
        img_exposed: bool = False,
    ) -> List[Dict]:
        """
        Generate explanations for each clause.

        Adds ``explanation_text`` to each clause dict containing:
          - law_label          : str — "OSA — Section 18(a)"
          - title              : str
          - why_relevant       : str — specific reasoning for this clause in this scenario
          - legal_implications : str — formatted penalty and law details
          - impact_type        : str — "Criminal Offence" / "Civil & Administrative" etc.
          - impact_summary     : str — human-readable penalty
          - existing_explanation : str — original clause explanation from DB
          - structured         : dict — Detected Data / Risk / Legal Basis / Recommendation
        """
        tag_set = set(user_tags)
        # Derive indicator booleans from tags (overrides params)
        impersonate = impersonate or "impersonate" in tag_set
        img_exposed = img_exposed or "img_exposed" in tag_set
        results = []

        for clause in filtered_clauses:
            law_code  = clause.get("law_code", "")
            section   = clause.get("section", "")
            title     = clause.get("title", "")
            law_name  = clause.get("law_name", "")
            penalty   = clause.get("penalty", "")
            existing_expl = clause.get("explanation", "")
            clause_tags = set(clause.get("tags", []))

            # ── Why relevant: rule-driven generation based on context ──
            # Always use rule-driven dynamic generation for consistency and maintainability
            why = self._build_fallback_reasoning(
                tag_set, clause_tags, scenario_key, impersonate, img_exposed,
                clause=clause,
            )

            # ── Classify clause type and generate template-based explanation ──
            clause_type = _classify_clause_type(clause.get("description", ""), title)
            matched_pii = sorted([_TAG_LABELS.get(t, t) for t in (tag_set & clause_tags)])
            
            # Use template-based explanation for variety and context
            template_explanation = _build_explanation_template(
                clause_type, law_name or law_code, section, title, matched_pii, scenario_key
            )

            # ── Impact classification ──
            impact_type, impact_summary = _parse_impact_summary(penalty, law_code)

            # ── Legal implications ──
            implications = f"Under the {law_name}, Section {section}. {impact_summary}." if law_name else impact_summary

            # ── What this means for you ──
            what_this_means = _build_what_this_means_for_you(clause_type, law_code, matched_pii, scenario_key)

            explanation = {
                "law_label":           f"{law_name or law_code} — Section {section}",
                "title":               title,
                "clause_type":         clause_type,
                "why_relevant":        why,
                "context_explanation": template_explanation,
                "what_this_means":     what_this_means,
                "legal_implications":  implications,
                "impact_type":         impact_type,
                "impact_summary":      impact_summary,
                "existing_explanation": existing_expl,
                "structured": {
                    "detected_data": (
                        matched_pii
                        or (["Impersonation"] if impersonate else ["Image Exposure"] if img_exposed else ["Personal Data"])
                    ),
                    "risk_summary": _build_risk_summary(
                        impact_type, tag_set & clause_tags, impersonate, img_exposed
                    ),
                    "legal_basis": f"Under the {law_name or law_code}, Section {section} — {title}.",
                    "recommended_action": _LAW_RECOMMENDED_ACTION.get(
                        law_code,
                        "Document the incident, preserve all evidence, and seek legal advice from a qualified attorney.",
                    ),
                },
            }

            results.append({**clause, "explanation_text": explanation})

        return results

    def _build_fallback_reasoning(
        self,
        user_tags: set,
        clause_tags: set,
        scenario_key: str,
        impersonate: bool,
        img_exposed: bool,
        clause: dict = None,
    ) -> str:
        """
        Build SPECIFIC, CLAUSE-FOCUSED explanations driven by the ACTUAL LEGAL TEXT.
        
        Grounds explanations in the real legal requirements from full_text/description
        and explains why they apply to the user's specific incident.
        """
        clause = clause or {}
        clause_title = clause.get("title", "").strip()
        clause_desc = clause.get("description", "").strip()
        full_text = clause.get("full_text", "").strip()
        penalty_text = clause.get("penalty", "").strip()
        law_name = clause.get("law_name", clause.get("law_code", ""))
        section = clause.get("section", "")
        law_code = clause.get("law_code", "")

        matched_tags = sorted(user_tags & clause_tags)
        # Exclude attack-type tags (impersonate, img_exposed) from PII list — they're not exposed data
        matched_pii = [
            _TAG_LABELS.get(t, t) for t in matched_tags 
            if t not in ("impersonate", "img_exposed")
        ] if matched_tags else []
        pii_str = ", ".join(matched_pii) if matched_pii else ""

        # ──────────────────────────────────────────────────────────────────────
        # Deeper clause type classification
        # ──────────────────────────────────────────────────────────────────────
        desc_lower = clause_desc.lower()
        full_lower = full_text.lower()
        penalty_lower = penalty_text.lower()
        title_lower = clause_title.lower()
        
        is_criminal = any(w in desc_lower or w in penalty_lower or w in title_lower or w in full_lower
                         for w in ("criminal", "offence", "offense", "penalise", "penalize", "imprisonment", "unlawful", "commit"))
        is_obligation = any(w in desc_lower or w in title_lower or w in full_lower
                           for w in ("must", "require", "shall", "obligation", "maintain", "establish", "imposed", "ensure"))
        is_right = any(w in desc_lower or w in title_lower or w in full_lower
                      for w in ("right", "entitle", "may request", "may demand", "entitled to", "entitled", "demand"))
        is_procedure = any(w in desc_lower or w in title_lower or w in full_lower
                          for w in ("process", "procedure", "notify", "inform", "report", "disclosure", "notice"))
        is_security = any(w in desc_lower or w in title_lower or w in penalty_lower or w in full_lower
                         for w in ("security", "safeguard", "protect", "confidentiality", "integrity", "prevent loss", "unauthorized access"))

        # ──────────────────────────────────────────────────────────────────────
        # Extract SPECIFIC legal requirements from ACTUAL legal text
        # ──────────────────────────────────────────────────────────────────────
        legal_requirements = _extract_legal_requirements(full_text, clause_desc, clause_title)
        
        # ──────────────────────────────────────────────────────────────────────
        # SUBSECTION-SPECIFIC BEHAVIOR DETECTION: Generate distinct explanations
        # ──────────────────────────────────────────────────────────────────────
        subsection_behavior = ""
        subsection_framing = ""
        
        if section and "(" in section and ")" in section:
            # Extract subsection letter: 18(a) → a, 18(b) → b, etc.
            match = re.search(r'\(([a-z]+)\)', section.lower())
            if match:
                subsection_letter = match.group(1)
                desc_lower_check = clause_desc.lower() if clause_desc else ""
                
                # ── Behavior-specific analysis: Check description for specific behaviors ──
                if "pretend" in desc_lower_check or "fake" in desc_lower_check:
                    subsection_behavior = "FALSE_IDENTITY"  # Fake persona
                elif "substitut" in desc_lower_check:  # Matches "substitute", "substituting", etc.
                    subsection_behavior = "IDENTITY_SWAP"   # Replace real person
                elif "misrepresent" in desc_lower_check or "falsely" in desc_lower_check:
                    subsection_behavior = "MISREPRESENT"    # Wrong use of real identity
                
                # As safety net: Use section letter + title patterns to determine behavior
                # This ensures OSA 18 subsections get properly identified
                if not subsection_behavior and "personation" in clause_title.lower():
                    if subsection_letter == "a":
                        subsection_behavior = "FALSE_IDENTITY"
                    elif subsection_letter == "b":
                        subsection_behavior = "IDENTITY_SWAP"
                    elif subsection_letter == "c":
                        subsection_behavior = "MISREPRESENT"
                
                # Map subsection letters to role distinctions for fallback
                subsection_framing = {
                    "a": "as the primary/foundational provision",
                    "b": "as a secondary provision extending the scope of",
                    "c": "as an additional specific case concerning",
                    "d": "as a supplementary provision addressing",
                    "e": "as a broader application of",
                    "f": "as a specific enforcement mechanism for",
                    "g": "as a qualified exception or limitation to",
                    "h": "as a further elaboration on",
                }.get(subsection_letter, "")
        
        # ──────────────────────────────────────────────────────────────────────
        # PART A: LAW-GROUNDED explanation with actual legal requirements
        # ──────────────────────────────────────────────────────────────────────
        parts = []

        if matched_pii and clause_title:
            
            # Criminal provisions: grounded in actual legal text
            if is_criminal:
                if subsection_behavior == "FALSE_IDENTITY":
                    # Subsection (a): Pretending/fake persona
                    parts.append(
                        f"The perpetrator used your {pii_str} to create a **fake online identity** — posing as you to deceive others. "
                        f"{law_name} Section {section} states: \"{_extract_key_phrase(full_text, 'pretend|fake')}\" "
                        f"This false impersonation is a serious criminal offence punishable by imprisonment or substantial fines."
                    )
                elif subsection_behavior == "IDENTITY_SWAP":
                    # Subsection (b): Substituting/swapping identities
                    parts.append(
                        f"Your {pii_str} were used to **replace another person's identity** in online transactions or communications. "
                        f"{law_name} Section {section} criminalizes: \"{_extract_key_phrase(full_text, 'substitut|swap')}\" "
                        f"This identity substitution is a distinct criminal violation because it directly deceives platforms and other users."
                    )
                elif subsection_behavior == "MISREPRESENT":
                    # Subsection (c): Misrepresenting/false representation
                    parts.append(
                        f"Your {pii_str} were **misrepresented** online — your identity was falsely presented or your personal details wrongly attributed. "
                        f"{law_name} Section {section} prohibits: \"{_extract_key_phrase(full_text, 'misrepresent|represent')}\" "
                        f"This false representation constitutes a criminal offence, distinct from simple impersonation."
                    )
                elif legal_requirements:
                    # Use extracted legal requirements for other criminal cases
                    req = legal_requirements[0]
                    parts.append(
                        f"Your exposure of {pii_str} violates {law_name} Section {section}, which requires: \"{req}\" "
                        f"The exposure of your data during your {scenario_key.lower().replace('_', ' ')} incident directly breaches this criminal provision."
                    )
                else:
                    parts.append(
                        f"The exposure of your {pii_str} is a direct criminal violation under {law_name} Section {section}: {clause_title}."
                    )
            
            # Obligation/duty provisions: grounded in actual legal text
            elif is_obligation:
                if legal_requirements:
                    req = legal_requirements[0]
                    parts.append(
                        f"{law_name} Section {section} \"{clause_title}\" requires: \"{req}\" "
                        f"Your organization's exposure of your {pii_str} proves they breached this legal obligation. "
                        f"This breach creates direct liability for the data controller responsible for your information."
                    )
                else:
                    parts.append(
                        f"Your data holder violated {law_name} Section {section}: \"{clause_title}.\" "
                        f"The exposure of your {pii_str} demonstrates they failed to meet this legal requirement."
                    )
            
            # Rights provisions: grounded in actual legal text
            elif is_right:
                if legal_requirements:
                    req = legal_requirements[0]
                    parts.append(
                        f"Because your {pii_str} was exposed, {law_name} Section {section} grants you a right: \"{req}\" "
                        f"You can invoke this right immediately to demand remedial action, disclosure, or erasure from the responsible organization."
                    )
                else:
                    parts.append(
                        f"Your exposure of {pii_str} triggers a direct legal right under {law_name} Section {section}: {clause_title}. "
                        f"You can exercise this right immediately."
                    )
            
            # Procedural/security provisions: grounded in actual legal text
            elif is_security or is_procedure:
                if legal_requirements:
                    req = legal_requirements[0]
                    parts.append(
                        f"{law_name} Section {section} requires: \"{req}\" "
                        f"The fact that your {pii_str} were exposed shows this requirement was not met, "
                        f"creating both remedial obligations and legal liability for the responsible organization."
                    )
                else:
                    parts.append(
                        f"{law_name} Section {section} requires: \"{clause_title.lower()}.\" "
                        f"The exposure of your {pii_str} demonstrates this requirement was not implemented."
                    )
            
            else:
                if legal_requirements:
                    req = legal_requirements[0]
                    parts.append(
                        f"{law_name} Section {section} specifies: \"{req}\" "
                        f"Your {pii_str} fall directly within this provision's scope based on your incident."
                    )
                else:
                    parts.append(
                        f"The exposure of your {pii_str} falls within {law_name} Section {section}: {clause_title}."
                    )
        
        elif clause_title and legal_requirements:
            # No matched PII, but strong legal requirement
            req = legal_requirements[0]
            if is_criminal:
                parts.append(
                    f"{law_name} Section {section} defines a criminal offence: \"{req}\" "
                    f"This applies to the unauthorized conduct in your {scenario_key.lower().replace('_', ' ')} incident."
                )
            elif is_right:
                parts.append(
                    f"{law_name} Section {section} grants you: \"{req}\" "
                    f"This right is directly applicable to your situation."
                )
            elif is_obligation:
                parts.append(
                    f"{law_name} Section {section} imposes the requirement: \"{req}\" "
                    f"The incident demonstrates a breach of this legal obligation."
                )
            else:
                parts.append(
                    f"{law_name} Section {section} establishes: \"{req}\" "
                    f"This applies directly to your incident."
                )
        
        elif clause_title:
            parts.append(
                f"{law_name} Section {section} addresses: {clause_title}. "
                f"This provision applies specifically to your {scenario_key.lower().replace('_', ' ')} incident type."
            )

        # ──────────────────────────────────────────────────────────────────────
        # PART B: Scenario-specific integration (keep existing, concise)
        # ──────────────────────────────────────────────────────────────────────
        scenario_context_map = {
            "IDENTITY_IMPERSONATION": (
                "In your impersonation scenario, this provision creates criminal and civil liability for the perpetrator."
            ),
            "IMAGE_ABUSE": (
                "In your image abuse scenario, this provision protects your right to privacy and dignity in personal content."
            ),
            "ACCOUNT_MISUSE": (
                "In your account misuse scenario, this provision applies to unauthorized access and system compromise."
            ),
            "DATABASE_BREACH": (
                "In a data breach scenario like yours, this provision creates direct accountability for the data controller."
            ),
            "UNAUTHORIZED_DATA_PROCESSING": (
                "In your unauthorized processing scenario, this provision enforces your right to control how your data is used."
            ),
            "DATA_EXPOSURE": (
                "In your data exposure scenario, this provision protects against unauthorized disclosure and access."
            ),
            "DOXXING": (
                "In your doxxing scenario, this provision protects against weaponized personal information disclosure."
            ),
            "HARASSMENT": (
                "In your harassment scenario, this provision protects your safety and dignity from online abuse."
            ),
            "IDENTITY_THEFT": (
                "In your identity theft scenario, this provision addresses fraudulent misuse of stolen personal identity."
            ),
            "ACCOUNT_TAKEOVER": (
                "In your account takeover scenario, this provision applies to unauthorized account access and operation."
            ),
        }
        
        scenario_context = scenario_context_map.get(scenario_key, "")
        if scenario_context and len(parts) <= 2:
            parts.append(scenario_context)

        # ──────────────────────────────────────────────────────────────────────
        # Safety net
        # ──────────────────────────────────────────────────────────────────────
        if not parts:
            if impersonate:
                parts.append(
                    f"{law_name} Section {section} directly applies to identity impersonation and fraudulent use of personal identity."
                )
            elif img_exposed:
                parts.append(
                    f"{law_name} Section {section} protects against non-consensual sharing and misuse of personal images."
                )
            else:
                parts.append(
                    f"{law_name} Section {section} applies to the unauthorized access, processing, or disclosure of personal data in your incident."
                )

        return " ".join(parts)
