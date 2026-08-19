# Install — EU AI Act Compliance MCP

## Manual install (Claude Desktop / Cline / any MCP client)
Add to your MCP client config:

```json
{
  "mcpServers": {
    "eu-ai-act-compliance-mcp": {
      "command": "uvx",
      "args": ["eu_ai_act_compliance_mcp"]
    }
  }
}
```

Or via pip:
```bash
pip install eu_ai_act_compliance_mcp
```

## Remote (streamable HTTP)
```
https://csoai-gspc-mcp.nicholastempleman.workers.dev/mcp
```

## What it does
- **417 frozen EU AI Act provisions** (113 Articles, provision-level granularity)
- Deterministic predicates (temp=0, exact-label) — never LLM-as-judge
- **Ed25519-signed receipts** — every result recomputable, verify free forever
- Honest UNMEASURED — never hidden, never fabricated
- **Measurement, not certification** — we don't remediate, we don't certify

## Verify
`https://councilof.ai/gspc-verify` — any card, any time, no account.
