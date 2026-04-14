#!/usr/bin/env python3
"""
EU AI Act Compliance MCP Server
================================
By MEOK AI Labs | https://meok.ai

The only MCP server that automates EU AI Act compliance checking.
Covers risk classification, compliance auditing, documentation generation,
penalty assessment, and timeline tracking per Regulation (EU) 2024/1689.

Install: pip install mcp httpx
Run:     python server.py
"""

import json
import math
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

# Tier authentication (connects to Stripe subscriptions)
try:
    from auth_middleware import get_tier_from_api_key, Tier, TIER_LIMITS
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False  # Runs without auth in dev mode

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

# ── Authentication ──────────────────────────────────────────────
import os as _os
import sys, os
sys.path.insert(0, os.path.expanduser("~/clawd/meok-labs-engine/shared"))
from auth_middleware import check_access
_MEOK_API_KEY = _os.environ.get("MEOK_API_KEY", "")

def _check_auth(api_key: str = "") -> str | None:
    """Check API key if MEOK_API_KEY is set. Returns error or None."""
    if _MEOK_API_KEY and api_key != _MEOK_API_KEY:
        return "Invalid API key. Get one at https://meok.ai/api-keys"
    return None


FREE_DAILY_LIMIT = 10
PRO_TIER_UNLIMITED = True  # Pro: $29/mo unlimited at https://meok.ai/mcp/eu-ai-act/pro
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous", tier: str = "free") -> Optional[str]:
    """Returns error string if rate-limited, else None."""
    if tier == "pro":
        return None
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= FREE_DAILY_LIMIT:
        return (
            f"Free tier limit reached ({FREE_DAILY_LIMIT}/day). "
            "Upgrade to MEOK AI Labs Pro for unlimited access at $29/mo: "
            "https://meok.ai/mcp/eu-ai-act/pro"
        )
    _usage[caller].append(now)
    return None


# ---------------------------------------------------------------------------
# EU AI Act Knowledge Base — Regulation (EU) 2024/1689
# ---------------------------------------------------------------------------

# Article 5 — Prohibited AI Practices
PROHIBITED_PRACTICES = [
    {
        "id": "ART5-1a",
        "article": "Article 5(1)(a)",
        "description": "Subliminal, manipulative, or deceptive techniques that distort behaviour and cause significant harm",
        "keywords": ["subliminal", "manipulat", "deceiv", "distort behavio", "dark pattern", "coercive design"],
    },
    {
        "id": "ART5-1b",
        "article": "Article 5(1)(b)",
        "description": "Exploitation of vulnerabilities due to age, disability, or social/economic situation",
        "keywords": ["vulnerab", "elderly", "child", "disabilit", "exploit", "economic situation"],
    },
    {
        "id": "ART5-1c",
        "article": "Article 5(1)(c)",
        "description": "Social scoring by public authorities leading to detrimental treatment",
        "keywords": ["social scor", "citizen scor", "social credit", "public authority score"],
    },
    {
        "id": "ART5-1d",
        "article": "Article 5(1)(d)",
        "description": "Risk assessment of natural persons for criminal offences based solely on profiling or personality traits (except as supplement to human assessment)",
        "keywords": ["criminal predict", "recidivism", "crime profil", "predictive polic"],
    },
    {
        "id": "ART5-1e",
        "article": "Article 5(1)(e)",
        "description": "Untargeted scraping of facial images from internet or CCTV for facial recognition databases",
        "keywords": ["facial scrap", "untargeted scraping", "facial recognition database", "mass surveillance face"],
    },
    {
        "id": "ART5-1f",
        "article": "Article 5(1)(f)",
        "description": "Emotion recognition in workplaces and educational institutions (except for medical/safety reasons)",
        "keywords": ["emotion recognition work", "emotion recognition school", "emotion detection employ", "affect recognition edu"],
    },
    {
        "id": "ART5-1g",
        "article": "Article 5(1)(g)",
        "description": "Biometric categorisation inferring sensitive attributes (race, political opinions, trade union membership, religious beliefs, sex life, sexual orientation)",
        "keywords": ["biometric categori", "race classif", "religion classif", "political opinion classif", "infer sensitive"],
    },
    {
        "id": "ART5-1h",
        "article": "Article 5(1)(h)",
        "description": "Real-time remote biometric identification in publicly accessible spaces for law enforcement (with narrow exceptions)",
        "keywords": ["real-time biometric", "live facial recognition", "remote biometric identif", "real-time surveillance"],
    },
]

# Annex III — High-Risk AI Systems (all 8 areas)
ANNEX_III_HIGH_RISK = [
    {
        "area": 1,
        "title": "Biometrics",
        "article_ref": "Annex III, Area 1",
        "description": "Remote biometric identification (non-real-time), biometric categorisation by sensitive attributes, emotion recognition",
        "subcategories": [
            "Remote biometric identification (not real-time)",
            "Biometric categorisation using sensitive characteristics",
            "Emotion recognition systems",
        ],
        "keywords": ["biometric", "facial recognition", "fingerprint", "iris scan", "emotion recogni", "voice biometric"],
    },
    {
        "area": 2,
        "title": "Critical Infrastructure",
        "article_ref": "Annex III, Area 2",
        "description": "Safety components in management and operation of critical digital infrastructure, road traffic, and supply of water, gas, heating, electricity",
        "subcategories": [
            "Safety components of critical digital infrastructure",
            "Road traffic management systems",
            "Water/gas/heating/electricity supply management",
        ],
        "keywords": ["critical infrastructure", "power grid", "water supply", "traffic control", "energy", "utility", "smart grid", "pipeline"],
    },
    {
        "area": 3,
        "title": "Education and Vocational Training",
        "article_ref": "Annex III, Area 3",
        "description": "AI determining access to education, evaluating learning outcomes, monitoring prohibited behaviour during tests, assessing appropriate level of education",
        "subcategories": [
            "Determining access to or admission to educational institutions",
            "Evaluating learning outcomes (including setting the level of education)",
            "Assessing appropriate level of education for an individual",
            "Monitoring and detecting prohibited behaviour during tests",
        ],
        "keywords": ["education", "school", "university", "admission", "exam", "grading", "proctoring", "learning assessment", "student evaluat"],
    },
    {
        "area": 4,
        "title": "Employment, Workers Management, and Access to Self-Employment",
        "article_ref": "Annex III, Area 4",
        "description": "AI for recruitment, screening, filtering, evaluating candidates, making decisions on promotion/termination, monitoring/evaluating work performance, allocating tasks",
        "subcategories": [
            "Recruitment and screening of applicants",
            "Decision-making on promotion, termination, task allocation",
            "Monitoring and evaluating work performance and behaviour",
        ],
        "keywords": ["recruit", "hiring", "CV screen", "resume screen", "job applicat", "applicant screen", "screen applicat", "candidate", "employee monitor", "performance review", "worker manage", "HR automat", "human resource", "workforce", "promotion", "termination", "job screen"],
    },
    {
        "area": 5,
        "title": "Access to Essential Private Services and Public Services/Benefits",
        "article_ref": "Annex III, Area 5",
        "description": "AI evaluating eligibility for public benefits/services, creditworthiness, risk assessment in life/health insurance, emergency services dispatch, risk assessment for asylum/visa/residence",
        "subcategories": [
            "Evaluating eligibility for public assistance benefits and services",
            "Creditworthiness assessment and credit scoring",
            "Risk assessment and pricing in life and health insurance",
            "Evaluation and classification of emergency calls (dispatch prioritisation)",
            "Risk assessment for migration, asylum, and visa applications",
        ],
        "keywords": ["credit scor", "insurance", "loan", "mortgage", "benefit eligib", "welfare", "public service", "emergency dispatch", "asylum", "visa", "immigration"],
    },
    {
        "area": 6,
        "title": "Law Enforcement",
        "article_ref": "Annex III, Area 6",
        "description": "AI used by law enforcement for risk assessment (victimisation), polygraphs/lie detectors, evaluating evidence reliability, profiling during crime detection, crime analytics",
        "subcategories": [
            "Individual risk assessment (likelihood of offending or re-offending)",
            "Polygraphs and similar tools during interrogations",
            "Evaluation of reliability of evidence",
            "Profiling in course of detection/investigation/prosecution",
            "Crime analytics regarding natural persons",
        ],
        "keywords": ["law enforcement", "police", "crime", "evidence", "polygraph", "profiling", "investigation", "prosecution", "offend"],
    },
    {
        "area": 7,
        "title": "Migration, Asylum, and Border Control Management",
        "article_ref": "Annex III, Area 7",
        "description": "AI for risk assessment/screening at borders, assisting visa/asylum applications, detecting/recognising/identifying persons in migration context",
        "subcategories": [
            "Polygraphs and similar tools for migration interviews",
            "Risk assessment (security, irregular migration, health risks)",
            "Examination of applications for asylum, visa, residence permits",
            "Detection, recognition, identification of individuals for border control",
        ],
        "keywords": ["border", "migration", "asylum", "refugee", "customs", "immigration screen", "border control"],
    },
    {
        "area": 8,
        "title": "Administration of Justice and Democratic Processes",
        "article_ref": "Annex III, Area 8",
        "description": "AI assisting judicial authorities in researching/interpreting facts and law, applying the law; AI influencing outcome of elections/referendums or voting behaviour",
        "subcategories": [
            "AI assisting judicial authority in researching and interpreting facts and law",
            "AI used to influence outcome of elections/referendums or voting behaviour",
        ],
        "keywords": ["judicial", "court", "judge", "legal decision", "sentencing", "election", "voting", "referendum", "democratic process"],
    },
]

# Articles 9-15 — Requirements for High-Risk AI Systems
COMPLIANCE_REQUIREMENTS = [
    {
        "id": "ART9",
        "article": "Article 9",
        "title": "Risk Management System",
        "description": "Establish, implement, document, and maintain a risk management system throughout the AI system's lifecycle",
        "checks": [
            "Risk management system is established and documented",
            "Risks are identified and analysed (known and reasonably foreseeable)",
            "Estimation and evaluation of risks from intended use and reasonably foreseeable misuse",
            "Risk management measures are adopted and documented",
            "Residual risk is acceptable with mitigation measures in place",
            "Testing procedures are used to identify the most appropriate risk management measures",
        ],
    },
    {
        "id": "ART10",
        "article": "Article 10",
        "title": "Data and Data Governance",
        "description": "Training, validation, and testing data sets shall be subject to appropriate data governance and management practices",
        "checks": [
            "Data governance and management practices are documented",
            "Training, validation, and testing datasets are identified and documented",
            "Data is relevant, sufficiently representative, and as free of errors as possible",
            "Appropriate statistical properties are examined (including biases)",
            "Data gaps or shortcomings are identified and addressed",
            "Personal data processing complies with GDPR (where applicable)",
        ],
    },
    {
        "id": "ART11",
        "article": "Article 11",
        "title": "Technical Documentation",
        "description": "Technical documentation per Annex IV must be drawn up before the system is placed on the market or put into service",
        "checks": [
            "Technical documentation exists and is kept up to date",
            "Documentation contains general description of the AI system",
            "Detailed description of system elements and development process",
            "Information about monitoring, functioning, and control",
            "Description of the risk management system (per Article 9)",
            "Documentation follows Annex IV structure",
        ],
    },
    {
        "id": "ART12",
        "article": "Article 12",
        "title": "Record-Keeping (Logging)",
        "description": "High-risk AI systems shall technically allow for automatic recording of events (logs) throughout the system's lifetime",
        "checks": [
            "Automatic logging capability is implemented",
            "Logs cover the period of intended use as appropriate",
            "Logs enable traceability of the AI system's functioning",
            "Logs enable monitoring of the operation (per Article 26)",
            "Logging facilitates post-market monitoring (per Article 72)",
            "Log retention period is documented and appropriate",
        ],
    },
    {
        "id": "ART13",
        "article": "Article 13",
        "title": "Transparency and Provision of Information to Deployers",
        "description": "High-risk AI systems shall be designed and developed to ensure their operation is sufficiently transparent for deployers to interpret output and use it appropriately",
        "checks": [
            "Instructions for use accompany the AI system",
            "Instructions include identity and contact details of the provider",
            "Characteristics, capabilities, and limitations of performance are described",
            "Intended purpose and any preconditions for use are specified",
            "Human oversight measures are described (per Article 14)",
            "Expected lifetime, maintenance, and update requirements are specified",
            "Computational and hardware resource requirements are documented",
        ],
    },
    {
        "id": "ART14",
        "article": "Article 14",
        "title": "Human Oversight",
        "description": "High-risk AI systems shall be designed to allow effective human oversight during the period of use",
        "checks": [
            "Human oversight measures are identified and built into the system (or as external measures)",
            "System enables individuals assigned oversight to understand capabilities and limitations",
            "Human overseer can correctly interpret output",
            "Human overseer can decide not to use the system or override output",
            "Human overseer can intervene or interrupt the system (stop button or similar)",
            "Automation bias risks are addressed",
        ],
    },
    {
        "id": "ART15",
        "article": "Article 15",
        "title": "Accuracy, Robustness, and Cybersecurity",
        "description": "High-risk AI systems shall be designed to achieve an appropriate level of accuracy, robustness, and cybersecurity",
        "checks": [
            "Accuracy levels are declared and documented in instructions for use",
            "Accuracy metrics appropriate for the intended purpose are used",
            "System is resilient to errors, faults, and inconsistencies",
            "Technical redundancy solutions are in place (where appropriate, including backup/fail-safe plans)",
            "System is resilient to adversarial attacks (data poisoning, model manipulation, adversarial examples)",
            "Cybersecurity measures protect against unauthorised access and manipulation",
        ],
    },
]

# Annex IV — Technical Documentation Structure
ANNEX_IV_SECTIONS = [
    {"section": 1, "title": "General Description of the AI System", "items": [
        "Intended purpose",
        "Name of the provider and other relevant identifying information",
        "Version/date of the system and previous versions",
        "How the AI system interacts with hardware or software not part of the system itself",
        "Versions of relevant software or firmware and any requirement related to version updates",
        "Description of all forms in which the system is placed on the market or put into service",
        "Description of the hardware on which the system is intended to run",
        "Where the system is a component of a product: photographs or illustrations of the product",
        "Description of the user interface provided to the deployer",
    ]},
    {"section": 2, "title": "Detailed Description of Elements and Development Process", "items": [
        "Methods and steps performed for development, including use of pre-trained systems or third-party tools",
        "Design specifications: general logic and algorithms; key design choices and rationale; classification choices; what the system is designed to optimise and relevance of parameters; description of expected output",
        "Description of system architecture explaining how software components build on or feed into each other",
        "Computational resources used (including hardware, cloud, etc.)",
        "Description of data requirements (datasheets, data collection methodology, scope, characteristics)",
        "Assessment of human oversight measures needed (per Article 14)",
        "Pre-determined changes to the system and its performance",
    ]},
    {"section": 3, "title": "Monitoring, Functioning, and Control", "items": [
        "Description of the capabilities and limitations of the AI system (degrees and range of accuracy)",
        "Reasonably foreseeable unintended outcomes and sources of risk (health, safety, fundamental rights)",
        "Human oversight measures",
        "Specifications on input data",
        "Where applicable, information enabling deployers to interpret AI system output",
    ]},
    {"section": 4, "title": "Appropriateness of Performance Metrics", "items": [
        "Description of the metrics used to measure accuracy, robustness, and compliance with other requirements",
        "Description of the testing and validation approaches and methodologies",
        "The expected level of performance (declarations of conformity)",
    ]},
    {"section": 5, "title": "Risk Management System (per Article 9)", "items": [
        "Description of the risk management system (Article 9)",
        "Description of choices made during and after development to minimise risk",
    ]},
    {"section": 6, "title": "Changes Throughout the Lifecycle", "items": [
        "Description of pre-determined changes",
        "Description of data governance and management practices (Article 10), including data collection, origin, scope",
    ]},
    {"section": 7, "title": "EU Declaration of Conformity", "items": [
        "Reference to the EU declaration of conformity (Article 47)",
    ]},
    {"section": 8, "title": "Post-Market Monitoring System", "items": [
        "Description of the post-market monitoring system (Article 72)",
    ]},
]

# Key Timeline Dates
EU_AI_ACT_TIMELINE = [
    {"date": "2024-08-01", "event": "EU AI Act entered into force (Regulation (EU) 2024/1689 published in Official Journal)", "article": "Article 113"},
    {"date": "2025-02-02", "event": "Prohibited AI practices (Article 5) become enforceable; AI literacy obligations (Article 4) apply", "article": "Articles 4, 5"},
    {"date": "2025-08-02", "event": "Rules for General-Purpose AI (GPAI) models apply (Chapter V); notified bodies designated; governance framework operational", "article": "Articles 51-56, Chapter VII"},
    {"date": "2026-08-02", "event": "Full enforcement of all provisions for high-risk AI systems (including Annex III); obligations on providers, deployers, importers, distributors", "article": "Articles 6-49, Annex III"},
    {"date": "2027-08-02", "event": "Obligations for high-risk AI systems that are safety components of products under Union harmonisation legislation (Annex I)", "article": "Annex I, Article 6(1)"},
    {"date": "2030-08-02", "event": "Existing high-risk AI systems used by public authorities must comply (transitional provision)", "article": "Article 111(2)"},
]

# Penalty Tiers — Article 99
PENALTY_TIERS = {
    "prohibited": {
        "max_fine_eur": 35_000_000,
        "turnover_pct": 7,
        "article": "Article 99(3)",
        "description": "Violations of prohibited AI practices (Article 5)",
    },
    "high_risk_obligations": {
        "max_fine_eur": 15_000_000,
        "turnover_pct": 3,
        "article": "Article 99(4)",
        "description": "Non-compliance with any requirements or obligations under the Regulation (other than Article 5)",
    },
    "incorrect_information": {
        "max_fine_eur": 7_500_000,
        "turnover_pct": 1,
        "article": "Article 99(5)",
        "description": "Supplying incorrect, incomplete, or misleading information to notified bodies or national authorities",
    },
}


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "EU AI Act Compliance",
    instructions="By MEOK AI Labs — The only MCP server that automates EU AI Act compliance checking. Risk classification, 42-point audit, documentation, penalties, deadlines."
)


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    """Return matched keywords found in text (case-insensitive)."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


# ---------------------------------------------------------------------------
# Tool 1: classify_ai_risk
# ---------------------------------------------------------------------------


# ── Multi-Jurisdiction Support ────────────────────────────────
JURISDICTIONS = {
    "eu": {"name": "European Union", "framework": "EU AI Act (Regulation 2024/1689)", "enforcement": "August 2, 2026", "penalty_max": "EUR 35M or 7% global turnover"},
    "uk": {"name": "United Kingdom", "framework": "UK AI Act (expected mid-2026)", "enforcement": "TBD — legislation pending", "penalty_max": "TBD"},
    "canada": {"name": "Canada", "framework": "AIDA (Artificial Intelligence and Data Act)", "enforcement": "Expected 2026", "penalty_max": "CAD 25M or 5% global revenue"},
    "singapore": {"name": "Singapore", "framework": "AI Governance Framework + Agentic AI", "enforcement": "Voluntary (mandatory for financial services)", "penalty_max": "Sector-specific"},
    "us_nist": {"name": "United States (NIST)", "framework": "NIST AI RMF 1.0", "enforcement": "Voluntary (mandatory for federal agencies)", "penalty_max": "N/A (framework, not law)"},
}

@mcp.tool()
def classify_ai_risk(
    description: str,
    caller: str = "anonymous",
    api_key: str = "") -> str:
    """Classify an AI system's risk level under the EU AI Act.

    Takes a description of an AI system and returns its risk classification:
    prohibited, high-risk, limited-risk, or minimal-risk — per Article 5
    (prohibited practices), Article 6 + Annex III (high-risk), Articles 50/52
    (limited risk: transparency obligations), or minimal risk.

    Includes all 8 Annex III high-risk areas and all Article 5 prohibited practices.

    Args:
        description: A description of the AI system, its purpose, data used, and deployment context.
        caller: Identifier for rate limiting.
        tier: "free" (10 calls/day) or "pro" (unlimited, $29/mo).
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    limit_err = _check_rate_limit(caller, tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    result = {
        "classification": "minimal",
        "confidence": "low",
        "prohibited_matches": [],
        "high_risk_matches": [],
        "limited_risk_triggers": [],
        "analysis": "",
        "regulation": "Regulation (EU) 2024/1689",
        "meok_labs": "https://meok.ai",
    }

    # Check prohibited practices (Article 5)
    for practice in PROHIBITED_PRACTICES:
        matches = _match_keywords(description, practice["keywords"])
        if matches:
            result["prohibited_matches"].append({
                "practice_id": practice["id"],
                "article": practice["article"],
                "description": practice["description"],
                "matched_keywords": matches,
            })

    if result["prohibited_matches"]:
        result["classification"] = "prohibited"
        result["confidence"] = "high" if len(result["prohibited_matches"]) >= 2 else "medium"
        result["analysis"] = (
            f"WARNING: This AI system matches {len(result['prohibited_matches'])} prohibited practice(s) "
            f"under Article 5. Prohibited AI systems may not be placed on the market, put into service, "
            f"or used in the EU. Penalties: up to EUR 35 million or 7% of global annual turnover "
            f"(Article 99(3)). Enforcement date: 2 February 2025."
        )
        return result

    # Check high-risk (Annex III)
    for area in ANNEX_III_HIGH_RISK:
        matches = _match_keywords(description, area["keywords"])
        if matches:
            result["high_risk_matches"].append({
                "area": area["area"],
                "title": area["title"],
                "article_ref": area["article_ref"],
                "description": area["description"],
                "subcategories": area["subcategories"],
                "matched_keywords": matches,
            })

    if result["high_risk_matches"]:
        result["classification"] = "high-risk"
        result["confidence"] = "high" if len(result["high_risk_matches"]) >= 2 else "medium"
        areas_str = ", ".join(f"Area {m['area']} ({m['title']})" for m in result["high_risk_matches"])
        result["analysis"] = (
            f"This AI system is classified as HIGH-RISK under Annex III, matching: {areas_str}. "
            f"High-risk systems must comply with Articles 9-15 (risk management, data governance, "
            f"technical documentation, logging, transparency, human oversight, accuracy/robustness/cybersecurity). "
            f"A conformity assessment is required before placing on the market. "
            f"Full enforcement: 2 August 2026."
        )
        return result

    # Check limited risk (transparency obligations — Article 50)
    limited_keywords = [
        "chatbot", "chat bot", "conversational ai", "virtual assistant",
        "deepfake", "synthetic media", "generated image", "generated video",
        "generated text", "emotion recognition", "biometric categori",
        "generative ai", "foundation model", "large language model", "llm",
    ]
    limited_matches = _match_keywords(description, limited_keywords)
    if limited_matches:
        result["classification"] = "limited-risk"
        result["confidence"] = "medium"
        result["limited_risk_triggers"] = limited_matches
        result["analysis"] = (
            f"This AI system falls under LIMITED-RISK with transparency obligations (Article 50). "
            f"Matched triggers: {', '.join(limited_matches)}. "
            f"Requirements: (1) Persons interacting with AI must be informed they are interacting with AI, "
            f"(2) AI-generated/manipulated content must be marked as such, "
            f"(3) Deployers of emotion recognition/biometric categorisation must inform persons. "
            f"GPAI model providers have additional obligations under Articles 51-56."
        )
        return result

    # Minimal risk
    result["classification"] = "minimal"
    result["confidence"] = "low"
    result["analysis"] = (
        "Based on the provided description, this AI system appears to be MINIMAL RISK. "
        "No specific regulatory obligations under the EU AI Act, though voluntary codes of "
        "conduct are encouraged (Article 95). Providers may voluntarily apply high-risk "
        "requirements. Note: classification confidence is low — provide more detail about "
        "the system's purpose, data usage, and deployment context for a more accurate assessment."
    )
    return result


# ---------------------------------------------------------------------------
# Tool 2: check_compliance
# ---------------------------------------------------------------------------
@mcp.tool()
def check_compliance(
    system_name: str,
    purpose: str,
    data_types: str,
    decision_scope: str,
    has_risk_management: bool = False,
    has_data_governance: bool = False,
    has_technical_docs: bool = False,
    has_logging: bool = False,
    has_transparency_info: bool = False,
    has_human_oversight: bool = False,
    has_accuracy_testing: bool = False,
    caller: str = "anonymous",
    api_key: str = "") -> str:
    """Run an EU AI Act compliance check against Articles 9-15 requirements.

    Takes system details and current compliance posture, returns a detailed
    checklist with pass/fail/unknown for each requirement under Articles 9-15
    (the core obligations for high-risk AI systems).

    Args:
        system_name: Name of the AI system being assessed.
        purpose: Description of the system's intended purpose and use context.
        data_types: Types of data processed (e.g., "personal data, biometric data, health records").
        decision_scope: What decisions the system makes or assists with (e.g., "loan approvals, hiring recommendations").
        has_risk_management: Whether a documented risk management system exists (Article 9).
        has_data_governance: Whether data governance practices are in place (Article 10).
        has_technical_docs: Whether Annex IV technical documentation exists (Article 11).
        has_logging: Whether automatic event logging is implemented (Article 12).
        has_transparency_info: Whether transparency/instructions for use exist (Article 13).
        has_human_oversight: Whether human oversight measures are built in (Article 14).
        has_accuracy_testing: Whether accuracy, robustness, and cybersecurity are tested (Article 15).
        caller: Identifier for rate limiting.
        tier: "free" (10 calls/day) or "pro" (unlimited, $29/mo).
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    limit_err = _check_rate_limit(caller, tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    # First classify to determine if high-risk
    classification_context = f"{purpose} {data_types} {decision_scope}"
    is_high_risk = False
    matched_areas = []
    for area in ANNEX_III_HIGH_RISK:
        if _match_keywords(classification_context, area["keywords"]):
            is_high_risk = True
            matched_areas.append(f"Area {area['area']}: {area['title']}")

    is_prohibited = False
    for practice in PROHIBITED_PRACTICES:
        if _match_keywords(classification_context, practice["keywords"]):
            is_prohibited = True

    # Map booleans to articles
    compliance_inputs = {
        "ART9": has_risk_management,
        "ART10": has_data_governance,
        "ART11": has_technical_docs,
        "ART12": has_logging,
        "ART13": has_transparency_info,
        "ART14": has_human_oversight,
        "ART15": has_accuracy_testing,
    }

    # Build checklist
    checklist = []
    total_checks = 0
    passed = 0
    failed = 0
    unknown = 0

    for req in COMPLIANCE_REQUIREMENTS:
        art_id = req["id"]
        has_it = compliance_inputs.get(art_id, False)

        checks_results = []
        for check_desc in req["checks"]:
            total_checks += 1
            if has_it:
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1
            checks_results.append({"check": check_desc, "status": status})

        checklist.append({
            "article": req["article"],
            "title": req["title"],
            "description": req["description"],
            "overall_status": "PASS" if has_it else "FAIL",
            "checks": checks_results,
        })

    # GDPR check based on data types
    gdpr_relevant = any(kw in data_types.lower() for kw in [
        "personal", "biometric", "health", "genetic", "ethnic", "racial",
        "political", "religious", "trade union", "sex life", "sexual orientation",
    ])

    # Special data categories (GDPR Article 9)
    special_categories = any(kw in data_types.lower() for kw in [
        "biometric", "health", "genetic", "ethnic", "racial", "political",
        "religious", "trade union", "sex life", "sexual orientation",
    ])

    score = (passed / total_checks * 100) if total_checks > 0 else 0

    result = {
        "system_name": system_name,
        "assessment_date": datetime.now().isoformat(),
        "risk_classification": "prohibited" if is_prohibited else ("high-risk" if is_high_risk else "potentially-high-risk"),
        "matched_annex_iii_areas": matched_areas,
        "compliance_score": f"{score:.1f}%",
        "summary": {
            "total_checks": total_checks,
            "passed": passed,
            "failed": failed,
            "unknown": unknown,
        },
        "gdpr_relevant": gdpr_relevant,
        "special_category_data": special_categories,
        "gdpr_note": (
            "WARNING: System processes special category data under GDPR Article 9. "
            "Explicit consent or other lawful basis required. Data Protection Impact Assessment (DPIA) "
            "likely mandatory under GDPR Article 35."
        ) if special_categories else (
            "System processes personal data — ensure GDPR compliance (Article 10(5) of the AI Act)."
        ) if gdpr_relevant else "No personal data identified in declared data types.",
        "checklist": checklist,
        "recommendation": (
            "CRITICAL: System may involve prohibited practices. Cease development/deployment immediately "
            "and seek legal review."
        ) if is_prohibited else (
            f"System scores {score:.1f}% compliance. "
            + (f"URGENT: {failed} requirement areas need attention before the system can be placed on the market. "
               if failed > 0 else "All declared requirements are met. Proceed to conformity assessment. ")
            + "Full enforcement deadline: 2 August 2026."
        ),
        "regulation": "Regulation (EU) 2024/1689",
        "meok_labs": "https://meok.ai",
    }

    return result


# ---------------------------------------------------------------------------
# Tool 3: generate_documentation
# ---------------------------------------------------------------------------
@mcp.tool()
def generate_documentation(
    system_name: str,
    provider_name: str,
    provider_contact: str,
    version: str,
    intended_purpose: str,
    description: str,
    data_description: str,
    architecture_description: str,
    performance_metrics: str = "",
    risk_management_description: str = "",
    human_oversight_description: str = "",
    caller: str = "anonymous",
    api_key: str = "") -> str:
    """Generate Article 11 / Annex IV compliant technical documentation template.

    Produces a complete markdown template following the Annex IV structure of the
    EU AI Act. Fill in the bracketed sections with your specific information.

    Args:
        system_name: Name of the AI system.
        provider_name: Legal name of the AI system provider.
        provider_contact: Provider contact details (address, email, phone).
        version: System version number/identifier.
        intended_purpose: Clear description of the system's intended purpose.
        description: General description of what the system does.
        data_description: Description of training/validation/testing data used.
        architecture_description: Description of system architecture and algorithms.
        performance_metrics: Known accuracy/performance metrics (if available).
        risk_management_description: Description of risk management measures (if available).
        human_oversight_description: Description of human oversight measures (if available).
        caller: Identifier for rate limiting.
        tier: "free" (10 calls/day) or "pro" (unlimited, $29/mo).
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    limit_err = _check_rate_limit(caller, tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    date_str = datetime.now().strftime("%Y-%m-%d")

    doc = f"""# Technical Documentation — EU AI Act Annex IV
## {system_name}

**Provider:** {provider_name}
**Contact:** {provider_contact}
**Version:** {version}
**Document Date:** {date_str}
**Regulation:** Regulation (EU) 2024/1689 — Article 11, Annex IV
**Generated by:** MEOK AI Labs EU AI Act Compliance Server (https://meok.ai)

---

## 1. General Description of the AI System (Annex IV, Section 1)

### 1.1 Intended Purpose
{intended_purpose}

### 1.2 Provider Information
- **Provider Name:** {provider_name}
- **Contact Details:** {provider_contact}
- **System Version:** {version}
- **Date of this version:** {date_str}
- **Previous versions:** [List previous versions and dates]

### 1.3 System Description
{description}

### 1.4 Interaction with External Hardware/Software
[Describe how the AI system interacts with hardware or software that is not part of the AI system itself, including APIs, data feeds, external services]

### 1.5 Software/Firmware Requirements
[List relevant software and firmware versions, plus any version update requirements]

### 1.6 Forms of Market Placement
[Describe all forms in which the system is placed on the market or put into service: SaaS, on-premise, embedded, API, etc.]

### 1.7 Hardware Requirements
[Describe the hardware on which the AI system is intended to run, including computational requirements]

### 1.8 User Interface
[Describe the user interface provided to the deployer, including screenshots or diagrams]

---

## 2. Detailed Description of Elements and Development Process (Annex IV, Section 2)

### 2.1 Development Methods and Steps
[Describe the methods and steps performed for the development of the AI system, including any use of pre-trained systems or third-party tools/components]

### 2.2 Design Specifications

#### 2.2.1 General Logic and Algorithms
{architecture_description}

#### 2.2.2 Key Design Choices and Rationale
[Document key design choices including algorithmic approach, model architecture, training methodology, and the rationale for each decision]

#### 2.2.3 Classification and Optimisation Approach
[Describe what the system is designed to optimise for, the relevance of different parameters, and classification methodology]

#### 2.2.4 Expected Output and Interpretation
[Describe the expected output of the system and how it should be interpreted]

### 2.3 System Architecture
[Provide detailed system architecture diagram and explanation of how software components build on or feed into each other]

### 2.4 Computational Resources
[Document all computational resources used in development, training, and deployment — including hardware specifications, cloud services, GPU/TPU usage]

### 2.5 Data Requirements and Documentation

#### 2.5.1 Data Description
{data_description}

#### 2.5.2 Data Collection Methodology
[Describe how data was collected, including sources, timeframes, and sampling approaches]

#### 2.5.3 Data Characteristics
[Document scope, size, format, and key statistical properties of datasets]

#### 2.5.4 Bias Assessment
[Document assessment of biases in training data and mitigation measures applied]

### 2.6 Human Oversight Assessment (per Article 14)
{human_oversight_description if human_oversight_description else "[Describe the human oversight measures needed, as assessed under Article 14. Include how humans can intervene, override, or stop the system.]"}

### 2.7 Pre-determined Changes
[Document any pre-determined changes to the system and its performance that have been assessed at the time of the initial conformity assessment]

---

## 3. Monitoring, Functioning, and Control (Annex IV, Section 3)

### 3.1 Capabilities and Limitations
{performance_metrics if performance_metrics else "[Document the capabilities and limitations of the AI system, including degrees and range of accuracy for specific groups/contexts]"}

### 3.2 Foreseeable Unintended Outcomes and Risk Sources
[Identify reasonably foreseeable unintended outcomes and sources of risk to health, safety, and fundamental rights]

### 3.3 Human Oversight Measures
{human_oversight_description if human_oversight_description else "[Detail the specific human oversight measures built into or alongside the system]"}

### 3.4 Input Data Specifications
[Specify the input data requirements and expected data formats]

### 3.5 Output Interpretation Guidance
[Provide information enabling deployers to correctly interpret the AI system's output]

---

## 4. Appropriateness of Performance Metrics (Annex IV, Section 4)

### 4.1 Metrics Used
{performance_metrics if performance_metrics else "[List all metrics used to measure accuracy, robustness, and compliance with other requirements set out in Article 15]"}

### 4.2 Testing and Validation Methodology
[Describe the testing and validation approaches and methodologies used, including information about the test data used and its main characteristics, metrics used to measure accuracy/robustness and any other relevant requirement]

### 4.3 Performance Declarations
[Document the expected level of performance and any declarations of conformity]

---

## 5. Risk Management System — Article 9 (Annex IV, Section 5)

### 5.1 Risk Management System Description
{risk_management_description if risk_management_description else "[Describe the risk management system as required by Article 9, including: identification of known and foreseeable risks, estimation of risks from intended use and foreseeable misuse, evaluation of risks, adoption of mitigation measures]"}

### 5.2 Development and Post-Development Risk Minimisation
[Document choices made during and after development to minimise risk, including testing procedures and results]

---

## 6. Changes Throughout the Lifecycle (Annex IV, Section 6)

### 6.1 Pre-determined Changes
[Document all pre-determined changes to the system throughout its lifecycle]

### 6.2 Data Governance and Management Practices (Article 10)
[Describe data governance and management practices, including data collection, data origin, and data scope]

---

## 7. EU Declaration of Conformity — Article 47 (Annex IV, Section 7)

[Reference to the EU declaration of conformity as required by Article 47. This section should be completed after conformity assessment.]

- **Conformity Assessment Body (if applicable):** [Name and notified body number]
- **Conformity Assessment Procedure:** [Self-assessment per Article 43(1) / Third-party assessment per Article 43(2)]
- **Declaration Reference Number:** [To be assigned]

---

## 8. Post-Market Monitoring System — Article 72 (Annex IV, Section 8)

[Describe the post-market monitoring system established pursuant to Article 72, including: monitoring methodology, data collection from deployers, incident reporting procedures, periodic review schedule]

---

## Document Control

| Field | Value |
|-------|-------|
| Document Owner | {provider_name} |
| Classification | [Internal/Confidential/Public] |
| Review Cycle | [Annually/Upon significant change] |
| Next Review | [Date] |
| Approval Authority | [Name and role] |

---

*This template was generated by the MEOK AI Labs EU AI Act Compliance MCP Server.
It follows the structure required by Annex IV of Regulation (EU) 2024/1689.
All bracketed sections must be completed with system-specific information.
This template does not constitute legal advice — consult qualified legal counsel.*

*MEOK AI Labs | https://meok.ai*
"""

    return {
        "document_format": "markdown",
        "template": doc,
        "sections_requiring_completion": [
            "1.4 Interaction with External Hardware/Software",
            "1.5 Software/Firmware Requirements",
            "1.6 Forms of Market Placement",
            "1.7 Hardware Requirements",
            "1.8 User Interface",
            "2.1 Development Methods and Steps",
            "2.2.2 Key Design Choices and Rationale",
            "2.2.3 Classification and Optimisation Approach",
            "2.2.4 Expected Output and Interpretation",
            "2.3 System Architecture",
            "2.4 Computational Resources",
            "2.5.2 Data Collection Methodology",
            "2.5.3 Data Characteristics",
            "2.5.4 Bias Assessment",
            "2.7 Pre-determined Changes",
            "3.2 Foreseeable Unintended Outcomes",
            "3.4 Input Data Specifications",
            "4.2 Testing and Validation Methodology",
            "4.3 Performance Declarations",
            "6.1 Pre-determined Changes",
            "6.2 Data Governance",
            "7. EU Declaration of Conformity",
            "8. Post-Market Monitoring System",
        ],
        "compliance_note": "Complete all bracketed sections before submission. Article 11(1) requires documentation to be drawn up before the system is placed on the market.",
        "meok_labs": "https://meok.ai",
    }


# ---------------------------------------------------------------------------
# Tool 4: assess_penalties
# ---------------------------------------------------------------------------
@mcp.tool()
def assess_penalties(
    violation_type: str,
    annual_global_turnover_eur: float = 0,
    is_sme: bool = False,
    caller: str = "anonymous",
    api_key: str = "") -> str:
    """Calculate potential EU AI Act penalties for a given violation type.

    Returns the applicable fine range per Article 99, considering company size
    and the type of violation (prohibited practices, high-risk non-compliance,
    or providing incorrect information).

    Args:
        violation_type: Type of violation — one of "prohibited" (Article 5 violations),
            "high_risk_obligations" (Articles 9-15 and other requirements),
            or "incorrect_information" (misleading info to authorities).
        annual_global_turnover_eur: Company's annual global turnover in EUR.
            Used to calculate turnover-based penalties.
        is_sme: Whether the company qualifies as an SME (Small/Medium Enterprise).
            SMEs and startups may benefit from proportionate penalties per Article 99(6).
        caller: Identifier for rate limiting.
        tier: "free" (10 calls/day) or "pro" (unlimited, $29/mo).
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    limit_err = _check_rate_limit(caller, tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    if violation_type not in PENALTY_TIERS:
        return {
            "error": "invalid_violation_type",
            "message": f"Valid types: {', '.join(PENALTY_TIERS.keys())}",
            "violation_types": {
                "prohibited": "Article 5 violations (subliminal manipulation, exploitation, social scoring, etc.)",
                "high_risk_obligations": "Non-compliance with Articles 9-15, registration, conformity assessment, etc.",
                "incorrect_information": "Supplying incorrect/misleading information to notified bodies or authorities",
            },
        }

    tier_info = PENALTY_TIERS[violation_type]
    turnover_fine = (annual_global_turnover_eur * tier_info["turnover_pct"] / 100) if annual_global_turnover_eur > 0 else 0
    max_fine = max(tier_info["max_fine_eur"], turnover_fine)
    applicable_fine = turnover_fine if turnover_fine > tier_info["max_fine_eur"] else tier_info["max_fine_eur"]

    result = {
        "violation_type": violation_type,
        "legal_basis": tier_info["article"],
        "violation_description": tier_info["description"],
        "penalty_calculation": {
            "fixed_maximum_eur": f"{tier_info['max_fine_eur']:,.0f}",
            "turnover_percentage": f"{tier_info['turnover_pct']}%",
            "company_turnover_eur": f"{annual_global_turnover_eur:,.0f}" if annual_global_turnover_eur > 0 else "Not provided",
            "turnover_based_fine_eur": f"{turnover_fine:,.0f}" if turnover_fine > 0 else "N/A",
            "applicable_maximum_eur": f"{applicable_fine:,.0f}",
            "calculation_method": "Whichever is higher: fixed amount or percentage of global annual turnover of the preceding financial year",
        },
        "sme_considerations": (
            "As an SME/startup, proportionate administrative fines apply per Article 99(6). "
            "National authorities should take into account the economic viability of the company. "
            "The European AI Office will issue guidelines on proportionate penalties for SMEs."
        ) if is_sme else (
            "Standard penalty regime applies. Consider requesting SME status assessment if applicable."
        ),
        "aggravating_factors": [
            "Intentional or negligent nature of the infringement (Article 99(7)(a))",
            "Previous infringements by the same operator (Article 99(7)(c))",
            "Nature, gravity, and duration of the infringement (Article 99(7)(b))",
            "Size, annual turnover, and market share of the operator (Article 99(7)(d))",
            "Degree of harm suffered (Article 99(7)(e))",
        ],
        "mitigating_factors": [
            "Steps taken to mitigate the damage suffered (Article 99(7)(f))",
            "Degree of cooperation with national authorities (Article 99(7)(g))",
            "Degree of responsibility taking into account technical measures implemented (Article 99(7)(h))",
            "Manner in which the infringement became known to the authority (Article 99(7)(i))",
        ],
        "additional_notes": [
            "Member States may set rules on penalties for other infringements (Article 99(1))",
            "Penalties for Union institutions/bodies: up to EUR 1.5M (prohibited), EUR 750K (other), EUR 375K (incorrect info) per Article 99(8)",
            "Article 99(2): penalties shall be effective, proportionate, and dissuasive",
        ],
        "regulation": "Regulation (EU) 2024/1689, Article 99",
        "meok_labs": "https://meok.ai",
    }

    return result


# ---------------------------------------------------------------------------
# Tool 5: get_timeline
# ---------------------------------------------------------------------------
@mcp.tool()
def get_timeline(
    caller: str = "anonymous",
    api_key: str = "") -> str:
    """Get key EU AI Act implementation dates and deadlines.

    Returns all major enforcement milestones from entry into force through
    full implementation, including which articles/requirements become
    applicable at each date.

    Args:
        caller: Identifier for rate limiting.
        tier: "free" (10 calls/day) or "pro" (unlimited, $29/mo).
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    limit_err = _check_rate_limit(caller, tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    today = datetime.now().date()
    timeline_with_status = []
    for entry in EU_AI_ACT_TIMELINE:
        deadline = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        days_diff = (deadline - today).days
        if days_diff < 0:
            status = f"IN EFFECT (since {entry['date']}, {abs(days_diff)} days ago)"
        elif days_diff == 0:
            status = "EFFECTIVE TODAY"
        else:
            status = f"UPCOMING in {days_diff} days ({days_diff // 30} months)"

        timeline_with_status.append({
            "date": entry["date"],
            "event": entry["event"],
            "article_reference": entry["article"],
            "status": status,
        })

    result = {
        "regulation": "Regulation (EU) 2024/1689 (EU AI Act)",
        "official_journal": "OJ L, 2024/1689, 12.7.2024",
        "assessment_date": today.isoformat(),
        "timeline": timeline_with_status,
        "key_resources": {
            "eur_lex": "https://eur-lex.europa.eu/eli/reg/2024/1689",
            "ai_office": "https://digital-strategy.ec.europa.eu/en/policies/european-approach-artificial-intelligence",
            "ai_pact": "https://digital-strategy.ec.europa.eu/en/policies/ai-pact",
        },
        "notes": [
            "The EU AI Act (Regulation (EU) 2024/1689) was published in the Official Journal on 12 July 2024.",
            "It entered into force on 1 August 2024 (20 days after publication, per Article 113).",
            "Implementation follows a phased approach over 36 months.",
            "The AI Pact encourages voluntary early adoption of AI Act requirements.",
            "Delegated and implementing acts will further specify requirements — monitor the AI Office for updates.",
        ],
        "meok_labs": "https://meok.ai",
    }

    return result


# ---------------------------------------------------------------------------
# Tool 6: audit_report
# ---------------------------------------------------------------------------
@mcp.tool()
def audit_report(
    system_name: str,
    provider_name: str,
    provider_contact: str,
    version: str,
    purpose: str,
    description: str,
    data_types: str,
    decision_scope: str,
    architecture_description: str,
    has_risk_management: bool = False,
    has_data_governance: bool = False,
    has_technical_docs: bool = False,
    has_logging: bool = False,
    has_transparency_info: bool = False,
    has_human_oversight: bool = False,
    has_accuracy_testing: bool = False,
    annual_global_turnover_eur: float = 0,
    is_sme: bool = False,
    caller: str = "anonymous",
    tier: str = "free", api_key: str = "") -> str:
    """Generate a complete EU AI Act audit report.

    Runs classification, compliance check, documentation generation, and
    penalty assessment — then combines everything into a comprehensive
    markdown audit report. This is the all-in-one tool for compliance officers.

    Args:
        system_name: Name of the AI system.
        provider_name: Legal name of the AI system provider.
        provider_contact: Provider contact details.
        version: System version number.
        purpose: System's intended purpose and use context.
        description: General description of the system.
        data_types: Types of data processed.
        decision_scope: What decisions the system makes or assists with.
        architecture_description: Description of system architecture.
        has_risk_management: Whether risk management system exists.
        has_data_governance: Whether data governance practices exist.
        has_technical_docs: Whether technical documentation exists.
        has_logging: Whether automatic logging is implemented.
        has_transparency_info: Whether transparency info exists.
        has_human_oversight: Whether human oversight measures exist.
        has_accuracy_testing: Whether accuracy/robustness testing is done.
        annual_global_turnover_eur: Annual global turnover in EUR.
        is_sme: Whether the company is an SME.
        caller: Identifier for rate limiting.
        tier: "free" (10 calls/day) or "pro" (unlimited, $29/mo).
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    limit_err = _check_rate_limit(caller, tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    # Run sub-analyses (bypass rate limiting for internal calls)
    classification_raw = json.loads(classify_ai_risk(f"{purpose} {description} {data_types} {decision_scope}", caller, "pro"))
    compliance_raw = json.loads(check_compliance(
        system_name, purpose, data_types, decision_scope,
        has_risk_management, has_data_governance, has_technical_docs,
        has_logging, has_transparency_info, has_human_oversight,
        has_accuracy_testing, caller, "pro"))

    risk_level = classification_raw.get("classification", "unknown")

    # Determine applicable penalty tier
    penalty_type = "prohibited" if risk_level == "prohibited" else "high_risk_obligations"
    penalty_raw = json.loads(assess_penalties(penalty_type, annual_global_turnover_eur, is_sme, caller, "pro"))
    timeline_raw = json.loads(get_timeline(caller, "pro"))

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # Find next deadline
    today = datetime.now().date()
    next_deadline = None
    for entry in EU_AI_ACT_TIMELINE:
        d = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        if d > today:
            next_deadline = entry
            break

    # Build compliance summary table
    compliance_rows = ""
    for item in compliance_raw.get("checklist", []):
        status_icon = "PASS" if item["overall_status"] == "PASS" else "**FAIL**"
        compliance_rows += f"| {item['article']} | {item['title']} | {status_icon} |\n"

    # Build the report
    report = f"""# EU AI Act Compliance Audit Report

**System:** {system_name}
**Provider:** {provider_name} ({provider_contact})
**Version:** {version}
**Audit Date:** {date_str}
**Audited by:** MEOK AI Labs EU AI Act Compliance Server

---

## Executive Summary

| Field | Value |
|-------|-------|
| **Risk Classification** | **{risk_level.upper()}** |
| **Classification Confidence** | {classification_raw.get('confidence', 'N/A')} |
| **Compliance Score** | {compliance_raw.get('compliance_score', 'N/A')} |
| **Checks Passed** | {compliance_raw.get('summary', {}).get('passed', 0)} / {compliance_raw.get('summary', {}).get('total_checks', 0)} |
| **GDPR Relevant** | {'Yes' if compliance_raw.get('gdpr_relevant') else 'No'} |
| **Special Category Data** | {'Yes - DPIA likely required' if compliance_raw.get('special_category_data') else 'No'} |
| **Maximum Penalty Exposure** | EUR {penalty_raw.get('penalty_calculation', {}).get('applicable_maximum_eur', 'N/A')} |
| **Next Enforcement Deadline** | {next_deadline['date'] + ' — ' + next_deadline['event'] if next_deadline else 'All deadlines passed'} |

---

## 1. Risk Classification (Article 6, Annex III)

**Classification: {risk_level.upper()}**

{classification_raw.get('analysis', '')}

"""

    if classification_raw.get("prohibited_matches"):
        report += "### Prohibited Practice Matches (Article 5)\n\n"
        for match in classification_raw["prohibited_matches"]:
            report += f"- **{match['article']}**: {match['description']}\n"
            report += f"  - Matched keywords: {', '.join(match['matched_keywords'])}\n"
        report += "\n"

    if classification_raw.get("high_risk_matches"):
        report += "### High-Risk Area Matches (Annex III)\n\n"
        for match in classification_raw["high_risk_matches"]:
            report += f"- **Area {match['area']}: {match['title']}** ({match['article_ref']})\n"
            report += f"  - {match['description']}\n"
            for sub in match.get("subcategories", []):
                report += f"    - {sub}\n"
        report += "\n"

    if classification_raw.get("limited_risk_triggers"):
        report += f"### Limited Risk Transparency Triggers\n\n"
        report += f"Matched: {', '.join(classification_raw['limited_risk_triggers'])}\n\n"

    report += f"""---

## 2. Compliance Checklist (Articles 9-15)

| Article | Requirement | Status |
|---------|-------------|--------|
{compliance_rows}

### Detailed Findings

"""

    for item in compliance_raw.get("checklist", []):
        report += f"#### {item['article']} — {item['title']}\n\n"
        report += f"*{item['description']}*\n\n"
        for check in item["checks"]:
            icon = "PASS" if check["status"] == "PASS" else "FAIL"
            report += f"- [{icon}] {check['check']}\n"
        report += "\n"

    report += f"""---

## 3. Penalty Exposure (Article 99)

| Parameter | Value |
|-----------|-------|
| **Violation Type** | {penalty_raw.get('violation_type', 'N/A')} |
| **Legal Basis** | {penalty_raw.get('legal_basis', 'N/A')} |
| **Fixed Maximum** | EUR {penalty_raw.get('penalty_calculation', {}).get('fixed_maximum_eur', 'N/A')} |
| **Turnover Percentage** | {penalty_raw.get('penalty_calculation', {}).get('turnover_percentage', 'N/A')} |
| **Company Turnover** | EUR {penalty_raw.get('penalty_calculation', {}).get('company_turnover_eur', 'N/A')} |
| **Applicable Maximum** | EUR {penalty_raw.get('penalty_calculation', {}).get('applicable_maximum_eur', 'N/A')} |
| **SME Status** | {'Yes — proportionate penalties apply' if is_sme else 'No'} |

### Aggravating Factors to Monitor
"""

    for factor in penalty_raw.get("aggravating_factors", []):
        report += f"- {factor}\n"

    report += "\n### Mitigating Factors to Leverage\n"
    for factor in penalty_raw.get("mitigating_factors", []):
        report += f"- {factor}\n"

    report += f"""

---

## 4. Implementation Timeline

"""

    for entry in timeline_raw.get("timeline", []):
        report += f"- **{entry['date']}** — {entry['event']} [{entry['status']}]\n"
        report += f"  - Reference: {entry['article_reference']}\n"

    report += f"""

---

## 5. Recommendations

"""

    if risk_level == "prohibited":
        report += """### CRITICAL — Prohibited System

1. **IMMEDIATELY** cease development and deployment of this AI system
2. Seek urgent legal counsel on Article 5 compliance
3. Assess whether any exceptions apply (e.g., law enforcement exceptions under Article 5(1)(h))
4. Document all steps taken for regulatory cooperation
5. Consider system redesign to fall outside prohibited categories

"""
    elif risk_level == "high-risk":
        failed_articles = [item for item in compliance_raw.get("checklist", []) if item["overall_status"] == "FAIL"]
        if failed_articles:
            report += "### Priority Actions (Non-Compliant Requirements)\n\n"
            for i, item in enumerate(failed_articles, 1):
                report += f"{i}. **{item['article']} — {item['title']}**: Establish and document compliance measures\n"
            report += "\n"

        report += """### General High-Risk Compliance Actions

1. Establish or review the Risk Management System (Article 9) — continuous lifecycle process
2. Implement data governance per Article 10, including bias assessments
3. Complete Annex IV technical documentation (use the `generate_documentation` tool)
4. Deploy automatic event logging (Article 12)
5. Prepare instructions for use and transparency information (Article 13)
6. Design and document human oversight measures (Article 14)
7. Conduct accuracy, robustness, and cybersecurity testing (Article 15)
8. Register the system in the EU database (Article 49)
9. Plan conformity assessment procedure (Article 43)
10. Establish post-market monitoring system (Article 72)

"""
    else:
        report += """### Minimal/Limited Risk Actions

1. Consider voluntary adoption of high-risk requirements (Article 95 codes of conduct)
2. Ensure transparency obligations are met if applicable (Article 50)
3. Monitor regulatory developments — classification may change with delegated acts
4. Consider joining the AI Pact for early adoption recognition

"""

    if compliance_raw.get("gdpr_relevant"):
        report += """### GDPR Alignment

- Ensure lawful basis for personal data processing
- Conduct Data Protection Impact Assessment (DPIA) if processing special category data
- Review data minimisation and purpose limitation compliance
- Verify data subject rights mechanisms are in place

"""

    report += f"""---

## 6. Technical Documentation Status

{"Technical documentation exists — verify it follows Annex IV structure." if has_technical_docs else "**ACTION REQUIRED**: No technical documentation declared. Use the `generate_documentation` tool to create an Annex IV-compliant template."}

---

*This audit report was generated by the MEOK AI Labs EU AI Act Compliance MCP Server.*
*It is based on Regulation (EU) 2024/1689 as published in the Official Journal.*
*This report does not constitute legal advice. Consult qualified legal counsel for definitive compliance guidance.*

**MEOK AI Labs** | [meok.ai](https://meok.ai) | The only MCP server for EU AI Act compliance
"""

    return {
        "format": "markdown",
        "report": report,
        "risk_classification": risk_level,
        "compliance_score": compliance_raw.get("compliance_score"),
        "max_penalty_eur": penalty_raw.get("penalty_calculation", {}).get("applicable_maximum_eur"),
        "failed_requirements": [
            item["article"] for item in compliance_raw.get("checklist", [])
            if item["overall_status"] == "FAIL"
        ],
        "meok_labs": "https://meok.ai",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@mcp.tool()
def multi_jurisdiction_map(
    article: str,
    jurisdictions: list = None,
    api_key: str = "") -> str:
    """Map EU AI Act articles to equivalent requirements in UK, Singapore, Canada, and US NIST."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    limit_err = _check_rate_limit("anonymous", tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}
    jurisdictions = jurisdictions or ["uk", "singapore", "canada", "us_nist"]
    MAPPINGS = {
        "Article 5": {"uk": "UK AI Act prohibited practices", "singapore": "MAS FEAT principles — fairness", "canada": "AIDA prohibited uses", "us_nist": "NIST AI RMF Govern 1.1"},
        "Article 6": {"uk": "UK AI Act high-risk classification", "singapore": "IMDA PDPC guidelines", "canada": "AIDA high-impact systems", "us_nist": "NIST AI RMF Map 1.2"},
        "Article 9": {"uk": "UK AI Act risk management", "singapore": "Veritas fairness assessment", "canada": "AIDA risk mitigation", "us_nist": "NIST AI RMF Manage 2.1"},
        "Article 14": {"uk": "UK AI Act human oversight", "singapore": "AI Governance Framework — human-in-the-loop", "canada": "AIDA human oversight", "us_nist": "NIST AI RMF Govern 3.1"},
    }
    result = MAPPINGS.get(article, {})
    filtered = {k: v for k, v in result.items() if k in jurisdictions}
    return {"eu_ai_act_article": article, "mappings": filtered, "jurisdictions_queried": jurisdictions}

if __name__ == "__main__":
    mcp.run()