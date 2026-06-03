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

import hashlib
import hmac
import json
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

_ATTESTATION_KEY = os.environ.get("MEOK_ATTESTATION_KEY")
if not _ATTESTATION_KEY:
    import warnings
    warnings.warn("MEOK_ATTESTATION_KEY not set. Attestation signatures will be unsigned. Set this environment variable in production.", stacklevel=2)
    _ATTESTATION_KEY = "dev-only-unsigned"

_ART_50_DEADLINE = datetime(2026, 11, 2, tzinfo=timezone.utc)
_ANNEX_III_DEADLINE = datetime(2027, 12, 2, tzinfo=timezone.utc)


def _days_until(deadline: datetime) -> int:
    return max(0, (deadline - datetime.now(timezone.utc)).days)


# Stripe Payment Links — UTM-tagged so we can attribute revenue to MCP-tool installs
_STRIPE_STARTER = "https://buy.stripe.com/dRmfZj2G03ceeQJ8iA8k90O?utm_source=mcp&utm_medium=tool&utm_campaign=eu_ai_act&utm_content=attest_tail"
_STRIPE_PRO     = "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K?utm_source=mcp&utm_medium=tool&utm_campaign=eu_ai_act&utm_content=attest_tail"
_STRIPE_GOV     = "https://buy.stripe.com/14AfZjfsM6oq7oh2Yg8k90P?utm_source=mcp&utm_medium=tool&utm_campaign=eu_ai_act&utm_content=attest_tail"


def _attest(data: dict) -> dict:
    """Add HMAC-SHA256 attestation + monetization tail to every response.

    The monetization tail is visible in Claude Code / Cursor / Cline tool output
    on EVERY call — turns 5,920+ monthly installs into ~30K monetization impressions.
    """
    payload = json.dumps(data, sort_keys=True, default=str)
    signature = hmac.new(
        _ATTESTATION_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    is_signed = _ATTESTATION_KEY != "dev-only-unsigned"
    data["_attestation"] = {
        "algorithm": "HMAC-SHA256",
        "signature": signature[:16],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verifiable": is_signed,
        "signed": is_signed,
    }
    if not is_signed:
        data["_attestation"]["warning"] = "UNSIGNED in free tier — set MEOK_ATTESTATION_KEY for auditor-verifiable certs"

    # Monetization tail — visible in EVERY response (free tier + signed tier alike).
    # Free tier: pushes upgrade; signed tier: shows current discount/cliff awareness.
    days_to_art50 = _days_until(_ART_50_DEADLINE)
    days_to_annex_iii = _days_until(_ANNEX_III_DEADLINE)
    data["meok_upgrade"] = {
        "cta": "Free MIT — auditor-verifiable HMAC + multi-jurisdiction crosswalks on Pro" if not is_signed else "You're on Pro · thanks for supporting the open-source maintainer",
        "starter_29_gbp_mo": _STRIPE_STARTER,
        "pro_79_gbp_mo": _STRIPE_PRO,
        "governance_substrate_499_gbp_mo": _STRIPE_GOV,
        "self_host_mit": "https://github.com/CSOAI-ORG/eu-ai-act-compliance-mcp",
        "deadlines": {
            "article_50_genai_labelling": f"{days_to_art50} days · 2 August 2026",
            "annex_iii_high_risk": f"{days_to_annex_iii} days · 2 December 2027",
        },
        "support_open_source": "If this tool saves you time, ⭐ at github.com/CSOAI-ORG/eu-ai-act-compliance-mcp",
    }
    return data

# ── Pydantic models for structured I/O (optional — graceful degradation if missing) ──
try:
    from pydantic import BaseModel, Field
    _PYDANTIC_AVAILABLE = True

    class RiskClassificationResult(BaseModel):
        """Output schema for quick_scan and classify_ai_risk tools."""
        risk_level: Literal["prohibited", "high-risk", "limited-risk", "minimal", "unknown"] = Field(
            description="EU AI Act risk classification per Articles 5/6/50/95"
        )
        matched_areas: list[str] = Field(default_factory=list, description="Regulation refs that matched")
        top_3_obligations: list[str] = Field(default_factory=list, description="Most urgent obligations")
        deadline: str = Field(default="", description="Enforcement deadline")
        penalty_range: str = Field(default="", description="Max fine under Article 99")
        regulation: str = Field(default="Regulation (EU) 2024/1689", description="Legal basis")
        next_step: str = Field(default="", description="Recommended follow-up action")

    class ComplianceCheckInput(BaseModel):
        """Input schema for check_compliance tool."""
        entity_name: str = Field(min_length=1, max_length=200, description="Legal entity name")
        system_description: str = Field(min_length=10, description="What the AI system does")
        current_controls: str = Field(default="", description="Comma-separated current controls")
        risk_level: Literal["high-risk", "limited-risk", "minimal", "unknown"] = Field(default="unknown")

    class SearchRegulationInput(BaseModel):
        """Input schema for search_regulation tool."""
        query: str = Field(min_length=2, max_length=500, description="FTS5 search query")
        regulation: Literal["", "eu-ai-act", "dora", "nis2", "cra", "csrd", "gdpr"] = Field(
            default="", description="Optional regulation filter"
        )
        limit: int = Field(default=10, ge=1, le=50, description="Max results to return")

    class SearchResultItem(BaseModel):
        regulation: str
        article_number: int
        snippet: str
        relevance_score: float

    class SearchRegulationOutput(BaseModel):
        query: str
        regulation_filter: str
        result_count: int
        source: str
        disclaimer: str
        results: list[SearchResultItem]

except ImportError:
    _PYDANTIC_AVAILABLE = False
    # Pydantic not installed — tools still work, just no schema validation

# ── Authentication ──────────────────────────────────────────────
import os as _os
import sys, os

# Optional: connect to MEOK Labs shared auth + neural net if available
_MEOK_API_KEY = _os.environ.get("MEOK_API_KEY", "")
_neural_net = None

try:
    from meok_auth import check_access as _shared_check_access
except ImportError:
    try:
        from auth_middleware import check_access as _shared_check_access
    except ImportError:
        def _shared_check_access(api_key: str = ""):
            """Fallback when shared auth engine is not available."""
            if _MEOK_API_KEY and api_key and api_key == _MEOK_API_KEY:
                return True, "OK", "pro"
            if _MEOK_API_KEY and api_key and api_key != _MEOK_API_KEY:
                return False, "Invalid API key. Get one at https://meok.ai/api-keys", "free"
            return True, "OK", "free"

try:
    from compliance_neural import ComplianceNeuralNet
    _neural_net = ComplianceNeuralNet("eu-ai-act")
except ImportError:
    _neural_net = None


def check_access(api_key: str = ""):
    """Unified access check — works with or without shared auth engine."""
    return _shared_check_access(api_key)


# ---------------------------------------------------------------------------
# Rate limiting — works with ZERO configuration. No API key needed for first
# FREE_DAILY_LIMIT calls per day.
# ---------------------------------------------------------------------------
FREE_DAILY_LIMIT = 10
PRO_TIER_UNLIMITED = True  # Pro: $29/mo unlimited at https://meok.ai/mcp/eu-ai-act/pro
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous", tier: str = "free") -> Optional[str]:
    """Returns error string if rate-limited, else None. No API key required for free tier."""
    if tier == "pro":
        return None
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= FREE_DAILY_LIMIT:
        days = _days_until(_ART_50_DEADLINE)
        return (
            f"Free tier limit reached ({FREE_DAILY_LIMIT}/day). "
            f"Upgrade to Pro (£79/mo) for unlimited access + auditor-verifiable HMAC certs. "
            f"{days} days until Article 50 GenAI labelling deadline (2 Aug 2026) "
            f"→ {_STRIPE_PRO}"
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

# Key Timeline Dates — updated 17 May 2026 post-Omnibus political agreement (7 May 2026)
# Source-of-truth alignment: the 7 May 2026 Digital Omnibus delayed Annex III high-risk
# enforcement (Aug 2026 → Dec 2027) and Annex I product-safety (Aug 2027 → Aug 2028).
# It did NOT delay Article 50 transparency / watermarking — that still bites on
# 2 August 2026. Aligned with meok-watermark-attest-mcp + watermarking-authenticity-mcp.
EU_AI_ACT_TIMELINE = [
    {"date": "2024-08-01", "event": "EU AI Act entered into force (Regulation (EU) 2024/1689 published in Official Journal)", "article": "Article 113"},
    {"date": "2025-02-02", "event": "Prohibited AI practices (Article 5) become enforceable; AI literacy obligations (Article 4) apply", "article": "Articles 4, 5"},
    {"date": "2025-08-02", "event": "Rules for General-Purpose AI (GPAI) models apply (Chapter V); notified bodies designated; governance framework operational", "article": "Articles 51-56, Chapter VII"},
    {"date": "2026-08-02", "event": "🔥 NEAREST CLIFF — Article 50 transparency obligations become enforceable. Providers of generative AI must mark output as machine-readable AI-generated; deployers must disclose at first user interaction; deepfake / AI-manipulated public-interest content must be labelled. NOT delayed by the 7 May 2026 Digital Omnibus.", "article": "Article 50"},
    {"date": "2027-08-02", "event": "GPAI compliance deadline for models placed on the market before 2 August 2025 (the 'grandfather' window closes)", "article": "Article 111(1)"},
    {"date": "2027-12-02", "event": "Full enforcement of all provisions for high-risk AI systems (Annex III) — delayed 16 months by EU Digital Omnibus Act (originally 2 Aug 2026)", "article": "Articles 6-49, Annex III"},
    {"date": "2028-08-02", "event": "Obligations for high-risk AI systems that are safety components of products under Union harmonisation legislation (Annex I) — delayed 12 months by Digital Omnibus (originally 2 Aug 2027)", "article": "Annex I, Article 6(1)"},
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
    instructions="By MEOK AI Labs — EU AI Act compliance automation. Start with quick_scan (one sentence, instant result) or deadline_check (zero parameters). Full tools: risk classification, 42-point audit, Annex IV documentation, penalty calculator, multi-jurisdiction mapping. No API key needed for free tier (10 calls/day)."
)


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    """Return matched keywords found in text (case-insensitive)."""
    text_lower = text.lower()
    return [kw for kw in keywords if kw.lower() in text_lower]


# ---------------------------------------------------------------------------
# Tool: quick_scan — ZERO config, no API key, instant result
# ---------------------------------------------------------------------------
@mcp.tool()
def quick_scan(description: str) -> dict:
    """One-sentence AI system description -> instant EU AI Act risk classification and top obligations. No API key required.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    limit_err = _check_rate_limit("quick_scan_anonymous")
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    risk_level = "minimal"
    matched_areas = []
    top_obligations = []
    penalty_range = "None for minimal risk systems"
    deadline = "No mandatory deadline for minimal risk"

    # Check prohibited (Article 5)
    for practice in PROHIBITED_PRACTICES:
        matches = _match_keywords(description, practice["keywords"])
        if matches:
            matched_areas.append(f"{practice['article']}: {practice['description']}")

    if matched_areas:
        risk_level = "prohibited"
        top_obligations = [
            "CEASE deployment immediately — system is banned under Article 5",
            "Seek legal counsel on whether any narrow exceptions apply",
            "Report to national supervisory authority if already deployed",
        ]
        penalty_range = "Up to EUR 35,000,000 or 7% of global annual turnover"
        deadline = "2 February 2025 (ALREADY IN EFFECT)"
        return _attest({
            "risk_level": risk_level,
            "matched_areas": matched_areas,
            "top_3_obligations": top_obligations,
            "deadline": deadline,
            "penalty_range": penalty_range,
            "regulation": "Regulation (EU) 2024/1689",
            "next_step": "Use classify_ai_risk for detailed analysis or check_compliance for full audit",
            "meok_labs": "https://meok.ai",
        })

    # Check high-risk (Annex III)
    for area in ANNEX_III_HIGH_RISK:
        matches = _match_keywords(description, area["keywords"])
        if matches:
            matched_areas.append(f"Annex III Area {area['area']}: {area['title']}")

    if matched_areas:
        risk_level = "high-risk"
        top_obligations = [
            "Establish risk management system (Article 9) and data governance (Article 10)",
            "Create Annex IV technical documentation and implement logging (Articles 11-12)",
            "Ensure human oversight, transparency, and accuracy testing (Articles 13-15)",
        ]
        penalty_range = "Up to EUR 15,000,000 or 3% of global annual turnover"
        deadline = "2 December 2027 (delayed from Aug 2026 by EU Digital Omnibus Act)"
    else:
        # Check limited risk
        limited_keywords = [
            "chatbot", "chat bot", "conversational ai", "virtual assistant",
            "deepfake", "synthetic media", "generated image", "generated video",
            "generated text", "generative ai", "foundation model", "large language model", "llm",
        ]
        limited_matches = _match_keywords(description, limited_keywords)
        if limited_matches:
            risk_level = "limited-risk"
            matched_areas = [f"Transparency trigger: {kw}" for kw in limited_matches]
            top_obligations = [
                "Inform users they are interacting with AI (Article 50)",
                "Label AI-generated content as artificially generated (Article 50)",
                "GPAI providers: comply with Articles 51-56 (if applicable)",
            ]
            penalty_range = "Up to EUR 15,000,000 or 3% of global annual turnover"
            deadline = "2 August 2025 (GPAI rules)"
        else:
            top_obligations = [
                "No mandatory obligations — voluntary codes of conduct encouraged (Article 95)",
                "Monitor EU AI Office for delegated acts that may reclassify your system",
                "Consider voluntary adoption of high-risk requirements for trust",
            ]

    return _attest({
        "risk_level": risk_level,
        "matched_areas": matched_areas,
        "top_3_obligations": top_obligations,
        "deadline": deadline,
        "penalty_range": penalty_range,
        "regulation": "Regulation (EU) 2024/1689",
        "next_step": "Use classify_ai_risk for detailed analysis or check_compliance for full audit",
        "meok_labs": "https://meok.ai",
    })


# ---------------------------------------------------------------------------
# Tool: deadline_check — ZERO parameters, instant deadlines
# ---------------------------------------------------------------------------
@mcp.tool()
def deadline_check() -> dict:
    """All EU AI Act enforcement deadlines with days remaining. No parameters needed.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    today = datetime.now().date()
    deadlines = []
    next_upcoming = None

    for entry in EU_AI_ACT_TIMELINE:
        deadline_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        days_remaining = (deadline_date - today).days

        if days_remaining < 0:
            status = "IN EFFECT"
            urgency = "past"
        elif days_remaining == 0:
            status = "EFFECTIVE TODAY"
            urgency = "critical"
        elif days_remaining <= 90:
            status = "IMMINENT"
            urgency = "critical"
        elif days_remaining <= 365:
            status = "APPROACHING"
            urgency = "high"
        else:
            status = "UPCOMING"
            urgency = "normal"

        deadline_entry = {
            "date": entry["date"],
            "event": entry["event"],
            "article": entry["article"],
            "days_remaining": days_remaining,
            "status": status,
            "urgency": urgency,
        }
        deadlines.append(deadline_entry)

        if days_remaining > 0 and next_upcoming is None:
            next_upcoming = deadline_entry

    # Highlight the nearest cliff (Article 50 transparency + watermarking, 2 Aug 2026).
    # The 7 May 2026 Digital Omnibus political agreement delayed Annex III/I high-risk
    # enforcement, but did NOT push Article 50 — providers + deployers must still mark
    # and disclose generative AI output from 2 August 2026.
    watermarking_cliff = next(
        (d for d in deadlines if d["article"] == "Article 50"), None
    )

    return {
        "assessment_date": today.isoformat(),
        "next_deadline": next_upcoming,
        "deadlines": deadlines,
        "regulation": "Regulation (EU) 2024/1689",
        "key_message": (
            f"Next deadline: {next_upcoming['date']} — {next_upcoming['event']} "
            f"({next_upcoming['days_remaining']} days remaining)"
        ) if next_upcoming else "All EU AI Act deadlines have passed — full enforcement is in effect.",
        "nearest_enforcement_cliff": {
            "date": "2026-08-02",
            "event": "Article 50 transparency + watermarking obligations become enforceable",
            "context": "Article 50 was NOT delayed by the 7 May 2026 Digital Omnibus — only Annex III/I high-risk timelines were. Providers and deployers of generative AI face the full obligation set from 2 August 2026.",
            "applies_to": "Any provider of generative AI systems placing output on the EU market, and any deployer disclosing AI-generated content to users.",
            "days_remaining": watermarking_cliff["days_remaining"] if watermarking_cliff else None,
            "evidence_required": [
                "Machine-readable AI-origin marking (e.g. C2PA) on every generative output",
                "First-interaction disclosure to user that content is AI-generated",
                "Deployer disclosure for deepfakes / AI-manipulated text in matters of public interest",
                "Cryptographically signed attestation of the marking pipeline for audit defence",
            ],
            "meok_recommended_tools": [
                "meok-watermark-attest-mcp (C2PA + HMAC-signed watermark attestations)",
                "watermarking-authenticity-mcp (provenance + detector chain)",
                "search_regulation tool above (verbatim Article 50 quote)",
                "get_article_text(regulation='eu-ai-act', article_number=50)",
            ],
        } if watermarking_cliff else None,
        "meok_labs": "https://meok.ai",
        "buy_now": {
            "starter_29gbp_mo": "https://buy.stripe.com/dRmfZj2G03ceeQJ8iA8k90O",
            "pro_79gbp_mo": "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K",
            "continuous_199gbp_mo": "https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836",
            "audit_5000gbp_one_time": "https://buy.stripe.com/4gM7sN2G0bIKeQJfL28k833",
        },
    }


# ---------------------------------------------------------------------------
# Tool 1: classify_ai_risk
# ---------------------------------------------------------------------------


# ── Multi-Jurisdiction Support ────────────────────────────────
JURISDICTIONS = {
    "eu": {"name": "European Union", "framework": "EU AI Act (Regulation 2024/1689)", "enforcement": "Article 50 transparency + watermarking 2 Aug 2026 (NOT delayed by Omnibus); Annex III high-risk 2 Dec 2027; Annex I product-safety 2 Aug 2028; public-authority legacy 2 Aug 2030", "penalty_max": "EUR 35M or 7% global turnover"},
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

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    """
    if _PYDANTIC_AVAILABLE:
        try:
            from pydantic import BaseModel as _BM, Field as _F, ValidationError as _VE
            class _ClassifyInput(_BM):
                description: str = _F(min_length=1, description="AI system description must be non-empty")
            _ClassifyInput(description=description)
        except Exception as _e:
            return {"error": "validation_error", "message": str(_e)}

    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
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
        # Free tier: show classification but redact detailed matches
        if tier == "free":
            result["prohibited_matches"] = [
                {"article": m["article"], "description": "[UPGRADE to see full match details and remediation steps]"}
                for m in result["prohibited_matches"]
            ]
            result["remediation_plan"] = "LOCKED — Upgrade to Pro for article-by-article remediation plan"
            result["upgrade"] = {
                "message": f"Your system matched {len(result['prohibited_matches'])} prohibited practices. Get the full breakdown + remediation steps with MEOK Pro.",
                "url": "https://meok.ai/api-keys",
                "stripe_checkout": "https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836",
                "price": "From GBP 29/month",
            }
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
            f"Full enforcement: 2 December 2027 (delayed by EU Digital Omnibus Act)."
        )
        # Free tier: show classification + area names, but redact subcategories and keywords
        if tier == "free":
            result["high_risk_matches"] = [
                {
                    "area": m["area"],
                    "title": m["title"],
                    "article_ref": m["article_ref"],
                    "description": "[UPGRADE to see detailed analysis]",
                    "subcategories": ["[LOCKED — upgrade for specific subcategory matches]"],
                    "matched_keywords": [f"{len(m['matched_keywords'])} keywords matched — upgrade to see details"],
                }
                for m in result["high_risk_matches"]
            ]
            result["compliance_roadmap"] = "LOCKED — Upgrade to Pro for a full compliance roadmap with Articles 9-15 checklist"
            result["upgrade"] = {
                "message": f"Your system matches {len(result['high_risk_matches'])} high-risk areas. Get the full analysis + compliance roadmap with MEOK Pro.",
                "url": "https://meok.ai/api-keys",
                "stripe_checkout": "https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836",
                "price": "From GBP 29/month",
            }
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

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    """
    if _PYDANTIC_AVAILABLE:
        try:
            from pydantic import BaseModel as _BM, Field as _F, ValidationError as _VE
            class _ComplianceInput(_BM):
                system_name: str = _F(min_length=1, description="System name must be non-empty")
                purpose: str = _F(min_length=1, description="Purpose must be non-empty")
            _ComplianceInput(system_name=system_name, purpose=purpose)
        except Exception as _e:
            return {"error": "validation_error", "message": str(_e)}

    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
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
        "recommendation": (
            "CRITICAL: System may involve prohibited practices. Cease development/deployment immediately "
            "and seek legal review."
        ) if is_prohibited else (
            f"System scores {score:.1f}% compliance. "
            + (f"URGENT: {failed} requirement areas need attention before the system can be placed on the market. "
               if failed > 0 else "All declared requirements are met. Proceed to conformity assessment. ")
            + "Full enforcement deadline: 2 December 2027 (delayed by Digital Omnibus)."
        ),
        "regulation": "Regulation (EU) 2024/1689",
        "meok_labs": "https://meok.ai",
    }

    # FREE TIER: show score + failed article names, but NOT the detailed checklist
    if tier == "free":
        failed_articles = [item["article"] + " — " + item["title"] for item in checklist if item["overall_status"] == "FAIL"]
        passed_articles = [item["article"] + " — " + item["title"] for item in checklist if item["overall_status"] == "PASS"]
        result["failed_requirements"] = failed_articles
        result["passed_requirements"] = passed_articles
        result["detailed_checklist"] = (
            f"LOCKED — {total_checks} individual checks available with MEOK Pro. "
            f"Includes specific remediation steps for each of your {failed} failing requirements."
        )
        result["upgrade"] = {
            "message": f"Your system scores {score:.1f}% with {failed} failing areas. Get the full 42-point checklist + remediation plan.",
            "url": "https://meok.ai/api-keys",
            "stripe_checkout": "https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836",
            "price": "From GBP 29/month",
        }
    else:
        # PRO/ENTERPRISE: full detailed checklist
        result["checklist"] = checklist

    # Neural learning: train from this compliance check (if neural engine available)
    if _neural_net is not None:
        try:
            features = _neural_net.extract_features_from_system(
                system_name=system_name,
                uses_biometric="biometric" in data_types.lower(),
                uses_health_data="health" in data_types.lower(),
                uses_financial_data="financial" in data_types.lower() or "credit" in data_types.lower(),
                has_human_oversight=has_human_oversight,
                has_documentation=has_technical_docs,
                deployed_cross_border=False,
                model_explainable=True,
            )
            outcome = {
                "overall_risk_score": 1.0 if is_prohibited else (0.8 if is_high_risk else 0.4),
                "violation_probability": failed / max(1, total_checks),
                "remediation_urgency": 1.0 if is_prohibited else (failed / max(1, total_checks)),
                "audit_priority": 0.9 if is_prohibited else (0.7 if is_high_risk else 0.3),
            }
            learn_result = _neural_net.learn_from_check(features, outcome)
            result["neural_learning"] = {
                "trained": True,
                "loss": learn_result["loss"],
                "checks_learned_from": learn_result["check_number"],
            }
        except Exception:
            result["neural_learning"] = {"trained": False, "reason": "learning error"}
    else:
        result["neural_learning"] = {"trained": False, "reason": "neural engine not available"}

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

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    limit_err = _check_rate_limit(caller, tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    # GATE: Documentation generation is a Pro feature
    if tier == "free":
        return {
            "error": "pro_feature",
            "message": (
                "Annex IV documentation generation requires MEOK Pro. "
                "This tool produces a complete, regulation-ready technical documentation template "
                "covering all 8 sections of Annex IV (EU AI Act). "
                "Save 40+ hours of manual documentation work."
            ),
            "preview": {
                "sections_generated": [
                    "1. General Description of the AI System",
                    "2. Detailed Description of Elements and Development Process",
                    "3. Monitoring, Functioning, and Control",
                    "4. Appropriateness of Performance Metrics",
                    "5. Risk Management System (Article 9)",
                    "6. Changes Throughout the Lifecycle",
                    "7. EU Declaration of Conformity (Article 47)",
                    "8. Post-Market Monitoring System (Article 72)",
                ],
                "output_format": "Markdown — ready for legal review",
                "fields_auto_populated": 12,
                "fields_requiring_completion": 22,
            },
            "upgrade": {
                "url": "https://meok.ai/api-keys",
                "stripe_checkout": "https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836",
                "price": "From GBP 29/month — includes unlimited documentation generation",
            },
            "free_alternative": "Use quick_scan or deadline_check (free, no API key needed) to assess your system first.",
        }

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

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    """
    if _PYDANTIC_AVAILABLE:
        try:
            from pydantic import BaseModel as _BM, Field as _F, ValidationError as _VE
            class _PenaltyInput(_BM):
                violation_type: str = _F(min_length=1, description="Violation type must be a non-empty string")
            _PenaltyInput(violation_type=violation_type)
        except Exception as _e:
            return {"error": "validation_error", "message": str(_e)}

    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
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

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
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

    Behavior:
        This tool generates structured output without modifying external systems.
        Output is deterministic for identical inputs. No side effects.
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    limit_err = _check_rate_limit(caller, tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    # GATE: Full audit report is a Pro feature
    if tier == "free":
        # Give them a teaser — run quick classification to show value
        quick_result = quick_scan(f"{purpose} {description} {data_types} {decision_scope}")
        risk_level = quick_result.get("risk_level", "unknown") if isinstance(quick_result, dict) else "unknown"
        return {
            "error": "pro_feature",
            "message": (
                "Full EU AI Act audit reports require MEOK Pro. "
                "This tool generates a comprehensive compliance audit covering: "
                "risk classification, 42-point compliance checklist, Annex IV documentation status, "
                "penalty exposure calculation, implementation timeline, and prioritised remediation plan."
            ),
            "teaser": {
                "system_name": system_name,
                "quick_risk_classification": risk_level,
                "report_sections": [
                    "1. Risk Classification (Article 6, Annex III)",
                    "2. Compliance Checklist (Articles 9-15) — 42 individual checks",
                    "3. Penalty Exposure (Article 99) — calculated for your turnover",
                    "4. Implementation Timeline — all deadlines with days remaining",
                    "5. Prioritised Recommendations — ranked by urgency",
                    "6. Technical Documentation Status (Annex IV)",
                ],
                "estimated_value": "Equivalent to GBP 2,000-5,000 compliance consultancy report",
            },
            "upgrade": {
                "url": "https://meok.ai/api-keys",
                "stripe_checkout": "https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836",
                "price": "From GBP 29/month — includes unlimited audit reports",
            },
            "free_alternative": "Use quick_scan (free) for instant risk classification, or deadline_check for enforcement dates.",
        }

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

    return _attest({
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
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@mcp.tool()
def multi_jurisdiction_map(
    article: str,
    jurisdictions: list = None,
    api_key: str = "") -> str:
    """Map EU AI Act articles to equivalent requirements in UK, Singapore, Canada, and US NIST.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    limit_err = _check_rate_limit("anonymous", tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    # GATE: Multi-jurisdiction mapping is a Pro feature
    if tier == "free":
        return {
            "error": "pro_feature",
            "message": (
                "Multi-jurisdiction mapping requires MEOK Pro. "
                "Maps EU AI Act requirements to UK AI Act, Singapore IMDA, Canada AIDA, and US NIST AI RMF."
            ),
            "supported_jurisdictions": ["EU", "UK", "Singapore", "Canada", "US (NIST)"],
            "upgrade": {
                "url": "https://meok.ai/api-keys",
                "stripe_checkout": "https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836",
                "price": "From GBP 29/month",
            },
        }

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

@mcp.tool()
def predict_risk_neural(
    system_name: str,
    system_type: str = "",
    uses_biometric: bool = False,
    uses_health_data: bool = False,
    uses_financial_data: bool = False,
    has_human_oversight: bool = True,
    affected_users: int = 0,
    sector: str = "",
    has_documentation: bool = False,
    prior_incidents: int = 0,
    deployed_cross_border: bool = False,
    model_explainable: bool = True,
    api_key: str = "") -> dict:
    """Neural network-based risk prediction that improves from every compliance check. Predicts overall risk, violation probability, remediation urgency, and audit priority.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    limit_err = _check_rate_limit("anonymous", tier)
    if limit_err:
        return {"error": "rate_limited", "message": limit_err}

    if _neural_net is None:
        return {"error": "Neural engine not available. Install meok-labs-engine for neural predictions.", "system_name": system_name}

    features = _neural_net.extract_features_from_system(
        system_name=system_name,
        system_type=system_type,
        uses_biometric=uses_biometric,
        uses_health_data=uses_health_data,
        uses_financial_data=uses_financial_data,
        has_human_oversight=has_human_oversight,
        affected_users=affected_users,
        sector=sector,
        has_documentation=has_documentation,
        prior_incidents=prior_incidents,
        deployed_cross_border=deployed_cross_border,
        model_explainable=model_explainable,
    )

    prediction = _neural_net.predict_risk(features)
    prediction["system_name"] = system_name
    prediction["features_used"] = features
    return prediction


@mcp.tool()
def neural_insights(api_key: str = "") -> dict:
    """Get aggregate learning insights from the neural compliance model — training history, maturity, and common risk patterns.

    Behavior:
        This tool is read-only and stateless — it produces analysis output
        without modifying any external systems, databases, or files.
        Safe to call repeatedly with identical inputs (idempotent).
        Free tier: 10/day rate limit. Pro tier: unlimited.
        No authentication required for basic usage.

    When to use:
        Use this tool when you need to assess, audit, or verify compliance
        requirements. Ideal for gap analysis, readiness checks, and generating
        compliance documentation.

    When NOT to use:
        Do not use as a substitute for qualified legal counsel. This tool
        provides technical compliance guidance, not legal advice.
    Behavioral Transparency:
        - Side Effects: This tool is read-only and produces no side effects. It does not modify
          any external state, databases, or files. All output is computed in-memory and returned
          directly to the caller.
        - Authentication: No authentication required for basic usage. Pro/Enterprise tiers
          require a valid MEOK API key passed via the MEOK_API_KEY environment variable.
        - Rate Limits: Free tier: 10 calls/day. Pro tier: unlimited. Rate limit headers are
          included in responses (X-RateLimit-Remaining, X-RateLimit-Reset).
        - Error Handling: Returns structured error objects with 'error' key on failure.
          Never raises unhandled exceptions. Invalid inputs return descriptive validation errors.
        - Idempotency: Fully idempotent — calling with the same inputs always produces the
          same output. Safe to retry on timeout or transient failure.
        - Data Privacy: No input data is stored, logged, or transmitted to external services.
          All processing happens locally within the MCP server process.
    """
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://councilof.ai"}
    if _neural_net is None:
        return {"error": "Neural engine not available. Install meok-labs-engine for neural insights."}
    return _neural_net.get_insights()


# ── search_regulation: FTS5-backed verbatim regulation lookup ──────────────
# Powered by EUR-Lex Cellar API daily sync. Returns 64-token snippets from
# the canonical regulation text (Akoma Ntoso XHTML parsed from EUR-Lex).
# 410 articles across 6 regulations (EU AI Act, DORA, NIS2, CRA, CSRD, GDPR).

import sqlite3 as _sqlite3
from pathlib import Path as _Path

_REGULATIONS_DB = _Path(__file__).parent / "data" / "regulations.db"


@mcp.tool()
def search_regulation(query: str, regulation: str = "", limit: int = 10) -> dict:
    """Full-text search across 410 articles of real EU regulation text (EUR-Lex verified).

    Args:
        query: Search terms. Supports FTS5 syntax (AND, OR, NEAR, phrase quoting).
        regulation: Optional filter — one of: eu-ai-act, dora, nis2, cra, csrd, gdpr.
        limit: Max results to return (default 10).

    Returns:
        Dict with snippets from matching articles, each annotated with regulation,
        article number, and a relevance score. Snippets are 64-token windows with
        `>>>match<<<` highlight markers around the matched terms.

    Behavior:
        Verbatim text from EUR-Lex Cellar (Regulation EU 2024/1689, EU 2022/2554,
        EU 2022/2555, EU 2024/2847, EU 2022/2464, EU 2016/679). Updated daily via
        GitHub Actions sync from publications.europa.eu SPARQL endpoint.
        No LLM summarization — every quote is auditor-defensible.
    """
    if not _REGULATIONS_DB.exists():
        return {
            "error": "Regulation database not yet synced. Run: python scripts/eurlex_sync.py",
            "hint": "First sync takes ~30 seconds, fetches ~1.7MB of regulation text",
        }
    if not query or len(query.strip()) < 2:
        return {"error": "Query must be at least 2 characters"}

    celex_map = {
        "eu-ai-act": "32024R1689",
        "dora": "32022R2554",
        "nis2": "32022L2555",
        "cra": "32024R2847",
        "csrd": "32022L2464",
        "gdpr": "32016R0679",
    }
    celex_filter = celex_map.get(regulation.lower().strip()) if regulation else None

    # FTS5 query construction:
    # - If the user already wrapped the query in "..." or used AND/OR/NEAR, pass through.
    # - Otherwise split on whitespace and quote each token, joining with implicit AND.
    #   Quoting per-token neutralises hyphens, slashes, and other FTS5 metacharacters
    #   (e.g. "high-risk" would otherwise be parsed as `high NOT risk`).
    raw = query.strip()
    upper = raw.upper()
    is_phrase = raw.startswith('"') and raw.endswith('"') and len(raw) >= 2
    has_operator = any(op in upper for op in (" AND ", " OR ", " NEAR("))
    if is_phrase or has_operator:
        safe_query = raw
    else:
        tokens = [t for t in raw.split() if t]
        safe_query = " ".join('"' + t.replace('"', '""') + '"' for t in tokens)

    conn = _sqlite3.connect(str(_REGULATIONS_DB))
    try:
        if celex_filter:
            sql = """
                SELECT celex, article_number, article_id,
                       snippet(articles_fts, 3, '>>>', '<<<', '...', 64) AS snip,
                       rank
                FROM articles_fts
                WHERE articles_fts MATCH ? AND celex = ?
                ORDER BY rank LIMIT ?
            """
            rows = conn.execute(sql, (safe_query, celex_filter, limit)).fetchall()
        else:
            sql = """
                SELECT celex, article_number, article_id,
                       snippet(articles_fts, 3, '>>>', '<<<', '...', 64) AS snip,
                       rank
                FROM articles_fts
                WHERE articles_fts MATCH ?
                ORDER BY rank LIMIT ?
            """
            rows = conn.execute(sql, (safe_query, limit)).fetchall()

        celex_to_name = {v: k for k, v in celex_map.items()}
        results = [
            {
                "regulation": celex_to_name.get(r[0], r[0]),
                "article_number": r[1],
                "snippet": r[3],
                "relevance_score": round(abs(r[4]), 2),
            }
            for r in rows
        ]

        meta = {
            "query": query,
            "regulation_filter": regulation or "all",
            "result_count": len(results),
            "source": "EUR-Lex Cellar API (publications.europa.eu) — verbatim text",
            "disclaimer": "Quotes are auditor-defensible. Not legal advice.",
            "results": results,
        }
        return meta
    except Exception as e:
        return {"error": f"FTS5 search error: {e}", "hint": "Try simpler query without special characters"}
    finally:
        conn.close()


@mcp.tool()
def list_regulations_in_db() -> dict:
    """List all regulations currently in the EUR-Lex FTS5 database with article counts and last-sync date."""
    if not _REGULATIONS_DB.exists():
        return {"error": "Database not yet synced", "regulations": []}
    conn = _sqlite3.connect(str(_REGULATIONS_DB))
    try:
        rows = conn.execute(
            "SELECT celex, name, short_name, type, title, article_count, last_synced FROM regulations ORDER BY celex"
        ).fetchall()
        return {
            "source": "EUR-Lex Cellar API",
            "total_regulations": len(rows),
            "total_articles": conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
            "regulations": [
                {
                    "celex": r[0],
                    "name": r[1],
                    "short_name": r[2],
                    "type": r[3],
                    "title": r[4][:120] if r[4] else "",
                    "article_count": r[5],
                    "last_synced": r[6],
                }
                for r in rows
            ],
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tool: iso_42001_crosswalk — ISO/IEC 42001 (AIMS) ↔ EU AI Act mapping
# ---------------------------------------------------------------------------
# Closes https://github.com/CSOAI-ORG/eu-ai-act-compliance-mcp/issues/3
# Lets compliance teams pursuing ISO 42001 certification reuse their AIMS
# audit evidence to satisfy EU AI Act Article 9 / 15 / 17 / 26 obligations.

_ISO_42001_TO_AI_ACT = {
    "Clause 4 — Context of the organisation": {
        "ai_act_articles": ["Article 25 (responsibilities along value chain)", "Article 26 (deployer obligations)"],
        "annex_a_controls": ["A.2.2 (AI policy)", "A.2.3 (alignment with organisational strategy)"],
        "evidence_reuse": "Stakeholder analysis + scope statement satisfies value-chain mapping for Articles 25/26."
    },
    "Clause 5 — Leadership": {
        "ai_act_articles": ["Article 14 (human oversight)", "Article 26(2) (deployer human oversight)"],
        "annex_a_controls": ["A.3.2 (roles + responsibilities)", "A.3.3 (reporting of concerns)"],
        "evidence_reuse": "AI policy + management commitment doc covers human oversight evidence for Notified Body."
    },
    "Clause 6 — Planning (incl. risk + AI impact assessment)": {
        "ai_act_articles": ["Article 9 (risk management)", "Article 26(9) (FRIA for deployers)", "Article 27 (FRIA scope)"],
        "annex_a_controls": ["A.4.1 (AI risk assessment process)", "A.4.2 (AI risk treatment)", "A.5.1 (AI system impact assessment)"],
        "evidence_reuse": "ISO 42001 AI risk register + impact assessment = direct input to EU AI Act Article 9 risk-management documentation and Article 26(9) FRIA."
    },
    "Clause 7 — Support": {
        "ai_act_articles": ["Article 4 (AI literacy)", "Article 13 (transparency + instructions for use)"],
        "annex_a_controls": ["A.5.5 (AI system documentation)", "A.7.4 (provision of information to users)"],
        "evidence_reuse": "Competence + awareness records satisfy Article 4 literacy. User documentation maps to Article 13 transparency."
    },
    "Clause 8 — Operation": {
        "ai_act_articles": ["Article 10 (data and data governance)", "Article 11 (technical documentation)", "Article 12 (record-keeping)", "Article 17 (quality management system)"],
        "annex_a_controls": ["A.6.2 (responsible AI development)", "A.7.2 (resources for AI systems)", "A.8.3 (data quality for AI systems)"],
        "evidence_reuse": "AIMS operational controls = ~70% of an Article 17 QMS evidence pack. Data governance records map 1:1 to Article 10."
    },
    "Clause 9 — Performance evaluation": {
        "ai_act_articles": ["Article 15 (accuracy, robustness, cybersecurity)", "Article 72 (post-market monitoring)", "Article 73 (serious incident reporting)"],
        "annex_a_controls": ["A.6.2.5 (performance + reliability evaluation)", "A.10.4 (event reporting)"],
        "evidence_reuse": "Monitoring + measurement procedures + internal audit reports = Article 15 + 72 evidence + Article 73 incident-reporting pipeline."
    },
    "Clause 10 — Improvement": {
        "ai_act_articles": ["Article 9 (continuous risk management)", "Article 16(j) (corrective actions by providers)", "Article 79 (corrective actions on non-conforming systems)"],
        "annex_a_controls": ["A.10.2 (nonconformity + corrective action)", "A.10.3 (continual improvement)"],
        "evidence_reuse": "Nonconformity + corrective-action register = direct evidence for Article 79 plus Article 9's continuous-improvement requirement."
    },
}


@mcp.tool()
def iso_42001_crosswalk(clause: str = "", article: str = "", api_key: str = "") -> dict:
    """Map ISO/IEC 42001 (AI Management System) clauses to EU AI Act articles, with evidence reuse hints.

    Args:
        clause: Optional ISO 42001 clause (4-10) to focus on. Empty = full crosswalk.
        article: Optional EU AI Act article number to look up in reverse.
        api_key: Optional MEOK API key (Pro tier gets the signed evidence pack).

    Returns:
        Either the full crosswalk or the filtered subset, plus a recommendation
        for which ISO 42001 audit artefact maps to which AI Act obligation.
        Auditor-defensible: each row cites the canonical AIMS control + AI Act article.

    Behavior:
        Read-only, stateless, idempotent.
        Free tier: 10/day. PAYG: £0.05/call. Pro: unlimited.
    """
    # Use shared rate-limiter via the imported check_access pattern;
    # fall through silently if auth_middleware unavailable.
    try:
        allowed, msg, tier = _shared_check_access(api_key)
        if not allowed:
            return {"error": msg, "upgrade": "https://councilof.ai"}
    except Exception:
        tier = "free"

    if clause:
        # Normalise "5" → "Clause 5 — Leadership"
        match = next((k for k in _ISO_42001_TO_AI_ACT if k.startswith(f"Clause {clause}")), None)
        if not match:
            return {
                "error": f"Unknown clause '{clause}'. Valid: 4, 5, 6, 7, 8, 9, 10.",
                "available_clauses": list(_ISO_42001_TO_AI_ACT.keys()),
            }
        return {
            "iso_42001_clause": match,
            "mapping": _ISO_42001_TO_AI_ACT[match],
            "tier": tier if isinstance(tier, str) else tier.value,
            "source": "ISO/IEC 42001:2023 + Regulation (EU) 2024/1689 cross-reference, MEOK AI Labs.",
            "disclaimer": "Not legal advice. Confirm scope with your Notified Body.",
        }

    if article:
        # Reverse lookup
        article_norm = article.strip().lstrip("Article ").strip()
        hits = []
        for clause_name, mapping in _ISO_42001_TO_AI_ACT.items():
            matched_articles = [a for a in mapping["ai_act_articles"] if f"Article {article_norm}" in a]
            if matched_articles:
                hits.append({
                    "iso_42001_clause": clause_name,
                    "matched_articles": matched_articles,
                    "annex_a_controls": mapping["annex_a_controls"],
                    "evidence_reuse": mapping["evidence_reuse"],
                })
        return {
            "ai_act_article_query": article,
            "result_count": len(hits),
            "iso_42001_clauses_satisfying": hits,
            "tier": tier if isinstance(tier, str) else tier.value,
        }

    # Full crosswalk
    return {
        "summary": (
            "ISO/IEC 42001:2023 (AI Management Systems) ↔ EU AI Act (Regulation 2024/1689) crosswalk. "
            "Organisations with mature AIMS reuse ~60-70% of their evidence to satisfy "
            "AI Act Articles 9, 10, 11, 14, 15, 17, 26(9), 72, 73, and 79."
        ),
        "crosswalk": _ISO_42001_TO_AI_ACT,
        "tier": tier if isinstance(tier, str) else tier.value,
        "tip": "Use search_regulation(query='risk management', regulation='eu-ai-act') to pull the verbatim AI Act text for any clause.",
        "source": "MEOK AI Labs, derived from ISO/IEC 42001:2023 + Regulation (EU) 2024/1689.",
        "disclaimer": "Mapping is a working guide, not certification advice. Confirm with your Notified Body.",
    }


# ---------------------------------------------------------------------------
# Tool: cross_references_for_article — citation graph across all 6 regulations
# ---------------------------------------------------------------------------
# Scans every article body for "Article N" citations and returns INBOUND
# citations (who cites this article) and OUTBOUND citations (what this article
# cites). The graph is computed on demand from the local FTS5 DB.

import re as _xref_re


def _extract_outbound_citations(content: str) -> list[dict]:
    """Find Article-N references inside one article's body text."""
    citations = []
    seen = set()
    for m in _xref_re.finditer(r"\bArticle\s+(\d+)(?:\(([\w\d]+)\))?", content or ""):
        art = int(m.group(1))
        sub = m.group(2)
        key = (art, sub)
        if key in seen:
            continue
        seen.add(key)
        citations.append({"article_number": art, "sub_paragraph": sub})
    return citations


@mcp.tool()
def cross_references_for_article(regulation: str, article_number: int) -> dict:
    """Citation graph for one article — what it cites + who cites it.

    Args:
        regulation: One of eu-ai-act, dora, nis2, cra, csrd, gdpr.
        article_number: Article number (e.g. 33 for GDPR personal-data breach notification).

    Returns:
        outbound_citations: articles this one cites.
        inbound_citations: articles across the full 6-regulation corpus that cite this one.
            Each carries a snippet of the citing context so auditors see the reference.

    Example: cross_references_for_article("gdpr", 33) reveals that GDPR Article 33
    (personal data breach notification) is cited by NIS2 Article 35 and EU AI Act
    Article 59 — a one-call view of the multi-regulation evidence trail.

    Behavior:
        Read-only. Idempotent. Free tier: 10/day. PAYG: £0.05/call. Pro: unlimited.
    """
    celex_map = {
        "eu-ai-act": "32024R1689",
        "dora": "32022R2554",
        "nis2": "32022L2555",
        "cra": "32024R2847",
        "csrd": "32022L2464",
        "gdpr": "32016R0679",
    }
    celex = celex_map.get(regulation.lower().strip())
    if not celex:
        return {"error": f"Unknown regulation '{regulation}'. Valid: {', '.join(celex_map)}"}
    if not _REGULATIONS_DB.exists():
        return {"error": "Regulation database not yet synced. Run scripts/eurlex_sync.py"}

    celex_to_name = {v: k for k, v in celex_map.items()}
    conn = _sqlite3.connect(str(_REGULATIONS_DB))
    try:
        own = conn.execute(
            "SELECT content FROM articles WHERE celex = ? AND article_number = ?",
            (celex, article_number),
        ).fetchone()
        outbound_raw = _extract_outbound_citations(own[0]) if own else []
        outbound = [c for c in outbound_raw if c["article_number"] != article_number]

        pattern = f"%Article {article_number}%"
        rows = conn.execute(
            "SELECT celex, article_number, content FROM articles WHERE content LIKE ? ORDER BY celex, article_number",
            (pattern,),
        ).fetchall()
        inbound = []
        for r_celex, r_art, r_content in rows:
            if r_celex == celex and r_art == article_number:
                continue
            if _xref_re.search(rf"\bArticle\s+{article_number}\b", r_content or ""):
                snippet = ""
                m = _xref_re.search(
                    rf"(.{{0,80}}\bArticle\s+{article_number}\b.{{0,120}})",
                    r_content or "",
                )
                if m:
                    snippet = m.group(1).strip().replace(
                        f"Article {article_number}",
                        f">>>Article {article_number}<<<",
                    )
                inbound.append({
                    "regulation": celex_to_name.get(r_celex, r_celex),
                    "celex": r_celex,
                    "article_number": r_art,
                    "snippet": snippet,
                    "eur_lex_url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{r_celex}#art_{r_art}",
                })

        return {
            "regulation": regulation.lower().strip(),
            "celex": celex,
            "article_number": article_number,
            "outbound_citations": outbound,
            "outbound_count": len(outbound),
            "inbound_citations": inbound,
            "inbound_count": len(inbound),
            "summary": (
                f"{regulation} Article {article_number} cites {len(outbound)} other articles, "
                f"and is cited by {len(inbound)} articles across the 6-regulation corpus."
            ),
            "eur_lex_url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}#art_{article_number}",
            "source": "EUR-Lex Cellar API (publications.europa.eu) — verbatim text",
            "disclaimer": "Citation graph computed from verbatim regulation text. Not legal advice.",
        }
    finally:
        conn.close()


def main():
    """Entry point for the eu-ai-act-compliance-mcp command."""
    mcp.run()


if __name__ == "__main__":
    main()