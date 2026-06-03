#!/usr/bin/env python3
"""
EUR-Lex Cellar API Sync Script
================================
Fetches EU regulation text from the official EUR-Lex SPARQL endpoint
and builds a SQLite FTS5 database for full-text search.

Architecture inspired by Ansvar Systems' daily sync pattern, but built
for MEOK AI Labs' multi-regulation MCP ecosystem.

Data source: https://publications.europa.eu/webapi/rdf/sparql
No authentication required. Public SPARQL 1.1 endpoint.

Usage:
    python scripts/eurlex_sync.py              # Sync all tracked regulations
    python scripts/eurlex_sync.py --celex 32024R1689  # Sync specific regulation
    python scripts/eurlex_sync.py --check      # Check for updates only
"""

import json
import sqlite3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# CELEX IDs for regulations we track
TRACKED_REGULATIONS = {
    "32024R1689": {"name": "EU AI Act", "short": "eu-ai-act", "type": "regulation"},
    "32022R2554": {"name": "DORA", "short": "dora", "type": "regulation"},
    "32022L2555": {"name": "NIS2 Directive", "short": "nis2", "type": "directive"},
    "32024R2847": {"name": "Cyber Resilience Act", "short": "cra", "type": "regulation"},
    "32022L2464": {"name": "CSRD", "short": "csrd", "type": "directive"},
    "32016R0679": {"name": "GDPR", "short": "gdpr", "type": "regulation"},
}

SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"
DB_PATH = Path(__file__).parent.parent / "data" / "regulations.db"


def sparql_query(query: str, timeout: int = 30) -> dict:
    """Execute a SPARQL query against the EUR-Lex Cellar endpoint."""
    params = urllib.parse.urlencode({"query": query})
    url = f"{SPARQL_ENDPOINT}?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "MEOK-AI-Labs-EUR-Lex-Sync/1.0 (hello@meok.ai)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"SPARQL query failed: {e}")
        return {"results": {"bindings": []}}


def fetch_regulation_metadata(celex: str) -> dict:
    """Fetch metadata + English XHTML manifestation URL for a CELEX ID.

    The CELEX value in Cellar is a typed literal, so direct string equality
    (`cdm:resource_legal_id_celex "32024R1689"`) returns no rows. We bind it
    to a variable and compare via STR(). The English expression is reached
    via `expression_belongs_to_work`, and we restrict manifestations to the
    XHTML rendering (CSRD uses .0006.02, others .0006.03 — never hardcode).
    """
    query = f"""
    PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>

    SELECT ?work ?manif ?title ?dateDocument ?dateForce
    WHERE {{
      ?work cdm:resource_legal_id_celex ?celex .
      FILTER(STR(?celex) = "{celex}")
      OPTIONAL {{ ?work cdm:work_date_document ?dateDocument . }}
      OPTIONAL {{ ?work cdm:resource_legal_date_entry-into-force ?dateForce . }}
      ?expr cdm:expression_belongs_to_work ?work .
      ?expr cdm:expression_uses_language
            <http://publications.europa.eu/resource/authority/language/ENG> .
      OPTIONAL {{ ?expr cdm:expression_title ?title . }}
      ?manif cdm:manifestation_manifests_expression ?expr .
      ?manif cdm:manifestation_type ?mtype .
      FILTER(STR(?mtype) = "xhtml")
    }}
    LIMIT 1
    """
    result = sparql_query(query)
    bindings = result.get("results", {}).get("bindings", [])
    if bindings:
        b = bindings[0]
        work_uri = b.get("work", {}).get("value", "")
        # Derive ELI from CELEX: 32024R1689 -> reg/2024/1689, 32022L2555 -> dir/2022/2555
        eli = ""
        if len(celex) >= 8 and celex[0] == "3":
            year = celex[1:5]
            kind = "reg" if celex[5] == "R" else ("dir" if celex[5] == "L" else "")
            num = celex[6:].lstrip("0") or "0"
            if kind:
                eli = f"http://data.europa.eu/eli/{kind}/{year}/{num}/oj"
        return {
            "celex": celex,
            "work_uri": work_uri,
            "manifestation_uri": b.get("manif", {}).get("value", ""),
            "eli": eli,
            "title": b.get("title", {}).get("value", ""),
            "date_document": b.get("dateDocument", {}).get("value", ""),
            "date_force": b.get("dateForce", {}).get("value", ""),
        }
    return {"celex": celex, "title": "Not found", "manifestation_uri": ""}


def fetch_regulation_text(manifestation_uri: str) -> str:
    """Fetch the full XHTML body via Cellar content negotiation.

    Cellar responds with a 303 redirect to a /DOC_N resource; urllib's
    default opener follows 303s on GET, so no extra wiring is needed.
    """
    if not manifestation_uri:
        return ""
    req = urllib.request.Request(
        manifestation_uri,
        headers={
            "Accept": "application/xhtml+xml, text/html;q=0.9",
            "User-Agent": "MEOK-AI-Labs-EUR-Lex-Sync/1.0 (hello@meok.ai)",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"Cellar fetch failed for {manifestation_uri}: {e}")
        return ""


def parse_articles_from_xhtml(xhtml: str, celex: str) -> list[dict]:
    """Parse article-level elements from EUR-Lex XHTML using Akoma Ntoso eId patterns.

    For amending directives like CSRD (32022L2464), the body contains nested
    "Article N" titles inside amendment blocks (which insert new articles into a
    parent directive). The previous parser captured every "Article N" title as
    if it were a top-level article of the current regulation, collapsing 17
    detected markers into 11 stored rows via the UNIQUE(celex, article_number)
    constraint.

    Strategy now:
      1. Always prefer structural top-level divs (`<div id="art_N">` or
         `eId="art_N"`).
      2. Only fall back to the visible `<p class="oj-ti-art">Article N` pattern
         when NO structural divs are found (some legacy regulations).
    """
    articles = []
    if not xhtml:
        return articles

    structural_pattern = re.compile(
        r'<div[^>]*(?:id=["\']art[_-]?(\d+)["\']|eId=["\']art_(\d+)["\'])[^>]*>',
        re.IGNORECASE,
    )
    title_pattern = re.compile(
        r'<p[^>]*class=["\'][^"\']*oj-ti-art[^"\']*["\'][^>]*>\s*Article\s+(\d+)',
        re.IGNORECASE,
    )

    has_structural = bool(structural_pattern.search(xhtml))
    primary = structural_pattern if has_structural else title_pattern

    def strip_tags(html: str) -> str:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    for match in primary.finditer(xhtml):
        art_num = next((g for g in match.groups() if g), None)
        if not art_num:
            continue

        start = match.end()
        next_match = primary.search(xhtml, start)
        end = next_match.start() if next_match else min(start + 5000, len(xhtml))

        content = strip_tags(xhtml[start:end])
        if len(content) > 50:
            articles.append({
                "celex": celex,
                "article_number": int(art_num),
                "article_id": f"art_{art_num}",
                "content": content[:10000],
                "content_length": len(content),
            })

    return articles


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize the SQLite FTS5 database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    # Metadata table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regulations (
            celex TEXT PRIMARY KEY,
            name TEXT,
            short_name TEXT,
            type TEXT,
            eli TEXT,
            title TEXT,
            date_document TEXT,
            date_force TEXT,
            last_synced TEXT,
            article_count INTEGER DEFAULT 0
        )
    """)

    # Articles table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            celex TEXT NOT NULL,
            article_number INTEGER,
            article_id TEXT,
            content TEXT,
            content_length INTEGER,
            UNIQUE(celex, article_number)
        )
    """)

    # FTS5 virtual table for full-text search
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            celex,
            article_number,
            article_id,
            content,
            content='articles',
            content_rowid='id'
        )
    """)

    # Sync log
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            celex TEXT,
            action TEXT,
            articles_found INTEGER,
            status TEXT
        )
    """)

    conn.commit()
    return conn


def _build_fts_query(query: str) -> str:
    """Coerce user input into a safe FTS5 MATCH expression.

    - "phrase"-wrapped input or input containing AND/OR/NEAR( is passed through.
    - Otherwise each whitespace-separated token is double-quoted, giving an
      implicit AND across tokens. Per-token quoting neutralises hyphens, slashes,
      and other FTS5 metacharacters (e.g. `high-risk` -> `"high-risk"`).
    """
    raw = query.strip()
    upper = raw.upper()
    is_phrase = raw.startswith('"') and raw.endswith('"') and len(raw) >= 2
    has_operator = any(op in upper for op in (" AND ", " OR ", " NEAR("))
    if is_phrase or has_operator:
        return raw
    tokens = [t for t in raw.split() if t]
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


def search_regulations(conn: sqlite3.Connection, query: str, limit: int = 10, snippet_tokens: int = 64) -> list[dict]:
    """Search regulations using FTS5 with snippet extraction."""
    results = []
    fts_query = _build_fts_query(query)
    try:
        cursor = conn.execute(
            f"""
            SELECT celex, article_number, article_id,
                   snippet(articles_fts, 3, '>>>', '<<<', '...', {snippet_tokens}) as snippet,
                   rank
            FROM articles_fts
            WHERE articles_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, limit),
        )
        for row in cursor:
            results.append({
                "celex": row[0],
                "article_number": row[1],
                "article_id": row[2],
                "snippet": row[3],
                "relevance_score": abs(row[4]),
            })
    except Exception as e:
        print(f"Search error: {e}")
    return results


def sync_regulation(conn: sqlite3.Connection, celex: str, reg_info: dict) -> int:
    """Sync a single regulation from EUR-Lex into the database."""
    print(f"Syncing {reg_info['name']} ({celex})...")

    # Fetch metadata (includes XHTML manifestation URL)
    meta = fetch_regulation_metadata(celex)
    print(f"  Title: {meta.get('title', 'N/A')[:80]}")
    print(f"  Manifestation: {meta.get('manifestation_uri', '')[-60:]}")

    # Fetch full text via Cellar content negotiation
    xhtml = fetch_regulation_text(meta.get("manifestation_uri", ""))
    if not xhtml:
        print(f"  WARNING: Could not fetch XHTML for {celex}")
        conn.execute(
            """
            INSERT OR REPLACE INTO sync_log (timestamp, celex, action, articles_found, status)
            VALUES (?, ?, 'sync_failed', 0, 'xhtml_fetch_failed')
            """,
            (datetime.now(timezone.utc).isoformat(), celex),
        )
        conn.commit()
        return 0

    print(f"  Fetched {len(xhtml)} bytes of XHTML")

    # Parse articles
    articles = parse_articles_from_xhtml(xhtml, celex)
    print(f"  Parsed {len(articles)} articles")

    # Upsert regulation metadata
    conn.execute(
        """
        INSERT OR REPLACE INTO regulations
        (celex, name, short_name, type, eli, title, date_document, date_force, last_synced, article_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            celex,
            reg_info["name"],
            reg_info["short"],
            reg_info["type"],
            meta.get("eli", ""),
            meta.get("title", ""),
            meta.get("date_document", ""),
            meta.get("date_force", ""),
            datetime.now(timezone.utc).isoformat(),
            len(articles),
        ),
    )

    # Upsert articles
    for art in articles:
        conn.execute(
            """
            INSERT OR REPLACE INTO articles (celex, article_number, article_id, content, content_length)
            VALUES (?, ?, ?, ?, ?)
            """,
            (art["celex"], art["article_number"], art["article_id"], art["content"], art["content_length"]),
        )

    # Rebuild FTS index
    conn.execute("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')")

    # Log sync
    conn.execute(
        """
        INSERT INTO sync_log (timestamp, celex, action, articles_found, status)
        VALUES (?, ?, 'sync_complete', ?, 'ok')
        """,
        (datetime.now(timezone.utc).isoformat(), celex, len(articles)),
    )

    conn.commit()
    print(f"  Synced {len(articles)} articles to database")
    return len(articles)


def check_for_updates(db_path: Path = DB_PATH) -> list[str]:
    """Detect tracked regulations whose Cellar work_date_modified is newer than our last sync.

    Previous implementation hit a 404'd Atom feed URL and silently always returned
    an empty list — so the daily workflow effectively never auto-synced. This
    version asks SPARQL for each work's latest `work_date_modified` and compares
    it against `regulations.last_synced` in the local DB.
    """
    updated = []
    last_synced: dict[str, str] = {}
    if db_path.exists():
        try:
            with sqlite3.connect(str(db_path)) as conn:
                for row in conn.execute("SELECT celex, last_synced FROM regulations"):
                    last_synced[row[0]] = row[1] or ""
        except Exception as e:
            print(f"Could not read local sync timestamps: {e}")

    for celex, reg_info in TRACKED_REGULATIONS.items():
        query = f"""
        PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
        SELECT ?modified WHERE {{
          ?work cdm:resource_legal_id_celex ?celex .
          FILTER(STR(?celex) = "{celex}")
          OPTIONAL {{ ?work cdm:work_date_modified ?modified . }}
        }} LIMIT 1
        """
        result = sparql_query(query)
        bindings = result.get("results", {}).get("bindings", [])
        if not bindings:
            continue
        remote_modified = bindings[0].get("modified", {}).get("value", "")
        local = last_synced.get(celex, "")
        # First-time sync, or remote is provably newer
        if not local or (remote_modified and remote_modified > local[:10]):
            updated.append(celex)
            print(f"Update available for {reg_info['name']} ({celex}): "
                  f"remote_modified={remote_modified or 'unknown'} local_synced={local[:10] or 'never'}")
    return updated


def main():
    import argparse

    parser = argparse.ArgumentParser(description="EUR-Lex Cellar API Sync")
    parser.add_argument("--celex", help="Sync specific regulation by CELEX ID")
    parser.add_argument("--check", action="store_true", help="Check for updates only")
    parser.add_argument("--search", help="Search the database")
    parser.add_argument("--db", default=str(DB_PATH), help="Database path")
    args = parser.parse_args()

    db_path = Path(args.db)

    if args.check:
        print("Checking EUR-Lex for updates...")
        updated = check_for_updates()
        if updated:
            print(f"\nUpdates available for: {', '.join(updated)}")
        else:
            print("No updates detected")
        return

    conn = init_db(db_path)

    if args.search:
        results = search_regulations(conn, args.search)
        for r in results:
            reg_name = TRACKED_REGULATIONS.get(r["celex"], {}).get("name", r["celex"])
            print(f"\n[{reg_name} Article {r['article_number']}] (score: {r['relevance_score']:.2f})")
            print(f"  {r['snippet']}")
        conn.close()
        return

    if args.celex:
        reg_info = TRACKED_REGULATIONS.get(args.celex)
        if not reg_info:
            print(f"Unknown CELEX ID: {args.celex}")
            print(f"Tracked: {', '.join(TRACKED_REGULATIONS.keys())}")
            sys.exit(1)
        sync_regulation(conn, args.celex, reg_info)
    else:
        # Sync all tracked regulations
        total_articles = 0
        for celex, reg_info in TRACKED_REGULATIONS.items():
            count = sync_regulation(conn, celex, reg_info)
            total_articles += count
        print(f"\n{'='*60}")
        print(f"Total: {total_articles} articles across {len(TRACKED_REGULATIONS)} regulations")

    conn.close()
    print(f"\nDatabase: {db_path} ({db_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
