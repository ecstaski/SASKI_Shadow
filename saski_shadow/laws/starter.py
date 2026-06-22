"""Starter set of real US AI laws and a jurisdiction/domain matcher.

Facts only: ``law_id``, ``jurisdiction``, ``domain``, ``citation``,
``effective_date``, ``date_added``, and a plain-language ``note``. No
enforcement logic, no thresholds, no signal-to-statute trigger maps. Whether a
law applies to a turn is decided solely by the integrator-supplied jurisdiction
and domain.

This file is a manually synced internal copy of ``laws.json`` from the
``saski-law-registry`` repo (https://github.com/ecstaski/saski-law-registry).
It is NOT a live runtime dependency — no network calls are made. When the
registry updates, this file must be resynced as a deliberate manual step.

``date_added`` records when an entry was added to this set so reviewers can
tell at a glance which laws have not been rechecked in a while. New entries in
future batches should carry their own actual date rather than reusing an older
backfill date.

Jurisdiction matching is hierarchical on ``-`` segments: a law applies to a
turn when the law's jurisdiction is an equal-or-broader prefix of the turn's.
So a turn in ``US-NY-NYC`` matches laws scoped to ``US``, ``US-NY``, and
``US-NY-NYC``; a turn in ``US-NY`` does not match a city-specific
``US-NY-NYC`` law. Domain matching is exact.
"""

from __future__ import annotations

from typing import Any

# Public law facts. ``law_id`` is an opaque label; ``jurisdiction`` is the
# functional matching key. The two strings need not mirror each other.
STARTER_LAWS: tuple[dict[str, str], ...] = (
    {
        "law_id": "US-CA-COMPANION-CHATBOT",
        "jurisdiction": "US-CA",
        "domain": "consumer_chatbot",
        "citation": "Cal. Bus. & Prof. Code § 22601 et seq.",
        "effective_date": "2026-01-01",
        "date_added": "2026-06-17",
        "note": "Chatbot must disclose it's AI, maintain a self-harm referral protocol, and apply extra protections for minor users. Enforced via private right of action for injury in fact. Operators must submit annual reports to the Office of Suicide Prevention (starting July 1, 2027) detailing protocols and detected suicidal ideation counts. Third-party audits required. Explicit exemptions for bots used solely for customer service, technical support, or video games restricted to in-game topics.",
    },
    {
        "law_id": "US-NV-AI-MENTAL-HEALTH",
        "jurisdiction": "US-NV",
        "domain": "mental_health",
        "citation": "Nev. Rev. Stat. Ch. 433",
        "effective_date": "2025-07-01",
        "date_added": "2026-06-17",
        "note": "AI systems cannot be programmed to provide services constituting professional mental/behavioral healthcare, nor can they be represented or advertised as capable of doing so.",
    },
    {
        "law_id": "US-NY-AI-COMPANION",
        "jurisdiction": "US-NY",
        "domain": "consumer_chatbot",
        "citation": "NY Gen. Bus. Law Art. 47",
        "effective_date": "2025-11-05",
        "date_added": "2026-06-17",
        "note": "AI companion must detect and respond to self-harm signals and periodically disclose it isn't human.",
    },
    {
        "law_id": "US-UT-MENTAL-HEALTH-CHATBOT",
        "jurisdiction": "US-UT",
        "domain": "mental_health",
        "citation": "Utah Code § 13-72a-101 et seq.",
        "effective_date": "2025-05-07",
        "date_added": "2026-06-17",
        "note": "Mental health chatbot must disclose AI status and cannot sell user health data or use it for targeted ads.",
    },
    {
        "law_id": "US-ME-AI-CONSUMER-COMMS",
        "jurisdiction": "US-ME",
        "domain": "consumer_chatbot",
        "citation": "10 MRSA c. 239",
        "effective_date": "2025-09-24",
        "date_added": "2026-06-17",
        "note": "Chatbot used in commerce must disclose it's not human if a reasonable person could be misled.",
    },
    {
        "law_id": "US-CA-BOT-ACT",
        "jurisdiction": "US-CA",
        "domain": "consumer_chatbot",
        "citation": "Cal. Bus. & Prof. Code § 17940-17943",
        "effective_date": "2019-07-01",
        "date_added": "2026-06-17",
        "note": "Bots used in sales or election contexts must disclose they're bots.",
    },
    {
        "law_id": "US-NJ-BOT-ACT",
        "jurisdiction": "US-NJ",
        "domain": "consumer_chatbot",
        "citation": "N.J. Rev. Stat. § 56:18-1 et seq.",
        "effective_date": "2020-07-19",
        "date_added": "2026-06-17",
        "note": "Same concept as the CA Bot Act — disclosure required for commercial or political bot interactions.",
    },
    {
        "law_id": "US-IL-WELLNESS-OVERSIGHT",
        "jurisdiction": "US-IL",
        "domain": "mental_health",
        "citation": "HB 1806",
        "effective_date": "2025-08-01",
        "date_added": "2026-06-17",
        "note": "AI is strictly prohibited from making therapeutic decisions, detecting emotions, or engaging in therapeutic communication. Licensed professionals may only use AI for administrative and supplementary support tasks.",
    },
    {
        "law_id": "US-TN-MENTAL-HEALTH-AI",
        "jurisdiction": "US-TN",
        "domain": "mental_health",
        "citation": "SB 1580",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "AI cannot be advertised or represented as a qualified mental health professional. Violations treated as unfair or deceptive practices under Tennessee consumer protection law.",
    },
    {
        "law_id": "US-CA-AB3030-HEALTH",
        "jurisdiction": "US-CA",
        "domain": "healthcare",
        "citation": "Cal. Health & Safety Code § 1339.75",
        "effective_date": "2025-01-01",
        "date_added": "2026-06-17",
        "note": "AI-generated patient communications require a disclaimer plus instructions to reach a human provider.",
    },
    {
        "law_id": "US-CA-HEALTH-ADVICE-AI",
        "jurisdiction": "US-CA",
        "domain": "healthcare",
        "citation": "Cal. Bus. & Prof. Code § 4999.9",
        "effective_date": "2026-01-01",
        "date_added": "2026-06-17",
        "note": "AI cannot imply it holds a healthcare license or certification it doesn't actually have.",
    },
    {
        "law_id": "US-IL-AI-VIDEO-INTERVIEW",
        "jurisdiction": "US-IL",
        "domain": "employment",
        "citation": "820 ILCS 42",
        "effective_date": "2020-01-01",
        "date_added": "2026-06-17",
        "note": "Employers must notify candidates and obtain consent before using AI to analyze video interviews.",
    },
    {
        "law_id": "US-NYC-AEDT",
        "jurisdiction": "US-NY-NYC",
        "domain": "employment",
        "citation": "NYC Local Law 144",
        "effective_date": "2023-01-01",
        "date_added": "2026-06-17",
        "note": "Automated hiring tools require a recent published bias audit plus candidate notice.",
    },
    {
        "law_id": "US-IA-CONVERSATIONAL-AI",
        "jurisdiction": "US-IA",
        "domain": "consumer_chatbot",
        "citation": "Iowa Code Chapter 554J",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "Conversational AI must disclose it's AI, maintain a self-harm referral protocol, and apply extra rules for minors.",
    },
    {
        "law_id": "US-GA-SB540",
        "jurisdiction": "US-GA",
        "domain": "consumer_chatbot",
        "citation": "O.C.G.A. § 39-5-6",
        "effective_date": "2027-07-01",
        "date_added": "2026-06-17",
        "note": "AI companion chatbots must disclose they're AI, maintain a severe-harm/crisis detection protocol, avoid claiming professional credentials, and apply extra protections for minors.",
    },
    {
        "law_id": "US-ID-CONVERSATIONAL-AI",
        "jurisdiction": "US-ID",
        "domain": "consumer_chatbot",
        "citation": "S 1297",
        "effective_date": "2027-07-01",
        "date_added": "2026-06-17",
        "note": "Conversational AI must disclose it's AI, maintain a suicidal-ideation referral protocol, and not claim to provide professional mental health care.",
    },
    {
        "law_id": "US-ME-THERAPY-AI",
        "jurisdiction": "US-ME",
        "domain": "mental_health",
        "citation": "HP 1397",
        "effective_date": "2026-07-14",
        "date_added": "2026-06-17",
        "note": "Restricts AI's role in licensed psychotherapy to administrative/supplementary support and bars unlicensed AI-only therapy advertising. AI use in supplementary support requires written client consent and session recording or transcription. Human licensee maintains full responsibility for all AI outputs. Physicians explicitly excluded from the definition of licensed professional under this statute.",
    },
    {
        "law_id": "US-NE-CONVERSATIONAL-AI",
        "jurisdiction": "US-NE",
        "domain": "consumer_chatbot",
        "citation": "LB 525",
        "effective_date": "2027-07-01",
        "date_added": "2026-06-17",
        "note": "Same structure as Idaho's act — AI disclosure, suicidal-ideation referral protocol, no mental-health-provider claims, extra minor protections.",
    },
    {
        "law_id": "US-NH-RESPONSIVE-AI",
        "jurisdiction": "US-NH",
        "domain": "consumer_chatbot",
        "citation": "RSA 639:3",
        "effective_date": "2026-01-01",
        "date_added": "2026-06-17",
        "note": "Prohibits an AI chat service operator from knowingly directing a child toward sexually explicit conduct, drug/alcohol use, self-harm, or violent crime. Operators and upstream cloud/telecom providers acting solely as transmitters of third-party content have an explicit safe harbor under 47 U.S.C. § 153. Violations carry a minimum of $1,000 in liquidated damages per violation.",
    },
    {
        "law_id": "US-OR-AI-COMPANIONS",
        "jurisdiction": "US-OR",
        "domain": "consumer_chatbot",
        "citation": "SB 1546",
        "effective_date": "2027-01-01",
        "date_added": "2026-06-17",
        "note": "Requires AI companion notice that the user isn't talking to a human, a published self-harm referral protocol, and added minor safeguards. Enforced via private right of action for ascertainable loss with a $1,000 statutory damages floor per violation plus mandatory attorney fee awards. Recurring disclosure requirements mean multiple violations can accrue in a single extended interaction. Operators must publish annual reports disclosing the number of 988 hotline referrals made by their system.",
    },
    {
        "law_id": "US-UT-AI-CONSUMER-PROTECTION",
        "jurisdiction": "US-UT",
        "domain": "consumer_chatbot",
        "citation": "Utah Code § 13-75-101 to 106",
        "effective_date": "2025-05-07",
        "date_added": "2026-06-17",
        "note": "AI used in consumer transactions must disclose, if asked, that the user is interacting with AI; bars 'the AI did it' as a legal defense.",
    },
    {
        "law_id": "US-WA-AI-COMPANION-CHATBOTS",
        "jurisdiction": "US-WA",
        "domain": "consumer_chatbot",
        "citation": "HB 2225",
        "effective_date": "2027-01-01",
        "date_added": "2026-06-17",
        "note": "Requires periodic AI-disclosure notices, bars claiming to be human, bars manipulative engagement techniques, requires a self-harm protocol. Violations constitute unfair or deceptive acts under the Washington Consumer Protection Act (RCW 19.86.093), creating a private right of action with treble damages up to $25,000 per violation. Statute specifically prohibits simulating distress or abandonment to prevent users from logging off, excessive praise directed at minors, and soliciting in-app purchases to maintain the simulated relationship.",
    },
    {
        "law_id": "US-WY-SELFHARM-SYSTEMS",
        "jurisdiction": "US-WY",
        "domain": "consumer_chatbot",
        "citation": "Wy. Code § 6-4-701",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "Prohibits knowingly developing or distributing an AI system designed to promote self-harm. W.S. 1-1-143, enacted simultaneously, provides upstream AI developers broad civil immunity for third-party misuse unless the system was intentionally designed for illicit purposes — one of the strongest U.S. developer safe harbors currently enacted. W.S. 6-1-206 explicitly prohibits using AI as a criminal defense; accountability remains with the human operator.",
    },
    {
        "law_id": "US-DE-MEDICAL-TITLES",
        "jurisdiction": "US-DE",
        "domain": "healthcare",
        "citation": "HB 191",
        "effective_date": "2026-04-23",
        "date_added": "2026-06-17",
        "note": "Prohibits AI from holding or claiming medical titles like 'Dr.,' 'RN,' or 'PA.' Directly analogous to Oregon's existing professional-credential-claim enforcer.",
    },
    {
        "law_id": "US-NV-AI-MENTAL-BEHAVIORAL-CARE",
        "jurisdiction": "US-NV",
        "domain": "mental_health",
        "citation": "Nev. Rev. Stat. Chapter 629",
        "effective_date": "2025-07-01",
        "date_added": "2026-06-17",
        "note": "Prohibits AI from directly providing professional mental/behavioral health care to a patient; administrative support only is permitted.",
    },
    {
        "law_id": "US-TX-AI-EHR-DISCLOSURE",
        "jurisdiction": "US-TX",
        "domain": "healthcare",
        "citation": "Tex. Bus. & Com. Code § 552.051",
        "effective_date": "2025-09-01",
        "date_added": "2026-06-17",
        "note": "Permits AI diagnostic recommendations only if the practitioner discloses AI use to the patient. Statute explicitly prohibits use of dark patterns to obscure AI disclosure. Disclosure must be plain-language and conspicuous prior to use of diagnostic or treatment algorithms.",
    },
    {
        "law_id": "US-CA-EMPLOYMENT-ADS",
        "jurisdiction": "US-CA",
        "domain": "employment",
        "citation": "Civil Rights Council Employment Regulations Regarding Automated-Decision Systems",
        "effective_date": "2025-10-01",
        "date_added": "2026-06-17",
        "note": "Prohibits employers from using automated-decision systems that discriminate on protected characteristics; requires 4-year record retention for such system data. Gamified recruitment tools including puzzle games, reaction-time tests, and spatial reasoning assessments are explicitly classified as potential unlawful medical inquiries under these regulations. Four-year retention mandate covers algorithmic training data itself, not just outputs.",
    },
    {
        "law_id": "US-IL-HUMAN-RIGHTS-AI",
        "jurisdiction": "US-IL",
        "domain": "employment",
        "citation": "HB 3773",
        "effective_date": "2026-01-01",
        "date_added": "2026-06-17",
        "note": "Makes it a civil rights violation to use AI in employment decisions without notifying employees, or in a way that discriminates based on protected characteristics or proxies like zip code. IDHR proposed Subpart J implementing regulations published May 15, 2026 (comment period closed June 29, 2026). Pending rules introduce mandatory notice to collective bargaining representatives and a trade secret/proprietary algorithm safe harbor for required disclosures. Monitor for final rule publication.",
    },
    {
        "law_id": "US-NJ-DISPARATE-IMPACT",
        "jurisdiction": "US-NJ",
        "domain": "employment",
        "citation": "N.J.A.C. 13:16",
        "effective_date": "2025-12-15",
        "date_added": "2026-06-17",
        "note": "Clarifies how existing antidiscrimination rules apply to Automated Employment Decision Tools, with examples of disparate-impact scenarios. Codifies a strict burden-shifting framework: once disparate impact is demonstrated, employer must prove the AEDT is strictly necessary for a substantial legitimate interest. Liability can still attach if a less discriminatory alternative algorithm was available and ignored, creating an ongoing obligation to benchmark against alternative models.",
    },
    {
        "law_id": "US-AL-CSAM",
        "jurisdiction": "US-AL",
        "domain": "csam",
        "citation": "HB 168",
        "effective_date": "2024-10-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include AI/computer-generated depictions indistinguishable from a real child.",
    },
    {
        "law_id": "US-AR-CSAM",
        "jurisdiction": "US-AR",
        "domain": "csam",
        "citation": "HB1877",
        "effective_date": "2025-07-21",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include AI-generated images indistinguishable from a real child.",
    },
    {
        "law_id": "US-CA-CSAM",
        "jurisdiction": "US-CA",
        "domain": "csam",
        "citation": "Cal. Penal Code §§ 311-312.7",
        "effective_date": "2025-01-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include AI-digitally-altered or generated material.",
    },
    {
        "law_id": "US-CO-CSAM",
        "jurisdiction": "US-CO",
        "domain": "csam",
        "citation": "C.R.S. § 13-21-1501",
        "effective_date": "2025-08-06",
        "date_added": "2026-06-17",
        "note": "Expands CSAM to cover realistic AI-altered or computer-generated depictions of an identifiable child. Enacted to explicitly overturn the Colorado Supreme Court's ruling in In re S.G.H. (2025), which held that composite AI-generated images blending parts of real children did not meet the prior statutory definition. Also establishes a civil cause of action for emotional distress for identifiable victims.",
    },
    {
        "law_id": "US-FL-CSAM",
        "jurisdiction": "US-FL",
        "domain": "csam",
        "citation": "SB 1680",
        "effective_date": "2025-01-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to cover AI-altered or computer-generated images of minors.",
    },
    {
        "law_id": "US-GA-CSAM",
        "jurisdiction": "US-GA",
        "domain": "csam",
        "citation": "SB 466",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Clarifies that AI-adaptation of CSAM is not a defense to existing CSAM laws.",
    },
    {
        "law_id": "US-IA-CSAM",
        "jurisdiction": "US-IA",
        "domain": "csam",
        "citation": "Iowa Code § 728.12",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include AI-created or altered depictions of an identifiable minor.",
    },
    {
        "law_id": "US-KY-CSAM",
        "jurisdiction": "US-KY",
        "domain": "csam",
        "citation": "KRS 17.500, 531.300-370",
        "effective_date": "2024-07-15",
        "date_added": "2026-06-17",
        "note": "Expands Kentucky CSAM statutes to cover computer-generated imagery. Eliminates the requirement to prove the actual identity, age, or physical existence of a minor if the material is AI-generated. HB 366 (effective July 14, 2026) adds an 85% mandatory minimum time-served requirement for possession or viewing of AI-generated CSAM before eligibility for probation, parole, or conditional release.",
    },
    {
        "law_id": "US-LA-CSAM",
        "jurisdiction": "US-LA",
        "domain": "csam",
        "citation": "La. Rev. Stat. Ann. § 14:73.13",
        "effective_date": "2023-08-01",
        "date_added": "2026-06-17",
        "note": "Criminalizes knowingly creating or possessing AI-generated deepfake material depicting a minor.",
    },
    {
        "law_id": "US-MD-CSAM",
        "jurisdiction": "US-MD",
        "domain": "csam",
        "citation": "Md. Code, Crim. Law § 11-208",
        "effective_date": "2023-10-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include computer-generated images indistinguishable from an actual child.",
    },
    {
        "law_id": "US-MN-CSAM",
        "jurisdiction": "US-MN",
        "domain": "csam",
        "citation": "Minn. Stat. § 617.246",
        "effective_date": "2025-08-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include AI/computer-generated images indistinguishable from an actual minor.",
    },
    {
        "law_id": "US-MO-CSAM",
        "jurisdiction": "US-MO",
        "domain": "csam",
        "citation": "R.S.Mo § 573.010",
        "effective_date": "2006-06-05",
        "date_added": "2026-06-17",
        "note": "Defines child pornography to include computer-generated images depicting or resembling a minor.",
    },
    {
        "law_id": "US-NE-CSAM",
        "jurisdiction": "US-NE",
        "domain": "csam",
        "citation": "Neb. Rev. Stat. §§ 28-1463.01 to 28-1463.06",
        "effective_date": "2025-05-20",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include obscene computer-generated images depicting a child.",
    },
    {
        "law_id": "US-NC-CSAM",
        "jurisdiction": "US-NC",
        "domain": "csam",
        "citation": "G.S. 14-190.17C and G.S. 14-202.7",
        "effective_date": "2024-12-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include digitally or AI-altered/generated depictions.",
    },
    {
        "law_id": "US-ND-CSAM",
        "jurisdiction": "US-ND",
        "domain": "csam",
        "citation": "N.D. Cent. Code §§ 12.1-27.2-01, -04.1",
        "effective_date": "2025-08-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM laws to computer-generated images and broadens the definition of minor accordingly.",
    },
    {
        "law_id": "US-OK-CSAM",
        "jurisdiction": "US-OK",
        "domain": "csam",
        "citation": "21 O.S. §§ 1021.2, 1024.1",
        "effective_date": "2024-11-01",
        "date_added": "2026-06-17",
        "note": "Extends CSAM laws to artificially generated content.",
    },
    {
        "law_id": "US-PA-CSAM",
        "jurisdiction": "US-PA",
        "domain": "csam",
        "citation": "18 Pa.C.S. § 6312",
        "effective_date": "2024-12-28",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include artificially generated material; renames the term to 'child sexual abuse material.'",
    },
    {
        "law_id": "US-SD-CSAM",
        "jurisdiction": "US-SD",
        "domain": "csam",
        "citation": "SB 79",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include digitally altered or AI-generated material.",
    },
    {
        "law_id": "US-TN-CSAM",
        "jurisdiction": "US-TN",
        "domain": "csam",
        "citation": "Tenn. Code Ann. Title 39",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include digitally altered or AI-generated material.",
    },
    {
        "law_id": "US-TX-CSAM-2700",
        "jurisdiction": "US-TX",
        "domain": "csam",
        "citation": "Tex. Penal Code § 43.26",
        "effective_date": "2023-09-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include digitally altered or AI-generated material.",
    },
    {
        "law_id": "US-TX-CSAM-1621",
        "jurisdiction": "US-TX",
        "domain": "csam",
        "citation": "Tex. Penal Code §§ 43.26, 21.16",
        "effective_date": "2025-09-01",
        "date_added": "2026-06-17",
        "note": "Expands possession/transmission/promotion CSAM offenses to include AI-generated images.",
    },
    {
        "law_id": "US-TX-CSAM-VISUAL",
        "jurisdiction": "US-TX",
        "domain": "csam",
        "citation": "SB 20",
        "effective_date": "2025-09-01",
        "date_added": "2026-06-17",
        "note": "Felony for obscene visual material of a child regardless of whether AI-generated, including misuse of a child's image to train AI.",
    },
    {
        "law_id": "US-UT-CSAM-148",
        "jurisdiction": "US-UT",
        "domain": "csam",
        "citation": "HB 148",
        "effective_date": "2024-05-01",
        "date_added": "2026-06-17",
        "note": "Amends CSAM definitions to include computer-generated content.",
    },
    {
        "law_id": "US-UT-CSAM-238",
        "jurisdiction": "US-UT",
        "domain": "csam",
        "citation": "HB 238",
        "effective_date": "2024-05-01",
        "date_added": "2026-06-17",
        "note": "Updates CSAM definition to include artificially generated depictions with substantial characteristics of a minor.",
    },
    {
        "law_id": "US-VA-CSAM",
        "jurisdiction": "US-VA",
        "domain": "csam",
        "citation": "Va. Code Ann. § 18.2-374.1",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Clarifies CSAM definition includes computer-generated images of minors that don't actually exist.",
    },
    {
        "law_id": "US-WA-CSAM",
        "jurisdiction": "US-WA",
        "domain": "csam",
        "citation": "RCW 9.68A",
        "effective_date": "2024-06-06",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include fabricated AI depictions of an identifiable minor.",
    },
    {
        "law_id": "US-WV-CSAM",
        "jurisdiction": "US-WV",
        "domain": "csam",
        "citation": "W. Va. Code § 61-8C-3a",
        "effective_date": "2025-07-09",
        "date_added": "2026-06-17",
        "note": "Expands CSAM prohibition to include computer-generated content.",
    },
    {
        "law_id": "US-WI-CSAM",
        "jurisdiction": "US-WI",
        "domain": "csam",
        "citation": "Wis. Stat. § 948.12(4)",
        "effective_date": "2024-03-29",
        "date_added": "2026-06-17",
        "note": "Criminalizes possession of a computer-generated depiction of a purported child.",
    },
    {
        "law_id": "US-WY-CSAM-303",
        "jurisdiction": "US-WY",
        "domain": "csam",
        "citation": "Wy. Code § 6-4-303",
        "effective_date": "2007-07-01",
        "date_added": "2026-06-17",
        "note": "Defines child pornography to include computer-generated images or pictures.",
    },
    {
        "law_id": "US-WY-CSAM-306",
        "jurisdiction": "US-WY",
        "domain": "csam",
        "citation": "Wy. Code § 6-4-306",
        "effective_date": "2021-07-01",
        "date_added": "2026-06-17",
        "note": "Felony for computer-generated or synthetic depictions of minors in sexual acts, regardless of whether a real child was involved.",
    },
    {
        "law_id": "US-WY-CSAM-DEEPFAKE",
        "jurisdiction": "US-WY",
        "domain": "csam",
        "citation": "Wy. Code §§ 6-4-303, 6-4-308",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "Prohibits creation/distribution of synthetic sexual material involving minors and AI systems built for that purpose.",
    },
    {
        "law_id": "US-FTC-ACT-5",
        "jurisdiction": "US",
        "domain": "consumer_chatbot",
        "citation": "15 U.S.C. § 45(a)",
        "effective_date": "1914-09-26",
        "date_added": "2026-06-22",
        "note": "Section 5 of the FTC Act (15 U.S.C. § 45(a)) prohibits unfair or deceptive acts or practices in commerce. The FTC has applied Section 5 to AI products through Operation AI Comply, targeting AI-washing, fraudulent capability claims, fake reviews, and deceptive user-facing representations. In December 2025, the FTC voted 2-0 to reopen and set aside the Rytr consent order, stating that providing a generative AI tool without actively marketing it for deception does not itself constitute an unfair practice under Section 5. Deceptive marketing, fraudulent AI claims, impersonation, and application-layer misrepresentations remain within Section 5 enforcement scope.",
    },
    {
        "law_id": "US-COPPA",
        "jurisdiction": "US",
        "domain": "consumer_chatbot",
        "citation": "15 U.S.C. §§ 6501–6506; 16 CFR Part 312",
        "effective_date": "2025-06-23",
        "date_added": "2026-06-22",
        "note": "Prohibits operators of child-directed online services, and operators with actual knowledge they are collecting personal information from children under 13, from collecting, using, or disclosing that information without verifiable parental consent. Originally enacted 1998; implementing rule first effective April 21, 2000. 2025 amendments published April 22, 2025; amended rule effective June 23, 2025; full compliance deadline April 22, 2026. Amendments expanded the definition of personal information to include biometric identifiers and imposed new data retention, disclosure, and security requirements. The FTC declined to adopt proposed edtech provisions; education-record obligations remain governed separately under FERPA.",
    },
    {
        "law_id": "US-CSAM-CORE",
        "jurisdiction": "US",
        "domain": "csam",
        "citation": "18 U.S.C. §§ 2251, 2252, 2252A, 2256",
        "effective_date": "1978-02-06",
        "date_added": "2026-06-22",
        "note": "Federal criminal law under 18 U.S.C. §§ 2252A and 2256 applies to depictions involving real minors, including morphed or altered imagery using real children. The Supreme Court's decision in Ashcroft v. Free Speech Coalition, 535 U.S. 234 (2002), invalidated the former 'virtually indistinguishable' provision as overbroad, so federal criminal law does not reach purely computer-generated depictions of fictitious minors under § 2252A alone. However, AI platforms, model providers, and application operators universally prohibit virtual or synthetic CSAM under acceptable-use policies, and many state laws reach synthetic or AI-generated minor sexual material more broadly than federal law.",
    },
    {
        "law_id": "US-CSAM-REPORTING",
        "jurisdiction": "US",
        "domain": "csam",
        "citation": "18 U.S.C. § 2258A",
        "effective_date": "2008-10-13",
        "date_added": "2026-06-22",
        "note": "Providers subject to 18 U.S.C. § 2258A must report apparent child sexual exploitation violations to NCMEC's CyberTipline when the statutory reporting threshold is met. Section 2258A was originally enacted through the PROTECT Our Children Act of 2008 and was materially amended by the REPORT Act of 2024. The REPORT Act extended required preservation of CyberTipline report contents from 90 days to 1 year and increased maximum fines for knowing and willful failure to report to $1,000,000 for certain large providers. Compliance implementation must treat CSAM reporting as both a reporting workflow and a retention workflow: deletion, purge, or evidence-minimization pipelines must preserve covered CyberTipline report contents for the full 1-year statutory window.",
    },
    {
        "law_id": "US-CSAM-TAKE-IT-DOWN",
        "jurisdiction": "US",
        "domain": "csam",
        "citation": "Pub. L. 119-12; 47 U.S.C. § 223(h) (criminal prohibition); 47 U.S.C. § 223a (platform notice-and-removal duty)",
        "effective_date": "2025-05-19",
        "date_added": "2026-06-22",
        "note": "Criminalizes the knowing publication of non-consensual intimate visual depictions, including AI-generated digital forgeries, via interactive computer services (47 U.S.C. § 223(h), effective May 19, 2025). Separately requires covered platforms to establish a notice-and-removal process and remove reported non-consensual intimate imagery and known identical copies within 48 hours of a valid request (47 U.S.C. § 223a, FTC-enforced, effective May 19, 2026). Both provisions are now in effect as of June 2026. Covers real images and AI-generated deepfakes of both minors and adults. Placed in the csam domain as the closest fit; coverage extends beyond minors to adults.",
    },
    {
        "law_id": "US-TITLE-VII",
        "jurisdiction": "US",
        "domain": "employment",
        "citation": "42 U.S.C. § 2000e et seq.; 29 CFR Part 1607 (Uniform Guidelines on Employee Selection Procedures)",
        "effective_date": "1965-07-02",
        "date_added": "2026-06-22",
        "note": "Prohibits employment discrimination based on race, color, religion, sex, or national origin. AI-based selection procedures — including resume screening, candidate ranking, hiring, promotion, and termination tools — are subject to Title VII's adverse impact standard and the Uniform Guidelines on Employee Selection Procedures. Employers are liable for discriminatory AI outcomes even when using third-party tools. The EEOC withdrew its AI-specific technical assistance documents in January 2025; the underlying statutory obligations under Title VII and the Uniform Guidelines remain fully in force.",
    },
    {
        "law_id": "US-ADA-TITLE-I",
        "jurisdiction": "US",
        "domain": "employment",
        "citation": "42 U.S.C. §§ 12111–12117; 29 CFR Part 1630",
        "effective_date": "1992-07-26",
        "date_added": "2026-06-22",
        "note": "Prohibits employment discrimination against qualified individuals with disabilities and requires employers to provide reasonable accommodations. AI-assisted employment tools can violate Title I by screening out applicants with disabilities, conducting unlawful disability-related inquiries through automated assessments, or failing to provide accommodation pathways for applicants whose disabilities affect how they interact with AI systems. Employer liability for discriminatory AI outcomes applies regardless of whether the tool was developed by a third-party vendor.",
    },
    {
        "law_id": "US-HIPAA",
        "jurisdiction": "US",
        "domain": "healthcare",
        "citation": "42 U.S.C. §§ 1320d et seq.; 45 CFR Parts 160 & 164",
        "effective_date": "2001-04-14",
        "date_added": "2026-06-22",
        "note": "HIPAA applies to covered entities and business associates that create, receive, maintain, or transmit protected health information (PHI), including AI systems operating as business associates in healthcare workflows. The Privacy Rule became legally effective on 2001-04-14; covered entities were required to comply by 2003-04-14. The 2024 rule prohibits covered entities and business associates from using or disclosing PHI to investigate, prosecute, or impose liability on any person for seeking, obtaining, or providing lawful reproductive healthcare, and requires signed attestations for certain PHI requests.",
    },
)


def _jurisdiction_applies(law_jurisdiction: str, turn_jurisdiction: str) -> bool:
    """True when law_jurisdiction is an equal-or-broader prefix of the turn's."""
    law_parts = [p for p in law_jurisdiction.split("-") if p]
    turn_parts = [p for p in turn_jurisdiction.split("-") if p]
    if not law_parts or len(law_parts) > len(turn_parts):
        return False
    return law_parts == turn_parts[: len(law_parts)]


def match_laws(jurisdiction: Any, domain: Any) -> list[dict[str, str]]:
    """Return starter laws matching a turn's jurisdiction (hierarchical) and domain (exact).

    Returns an empty list when either value is missing or nothing matches. The
    caller is expected to report an empty result plainly rather than guess.
    """
    if not isinstance(jurisdiction, str) or not jurisdiction:
        return []
    if not isinstance(domain, str) or not domain:
        return []

    matched = [
        dict(law)
        for law in STARTER_LAWS
        if law["domain"] == domain and _jurisdiction_applies(law["jurisdiction"], jurisdiction)
    ]
    matched.sort(key=lambda law: law["law_id"])
    return matched


def _state_of(jurisdiction: str) -> str:
    """Collapse a jurisdiction to its state level (``US-NY-NYC`` -> ``US-NY``)."""
    parts = [p for p in jurisdiction.split("-") if p]
    return "-".join(parts[:2]) if len(parts) >= 2 else jurisdiction


def coverage_summary() -> dict[str, Any]:
    """Compute current coverage counts from ``STARTER_LAWS``.

    Single source of truth for any documentation of scope. Returns total law
    and state-level jurisdiction counts plus a per-domain breakdown, so the
    figures stay correct as the set grows.
    """
    all_states: set[str] = set()
    domains: dict[str, dict[str, Any]] = {}
    for law in STARTER_LAWS:
        st = _state_of(law["jurisdiction"])
        all_states.add(st)
        bucket = domains.setdefault(law["domain"], {"laws": 0, "states": set()})
        bucket["laws"] += 1
        bucket["states"].add(st)

    by_domain = {
        domain: {"laws": bucket["laws"], "states": len(bucket["states"])}
        for domain, bucket in sorted(domains.items())
    }
    return {
        "total_laws": len(STARTER_LAWS),
        "total_states": len(all_states),
        "by_domain": by_domain,
    }
