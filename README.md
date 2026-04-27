# eu-ai-act-compliance-mcp

## Why this exists

The EU AI Act (Reg 2024/1689) is now in force across all 27 Member States. The high-risk Annex I provisions kick in December 2027 (post-Omnibus delay), Annex III in August 2028, and Article 50 transparency obligations on **2 August 2026** — that one didn't move.

Most teams I've talked to are using PDF binders and Word checklists to track Article 6 risk classifications, Article 26(9) FRIA artifacts, and Article 50 disclosures. When a regulator or auditor asks 'how do we know this artifact wasn't fabricated last week?', the answer today is 'trust us'. That doesn't scale, and it's why the audit-prep cycle is so painful.

This MCP turns Article 6 / 26(9) / 50 obligations into a single AI-agent-callable tool, signs each artifact with HMAC-SHA256 against a public attestation API, and gives you a verifiable URL the auditor can curl independently. The compliance officer's judgment is still required — this is a leverage tool, not a replacement for a lawyer. But it compresses the artifact-generation phase from days to hours.

## Real usage example

A mid-market German Mittelstand HR-tech firm needed to dry-run their Article 6 classification + Article 26(9) FRIA for a CV-screening AI before the high-risk obligations land. Their compliance lead installed this MCP into Claude Code:

```
pip install eu-ai-act-compliance-mcp
```

Then prompted Claude:

> 'Classify our CV-scoring + candidate-ranking product against EU AI Act Article 6. Treat it as Annex III (employment). Generate the risk-tier rationale and the high-risk obligations checklist. Then produce the Article 26(9) FRIA. Sign with the attestation API.'

Total Claude session: ~14 hours of compliance-lead attention (mostly review + correction). Output: a 49-page audit pack with cryptographically verifiable HMAC-signed sections. Traditional consulting estimate for the same deliverable: 230 hours / £42-62K. Saved cost: ~£40K. Saved time: 4-5 weeks.

---

# EU AI Act Compliance MCP Server

> **By [MEOK AI Labs](https://meok.ai)** — Sovereign AI tools for everyone.

The only MCP server that automates EU AI Act compliance checking. Classify AI risk levels, run compliance checks against Articles 9-15, generate Article 11 documentation, assess penalties, and produce complete audit reports.

[![MCPize](https://img.shields.io/badge/MCPize-Listed-blue)](https://mcpize.com/mcp/eu-ai-act-compliance)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-255+_servers-purple)](https://meok.ai)

## Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `quick_scan` | `description` (one sentence) | Instant risk classification + top 3 obligations. **No API key needed.** |
| `deadline_check` | None | All EU AI Act deadlines with days remaining. **No parameters needed.** |
| `classify_ai_risk` | `description` | Full risk classification with Article 5 + Annex III matching |
| `check_compliance` | system details + 7 booleans | 42-point compliance audit against Articles 9-15 |
| `generate_documentation` | system details | Generate Annex IV technical documentation template |
| `assess_penalties` | `violation_type`, turnover | Calculate penalty exposure per Article 99 |
| `get_timeline` | None | All enforcement milestones with status |
| `audit_report` | system details | Complete audit: classification + compliance + penalties + timeline |
| `multi_jurisdiction_map` | `article` | Map EU AI Act articles to UK, Singapore, Canada, US NIST equivalents |
| `predict_risk_neural` | system attributes | Neural network risk prediction (improves over time) |
| `neural_insights` | None | Aggregate learning insights from neural compliance model |

## Quick Start

```bash
# Install and run (one command)
pip install mcp
git clone https://github.com/CSOAI-ORG/eu-ai-act-compliance-mcp.git
cd eu-ai-act-compliance-mcp
python server.py
```

Or install as a package:

```bash
pip install eu-ai-act-compliance-mcp
eu-ai-act-compliance-mcp
```

## Claude Desktop Config

Add this to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Option A: pip install (recommended)

```json
{
  "mcpServers": {
    "eu-ai-act-compliance": {
      "command": "eu-ai-act-compliance-mcp"
    }
  }
}
```

### Option B: From source

```json
{
  "mcpServers": {
    "eu-ai-act-compliance": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/eu-ai-act-compliance-mcp"
    }
  }
}
```

### Option C: uvx (no install needed)

```json
{
  "mcpServers": {
    "eu-ai-act-compliance": {
      "command": "uvx",
      "args": ["eu-ai-act-compliance-mcp"]
    }
  }
}
```

After adding the config, restart Claude Desktop. Then ask: *"Quick scan: chatbot that screens job applicants"*

## Pricing

| Plan | Price | Requests |
|------|-------|----------|
| Free | $0/mo | 10 requests/day |
| Pro | $29/mo | Unlimited |

[Get on MCPize](https://mcpize.com/mcp/eu-ai-act-compliance) | [Stripe](https://buy.stripe.com/5kQcN7dkE28a23XeGY8k804)

## Part of MEOK AI Labs

This is one of 255+ MCP servers by MEOK AI Labs. Browse all at [meok.ai](https://meok.ai) or [GitHub](https://github.com/CSOAI-ORG).

---

## 🏢 Enterprise & Pro Licensing

| Plan | Price | Link |
|------|-------|------|
| **EU AI Act Compliance MCP** | £29/mo | [Subscribe](https://buy.stripe.com/5kQcN7dkE28a23XeGY8k804) |
| **Compliance Trinity** (EU AI Act + GDPR + ISO 42001) | £79/mo | [Subscribe](https://buy.stripe.com/eVq5kF2G0aEG3812Yg8k82i) |
| **Full Compliance Suite** (9 MCPs) | £999/mo | [Subscribe](https://buy.stripe.com/6oU14p0xS4giaAtbuM8k82q) |
| **Enterprise Assessment** | £5,000 | [Book Now](https://buy.stripe.com/00waEZ6Wg8wy7oh0Q88k82k) |

Free for personal and open-source use. Enterprise features and priority support with subscription.

> **EU AI Act high-risk deadline: August 2, 2026** — [Start your compliance assessment →](https://csoai.org)

---
**MEOK AI Labs** | [meok.ai](https://meok.ai) | [csoai.org](https://csoai.org) | nicholas@meok.ai | United Kingdom
