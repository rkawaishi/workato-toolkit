"""Connector-doc value-density metadata guards (issue #12, Phase 1).

Every kit connector doc must carry frontmatter recording provenance and quality
so freshness/quality is detectable and the update pipeline has something to
refresh. The derivation rules live in scripts/connector_doc_meta.py (shared with
the backfill script) so the guard and the generator never drift.
"""
import re
import sys

from conftest import DOCS, REPO

sys.path.insert(0, str(REPO / "scripts"))
from connector_doc_meta import (  # noqa: E402
    VALID_SOURCES,
    VALID_TIERS,
    derive_meta,
    parse_frontmatter,
)

CONN = DOCS / "connectors"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _connector_docs():
    return [p for p in sorted(CONN.glob("*.md")) if p.name != "_index.md"]


def test_every_connector_doc_has_frontmatter():
    missing = [p.name for p in _connector_docs()
               if not p.read_text(encoding="utf-8").startswith("---\n")]
    assert not missing, f"connector docs without frontmatter: {missing[:10]} ({len(missing)} total)"


def test_frontmatter_fields_valid():
    offenders = []
    for p in _connector_docs():
        meta = parse_frontmatter(p.read_text(encoding="utf-8"))
        if meta.get("source") not in VALID_SOURCES:
            offenders.append(f"{p.name}: source={meta.get('source')!r}")
        if meta.get("tier") not in VALID_TIERS:
            offenders.append(f"{p.name}: tier={meta.get('tier')!r}")
        sa = meta.get("synced_at", "")
        if not (sa == "unknown" or _DATE.match(sa or "")):
            offenders.append(f"{p.name}: synced_at={sa!r} (want 'unknown' or YYYY-MM-DD)")
    assert not offenders, "invalid frontmatter:\n" + "\n".join(offenders[:20])


def test_tier_and_source_match_derivation():
    """The recorded tier/source must equal what the shared derivation produces
    from the body — a doc can't claim tier A while being a bare table."""
    offenders = []
    for p in _connector_docs():
        text = p.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        derived = derive_meta(text)
        if meta.get("tier") != derived["tier"]:
            offenders.append(f"{p.name}: tier recorded={meta.get('tier')} derived={derived['tier']}")
        if meta.get("source") != derived["source"]:
            offenders.append(f"{p.name}: source recorded={meta.get('source')} derived={derived['source']}")
    assert not offenders, "frontmatter drifted from content:\n" + "\n".join(offenders[:20])
