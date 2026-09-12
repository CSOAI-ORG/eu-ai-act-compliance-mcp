<!-- mcp-name: io.github.CSOAI-ORG/eu-ai-act-compliance-mcp -->

> Verification is free and public: signed measurement cards and live verification at **https://councilof.ai** — measurement, not certification.

[![MCP Scorecard: 90/100](https://img.shields.io/badge/proofof.ai-90%2F100-5b21b6)](https://proofof.ai/scorecard/eu-ai-act-compliance-mcp.html)

# Eu Ai Act Compliance MCP

> **⚖️ Need EU AI Act readiness _for your system_, fast?** This MCP is the free tool. For a tailored
> readiness pack + a second opinion from the team behind the [CSOAI charter](https://csoai.org),
> book a 30-min **Founder Office Hour (£29)** → **https://meok.ai/work**
>
> Part of the MEOK governance platform · [meok.ai](https://meok.ai) · [csoai.org](https://csoai.org)

[![MEOK AI Labs](https://img.shields.io/badge/MEOK-AI%20Labs-667eea)](https://meok.ai)
[![PAYG enabled](https://img.shields.io/badge/PAYG-%C2%A30.05%2Fcall-7c3aed?logo=stripe&logoColor=white&labelColor=1a1a2e)](https://councilof.ai/payg)
[![GSPC](https://img.shields.io/badge/GSPC-live%20GET%20%2Fapi%2Fgspc-0ea5e9)](https://councilof.ai/api/gspc)
[![Measurement](https://img.shields.io/badge/Measurement-not%20certification-64748b)](https://councilof.ai/api/gspc)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PyPI](https://img.shields.io/badge/PyPI-Install-3775a9)](https://pypi.org/project/eu_ai_act_compliance_mcp/)

> EU AI Act measurement corpus — 417 frozen provisions at provision-level granularity (the Act has 113 Articles; our corpus is the finer-grained provision map)

EU AI Act measurement corpus — 417 frozen provisions at provision-level granularity (the Act has 113 Articles; our corpus is the finer-grained provision map). Risk classification, 42-point audit, Article 11 docs, penalty calculator. MIT

---

## 🚀 Quick Start

```bash
# Install via pip
pip install eu_ai_act_compliance_mcp

# Or install via Smithery
npx -y @smithery/cli@latest install eu-ai-act-compliance-mcp --client claude
```

## ⚡ Pay-per-call (PAYG) — no subscription

This MCP supports universal pay-per-call billing across the MEOK compliance fleet:

```bash
# One-time setup
export MEOK_PAYG_KEY="your_topup_token"

# Every tool call now deducts £0.05 from your balance.
# When balance hits zero, the tool returns a top-up URL.
# Works across all 7 MEOK compliance MCPs with the same token.
```

- **No subscription** — top up once, deduct per call.
- **£0.05/call default** (configurable via `MEOK_PAYG_RATE_GBP`).
- **USDC on Base L2 accepted** — set `MEOK_X402_RECEIVER` and pay via stablecoin.
- **Backward-compatible** — when `MEOK_PAYG_KEY` is unset, behaviour is unchanged.

**Get a token**: [councilof.ai/payg](https://councilof.ai/payg) (£10 / £50 / £200 top-up tiers).


## ✨ Features

- MCP protocol compliant
- Easy installation
- Well-documented API
- Production-ready
- Active maintenance

## 📖 Documentation

- [Full Documentation](https://meok.ai/eu-ai-act-for-legal-tech)
- [API Reference](https://councilof.ai/api-docs)
- [EU AI Act Compliance Guide](https://councilof.ai)

## Honesty register (2026-09-02)

**Live authority is `GET https://councilof.ai/api/gspc`** — cite `totals.public_count` and `totals.lid` from that payload. Do not type axis counts into this README.

- **Measurement, not certification.** CSOAI Ltd measures and signs; it does not certify, accredit, or act as a notified body.
- **MEOK.ai is a shelf / frontend**, not a second Council. Printers and agents must read the live GSPC endpoint — never invent scores, never wrangler a stamp.
- Prefer honest **UNCHECKABLE** over a fake stamp. This package does **not** certify EU AI Act compliance.


## 🏢 Enterprise

Need custom development, SLA guarantees, or white-label deployment?

- **Pro:** £79/mo — Full MCP suite + EU AI Act tracking
- **Enterprise:** £499/mo — Custom dev + SLA + Dedicated support

[View Pricing →](https://councilof.ai/payg) | [Contact Sales →](mailto:sales@meok.ai)

## 🤝 Part of the MEOK Ecosystem

This server is part of the **[MEOK AI Labs](https://meok.ai)** ecosystem — 26 PyPI packages · ~16,300 monthly installs.

| Domain | Purpose |
|--------|---------|
| [councilof.ai](https://councilof.ai) | Independent measurement board — live `GET /api/gspc` |
| [safetyof.ai](https://safetyof.ai) | AI safety & monitoring |
| [meok.ai](https://meok.ai) | Shelf / frontend (not a second Council) |
| [cobolbridge.ai](https://cobolbridge.ai) | Legacy modernization |

## 📜 License

MIT © [CSOAI-ORG](https://github.com/CSOAI-ORG)

---

<p align="center">
  <sub>Built with 💜 by <a href="https://meok.ai">MEOK AI Labs</a> · UK Companies House 16939677</sub>
</p>


## Configuration

Add to your `claude_desktop_config.json` (Claude Desktop) or your MCP client config:

```json
{
  "mcpServers": {
    "eu-ai-act-compliance-mcp": {
      "command": "uvx",
      "args": ["eu-ai-act-compliance-mcp"]
    }
  }
}
```

Or: `pip install eu-ai-act-compliance-mcp` then run the `eu-ai-act-compliance-mcp` command (stdio transport).

## Examples

Once configured, ask your assistant, for example:
- "Use `quick_scan` to …"
- "Use `deadline_check` to …"
- "Use `classify_ai_risk` to …"
