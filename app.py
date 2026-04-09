"""
Privacy Advisor — Sri Lanka
============================
Streamlit application using the 16-module pipeline architecture.

Module 1  (User Input):  This file — collects inputs via Streamlit UI
Module 11 (Output):      This file — renders results via Streamlit UI
"""

import html
import json
import os
import streamlit as st
import streamlit.components.v1 as components
from modules.pipeline import Pipeline
from modules.relevance_matrix import get_clauses_for_tag, get_tags_for_clause



def _load_config() -> dict:
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "config", "config.json"))
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


APP_CONFIG = _load_config()

st.set_page_config(
    page_title="Privacy Advisor - Sri Lanka",
    page_icon="\U0001f6e1\ufe0f",
    layout="centered",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def init_pipeline():
    """Initialize pipeline with progress indicator for user visibility."""
    with st.spinner("🔄 Loading Privacy Advisor models and data..."):
        return Pipeline()


pipeline = init_pipeline()

# ---- Global styles ----
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #111827 !important;
        color: #e5e7eb;
    }
    .block-container {
        max-width: 640px;
        padding-top: 2rem;
        background-color: #111827;
    }
    .card {
        background-color: #1f2937;
        border-radius: 10px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1.2rem;
        border: 1px solid #374151;
    }
    .risk-banner {
        background: linear-gradient(135deg, #1e3a5f 0%, #3b1f6e 100%);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 1.5rem;
        border: 1px solid #4b5563;
    }
    .section-title {
        font-size: 15px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #9ca3af;
        margin-bottom: 0.8rem;
    }
    .clause-header {
        font-weight: 700;
        color: #93c5fd;
        font-size: 18px;
    }
    .clause-title {
        color: #d1d5db;
        font-size: 16px;
        margin-top: 2px;
        margin-bottom: 8px;
    }
    .penalty-box {
        background-color: #2d1515;
        border-left: 3px solid #ef4444;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 16px;
        color: #fca5a5;
        margin-top: 8px;
    }
    .expl-card {
        background-color: #1f2937;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        border: 1px solid #374151;
        border-left: 4px solid #6366f1;
    }
    .expl-law { font-weight: 700; color: #a5b4fc; font-size: 18px; }
    .expl-body { color: #d1d5db; font-size: 16px; margin-top: 8px; line-height: 1.65; }
    .expl-struct-row {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 12px;
        border-radius: 6px;
    }
    .expl-struct-label {
        font-size: 14px;
        font-weight: 700;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: .08em;
        margin-bottom: 6px;
    }
    .expl-struct-icon {
        font-size: 18px;
        margin-top: 1px;
        flex-shrink: 0;
    }
    .expl-pill {
        display: inline-block;
        background: #1e3a5f;
        color: #93c5fd;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 14px;
        margin: 3px 4px 3px 0;
        border: 1px solid #2d4a7a;
        font-weight: 500;
    }
    .metric-row { display: flex; gap: 1rem; margin-bottom: 1.2rem; }
    .metric-box {
        flex: 1;
        background: #1f2937;
        border-radius: 8px;
        padding: 0.8rem;
        text-align: center;
        border: 1px solid #374151;
    }
    .metric-val { font-size: 32px; font-weight: 700; color: #93c5fd; }
    .metric-label { font-size: 14px; color: #9ca3af; margin-top: 4px; }
    .stButton button {
        background-color: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-size: 17px !important;
        font-weight: 600 !important;
    }
    .stButton button:hover { background-color: #2563eb !important; }
    .stCheckbox label { color: #d1d5db !important; font-size: 16px; }
    .stTextInput input {
        background-color: #1f2937 !important;
        color: #e5e7eb !important;
        border: 1px solid #374151 !important;
        border-radius: 6px !important;
    }
    .tag { display:inline-block; background:#1e3a5f; color:#93c5fd; padding:2px 8px; border-radius:4px; font-size:14px; margin:2px; }
    hr { border-color: #374151 !important; }
    [data-testid="stExpander"] { background-color: #1f2937; border: 1px solid #374151; border-radius: 8px; }
    [data-testid="stExpander"] summary { color: #d1d5db !important; }
    [data-testid="stAppDeployButton"] { display: none !important; }
    p, span, div, label { color: #e5e7eb; }
</style>
""", unsafe_allow_html=True)

_TAG_LABELS = APP_CONFIG.get("tag_labels", {})
_SCENARIO_TITLES = {s["key"]: s["title"] for s in APP_CONFIG.get("scenario_definitions", [])}
_SCENARIO_DESCRIPTIONS = {s["key"]: s["description"] for s in APP_CONFIG.get("scenario_definitions", [])}



# ---- Law code → full name mapping ----
_LAW_FULL_NAMES = {
    "PDPA": "Personal Data Protection Act, No. 9 of 2022",
    "OSA":  "Online Safety Act, No. 9 of 2024",
    "CCA":  "Computer Crime Act, No. 24 of 2007",
    "TCA":  "Telecommunications Act No. 25 of 1991",
    "ETA":  "Electronic Transactions Act No. 19 of 2006",
    "RTI":  "Right to Information Act, No. 12 of 2016",
}

def _full_law(code: str, fallback: str = "") -> str:
    """Return full law name for a code, falling back to law_name field or code."""
    return _LAW_FULL_NAMES.get(code, fallback or code)

# ---- Item 5: Impact type badge colours ----
_IMPACT_BADGE_STYLES = {
    "Criminal Offence":        ("background:#3b0f0f;color:#fca5a5;border:1px solid #7f1d1d;",   "⚖️"),
    "Criminal & Regulatory":   ("background:#3b2208;color:#fcd34d;border:1px solid #92400e;",   "⚖️"),
    "Civil & Administrative":  ("background:#0f2b3b;color:#7dd3fc;border:1px solid #1e4a6e;",   "📋"),
    "Administrative":          ("background:#0f1f3b;color:#93c5fd;border:1px solid #1e3a5f;",   "📋"),
}

# =============================================================================
# Module 1 — User Input Page
# =============================================================================

def page_input():
    st.markdown(
        "<div style='text-align:center;color:#93c5fd;font-size:28px;font-weight:700;margin-bottom:4px;'>"
        "\U0001f6e1\ufe0f Privacy Advisor</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#9ca3af;font-size:15px;margin-bottom:2rem;'>"
        "Sri Lanka — Data Exposure Risk & Legal Guidance</p>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='card'><div class='section-title'>What personal data has been exposed?</div></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        name        = st.checkbox("\U0001f4dd Full Name")
        addr        = st.checkbox("\U0001f4cd Address")
        impersonate = st.checkbox("\u26a0\ufe0f Impersonation")
    with c2:
        nid         = st.checkbox("\U0001f194 ID / NIC")
        dob         = st.checkbox("\U0001f4c5 Birth Date")
        img_exposed = st.checkbox("\U0001f4f8 Image Exposed")
    with c3:
        phone       = st.checkbox("\U0001f4f1 Phone")
        username    = st.checkbox("\U0001f464 Username")
    with c4:
        email       = st.checkbox("\u2709\ufe0f Email")
        location    = st.checkbox("\U0001f5fa\ufe0f Location")

    platform_text = ""
    if img_exposed:
        platform_text = st.text_input(
            "", placeholder="\U0001f310 Which platform? (e.g. Facebook, Telegram)",
            label_visibility="collapsed",
        )

    tags_map = {"name": name, "id": nid, "phone": phone, "email": email,
                "addr": addr, "dob": dob, "username": username, "location": location,
                "impersonate": impersonate, "img_exposed": img_exposed}
    selected_tags = [k for k, v in tags_map.items() if v]

    if st.button("\U0001f50d Analyze My Risk", use_container_width=True, type="primary"):
        st.session_state.selected_tags   = selected_tags
        st.session_state.platform_text   = platform_text
        st.session_state.page            = "results"
        st.query_params["page"]          = "results"
        st.rerun()


# =============================================================================
# Module 11 — Output Page
# =============================================================================

def page_results():
    selected_tags  = st.session_state.get("selected_tags", [])
    platform_text  = st.session_state.get("platform_text", "")

    # Derive indicator booleans from the unified tag list
    impersonate   = "impersonate" in selected_tags
    img_exposed   = "img_exposed" in selected_tags

    # ---- Run the full pipeline ----
    result = pipeline.run(
        tags=selected_tags,
        impersonate=impersonate,
        img_exposed=img_exposed,
        platform=platform_text,
        description="",
    )

    if not result["valid"]:
        # No tags selected — show general safety guidance only
        st.markdown(
            "<div style='background:#064e3b;border:1px solid #059669;border-radius:10px;"
            "padding:20px 24px;text-align:center;margin-bottom:1.5rem;'>"
            "<div style='font-size:28px;margin-bottom:6px;'>✅</div>"
            "<div style='color:#6ee7b7;font-size:18px;font-weight:600;'>No personal data violations found</div>"
            "<div style='color:#a7f3d0;font-size:14px;margin-top:8px;'>"
            "No exposed data was reported. Here are some general safety tips to stay protected.</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='color:#93c5fd;font-size:18px;font-weight:600;margin-top:1.5rem;margin-bottom:0.8rem;'>"
            "\U0001f4cb General Safety Recommendations</div>",
            unsafe_allow_html=True,
        )
        _general_tips = [
            ("Monitor your accounts", "Regularly check bank statements, email logins, and social media activity for anything unusual."),
            ("Enable two-factor authentication", "Add 2FA to all important accounts — email, banking, and social media."),
            ("Use strong, unique passwords", "Use a password manager and avoid reusing passwords across services."),
            ("Be cautious with personal information", "Limit what you share on social media and verify requests before providing data."),
            ("Know your rights", "Sri Lanka's Personal Data Protection Act (PDPA) gives you the right to access, correct, and delete your personal data."),
            ("Report incidents", "If your data has been misused, file a complaint with the Data Protection Authority or Sri Lanka CERT."),
        ]
        for title, body in _general_tips:
            st.markdown(
                f"<div style='background:#1e293b;border-radius:8px;padding:12px 16px;"
                f"margin-bottom:8px;border-left:3px solid #3b82f6;'>"
                f"<div style='color:#e2e8f0;font-size:14px;font-weight:600;'>{title}</div>"
                f"<div style='color:#94a3b8;font-size:13px;margin-top:4px;'>{body}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        return

    severity            = result["severity"]
    scenario            = result["scenario"]
    scenario_key        = result["scenario_key"]
    clauses             = result["matched_clauses"]
    warnings            = result["warnings"]
    detected_scenarios  = result.get("detected_scenarios", [])
    incident_class      = result.get("incident_classification", {})
    pii_risk            = result.get("pii_risk", {})
    supporting_clauses  = result.get("supporting_clauses", [])
    related_clauses     = result.get("related_clauses", [])

    scenario_title = _SCENARIO_TITLES.get(scenario_key, "General Exposure")
    scenario_desc  = _SCENARIO_DESCRIPTIONS.get(scenario_key, scenario.get("scenario_description", ""))

    # ---- Risk Banner ----
    st.markdown(
        "<div style='text-align:center;color:#93c5fd;font-size:26px;font-weight:700;margin-bottom:4px;'>"
        "\U0001f6e1\ufe0f Risk Report</div>",
        unsafe_allow_html=True,
    )

    lvl_color = severity.get("color", "#9ca3af")
    st.markdown(f"""
    <div class='risk-banner'>
        <div style='font-size:14px;color:#9ca3af;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;'>Privacy Risk Score</div>
        <div style='font-size:56px;font-weight:800;color:{lvl_color};line-height:1;'>{severity['score']}</div>
        <div style='font-size:20px;font-weight:600;color:{lvl_color};margin-top:4px;'>{severity['level'].upper()}</div>
        <div style='margin-top:12px;font-size:14px;color:#9ca3af;'>{scenario_desc}</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Compliance Alert Card ----
    compliance_alert = result.get("compliance_alert", {})
    if compliance_alert and compliance_alert.get("risk_level", "NO_RISK") != "NO_RISK":
        _risk_colors = {"HIGH_RISK": "#ef4444", "MEDIUM_RISK": "#f97316", "LOW_RISK": "#22c55e"}
        ca_color = _risk_colors.get(compliance_alert.get("risk_level", "LOW_RISK"), "#6b7280")
        ca_summ  = compliance_alert.get("explainability_summary", "")
        st.markdown(f"""
        <div class='card' style='border-left:4px solid {ca_color};background:#191929;'>
            <div style='font-size:14px;font-weight:700;color:{ca_color};letter-spacing:0.05em;margin-bottom:8px;'>\U0001f6a8 COMPLIANCE ALERT</div>
            <div style='font-size:14px;color:#d1d5db;line-height:1.5;'>{ca_summ}</div>
        </div>
        """, unsafe_allow_html=True)

    # ---- Metrics row ----
    n_scenarios = len(detected_scenarios) if detected_scenarios else 1

    # ---- Incident Classification Badge ----
    if incident_class:
        inc_type = incident_class.get("incident_type", "UNKNOWN").replace("_", " ")
        inc_conf = incident_class.get("incident_confidence", 0.0)
        inc_pct = int(inc_conf * 100)
        inc_color = "#22c55e" if inc_conf >= 0.7 else "#eab308" if inc_conf >= 0.4 else "#6b7280"
        st.markdown(f"""
        <div class='card' style='border-left:4px solid {inc_color};padding:0.8rem 1.2rem;display:flex;align-items:center;gap:1rem;'>
            <div>
                <div style='font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.06em;'>Incident Type</div>
                <div style='font-size:16px;font-weight:700;color:#93c5fd;margin-top:2px;'>🎯 {inc_type}</div>
            </div>
            <div style='margin-left:auto;text-align:right;'>
                <div style='font-size:22px;font-weight:700;color:{inc_color};'>{inc_pct}%</div>
                <div style='font-size:10px;color:#6b7280;'>Confidence</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ---- PII Risk Summary ----
    if pii_risk and pii_risk.get("aggregate_score", 0) > 0:
        pr_score = pii_risk.get("aggregate_score", 0.0)
        pr_level = pii_risk.get("risk_level", "Low")
        pr_color = "#ef4444" if pr_level == "Critical" else "#f97316" if pr_level == "High" else "#eab308" if pr_level == "Medium" else "#22c55e"
        pr_top = pii_risk.get("top_risk_factors", [])
        top_pills = "".join(
            f"<span style='display:inline-block;background:#1e2a3a;color:#93c5fd;padding:3px 8px;border-radius:4px;font-size:12px;margin:2px;'>"
            f"{f.get('tag', '')} ({f.get('score', 0):.2f})</span>"
            for f in pr_top[:5]
        )
        st.markdown(f"""
        <div class='card' style='border-left:4px solid {pr_color};padding:0.8rem 1.2rem;'>
            <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;'>
                <div style='font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.06em;'>PII Risk Assessment</div>
                <div style='font-size:13px;font-weight:700;color:{pr_color};'>{pr_level.upper()} — {pr_score:.2f}</div>
            </div>
            <div>{top_pills}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class='metric-row'>
        <div class='metric-box'><div class='metric-val'>{len(selected_tags)}</div><div class='metric-label'>Data Types Exposed</div></div>
        <div class='metric-box'><div class='metric-val'>{n_scenarios}</div><div class='metric-label'>Scenarios Detected</div></div>
        <div class='metric-box'><div class='metric-val'>{len(clauses)}</div><div class='metric-label'>Laws Triggered</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Exposed data pills ----
    tag_pills = "".join(
        f"<span class='tag'>{_TAG_LABELS.get(t, t)}</span>"
        for t in selected_tags if t not in ("impersonate", "img_exposed")
    )
    flag_pills = ""
    if impersonate:
        flag_pills += "<span style='display:inline-block;background:#3b1515;color:#fca5a5;padding:3px 10px;border-radius:4px;font-size:13px;margin:2px;'>\u26a0\ufe0f Impersonation</span>"
    if img_exposed:
        plat = f" ({html.escape(platform_text)})" if platform_text else ""
        flag_pills += f"<span style='display:inline-block;background:#2d2315;color:#fde68a;padding:3px 10px;border-radius:4px;font-size:13px;margin:2px;'>\U0001f4f8 Image{plat}</span>"
    if tag_pills or flag_pills:
        st.markdown(f"""
        <div style='background:#1f2937;padding:0.8rem 1rem;border-radius:8px;margin-bottom:1rem;border:1px solid #374151;'>
            <div style='font-size:12px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;'>Exposed Data Inputs</div>
            <div>{tag_pills}{flag_pills}</div>
        </div>
        """, unsafe_allow_html=True)

    # ---- Warnings ----
    if warnings:
        for w in warnings:
            st.warning(w)

    st.divider()

    # ---- Scenario Summary ----
    st.markdown(
        "<div class='section-title' style='color:#93c5fd;font-size:14px;margin-bottom:1rem;'>"
        "\U0001f50e Detected Scenarios</div>",
        unsafe_allow_html=True,
    )

    if detected_scenarios:
        for ds in detected_scenarios:
            ds_key = ds["key"]
            ds_conf = ds.get("confidence", 0.0)
            ds_title = _SCENARIO_TITLES.get(ds_key, ds_key.replace("_", " ").title())
            ds_desc = _SCENARIO_DESCRIPTIONS.get(ds_key, "")
            # Confidence color
            conf_color = "#22c55e" if ds_conf >= 0.7 else "#eab308" if ds_conf >= 0.4 else "#6b7280"
            conf_pct = int(ds_conf * 100)
            is_primary = (ds_key == scenario_key)
            primary_badge = (
                "<span style='display:inline-block;background:#1e3a5f;color:#60a5fa;"
                "padding:1px 7px;border-radius:3px;font-size:10px;font-weight:600;"
                "margin-left:8px;'>PRIMARY</span>"
            ) if is_primary else ""
            st.markdown(f"""
            <div class='expl-card' style='border-left-color:{conf_color};'>
                <div style='display:flex;align-items:center;justify-content:space-between;'>
                    <div class='expl-law'>{ds_title}{primary_badge}</div>
                    <div style='font-size:13px;font-weight:600;color:{conf_color};'>{conf_pct}% confidence</div>
                </div>
                <div class='expl-body'>{ds_desc}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class='expl-card'>
            <div class='expl-law'>{scenario_title}</div>
            <div class='expl-body'>{scenario.get('scenario_description', '')}</div>
        </div>
        """, unsafe_allow_html=True)

    # ---- Severity Contributors ----
    if severity["contributors"]:
        with st.expander("\U0001f4ca What drove the severity score?"):
            for c in severity["contributors"][:8]:
                st.markdown(f"<div style='color:#d1d5db;font-size:14px;padding:2px 0;'>\u2022 {c['factor']} (+{c['weight']})</div>", unsafe_allow_html=True)

    st.divider()

    # =====================================================================
    # TABBED SECTIONS
    # =====================================================================
    recommendations = result.get("recommendations", [])
    _all_input_tags  = selected_tags

    tab_clauses, tab_explanations, tab_recs, tab_related = st.tabs([
        f"⚖️ Legal Clauses ({len(clauses)})",
        "🧠 Why It Applies",
        f"📋 Recommendations ({len(recommendations)})",
        f"🔗 Supporting ({len(supporting_clauses) + len(related_clauses)})",
    ])

    # ------------------------------------------------------------------
    # TAB 1 — Legal Clauses
    # ------------------------------------------------------------------
    with tab_clauses:
        if clauses:
            primary_count   = sum(1 for c in clauses if c.get("relevance_tier") == "PRIMARY")
            secondary_count = len(clauses) - primary_count
            st.markdown(
                f"<div style='font-size:13px;color:#9ca3af;margin-bottom:0.8rem;'>"
                f"{primary_count} directly applicable &middot; {secondary_count} supporting</div>",
                unsafe_allow_html=True,
            )

            for i, clause in enumerate(clauses, 1):
                law_code   = clause.get("law_code", "")
                section    = clause.get("section", "")
                title      = clause.get("title", "")
                law_name   = clause.get("law_name", "")
                full_text  = clause.get("full_text", "")
                descr      = clause.get("description", "")
                penalty    = clause.get("penalty", "")
                ref_url    = clause.get("reference_url", "")
                rel_score  = clause.get("relevance_score", 0.0)
                tier       = clause.get("relevance_tier", "SECONDARY")
                confidence = clause.get("confidence", 0.0)

                bar_color  = "#22c55e" if rel_score  >= 0.55 else "#eab308" if rel_score  >= 0.35 else "#6b7280"
                bar_width  = max(5, min(100, int(rel_score  * 100)))
                conf_color = "#22c55e" if confidence >= 0.7  else "#eab308" if confidence >= 0.4  else "#6b7280"
                conf_width = max(5, min(100, int(confidence * 100)))

                # Applicability badge from legal reasoning validation
                applicability = clause.get("applicability", "")
                appl_colors = {"Direct": "#22c55e", "Partial": "#eab308", "Weak": "#6b7280"}
                appl_color = appl_colors.get(applicability, "#6b7280")
                appl_badge = ""
                if applicability:
                    appl_badge = (
                        f"<span style='display:inline-block;background:#111827;color:{appl_color};"
                        f"padding:1px 7px;border-radius:3px;font-size:10px;font-weight:600;"
                        f"letter-spacing:0.04em;margin-left:6px;border:1px solid {appl_color};'>"
                        f"{applicability.upper()}</span>"
                    )

                if tier == "PRIMARY":
                    tier_badge = "<span style='display:inline-block;background:#1e3a5f;color:#60a5fa;padding:1px 7px;border-radius:3px;font-size:10px;font-weight:600;letter-spacing:0.04em;margin-left:8px;'>PRIMARY</span>"
                else:
                    tier_badge = "<span style='display:inline-block;background:#1f2937;color:#6b7280;padding:1px 7px;border-radius:3px;font-size:10px;font-weight:600;letter-spacing:0.04em;margin-left:8px;border:1px solid #374151;'>SUPPORTING</span>"

                protecting_tags = get_tags_for_clause(law_code, section, selected_tags)
                tag_pills_html = ""
                if protecting_tags:
                    pills = "".join(
                        f"<span style='display:inline-block;background:#1a2e1a;color:#86efac;padding:1px 6px;border-radius:3px;font-size:10px;margin:1px 2px;'>{_TAG_LABELS.get(t, t)}</span>"
                        for t in protecting_tags
                    )
                    tag_pills_html = f"<div style='margin-top:6px;'>{pills}</div>"

                st.markdown(f"""
                <div class='card' style='border-left:3px solid {bar_color};'>
                    <div class='clause-header'>{i}. {_full_law(law_code, law_name)} — Section {section}{tier_badge}{appl_badge}</div>
                    <div class='clause-title'>{title}</div>{tag_pills_html}
                    <div style='margin-top:8px;display:flex;gap:1rem;'>
                        <div style='flex:1;'>
                            <div style='background:#374151;border-radius:4px;height:5px;overflow:hidden;'>
                                <div style='width:{bar_width}%;height:100%;background:{bar_color};border-radius:4px;'></div>
                            </div>
                            <div style='font-size:12px;color:#9ca3af;margin-top:3px;'>Relevance: {rel_score:.3f}</div>
                        </div>
                        <div style='flex:1;'>
                            <div style='background:#374151;border-radius:4px;height:5px;overflow:hidden;'>
                                <div style='width:{conf_width}%;height:100%;background:{conf_color};border-radius:4px;'></div>
                            </div>
                            <div style='font-size:12px;color:#9ca3af;margin-top:3px;'>Confidence: {confidence:.3f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                clause_text_display = full_text.strip() if full_text and len(full_text.strip()) > 40 else descr
                with st.expander("\U0001f4c4 Relevant Clause"):
                    st.markdown(
                        f"<div style='color:#d1d5db;font-size:14px;line-height:1.7;'>{clause_text_display}</div>",
                        unsafe_allow_html=True,
                    )
                    if ref_url:
                        st.markdown(f"[\U0001f517 View Full Act]({ref_url})")

                if penalty:
                    st.markdown(
                        f"<div class='penalty-box'>\u26a0\ufe0f <b>Penalty:</b> {penalty}</div>",
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        else:
            st.success("\u2705 No specific legal clauses were triggered by your inputs.")

    # ------------------------------------------------------------------
    # TAB 2 — Why It Applies (Explanations)
    # ------------------------------------------------------------------
    with tab_explanations:
        has_expl = any(c.get("explanation_text") for c in clauses)
        if clauses and has_expl:
            for clause in clauses:
                expl = clause.get("explanation_text", {})
                if not expl:
                    continue

                impact_type    = expl.get("impact_type", "")
                badge_style, badge_icon = _IMPACT_BADGE_STYLES.get(
                    impact_type, ("background:#1f2937;color:#9ca3af;border:1px solid #374151;", "\U0001f4c4")
                )
                impact_badge_html = (
                    f"<span style='display:inline-block;{badge_style}padding:3px 10px;"
                    f"border-radius:4px;font-size:12px;font-weight:600;margin-top:6px;'>"
                    f"{badge_icon} {impact_type}</span>"
                    if impact_type else ""
                )

                existing_expl_html = ""
                _existing = expl.get('existing_explanation', '')
                if _existing:
                    existing_expl_html = (
                        f"<div style='font-size:13px;color:#9ca3af;margin-top:8px;"
                        f"padding:10px 12px;background:#111827;border-radius:6px;"
                        f"font-style:italic;line-height:1.6;border-left:2px solid #4b5563;'>"
                        f"{_existing}</div>"
                    )

                st.markdown(f"""
                <div class='expl-card'>
                    <div style='display:flex;align-items:center;justify-content:space-between;'>
                        <div class='expl-law'>{expl.get('law_label', '')}</div>
                        {impact_badge_html}
                    </div>
                    <div style='color:#93c5fd;font-size:14px;margin-top:2px;'>{expl.get('title', '')}</div>
                    <div class='expl-body'>{expl.get('why_relevant', '')}</div>
                    {existing_expl_html}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No detailed explanations available for the matched clauses.")

    # ------------------------------------------------------------------
    # TAB 3 — Recommendations
    # ------------------------------------------------------------------
    with tab_recs:
        if recommendations:
            _PRIORITY_COLORS = {
                "URGENT": "#ef4444",
                "HIGH":   "#f97316",
                "MEDIUM": "#eab308",
                "LOW":    "#22c55e",
            }
            _PRIORITY_ICONS = {
                "URGENT": "\U0001f534",
                "HIGH":   "\U0001f7e0",
                "MEDIUM": "\U0001f7e1",
                "LOW":    "\U0001f7e2",
            }

            cat_order: list = []
            cat_map:  dict  = {}
            for rec in recommendations:
                cat = rec["category"]
                if cat not in cat_map:
                    cat_order.append(cat)
                    cat_map[cat] = []
                cat_map[cat].append(rec)

            for cat in cat_order:
                recs = cat_map[cat]
                st.markdown(
                    f"<div style='font-size:14px;font-weight:600;color:#93c5fd;"
                    f"margin-top:1rem;margin-bottom:0.6rem;'>{cat}</div>",
                    unsafe_allow_html=True,
                )
                for rec in recs:
                    p_color      = _PRIORITY_COLORS.get(rec["priority"], "#6b7280")
                    p_icon       = _PRIORITY_ICONS.get(rec["priority"], "\u2022")
                    explanation  = rec.get("explanation", "")
                    contributions = rec.get("feature_contributions", [])
                    linked_clauses = rec.get("linked_clauses", [])

                    linked_html = ""
                    if linked_clauses:
                        pill_parts = []
                        for lc in linked_clauses:
                            lc_label = _full_law(lc.get('law_code', ''), lc.get('law_name', '')) + ' — Section ' + lc.get('section', '')
                            lc_title = lc.get("title", "")
                            pill_parts.append(
                                f"<span style='display:inline-block;background:#1e3a5f;"
                                f"color:#93c5fd;padding:2px 8px;border-radius:3px;font-size:12px;"
                                f"margin:1px 3px 1px 0;border:1px solid #2d4a7a;' "
                                f"title='{lc_title}'>{lc_label}</span>"
                            )
                        linked_html = (
                            f"<div style='margin-top:8px;padding-top:8px;border-top:1px solid #374151;'>"
                            f"<span style='font-size:10px;color:#6b7280;text-transform:uppercase;"
                            f"letter-spacing:0.05em;'>Legal basis: </span>"
                            f"{''.join(pill_parts)}</div>"
                        )

                    st.markdown(f"""
                    <div class='card' style='border-left:3px solid {p_color};padding:1rem 1.2rem;'>
                        <div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>
                            <span>{p_icon}</span>
                            <span style='font-size:12px;font-weight:700;color:{p_color};letter-spacing:0.05em;'>{rec['priority']}</span>
                        </div>
                        <div style='color:#e5e7eb;font-size:14px;line-height:1.6;'>{rec['action']}</div>
                        {linked_html}
                    </div>
                    """, unsafe_allow_html=True)

                    if explanation or contributions:
                        with st.expander("\U0001f9e0 Why this recommendation?"):
                            if explanation:
                                st.markdown(
                                    f"<div style='color:#d1d5db;font-size:14px;line-height:1.6;margin-bottom:8px;'>{explanation}</div>",
                                    unsafe_allow_html=True,
                                )
                            if contributions:
                                st.markdown(
                                    "<div style='font-size:13px;color:#9ca3af;margin-bottom:6px;font-weight:600;'>Contributing factors:</div>",
                                    unsafe_allow_html=True,
                                )
                                for contrib in contributions:
                                    bar_w = max(5, int(contrib["weight"] * 100))
                                    st.markdown(
                                        f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0;'>"
                                        f"<div style='flex:1;font-size:13px;color:#d1d5db;'>{contrib['label']}</div>"
                                        f"<div style='width:80px;background:#374151;border-radius:3px;height:4px;overflow:hidden;'>"
                                        f"<div style='width:{bar_w}%;height:100%;background:#6366f1;border-radius:3px;'></div></div>"
                                        f"<div style='font-size:12px;color:#9ca3af;width:30px;text-align:right;'>{contrib['weight']:.2f}</div>"
                                        f"</div>",
                                        unsafe_allow_html=True,
                                    )
                            if linked_clauses:
                                st.markdown(
                                    "<div style='font-size:13px;color:#9ca3af;margin-top:8px;margin-bottom:6px;font-weight:600;'>Triggered by these clauses:</div>",
                                    unsafe_allow_html=True,
                                )
                                for lc in linked_clauses:
                                    lc_law_label = _full_law(lc.get('law_code', ''), lc.get('law_name', '')) + ' — Section ' + lc.get('section', '')
                                    st.markdown(
                                        f"<div style='font-size:14px;color:#d1d5db;padding:4px 0;'>"
                                        f"<span style='color:#93c5fd;font-weight:600;'>{lc_law_label}</span>"
                                        f" — {lc.get('title', '')}</div>",
                                        unsafe_allow_html=True,
                                    )
        else:
            st.info("No recommendations generated for this input.")

    # ------------------------------------------------------------------
    # TAB 4 — Supporting & Related Clauses
    # ------------------------------------------------------------------
    with tab_related:
        if supporting_clauses:
            st.markdown(
                "<div class='section-title' style='color:#93c5fd;'>🏛️ Supporting Clauses</div>"
                "<div style='font-size:12px;color:#6b7280;margin-bottom:0.8rem;'>"
                "These clauses reinforce the primary legal provisions identified above.</div>",
                unsafe_allow_html=True,
            )
            for sc in supporting_clauses:
                sc_code = sc.get("law_code", "")
                sc_sect = sc.get("section", "")
                sc_title = sc.get("title", "")
                sc_rel = sc.get("relationship", "supports")
                rel_badge_color = "#22c55e" if sc_rel == "supports" else "#60a5fa"
                st.markdown(f"""
                <div class='card' style='border-left:3px solid {rel_badge_color};padding:0.8rem 1rem;'>
                    <div style='display:flex;align-items:center;justify-content:space-between;'>
                        <div style='font-weight:600;color:#93c5fd;font-size:14px;'>{_full_law(sc_code, sc.get('law_name', ''))} — Section {sc_sect}</div>
                        <span style='display:inline-block;background:#111827;color:{rel_badge_color};padding:1px 7px;
                        border-radius:3px;font-size:10px;font-weight:600;border:1px solid {rel_badge_color};'>{sc_rel.upper()}</span>
                    </div>
                    <div style='font-size:13px;color:#d1d5db;margin-top:4px;'>{sc_title}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No supporting clauses identified for this analysis.")

        if related_clauses:
            st.markdown(
                "<div class='section-title' style='color:#93c5fd;margin-top:1rem;'>🔗 Related Clauses</div>"
                "<div style='font-size:12px;color:#6b7280;margin-bottom:0.8rem;'>"
                "Cross-reference clauses that may be relevant to your situation.</div>",
                unsafe_allow_html=True,
            )
            for rc in related_clauses:
                rc_code = rc.get("law_code", "")
                rc_sect = rc.get("section", "")
                rc_title = rc.get("title", "")
                rc_rel = rc.get("relationship", "related_to")
                st.markdown(f"""
                <div class='card' style='border-left:3px solid #6b7280;padding:0.8rem 1rem;'>
                    <div style='font-weight:600;color:#93c5fd;font-size:14px;'>{_full_law(rc_code, rc.get('law_name', ''))} — Section {rc_sect}</div>
                    <div style='font-size:13px;color:#d1d5db;margin-top:4px;'>{rc_title}</div>
                </div>
                """, unsafe_allow_html=True)
        elif not supporting_clauses:
            pass  # already showed info message above

    st.divider()

    if st.button("\u2190 Analyze Again", use_container_width=True):
        st.session_state.page = "input"
        st.query_params.clear()
        st.rerun()


# =============================================================================
# Router
# =============================================================================

# Inject popstate listener so browser back/forward triggers a page reload
components.html("""
<script>
if (!window.parent._popstateListenerAdded) {
    window.parent._popstateListenerAdded = true;
    window.parent.addEventListener('popstate', function() {
        window.parent.location.reload();
    });
}
</script>
""", height=0)

# Sync page state from URL query params — enables browser back button
_url_page = st.query_params.get("page", "input")
if st.session_state.get("page", "input") != _url_page:
    st.session_state.page = _url_page

if st.session_state.get("page") == "results":
    page_results()
else:
    page_input()
