# meok-eu-ai-act

## Description
EU AI Act compliance checking and risk classification. Automated compliance validation for high-risk AI systems with Article 11 technical documentation generation.

## Category
compliance

## Use Cases
- AI system risk classification
- High-risk system documentation
- Regulatory gap analysis

## Installation
```bash
pip install eu-ai-act-compliance-mcp
```

## Quick Start
```python
from mcp import Client

client = Client("eu-ai-act-compliance-mcp")
result = client.call_tool("tool_name", {"param": "value"})
print(result)
```

## Tools
See the MCP server for available tools.

## Pricing
- Free: Basic compliance checks, 50 calls/day
- Starter £29/mo: 200 calls/day + EUR-Lex FTS5 search
- Pro £79/mo: 1,000 calls/day + multi-jurisdiction mapping + neural predictions + signed attestations
- Enterprise: Contact for custom pricing

## Links
- MCP Server: https://github.com/meok-ai-labs/eu-ai-act-compliance-mcp
- Documentation: https://meok.ai/docs/meok-eu-ai-act
- Compliance Portal: https://compliance.meok.ai

## Compliance Standards
- EU AI Act (2024/1689)
- NIS2 Directive (2022/2555)
- ISO 42001:2023
- NIST AI RMF 1.0
