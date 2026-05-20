# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.1] - 2026-05-17

### Changed

- Realigned Article 50 framing to **2 August 2026** as the watermarking + transparency cliff. The 7 May 2026 Digital Omnibus delayed Annex III high-risk (→ 2 Dec 2027) and Annex I product-safety (→ 2 Aug 2028), but **did NOT delay Article 50**. Aligns this MCP with meok-watermark-attest-mcp and watermarking-authenticity-mcp.
- `deadline_check` now returns `nearest_enforcement_cliff` keyed to 2 Aug 2026 (was incorrectly framed against a 2 Dec 2026 deadline that doesn't exist in the actual regulation).
- JURISDICTIONS["eu"] enforcement string clarified: "Article 50 transparency + watermarking 2 Aug 2026 (NOT delayed by Omnibus)".

## [1.5.0] - 2026-05-13

### Added

- `get_article_text` tool: returns full verbatim text of a single article plus the canonical EUR-Lex URL. Drop-in audit evidence.
- `eur_lex_url` field on every `search_regulation` hit (deep-linked to `#art_N`), making each quote one-click verifiable.

### Fixed

- EUR-Lex Cellar SPARQL sync was returning empty bindings. Switched to `FILTER(STR(?celex)=...)` matching and traversal via `expression_belongs_to_work` + `manifestation_manifests_expression`. All 6 tracked regulations now sync.
- XHTML manifestation URL is now read from SPARQL rather than guessed (CSRD lives at `.0006.02`, not `.0006.03` like the others).
- `check_for_updates` was hitting a 404'd Atom feed URL — rewritten to compare each work's Cellar `work_date_modified` against the local `last_synced` timestamp. The "Daily EUR-Lex Sync" workflow can now actually detect real updates.
- `search_regulation` no longer force-wraps unquoted multi-word queries as exact phrases — implicit AND across tokens (FTS5 default) is now used, with per-token quoting that neutralises hyphens and slashes. Queries like `incident reporting` against `nis2` no longer return zero.

### Changed

- README headline reframed around six-regulation coverage (EU AI Act, DORA, NIS2, CRA, CSRD, GDPR), not just the AI Act.
- `package.json` description rewritten to list all six regulations for registry discoverability.
- `SKILL.md` pricing reconciled with the live Stripe ladder (Starter £29 / Pro £79).

## [1.0.0] - 2026-05-07

### Added

- Initial public release
- Full MCP server implementation with stdio transport
- HMAC-SHA256 signed attestation support
- Comprehensive tool documentation
- PyPI package distribution
- MIT License

### Security

- Server-side API key validation
- Rate limiting per tier
- Input sanitization on all parameters
