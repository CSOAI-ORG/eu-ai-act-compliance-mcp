#!/usr/bin/env python3
"""
lint_publish_meta.py — fail-fast version + metadata consistency check.

Runs in CI on every PR. Exits non-zero (and prints a clear reason) if:
  - pyproject.toml / server.json / package.json versions disagree
  - server.json `name` doesn't match `io.github.CSOAI-ORG/<slug>` shape
  - server.json `repository.url` doesn't match the expected CSOAI-ORG repo
  - PyPI README is missing the `mcp-name: io.github.CSOAI-ORG/<slug>` attribution tag
  - MIT LICENSE missing
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"⚠️  {msg}", file=sys.stderr)


def pyproject_version() -> str | None:
    p = ROOT / "pyproject.toml"
    if not p.exists():
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', p.read_text(), re.MULTILINE)
    return m.group(1) if m else None


def server_json() -> dict | None:
    p = ROOT / "server.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def package_json() -> dict | None:
    p = ROOT / "package.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def main() -> int:
    py_ver = pyproject_version()
    sj = server_json()
    pj = package_json()
    slug = ROOT.name  # directory name == slug (eu-ai-act-compliance-mcp etc.)

    if py_ver is None:
        fail("pyproject.toml [project].version missing")

    if sj is None:
        warn("server.json missing — Anthropic Registry publish will be skipped")
    else:
        sj_ver = sj.get("version")
        if sj_ver != py_ver:
            fail(f"version drift: pyproject.toml={py_ver} ≠ server.json={sj_ver}")

        # Check packages[].version match
        for i, pkg in enumerate(sj.get("packages", [])):
            if pkg.get("version") != py_ver:
                fail(
                    f"server.json packages[{i}].version={pkg.get('version')} "
                    f"≠ pyproject.toml={py_ver}"
                )

        # Check name format
        expected_name = f"io.github.CSOAI-ORG/{slug}"
        if sj.get("name") != expected_name:
            fail(
                f"server.json .name = {sj.get('name')!r}, "
                f"expected {expected_name!r}"
            )

        # Check repository URL
        repo_url = (sj.get("repository") or {}).get("url", "")
        expected_repo = f"https://github.com/CSOAI-ORG/{slug}"
        if repo_url != expected_repo:
            fail(
                f"server.json .repository.url = {repo_url!r}, "
                f"expected {expected_repo!r}"
            )

    if pj is not None:
        pj_ver = pj.get("version")
        if pj_ver != py_ver:
            fail(f"version drift: pyproject.toml={py_ver} ≠ package.json={pj_ver}")

    # README must contain mcp-name attribution for Anthropic Registry ownership check
    readme = ROOT / "README.md"
    if readme.exists() and sj is not None:
        text = readme.read_text()
        expected_tag = f"mcp-name: io.github.CSOAI-ORG/{slug}"
        if expected_tag not in text:
            fail(
                f"README.md missing `{expected_tag}` ownership tag — "
                "Anthropic Registry will 400 on publish"
            )

    # MIT LICENSE check
    lic = ROOT / "LICENSE"
    if not lic.exists():
        fail("LICENSE missing — must be MIT for portfolio compliance")
    elif "MIT" not in lic.read_text():
        warn("LICENSE found but not MIT — confirm this is intentional")

    print(f"✅ all metadata aligned at version {py_ver}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
