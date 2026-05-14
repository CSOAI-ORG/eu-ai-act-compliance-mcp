[![eu-ai-act-compliance-mcp MCP server](https://glama.ai/mcp/servers/CSOAI-ORG/eu-ai-act-compliance-mcp/badges/score.svg)](https://glama.ai/mcp/servers/CSOAI-ORG/eu-ai-act-compliance-mcp)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-Published-green)](https://registry.modelcontextprotocol.io)
[![PyPI](https://img.shields.io/pypi/v/eu-ai-act-compliance-mcp)](https://pypi.org/project/eu-ai-act-compliance-mcp/)

[![eu-ai-act-compliance-mcp MCP server](https://glama.ai/mcp/servers/CSOAI-ORG/eu-ai-act-compliance-mcp/badges/card.svg)](https://glama.ai/mcp/servers/CSOAI-ORG/eu-ai-act-compliance-mcp)

<div align="center">

[![MCPize](https://mcpize.com/badge/@meok-ai-labs/eu-ai-act-compliance)](https://mcpize.com/mcp/eu-ai-act-compliance)
[![GitHub stars](https://img.shields.io/github/stars/meok-ai-labs/eu-ai-act-compliance-mcp)](https://github.com/meok-ai-labs/eu-ai-act-compliance-mcp/stargazers)

# EU AI Act + Multi-Regulation Compliance MCP Server

**Six EU regulations, one MCP. Verbatim text + active compliance scanning + cryptographic attestations.**

Covers **EU AI Act · DORA · NIS2 · Cyber Resilience Act · CSRD · GDPR** — 400+ articles indexed for FTS5 search, every quote auditor-defensible, every citation linked back to the canonical EUR-Lex URL.

🆕 **v1.4 — Verbatim EU regulation text from publications.europa.eu Cellar SPARQL, in SQLite FTS5. Daily sync.**

Search regulation text · Quote full articles · Classify AI risk levels · Run 42-point audits · Generate Annex IV docs · Assess penalties · Track deadlines · Sign attestations

[![npm version](https://img.shields.io/npm/v/@meok-ai/eu-ai-act-compliance-mcp)](https://www.npmjs.com/package/@meok-ai/eu-ai-act-compliance-mcp)
[![MCPize](https://img.shields.io/badge/MCPize-Listed-blue)](https://mcpize.com/mcp/eu-ai-act-compliance)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-255+_servers-purple)](https://meok.ai)

[Installation](#quick-start) · [Tools](#tools) · [Docs](https://meok.ai) · [Report Bug](https://github.com/meok-ai-labs/eu-ai-act-compliance-mcp/issues)

</div>

---


## Quick Install

| Client | Install |
|--------|---------|
| **Claude Desktop** | [![Install in Claude](https://img.shields.io/badge/Install-Claude-blue)](https://claude.ai) |
| **Cursor** | [![Install in Cursor](https://img.shields.io/badge/Install-Cursor-black)](https://cursor.com) |
| **VS Code** | [![Install in VS Code](https://img.shields.io/badge/Install-VS_Code-blue)](https://code.visualstudio.com) |
| **Windsurf** | [![Install in Windsurf](https://img.shields.io/badge/Install-Windsurf-purple)](https://codeium.com/windsurf) |
| **Docker** | `docker run -p 8000:8000 eu-ai-act-compliance-mcp` |
| **pip** | `pip install eu-ai-act-compliance-mcp` |

## Connect via MCPize

Use this MCP server instantly with no local installation:

```bash
npx -y mcpize connect @meok-ai-labs/eu-ai-act-compliance --client claude
```

Or connect at: **https://mcpize.com/mcp/eu-ai-act-compliance**

---

## Quick Start

```bash
pip install eu-ai-act-compliance-mcp
# or
npm install -g @meok-ai/eu-ai-act-compliance-mcp
```

## Why This Exists

The EU AI Act (Reg 2024/1689) is now in force. Following the March 2026 Digital Omnibus vote, the timeline shifted:

- **Article 50** transparency obligations: **2 November 2026** (was August 2026)
- **Annex III** high-risk systems: **2 December 2027** (was August 2026)
- **Annex I** high-risk systems: **2 August 2028** (was August 2027)

Penalties remain unchanged: up to **€35M or 7% of global turnover**.

Most teams are using PDF binders and Word checklists to track Article 6 risk classifications, Article 26(9) FRIA artifacts, and Article 50 disclosures. When a regulator asks "how do we know this artifact wasn't fabricated last week?", the answer today is "trust us".

This MCP turns Article 6 / 26(9) / 50 obligations into a single AI-agent-callable tool, signs each artifact with HMAC-SHA256, and gives you a verifiable URL the auditor can curl independently.

## Real Usage Example

A German Mittelstand HR-tech firm needed to dry-run their Article 6 classification + Article 26(9) FRIA for a CV-screening AI. Their compliance lead installed this MCP into Claude Code:

```bash
pip install eu-ai-act-compliance-mcp
```

Then prompted Claude:

> "Classify our CV-scoring product against EU AI Act Article 6. Treat it as Annex III (employment). Generate the risk-tier rationale and the high-risk obligations checklist. Then produce the Article 26(9) FRIA. Sign with the attestation API."

**Result:** 49-page audit pack with cryptographically verifiable HMAC-signed sections in ~14 hours of review time.

**Traditional consulting estimate:** 230 hours / £42-62K.

**Saved:** ~£40K and 4-5 weeks.

## Tools

### 🆕 v1.4 — EUR-Lex Search (free tier)

| Tool | Description |
|------|-------------|
| `search_regulation` | Full-text FTS5 search across verbatim EU regulation text (EU AI Act, DORA, NIS2, CRA, CSRD, GDPR). Returns 64-token snippets with relevance scores and a canonical EUR-Lex URL for every hit. |
| `get_article_text` | Return the **full verbatim text** of a single article (e.g. GDPR Article 33) plus its canonical EUR-Lex URL. Drop straight into audit evidence packs. |
| `list_regulations_in_db` | List all regulations in the local DB with article counts + last-sync date. |

### Core compliance tools

| Tool | Description |
|------|-------------|
| `quick_scan` | One-sentence AI system description → instant risk classification (no API key) |
| `deadline_check` | All EU AI Act enforcement deadlines with days remaining (zero params) |
| `classify_ai_risk` | Detailed Article 5/6/50 risk classification |
| `check_compliance` | 42-point compliance audit against Annex I-IX |
| `generate_annex_iv_docs` | Article 11 technical documentation generator |
| `assess_penalties` | Penalty exposure calculator (up to €35M or 7% global turnover) |
| `multi_jurisdiction_map` | Cross-border compliance mapping |
| `predict_risk_neural` | Neural-net risk prediction (Pro tier) |
| `neural_insights` | Compliance pattern insights from training data (Pro tier) |

### Example: search the EU AI Act for "biometric"

```python
result = search_regulation(query="biometric", regulation="eu-ai-act", limit=3)
```

Returns matched snippets from Article 3 (definitions), Article 5 (prohibitions), Article 26 (deployer duties), with relevance scores and `>>>highlight<<<` markers.

### Why FTS5?

- **Verbatim text** — no LLM summarization, every quote is auditor-defensible
- **Token-safe** — 64-token snippets fit in any context window
- **Daily sync** — GitHub Actions polls EUR-Lex Atom feed at 06:00 UTC
- **Stdlib only** — no Postgres, no external deps

## Pricing

| Tier | Price | What you get |
|------|-------|-------------|
| **Free** | £0/forever | 10 calls/day — quick_scan, deadline_check, risk classification (summary) |
| **Starter** | £29/mo | 100 calls/day — full detailed analysis + Annex IV docs + audit reports |
| **Professional** | £79/mo | 1,000 calls/day — multi-jurisdiction mapping + neural predictions + attestations |
| **Enterprise** | Custom | Unlimited — on-premise + custom models + SLA + SSO |

**[Get your API key &rarr;](https://meok.ai/api-keys)**

---

> **If this tool helps your compliance workflow, please [star this repo](https://github.com/meok-ai-labs/eu-ai-act-compliance-mcp/stargazers)** — it helps other compliance teams find it and keeps it maintained.

→ [Subscribe to Pro](https://buy.stripe.com/14A4gB3K4eUWgYR56o8k836) · [Enterprise](https://buy.stripe.com/4gM9AV80kaEG0ZT42k8k837) · [Book assessment](https://buy.stripe.com/4gM7sN2G0bIKeQJfL28k833)

## Attestation API

Every Pro/Enterprise audit produces a cryptographically signed certificate:

```
POST https://meok-attestation-api.vercel.app/sign
→ { cert_id, verify_url, hmac_sha256, valid_until }
```

Verify any certificate: `https://meok-attestation-api.vercel.app/verify/{cert_id}`

Or install the zero-dep verifier: `pip install meok-attestation-verify`

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=meok-ai-labs/eu-ai-act-compliance-mcp&type=Date)](https://star-history.com/#meok-ai-labs/eu-ai-act-compliance-mcp&Date)

## Need Full EU AI Act Compliance?

This MCP gives you the tools — **[councilof.ai](https://councilof.ai)** gives you the full platform.

| Tier | Price | What You Get |
|------|-------|-------------|
| **Starter** | £29/mo | Automated risk classification + deadline tracking |
| **Pro** | £79/mo | Full audit packs + HMAC-signed attestations |
| **Enterprise** | £1,499/mo | Dedicated compliance support + Notified Body prep |
| **Gap Analysis** | £5,000 | 48-hour expert assessment with signed report |

→ **[Get started at councilof.ai](https://councilof.ai)** — 100x cheaper than traditional compliance consulting.

## Support & Enterprise

- [GitHub Discussions](https://github.com/meok-ai-labs/eu-ai-act-compliance-mcp/discussions)
- [Report Issues](https://github.com/meok-ai-labs/eu-ai-act-compliance-mcp/issues)
- Enterprise support: hello@meok.ai
- Website: [meok.ai](https://meok.ai)
- All MCP servers: [meok.ai/labs/mcp/servers](https://meok.ai/labs/mcp/servers)
- Attestation API: [meok-attestation-api.vercel.app](https://meok-attestation-api.vercel.app)
- Compliance platform: [councilof.ai](https://councilof.ai)

## License

MIT © [MEOK AI Labs](https://meok.ai)


<!-- meok-faq-schema-v1 -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Is this MCP server free to use?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. The free tier gives you 10 calls per day with no API key required. Pro tier is £79/mo for unlimited calls plus cryptographically signed attestations your auditor can verify independently."
      }
    },
    {
      "@type": "Question",
      "name": "How does the signed attestation work?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Every Pro tier audit produces a HMAC-SHA256 signed certificate with a unique ID and a public verify URL. Your auditor pastes the cert into https://meok-attestation-api.vercel.app/verify and gets an independent valid/invalid response. No contact with MEOK required."
      }
    },
    {
      "@type": "Question",
      "name": "Which MCP clients does this work with?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "All standard MCP clients: Claude Desktop, Claude Code, Cursor, VS Code with MCP extension, Windsurf, Cline, and any custom MCP-compatible agent. Install via npx meok-setup or pip install for the underlying Python package."
      }
    },
    {
      "@type": "Question",
      "name": "Can I install all MEOK governance MCPs at once?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. Run npx meok-setup --pack governance to install all 10 governance MCPs and write the configs for Claude Desktop, Cursor, or Windsurf in one command."
      }
    },
    {
      "@type": "Question",
      "name": "Is the regulation text authoritative?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Yes. MEOK syncs daily from the EUR-Lex Cellar SPARQL endpoint, the canonical EU regulation publication system. The text is verbatim with no LLM summarization. Every quote is auditor-defensible and includes the exact article number plus relevance score."
      }
    }
  ]
}
</script>

<!-- mcp-name: io.github.CSOAI-ORG/eu-ai-act-compliance-mcp -->
