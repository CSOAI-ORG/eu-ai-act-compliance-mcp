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
