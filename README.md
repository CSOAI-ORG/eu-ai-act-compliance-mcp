# EU AI Act Compliance MCP Server
**By MEOK AI Labs** | [meok.ai](https://meok.ai)

The only MCP server that automates EU AI Act compliance checking.

---

## What It Does

Automates compliance workflows for **Regulation (EU) 2024/1689** (the EU AI Act) — the world's first comprehensive AI regulation. Built for compliance officers, legal teams, and AI developers who need to classify, audit, and document their AI systems.

### 6 Tools

| Tool | Description |
|------|-------------|
| `classify_ai_risk` | Classify any AI system as prohibited/high-risk/limited/minimal per Article 5 + Annex III |
| `check_compliance` | Run Articles 9-15 compliance checklist with pass/fail for each requirement |
| `generate_documentation` | Generate Annex IV technical documentation template (markdown) |
| `assess_penalties` | Calculate penalty exposure (up to EUR 35M / 7% turnover) per Article 99 |
| `get_timeline` | Get all enforcement deadlines with live countdown |
| `audit_report` | Complete audit combining classification + compliance + penalties + timeline |

### What's Covered

- **All 8 Article 5 prohibited practices** (subliminal manipulation, vulnerability exploitation, social scoring, criminal profiling, facial scraping, emotion recognition at work/school, biometric categorisation, real-time remote biometric ID)
- **All 8 Annex III high-risk areas** (biometrics, critical infrastructure, education, employment, essential services, law enforcement, migration/border, justice/democracy)
- **Articles 9-15 requirements** (risk management, data governance, technical documentation, logging, transparency, human oversight, accuracy/robustness/cybersecurity)
- **Article 99 penalty calculations** with aggravating/mitigating factors
- **GDPR cross-references** for personal and special category data
- **Full Annex IV documentation template** (8 sections, all required fields)

## Quick Start

### Install

```bash
pip install mcp httpx
```

### Run

```bash
python server.py
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "eu-ai-act-compliance": {
      "command": "python",
      "args": ["/path/to/eu-ai-act-compliance-mcp/server.py"]
    }
  }
}
```

## Usage Examples

### Classify an AI System

```
Use classify_ai_risk to assess: "Our system uses facial recognition cameras
in retail stores to identify repeat shoplifters and flag them to security staff."
```

### Run a Compliance Audit

```
Use audit_report for our system:
- Name: SmartHire AI
- Provider: Acme Corp
- Purpose: Screening job applications and ranking candidates
- Data types: CVs, personal data, employment history
- Decision scope: Shortlisting candidates for interview
```

### Generate Documentation

```
Use generate_documentation for our credit scoring model that evaluates
loan applications using financial history and demographic data.
```

## Pricing

| Tier | Rate Limit | Price |
|------|-----------|-------|
| **Free** | 10 calls/day | $0 |
| **Pro** | Unlimited | $29/mo |

Upgrade at [meok.ai/mcp/eu-ai-act/pro](https://meok.ai/mcp/eu-ai-act/pro)

## Key Dates

| Date | Milestone |
|------|-----------|
| 1 Aug 2024 | EU AI Act entered into force |
| **2 Feb 2025** | **Prohibited practices enforceable** |
| **2 Aug 2025** | **GPAI rules apply** |
| **2 Aug 2026** | **Full enforcement (high-risk systems)** |
| 2 Aug 2027 | Annex I product safety systems |
| 2 Aug 2030 | Public authority legacy systems |

## Legal Disclaimer

This tool provides automated compliance analysis based on the published text of Regulation (EU) 2024/1689. It does not constitute legal advice. Always consult qualified legal counsel for definitive compliance guidance. MEOK AI Labs is not responsible for regulatory decisions made based on this tool's output.

## License

MIT

---

**MEOK AI Labs** | [meok.ai](https://meok.ai) | Building the infrastructure for responsible AI
