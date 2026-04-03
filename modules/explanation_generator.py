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
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "config.json"))
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

# ── Scenario × Clause Specific Legal Reasoning ──────────────────────────────
# Format: _CLAUSE_REASONING[scenario_key][law_code:section] = "why this clause applies"
# Every PRIMARY clause for every scenario has a tailored rationale.
_CLAUSE_REASONING: Dict[str, Dict[str, str]] = {

    "IDENTITY_IMPERSONATION": {
        "OSA:18(a)": "Section 18(a) of the Online Safety Act directly criminalises using a computer to cheat by impersonating another person online. Creating a fake profile or account using your identity is a textbook violation of this section — it is one of the most directly applicable laws in your situation.",
        "OSA:18(b)": "Section 18(b) covers dishonest use of electronic means for personation. Anyone who deceives others by messaging, posting, or transacting as you through social media or messaging apps falls squarely under this provision.",
        "OSA:18(c)": "Section 18(c) targets impersonation that causes wrongful gain to the perpetrator or wrongful loss to you — for example, defrauding your contacts financially or damaging your reputation by acting as you.",
        "OSA:20(1)": "Section 20(1) criminalises transmitting communications that cause harassment, alarm, or distress. Messages, posts, or calls made under your identity to harm your reputation or harass others directly trigger this section.",
        "CCA:4(a)": "Section 4(a) penalises any act done to secure unauthorized access to a computer — if your accounts or devices were accessed or compromised to facilitate the impersonation, this section applies to that intrusion.",
        "CCA:4(b)": "Section 4(b) specifically covers unauthorized access with intent to commit a further offence. Accessing your data to enable impersonation satisfies both the access and the intent conditions of this provision.",
        "CCA:10": "Section 10 covers unauthorized disclosure of information that enables access to a computer or account. Sharing or leaking your credentials or identity data to enable someone to impersonate you falls directly under this section.",
        "TCA:46B": "Section 46B criminalises using telecommunications to deceive or mislead anyone — phone calls, SMS, or messaging apps used to impersonate you are specifically covered by this provision.",
        "TCA:46C": "Section 46C penalises providing false identity information to obtain a telecom service. If your identity was used to register a phone number or SIM card in your name, this section directly applies.",
        "PDPA:13(1)": "As a victim of impersonation, you have a right under Section 13(1) to demand access to all personal data held by any controller whose data was used to enable the impersonation.",
        "PDPA:10(a)": "The organisation or platform that failed to protect your personal data — allowing it to be used for impersonation — breached its confidentiality obligation under Section 10(a).",
        "CCA:7(a)": "Causing a computer to perform a function without authorization to copy or access your identity data for impersonation purposes is prohibited by Section 7(a).",
        "ETA:12(1)(a)": "Electronic records (messages, transactions) falsely attributed to you through impersonation are addressed by Section 12(1)(a), which governs the proper attribution of electronic records.",
        "ETA:12(2)(a)": "Section 12(2)(a) provides grounds to challenge electronic communications that were falsely attributed to you by an impersonator.",
        "TCA:52(d)": "Section 52(d) covers intrusion into telecommunications systems with intent to cause harm — accessing telecom tools to facilitate impersonation engages this provision.",
    },

    "IMAGE_ABUSE": {
        "OSA:20(1)": "Section 20(1) of the Online Safety Act is the primary provision for image-based abuse — it directly criminalises posting or sharing content (including images) that causes harassment, alarm, distress, or damage to reputation. This is the most applicable law to your situation.",
        "OSA:18(a)": "If your image was used to create a fake profile or avatar to impersonate you, Section 18(a) criminalises that act of digital personation using your likeness.",
        "OSA:18(c)": "Section 18(c) applies where your image was used to gain a wrongful advantage — such as defrauding others or damaging your standing — by impersonating you with your own photo.",
        "PDPA:10(a)": "Any platform or individual that held your personal images was obligated to maintain their confidentiality under Section 10(a). The exposure of your images is direct evidence of a failure to meet this legal duty.",
        "PDPA:10(b)": "Section 10(b) obliges all data controllers to prevent loss, destruction, or unauthorized disclosure of personal data including images. Sharing or leaking your photo constitutes a violation of this obligation.",
        "PDPA:7(a)": "Your images may only be used for the explicit purpose for which they were originally shared. Section 7(a) prohibits processing beyond that defined purpose — redistributing your images for any other reason is a direct breach.",
        "PDPA:7(c)": "Processing of your images must be confined strictly to the defined purpose. Any use of your images outside what you consented to violates Section 7(c).",
        "CCA:7(a)": "Causing a computer to perform a function without authorisation to access, copy, or distribute your personal images constitutes an offence under Section 7(a) of the Computer Crime Act.",
        "CCA:7(c)": "Acquiring or possessing your personal images obtained through unauthorized computer access is specifically prohibited by Section 7(c).",
        "PDPA:14(1)": "You have the right under Section 14(1) to withdraw consent for continued processing of your images and object to their further use on any platform.",
        "PDPA:16(a)": "Section 16(a) gives you the explicit right to demand erasure of your images from any data controller or platform that holds them.",
        "PDPA:11(a)": "Any person or platform that shared or distributed your images must have informed you of the purpose at the time of collection. Failure to disclose this violates Section 11(a).",
        "RTI:5(1)(a)": "Privacy protection provisions under Section 5(1)(a) restrict the disclosure of your personal information — including images — without lawful justification.",
        "TCA:49(c)": "Section 49(c) prohibits unauthorized disclosure of communications or content including images transmitted over telecommunications networks.",
    },

    "ACCOUNT_MISUSE": {
        "CCA:3(a)": "Section 3(a) of the Computer Crime Act is the foundational offence for computer misuse — it directly criminalises unauthorized access to any computer system. Accessing your account without permission is a violation of this section.",
        "CCA:3(b)": "Section 3(b) extends the offence to securing unauthorized access to information held in a computer — accessing your account data, messages, or files without your consent is covered here.",
        "CCA:4(a)": "Section 4(a) penalises unauthorized access committed with intent to carry out a further offence such as fraud, identity theft, or harassment. If your account was accessed for any such purpose, this heavier charge applies.",
        "CCA:4(b)": "Section 4(b) specifically targets accessing a computer with intent to commit or facilitate a further offence — the combined act of access plus intent is penalised more severely under this provision.",
        "CCA:5": "Section 5 covers causing a computer to perform unauthorized functions — using your compromised account to send messages, make transfers, or perform any action without your authorization falls under this.",
        "CCA:10": "Section 10 directly addresses the unauthorized disclosure of information (such as your password or credentials) that enables someone else to access your account.",
        "ETA:12(1)(a)": "Electronic records attributed to you — messages, transactions, consents — cannot be used without proper authorization. Unauthorized account use violates the attribution rules in Section 12(1)(a).",
        "ETA:12(1)(b)": "Section 12(1)(b) governs how electronic records are attributed when a party acts with authority — unauthorized account use directly contradicts this by exceeding any authorized scope.",
        "ETA:12(1)(c)": "Section 12(1)(c) covers negligent attribution — if your authentication information (passwords, OTPs) were exposed negligently, this section applies to the resulting unauthorized actions.",
        "ETA:7(a)": "Your electronic signature and digital identity cannot be used without authorization. Misuse of your account to sign or authenticate transactions violates Section 7(a).",
        "ETA:7(b)(ii)": "Section 7(b)(ii) addresses the legal recognition of electronic signatures and authentication — unauthorized use of your account to authenticate actions is invalid under this provision.",
        "PDPA:10(a)": "If the platform holding your account credentials failed to maintain their confidentiality, leading to the account misuse, Section 10(a) establishes their legal liability.",
        "PDPA:10(b)": "Section 10(b) obliges platforms to prevent loss or unauthorized access to your account data — a successful account takeover evidences a breach of this duty.",
        "TCA:46B": "Section 46B covers deception using telecommunications — if your compromised account was used to send deceptive messages via phone or messaging apps, this applies.",
        "TCA:52(a)": "Section 52(a) prohibits unauthorized intrusion into a telecommunication system — accessing messaging or telecom functions through your compromised account triggers this section.",
        "TCA:52(d)": "Section 52(d) covers telecoms intrusion with intent to cause harm — misusing your account to harass or harm your contacts through telecom channels engages this provision.",
        "ETA:12(2)(a)": "Section 12(2)(a) addresses reliance on attributed electronic records — any party who acted on records falsely attributed to your account has a legal remedy under this section.",
        "ETA:12(2)(b)": "Section 12(2)(b) deals with reliance on electronic records authenticated without proper authority — transactions completed through unauthorized account access can be challenged under this provision.",
    },

    "DATABASE_BREACH": {
        "PDPA:6(1)a)": "Section 6(1)(a) requires your data to be collected only for a specified purpose. A breach evidences that inadequate controls were in place over data collected under this obligation.",
        "PDPA:6(1)b)": "Section 6(1)(b) requires an explicit stated purpose for all personal data. If the breached data was held beyond its stated purposes, this constitutes a double violation — breach and purpose overreach.",
        "PDPA:6(1)c)": "Section 6(1)(c) requires a legitimate legal basis for holding your data. A breach forces the controller to demonstrate that holding your data met this test — and often it reveals it did not.",
        "PDPA:7(a)": "Section 7(a) requires that personal data be limited to what is necessary for the defined purpose. Holding your data in a breachable state suggests excess retention beyond what was necessary.",
        "PDPA:7(b)": "Section 7(b) requires proportionality — the amount and sensitivity of data held must be proportionate to the stated need. A large-scale breach often reveals disproportionate data accumulation.",
        "PDPA:7(c)": "Section 7(c) requires that processing be confined to the defined purpose. Exposure of your data to unauthorized parties through a breach goes beyond any authorized processing scope.",
        "PDPA:10(a)": "Section 10(a) is the core security obligation — data controllers must maintain integrity and confidentiality of personal data. A breach is direct and irrefutable evidence of failure to comply with this obligation.",
        "PDPA:10(b)": "Section 10(b) requires active measures to prevent loss, destruction, or unauthorized disclosure. The occurrence of the breach is itself evidence that adequate measures were not in place.",
        "PDPA:12(1)(a)": "Section 12(1)(a) holds data controllers accountable for all processing operations. The breach establishes their accountability — they must demonstrate their compliance programmes failed and explain why.",
        "PDPA:12(1)(f)": "Section 12(1)(f) requires controllers to have processes for detecting and responding to breaches. You can demand proof that such processes existed and were followed.",
        "PDPA:13(1)": "Section 13(1) gives you the right to know exactly which of your personal data was exposed in the breach and to receive a full account from the controller.",
        "CCA:7(a)": "Section 7(a) covers causing a computer to perform a function without authorization to access or copy your data from the breached system — the attacker's actions are a criminal offence.",
        "CCA:7(b)": "Section 7(b) covers offering to deal in unlawfully obtained computer data — if your breached data was sold or traded, this section applies to those transactions.",
        "CCA:7(c)": "Section 7(c) directly covers acquiring or possessing data obtained through unauthorized computer access — any person who received your data from the breach is liable under this.",
        "CCA:3(a)": "Section 3(a) criminalises the initial unauthorized access to the database system. The attacker who accessed the server or database commits this primary offence.",
        "CCA:3(b)": "Section 3(b) extends the offence to unauthorized access to information held in a computer — accessing your personal records within the breached database triggers this provision.",
        "PDPA:11(a)": "Section 11(a) requires the controller to inform you of how your data is used. Following a breach, you have an enhanced right to this information to understand the full scope of exposure.",
        "PDPA:9": "Section 9 requires data to be deleted once it is no longer needed. Breached data that was held beyond its retention period compounds the violation.",
        "PDPA:16(a)": "Section 16(a) gives you the right to demand erasure of your data from all systems — including any copies created during or after the breach.",
        "PDPA:12(1)(b)": "Section 12(1)(b) requires the controller to maintain appropriate governance. A breach reveals governance failures that you can cite in a complaint.",
        "PDPA:12(1)(c)": "Section 12(1)(c) requires internal oversight mechanisms — a breach demonstrates these failed and provides the basis for holding the controller liable.",
        "RTI:5(1)(a)": "Privacy protection provisions under Section 5(1)(a) restrict the disclosure of personal information. The breach constitutes unauthorized disclosure that this section was designed to prevent.",
    },

    "UNAUTHORIZED_DATA_PROCESSING": {
        "PDPA:6(1)a)": "Section 6(1)(a) requires that your data be collected and processed only for a specified purpose. If your data is being used for purposes you never agreed to, this is a foundational violation.",
        "PDPA:6(1)b)": "Section 6(1)(b) requires the purpose to be explicitly stated to you. Processing your data for unstated purposes — including profiling, marketing, or sharing — directly violates this provision.",
        "PDPA:6(1)c)": "Section 6(1)(c) requires a legitimate legal basis for all processing. If there is no valid legal basis for processing your data as described, the entire processing activity is unlawful under this section.",
        "PDPA:7(a)": "Section 7(a) requires that processing be confined strictly to the defined purpose. Any processing activity beyond what you were informed of at collection is a direct violation.",
        "PDPA:7(b)": "Section 7(b) requires proportionality — only the minimum data necessary should be processed. Excessive processing or use of data beyond what is needed violates this obligation.",
        "PDPA:7(c)": "Section 7(c) is the key proportionality provision — processing must be limited to what is strictly necessary. Unauthorized use of your data exceeds this limit.",
        "PDPA:9": "Section 9 requires that your data be deleted once the processing purpose is fulfilled. Retaining your data beyond this point for continuing unauthorized processing violates this section.",
        "PDPA:11(a)": "Section 11(a) obligates the controller to inform you of all processing activities. You were not informed of the processing you are reporting — this omission is itself a violation of this section.",
        "PDPA:11(b)": "Section 11(b) requires proactive communication about processing decisions. The lack of notification about the processing activity violates your right to be informed.",
        "PDPA:14(1)": "Section 14(1) gives you the explicit right to withdraw consent and object to the processing of your data at any time. The controller must cease processing upon receipt of your objection.",
        "PDPA:14(2)": "Section 14(2) provides specific rights to object to automated processing including profiling. If your data is being processed algorithmically without your knowledge, this section directly applies.",
        "PDPA:16(a)": "Section 16(a) gives you the right to demand immediate erasure of your data where there is no longer a lawful basis for its processing.",
        "PDPA:16(b)": "Section 16(b) extends erasure rights to situations where you withdraw consent. If processing was consent-based, your withdrawal of consent triggers an immediate erasure obligation.",
        "RTI:5(1)(a)": "Section 5(1)(a) of the Right to Information Act restricts disclosure or use of personal information held by institutions. Unauthorized processing by government-related bodies may invoke this additional protection.",
        "PDPA:12(1)(a)": "Section 12(1)(a) requires the controller to be fully accountable for all processing. Your ability to report unauthorized processing creates a direct accountability obligation on the controller.",
        "PDPA:12(1)(f)": "Section 12(1)(f) requires processes for identifying and rectifying compliance failures. The unauthorized processing you experienced demonstrates a failure in these processes.",
        "PDPA:10(a)": "Section 10(a) requires confidentiality in all processing. Using your data outside declared purposes breaches the confidentiality obligation attached to that data.",
        "PDPA:10(b)": "Section 10(b) requires measures to prevent unauthorized disclosure — unauthorized processing may involve disclosure of your data to parties not authorized to receive it.",
        "PDPA:16(c)": "Section 16(c) covers erasure where processing is unlawful — since the processing lacks legal basis, you have a compounded right to demand immediate deletion.",
        "PDPA:13(1)": "Section 13(1) gives you the right to know exactly what data of yours is being processed. Use this right to establish the full scope of the unauthorized processing activity.",
        "RTI:5(1)(e)": "Section 5(1)(e) provides special protection for sensitive categories of data such as medical information. If your sensitive personal data is being processed without authorization, this provision provides heightened protection.",
    },

    "DATA_EXPOSURE": {
        "PDPA:6(1)a)": "Section 6(1)(a) requires that your data be held only for a specified purpose. Its exposure to unauthorized parties is evidence that the controls required to enforce this limitation were absent.",
        "PDPA:6(1)b)": "Section 6(1)(b) requires an explicitly stated purpose. If your data was accessible beyond its stated purpose and then exposed, this provision is violated.",
        "PDPA:7(a)": "Section 7(a) requires processing to be confined to the defined purpose. Exposure of your data to unauthorized parties constitutes processing beyond the defined scope.",
        "PDPA:7(c)": "Section 7(c) requires strict proportionality and purpose-limitation. Exposure of your data to unintended recipients violates both the proportionality and confinement requirements.",
        "PDPA:10(a)": "Section 10(a) is the direct basis for your claim — the data controller had a legal duty to maintain confidentiality and integrity of your personal data. The exposure demonstrates a breach of this core obligation.",
        "PDPA:10(b)": "Section 10(b) requires active measures to prevent unauthorized disclosure. The fact that your data was exposed is direct evidence that these mandatory safeguards were inadequate or absent.",
        "PDPA:8(a)": "Section 8(a) requires that personal data be kept accurate. If your exposed data was inaccurate or outdated at the time of exposure, this compounds the violation.",
        "PDPA:13(1)": "Section 13(1) gives you the right to demand a full account from the data controller of what personal data of yours was exposed and to whom.",
        "CCA:7(a)": "Section 7(a) covers situations where a computer was used without authorization to access or distribute your personal data — the act causing the exposure is a criminal offence under this section.",
        "CCA:7(c)": "Section 7(c) directly covers the acquisition or possession of your personal data obtained through unauthorized computer access — recipients of your exposed data may be liable under this.",
        "PDPA:9": "Section 9 requires timely deletion of data no longer needed. If the exposed data was held longer than necessary, the retention itself was unlawful prior to the exposure.",
        "PDPA:11(a)": "Section 11(a) requires the controller to inform you of processing activities. Following the exposure, you have an enhanced right to full transparency about what was exposed and to whom.",
        "PDPA:14(1)": "Section 14(1) gives you the right to object to continued processing of your exposed data — demand that any further use of the exposed data be halted immediately.",
        "PDPA:16(a)": "Section 16(a) gives you the right to demand erasure of your exposed data from all systems — including any third parties who received it.",
        "TCA:49(c)": "Section 49(c) prohibits unlawful disclosure of data transmitted over telecommunications networks — if your data was exposed via a telecom channel, this provision applies.",
        "TCA:52(a)": "Section 52(a) covers unlawful intrusion into telecommunications systems. If the exposure occurred through unauthorized access to a telecoms platform, this section applies to the perpetrator.",
    },

    "DOXXING": {
        "OSA:20(1)": "Section 20(1) is the primary provision for doxxing — it directly criminalises communicating statements or personal information intended to cause harassment, alarm, or distress. Publishing your private details publicly to invite harassment is a clear violation.",
        "OSA:19": "Section 19 criminalises circulating false reports. If false claims accompanied the publication of your personal details, this section may apply.",
        "OSA:18(a)": "Section 18(a) applies when doxxing involves impersonation — if fake accounts using your identity were created alongside the doxxing, this section covers that element.",
        "OSA:18(c)": "Section 18(c) covers misrepresentation of identity. If the doxxer used your photos or details to create a false representation, this section applies.",
        "PDPA:10(a)": "Section 10(a) imposes a legal duty on data controllers to maintain the confidentiality of your personal data. The exposure of your private details — address, phone, NIC — demonstrates a failure to meet this obligation.",
        "PDPA:10(b)": "Section 10(b) requires measures to prevent unauthorized disclosure. The public posting of your personal information is direct evidence that these safeguards were inadequate.",
        "PDPA:7(a)": "Section 7(a) requires that processing of your data be confined to the declared purpose. Publishing your personal details publicly goes far beyond any consented purpose.",
        "PDPA:11(a)": "Section 11(a) requires transparency about how data is processed. You were never informed your data would be published publicly — this violates your right to be informed.",
        "PDPA:16(a)": "Section 16(a) gives you the right to demand immediate erasure of your published personal data from all platforms and systems.",
        "PDPA:14(1)": "Section 14(1) gives you the right to object to the continued processing and display of your personal information on any platform.",
        "PDPA:6(1)a)": "Section 6(1)(a) requires data to be held only for a specified purpose. Using your data for public shaming or harassment was never a legitimate purpose.",
        "RTI:5(1)(a)": "Section 5(1)(a) restricts the disclosure of personal information. The public posting of your private details violates the privacy protections established by this section.",
        "CCA:7(a)": "Section 7(a) covers unauthorized computer use to access or distribute personal data. If your details were obtained through unauthorized access, this criminal offence applies.",
        "CCA:7(b)": "Section 7(b) covers dealing in unlawfully obtained computer data. Anyone who received and further shared your doxxed information may be liable under this section.",
    },

    "HARASSMENT": {
        "OSA:20(1)": "Section 20(1) is the most directly applicable provision — it specifically criminalises communicating statements that cause harassment, alarm, or distress. The threatening messages, abusive content, or intimidating communications you experienced are textbook violations.",
        "OSA:19": "Section 19 criminalises circulating false reports intended to cause public alarm. If the harassment includes spreading false information, this section applies.",
        "OSA:18(a)": "Section 18(a) applies when harassment involves impersonation — if fake accounts using your identity were created to facilitate the harassment, this section covers that element.",
        "PDPA:10(a)": "Section 10(a) requires data controllers to maintain confidentiality. If your personal data was leaked or shared to enable the harassment, the controller failed this legal obligation.",
        "PDPA:10(b)": "Section 10(b) requires safeguards against unauthorized disclosure. The use of your personal data for harassment demonstrates inadequate protection measures.",
        "PDPA:7(a)": "Section 7(a) requires processing to be confined to the declared purpose. Using your personal data to harass you goes far beyond any legitimate purpose.",
        "PDPA:11(a)": "Section 11(a) requires transparency. You were never informed your data would be used for harassment — this is a violation of your right to be informed.",
        "PDPA:16(a)": "Section 16(a) gives you the right to demand erasure of any personal data being used in harassment campaigns.",
        "PDPA:14(1)": "Section 14(1) gives you the right to object to continued use of your personal data — demand that all processing related to the harassment cease immediately.",
        "RTI:5(1)(a)": "Section 5(1)(a) protects your private information from unauthorized disclosure. The exposure and misuse of your data for harassment violates these privacy protections.",
        "CCA:7(a)": "Section 7(a) covers unauthorized computer use to access your personal data. If the harasser obtained your information through unauthorized access, this criminal offence applies.",
        "TCA:46B": "Section 46B criminalises using telecommunications to deceive or mislead. Harassment via phone calls, SMS, or messaging platforms is directly covered by this provision.",
        "TCA:49(c)": "Section 49(c) prohibits unauthorized disclosure of communications. If your private messages or communications were shared as part of the harassment, this section applies.",
    },

    "IDENTITY_THEFT": {
        "CCA:4(a)": "Section 4(a) penalises unauthorized access to a computer with intent to commit a further offence. Accessing your identity data to commit fraud is a direct violation of this section.",
        "CCA:4(b)": "Section 4(b) covers unauthorized access with intent to facilitate a further offence. Using your stolen identity details to open accounts or obtain services triggers this section.",
        "CCA:3(a)": "Section 3(a) criminalises the initial unauthorized access to computer systems where your identity data was stored or obtained.",
        "CCA:10": "Section 10 covers unauthorized disclosure of access codes or identity information that enabled the theft of your identity.",
        "TCA:46B": "Section 46B criminalises using telecommunications to deceive — SIM registration, phone-based fraud, or telecom services obtained using your stolen identity fall under this provision.",
        "TCA:46C": "Section 46C penalises providing false information to obtain telecom services. If your identity was used to register a SIM card or phone number, this section directly applies.",
        "TCA:52(a)": "Section 52(a) covers unauthorized intrusion into telecom systems — accessing telecom services using your stolen identity constitutes such intrusion.",
        "PDPA:10(a)": "Section 10(a) requires confidentiality of your personal data. The organisation that allowed your identity data to be stolen breached this legal obligation.",
        "PDPA:10(b)": "Section 10(b) requires measures to prevent loss or unauthorized disclosure. The successful theft of your identity data proves these measures were inadequate.",
        "PDPA:7(a)": "Section 7(a) requires processing to be confined to the defined purpose. Your identity data was used for fraudulent purposes well beyond any legitimate scope.",
        "PDPA:6(1)a)": "Section 6(1)(a) requires a specified purpose for data collection. If identity data was collected poorly and then stolen, the purpose limitation was already violated.",
        "PDPA:6(1)b)": "Section 6(1)(b) requires the purpose to be explicitly stated. Inadequate purpose definition at the point of collection compounds the liability for the identity theft.",
        "PDPA:13(1)": "Section 13(1) gives you the right to know which of your personal data was compromised and used for the identity theft.",
        "CCA:7(a)": "Section 7(a) covers unauthorized computer use to access or copy your identity documents — the act of stealing your digital identity data is criminalised by this provision.",
        "ETA:12(1)(a)": "Section 12(1)(a) governs the attribution of electronic records. Transactions or records falsely created using your stolen identity are addressed by this section.",
        "ETA:12(1)(b)": "Section 12(1)(b) covers authorised scope of electronic records. Records created using your identity without your authority exceed any authorised scope.",
        "ETA:12(2)(a)": "Section 12(2)(a) provides grounds to challenge records falsely attributed to you due to the identity theft.",
        "TCA:52(d)": "Section 52(d) covers telecoms intrusion with intent to cause harm — using your stolen identity to access telecom services constitutes such intrusion.",
    },

    "ACCOUNT_TAKEOVER": {
        "CCA:3(a)": "Section 3(a) is the foundational offence — unauthorized access to your account is a direct criminal offence under this section.",
        "CCA:3(b)": "Section 3(b) covers unauthorized access to information held in a computer — accessing your account data, messages, or files without your consent is covered here.",
        "CCA:4(a)": "Section 4(a) penalises unauthorized access with intent to commit a further offence — if your account was used for fraud, harassment, or theft, this heavier charge applies.",
        "CCA:4(b)": "Section 4(b) covers unauthorized access to facilitate further offences. The combined act of account hijacking plus further misuse is penalised under this provision.",
        "CCA:5": "Section 5 covers causing a computer to perform unauthorized functions. Using your hijacked account to send messages, make transfers, or post content is a violation.",
        "CCA:10": "Section 10 covers unauthorized disclosure of credentials. If your password or recovery information was leaked to enable the takeover, this section applies.",
        "TCA:52(a)": "Section 52(a) covers unauthorized intrusion into telecom systems. If your account was accessed through phone or messaging platforms, this section applies.",
        "TCA:52(d)": "Section 52(d) covers telecoms intrusion with intent to cause harm. If the account takeover was used to harm you or your contacts, this provision applies.",
        "TCA:46B": "Section 46B covers deception via telecommunications. If your hijacked account was used to send deceptive messages, this section applies.",
        "TCA:46C": "Section 46C covers false information to obtain telecom services. If credentials were falsely obtained to facilitate the takeover, this applies.",
        "ETA:12(1)(a)": "Section 12(1)(a) governs proper attribution of electronic records. Actions taken through your hijacked account were falsely attributed to you.",
        "ETA:12(1)(b)": "Section 12(1)(b) covers the scope of authorized electronic actions. The attacker exceeded any authorized scope by hijacking and misusing your account.",
        "PDPA:10(a)": "Section 10(a) requires confidentiality of your credentials and account data. The platform that allowed the takeover failed this legal obligation.",
        "PDPA:10(b)": "Section 10(b) requires measures to prevent unauthorized access. A successful account takeover proves these security measures were inadequate.",
        "PDPA:13(1)": "Section 13(1) gives you the right to know what data was accessed or modified during the account takeover.",
        "CCA:7(a)": "Section 7(a) covers unauthorized computer use. Accessing and operating your account without authorization is a criminal offence under this section.",
        "CCA:7(b)": "Section 7(b) covers dealing in unlawfully obtained data. If your account data was sold or shared to facilitate the takeover, this section applies.",
    },
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

            # ── Why relevant: scenario+clause specific lookup ──
            key = f"{law_code}:{section}"
            scenario_reasonings = _CLAUSE_REASONING.get(scenario_key, {})
            why = scenario_reasonings.get(
                key,
                self._build_fallback_reasoning(
                    tag_set, clause_tags, scenario_key, impersonate, img_exposed,
                    clause=clause,
                ),
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
        Build a specific, varied fallback explanation when no hand-written
        reasoning exists for this (scenario, clause) pair.

        Uses the clause's own title/description + matched PII data + scenario
        context to construct a unique explanation per clause.
        """
        clause = clause or {}
        clause_title = clause.get("title", "")
        clause_desc = clause.get("description", "")
        law_name = clause.get("law_name", clause.get("law_code", ""))
        section = clause.get("section", "")

        matched = sorted(user_tags & clause_tags)
        readable = [_TAG_LABELS.get(t, t) for t in matched] if matched else []

        parts = []

        # ── Sentence 1: Link specific PII data to the clause's purpose ──
        if readable and clause_title:
            data_str = ", ".join(readable)
            parts.append(
                f"Your exposed personal data — specifically {data_str} — "
                f"falls within the scope of this provision, which addresses "
                f"{clause_title.lower().rstrip('.')}."
            )
        elif clause_title:
            parts.append(
                f"This provision addresses {clause_title.lower().rstrip('.')}, "
                f"which is directly applicable to your reported incident."
            )
        elif readable:
            data_str = ", ".join(readable)
            parts.append(
                f"The exposure of {data_str} engages this legal provision."
            )

        # ── Sentence 2: Explain what the law requires/prohibits ──
        if clause_desc:
            # Use the clause description to explain obligation/prohibition
            desc_lower = clause_desc.lower()
            if any(w in desc_lower for w in ("prohibit", "offence", "criminal", "penalis")):
                parts.append(
                    f"Under the {law_name}, Section {section} criminalises this type of conduct "
                    f"and provides for sanctions against the perpetrator."
                )
            elif any(w in desc_lower for w in ("obligation", "require", "must", "shall")):
                parts.append(
                    f"The {law_name}, Section {section} imposes a legal obligation on data controllers "
                    f"that is relevant to your situation — a failure to comply constitutes a breach."
                )
            elif any(w in desc_lower for w in ("right", "entitle", "may request")):
                parts.append(
                    f"Under the {law_name}, Section {section}, you have a legal right that can be "
                    f"exercised in response to this incident."
                )
            else:
                parts.append(
                    f"This section of the {law_name} establishes protections that are engaged "
                    f"by the circumstances of your incident."
                )

        # ── Sentence 3: Scenario-specific context ──
        _SCENARIO_CONTEXT = {
            "IDENTITY_IMPERSONATION": (
                "Because someone is actively impersonating you, provisions addressing "
                "online personation, identity fraud, and unauthorized use of personal data are applicable."
            ),
            "IMAGE_ABUSE": (
                "The non-consensual sharing of your personal images invokes protections "
                "against image-based abuse, harassment, and unauthorized data processing."
            ),
            "ACCOUNT_MISUSE": (
                "Unauthorized access to your account engages provisions covering "
                "computer misuse, unauthorized data access, and electronic authentication safeguards."
            ),
            "DATABASE_BREACH": (
                "A data breach of this nature triggers data controller accountability, "
                "security obligations, and your rights as a data subject to transparency and remedy."
            ),
            "UNAUTHORIZED_DATA_PROCESSING": (
                "Processing your personal data without lawful basis or beyond the declared purpose "
                "violates fundamental data protection principles and your right to control your data."
            ),
            "DATA_EXPOSURE": (
                "The unauthorized exposure of your personal data engages security obligations, "
                "purpose-limitation requirements, and your right to seek remedy and erasure."
            ),
            "DOXXING": (
                "The deliberate public exposure of your private personal information engages "
                "provisions against online harassment, data protection obligations, and your right to privacy."
            ),
            "HARASSMENT": (
                "Online harassment and threats using your personal data invoke protections "
                "against cyberbullying, non-consensual content sharing, and data misuse."
            ),
            "IDENTITY_THEFT": (
                "The fraudulent use of your stolen identity data triggers provisions covering "
                "computer crime, telecom fraud, and data controller accountability for failing to protect your data."
            ),
            "ACCOUNT_TAKEOVER": (
                "Unauthorized access to and hijacking of your account engages provisions covering "
                "computer misuse, unauthorized access, and electronic authentication safeguards."
            ),
        }
        ctx = _SCENARIO_CONTEXT.get(scenario_key, "")
        if ctx and len(parts) < 2:
            parts.append(ctx)

        # ── Safety net ──
        if not parts:
            if impersonate:
                parts.append(
                    "The impersonation activity in this incident directly engages this "
                    "legal provision, which protects against unauthorized use of personal identity."
                )
            elif img_exposed:
                parts.append(
                    "The non-consensual exposure of your personal images triggers this provision, "
                    "which addresses unauthorized sharing and processing of sensitive personal data."
                )
            else:
                parts.append(
                    "This clause addresses the type of data misuse described in your incident "
                    "and provides a legal basis for seeking remedy."
                )

        return " ".join(parts)
