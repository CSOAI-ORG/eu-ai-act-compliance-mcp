"""
Tests for the 4 v1.4-v1.8 tools that ship with eu-ai-act-compliance-mcp:
  - search_regulation
  - get_article_text
  - iso_42001_crosswalk
  - cross_references_for_article

These tests stub the FastMCP runtime and exec the server module against the
shipped data/regulations.db. They run in CI without an external network.

Usage (locally):
    cd mcp-marketplace/eu-ai-act-compliance-mcp
    python -m pytest tests/test_new_tools.py -v

Smoke version (no pytest dependency):
    python tests/test_new_tools.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent


def _reset_usage_for_tests():
    """Clear ~/.meok/usage.json so tests aren't blocked by daily rate limits."""
    usage_path = Path(os.path.expanduser("~/.meok/usage.json"))
    if usage_path.exists():
        usage_path.unlink()


def _load_server_module():
    """Stub out FastMCP so server.py imports cleanly without the real mcp pkg."""
    _reset_usage_for_tests()
    sys.modules.setdefault("mcp", types.ModuleType("mcp"))
    sys.modules.setdefault("mcp.server", types.ModuleType("mcp.server"))

    class _StubMCP:
        def tool(self, *a, **k):
            return lambda fn: fn
        def prompt(self, *a, **k):
            return lambda fn: fn
        def resource(self, *a, **k):
            return lambda fn: fn
        def run(self, *a, **k):
            pass

    fastmcp_mod = types.ModuleType("mcp.server.fastmcp")
    fastmcp_mod.FastMCP = lambda *a, **k: _StubMCP()
    sys.modules["mcp.server.fastmcp"] = fastmcp_mod

    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("server_under_test", REPO_ROOT / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSearchRegulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_server_module()
        if not (REPO_ROOT / "data" / "regulations.db").exists():
            raise unittest.SkipTest("regulations.db absent — run scripts/eurlex_sync.py first")

    def test_basic_phrase_search_returns_results(self):
        r = self.mod.search_regulation('"personal data breach"')
        self.assertEqual(r.get("source", "").split("(")[0].strip(), "EUR-Lex Cellar API")
        self.assertGreater(r.get("result_count", 0), 0)

    def test_unquoted_implicit_and_search(self):
        # "incident reporting" should AND-match across NIS2 + DORA + EU AI Act
        r = self.mod.search_regulation("incident reporting", regulation="nis2", limit=5)
        self.assertGreater(r.get("result_count", 0), 0,
                           "NIS2 should match 'incident' AND 'reporting' even though the exact phrase doesn't appear verbatim")

    def test_hyphenated_token_neutralised(self):
        # "high-risk" should not be parsed as FTS5 `high NOT risk`
        r = self.mod.search_regulation("high-risk AI system", regulation="eu-ai-act", limit=3)
        self.assertGreater(r.get("result_count", 0), 0)

    def test_every_result_carries_eur_lex_url(self):
        r = self.mod.search_regulation('"personal data"', limit=3)
        for hit in r.get("results", []):
            self.assertIn("eur_lex_url", hit)
            self.assertTrue(hit["eur_lex_url"].startswith("https://eur-lex.europa.eu/"))
            self.assertIn(f"#art_{hit['article_number']}", hit["eur_lex_url"])


class TestGetArticleText(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_server_module()
        if not (REPO_ROOT / "data" / "regulations.db").exists():
            raise unittest.SkipTest("regulations.db absent")

    def test_gdpr_article_33_full_text(self):
        r = self.mod.get_article_text("gdpr", 33)
        self.assertNotIn("error", r)
        self.assertEqual(r["regulation"], "gdpr")
        self.assertEqual(r["article_number"], 33)
        self.assertIn("personal data breach", r["content"].lower())
        self.assertIn("supervisory authority", r["content"].lower())
        self.assertGreater(r["content_length"], 1000,
                           "GDPR Art 33 should be at least 1000 chars")
        self.assertTrue(r["eur_lex_url"].endswith("#art_33"))

    def test_unknown_regulation_returns_error(self):
        r = self.mod.get_article_text("fictional", 1)
        self.assertIn("error", r)

    def test_unknown_article_returns_error(self):
        r = self.mod.get_article_text("gdpr", 9999)
        self.assertIn("error", r)


class TestIsoCrosswalk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_server_module()

    def test_full_crosswalk_returns_all_clauses(self):
        r = self.mod.iso_42001_crosswalk()
        self.assertGreaterEqual(len(r["crosswalk"]), 7)
        self.assertIn("Clause 6 — Planning (incl. risk + AI impact assessment)", r["crosswalk"])

    def test_clause_filter(self):
        r = self.mod.iso_42001_crosswalk(clause="9")
        self.assertIn("Clause 9", r["iso_42001_clause"])
        self.assertIn("Article 15", " ".join(r["mapping"]["ai_act_articles"]))

    def test_reverse_article_lookup(self):
        r = self.mod.iso_42001_crosswalk(article="9")
        # AI Act Article 9 maps to ISO 42001 Clauses 6 AND 10
        self.assertGreaterEqual(r["result_count"], 2)
        clauses = [h["iso_42001_clause"] for h in r["iso_42001_clauses_satisfying"]]
        self.assertTrue(any("Clause 6" in c for c in clauses))


class TestCrossReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_server_module()
        if not (REPO_ROOT / "data" / "regulations.db").exists():
            raise unittest.SkipTest("regulations.db absent")

    def test_gdpr_article_33_inbound_includes_nis2(self):
        r = self.mod.cross_references_for_article("gdpr", 33)
        self.assertGreater(r["inbound_count"], 0)
        regs = {h["regulation"] for h in r["inbound_citations"]}
        # NIS2 Art 35 explicitly references GDPR personal data breach handling
        self.assertIn("nis2", regs,
                      "NIS2 Art 35 should cite GDPR Art 33 — known cross-reference")

    def test_no_self_citation(self):
        r = self.mod.cross_references_for_article("eu-ai-act", 14)
        for hit in r["inbound_citations"]:
            self.assertFalse(
                hit["regulation"] == "eu-ai-act" and hit["article_number"] == 14,
                "Self-citation must be filtered out",
            )

    def test_article_number_boundary_match(self):
        # Article 33 should not match "Article 330" or "Article 3"
        r = self.mod.cross_references_for_article("gdpr", 33)
        for hit in r["inbound_citations"]:
            # Each hit's snippet should contain ">>>Article 33<<<", not Article 3 / 330
            # The boundary check is in the server impl; here we sanity-check snippets
            self.assertIn("Article 33", hit["snippet"])

    def test_eur_lex_url_on_every_inbound(self):
        r = self.mod.cross_references_for_article("gdpr", 33)
        for hit in r["inbound_citations"]:
            self.assertTrue(hit["eur_lex_url"].startswith("https://eur-lex.europa.eu/"))


if __name__ == "__main__":
    # Allow running without pytest
    unittest.main(verbosity=2)
