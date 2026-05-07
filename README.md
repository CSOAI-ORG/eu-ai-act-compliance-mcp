[![eu-ai-act-compliance-mcp MCP server](https://glama.ai/mcp/servers/CSOAI-ORG/eu-ai-act-compliance-mcp/badges/card.svg)](https://glama.ai/mcp/servers/CSOAI-ORG/eu-ai-act-compliance-mcp)

<div align="center">

[![MCPize](https://mcpize.com/badge/@CSOAI-ORG/eu-ai-act-compliance)](https://mcpize.com/mcp/eu-ai-act-compliance)
[![GitHub stars](https://img.shields.io/github/stars/CSOAI-ORG/eu-ai-act-compliance-mcp)](https://github.com/CSOAI-ORG/eu-ai-act-compliance-mcp/stargazers)

# EU AI Act Compliance MCP Server

**The only MCP server that automates EU AI Act compliance checking.**

Classify AI risk levels · Run 42-point compliance audits · Generate Article 11 documentation · Assess penalties · Track deadlines

[![npm version](https://img.shields.io/npm/v/@meok-ai/eu-ai-act-compliance-mcp)](https://www.npmjs.com/package/@meok-ai/eu-ai-act-compliance-mcp)
[![MCPize](https://img.shields.io/badge/MCPize-Listed-blue)](https://mcpize.com/mcp/eu-ai-act-compliance)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-255+_servers-purple)](https://meok.ai)

[Installation](#quick-start) · [Tools](#tools) · [Docs](https://csoai.org) · [Report Bug](https://github.com/CSOAI-ORG/eu-ai-act-compliance-mcp/issues)

</div>

---

## Connect via MCPize

Use this MCP server instantly with no local installation:

```bash
npx -y mcpize connect @CSOAI-ORG/eu-ai-act-compliance --client claude
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

| Tool | Description |
|------|-------------|
| `classify_risk` | Article 6 risk classification (minimal / limited / high / unacceptable) |
| `run_audit` | 42-point compliance checklist against Annex I-IX |
| `generate_article_11` | Technical documentation template generator |
| `assess_penalties` | Penalty exposure calculator (up to €35M or 7% global turnover) |
| `track_deadlines` | Deadline tracker with countdown to key dates |
| `sign_artifact` | HMAC-SHA256 attestation signing |

## Pricing

| Tier | Price | What you get |
|------|-------|-------------|
| **Free** | £0 | 10 calls/day — risk classification + audit |
| **Pro** | £199/mo | Unlimited calls + HMAC-signed attestations + public verify URLs |
| **Enterprise** | £1,499/mo | Multi-tenant + co-branded PDF reports + Trust Center webhooks |
| **One-off assessment** | £5,000 | 48h bespoke audit + signed deliverable |

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

[![Star History Chart](https://api.star-history.com/svg?repos=CSOAI-ORG/eu-ai-act-compliance-mcp&type=Date)](https://star-history.com/#CSOAI-ORG/eu-ai-act-compliance-mcp&Date)

## Support & Enterprise

- [GitHub Discussions](https://github.com/CSOAI-ORG/eu-ai-act-compliance-mcp/discussions)
- [Report Issues](https://github.com/CSOAI-ORG/eu-ai-act-compliance-mcp/issues)
- Enterprise support: nicholas@csoai.org
- Website: [meok.ai](https://meok.ai)
- All MCP servers: [meok.ai/labs/mcp/servers](https://meok.ai/labs/mcp/servers)
- Attestation API: [meok-attestation-api.vercel.app](https://meok-attestation-api.vercel.app)

## License

MIT © [CSOAI](https://csoai.org)
