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


# ---- derivation hardening (review of #12 Phase 1) ----

from connector_doc_meta import _description_cells_filled, strip_frontmatter  # noqa: E402


def test_description_detection_is_header_aware():
    # a real Description column with content → filled
    assert _description_cells_filled(
        "| Name | Description |\n|---|---|\n| A | does a thing |"
    )
    # em/en-dash placeholder in the Description column → not filled
    assert not _description_cells_filled(
        "| Name | Description |\n|---|---|\n| A | — |"
    )
    # a 3-column table with a Batch (not Description) last column → not filled
    assert not _description_cells_filled(
        "| Name | Internal | Batch |\n|---|---|---|\n| A | a | Yes |"
    )


def test_leading_hr_is_not_frontmatter():
    # a doc that opens with a '---' horizontal rule (prose between rules) must
    # not be eaten as frontmatter
    meta, body = strip_frontmatter("---\nSome intro prose.\n---\n# Title\n")
    assert meta == []
    assert body.startswith("---")


# ---- duplicate-section detection (issue #12, Phase 2) ----
# The bulk generator emits `## Triggers` / `## Actions` (H2). Some docs also
# carried older hand-written `### Triggers` / `### Actions` tables nested under
# the generated section — the same connector's triggers/actions documented
# twice (a merge artifact, e.g. the old slack.md). Guard against recurrence:
# a `### Triggers|Actions` must not sit under a `## Triggers|Actions|Field
# details` scope. A sub-connector's own `### Triggers` (under a distinctly
# named `##`, e.g. "Workbot for Slack") is legitimate and passes.

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_DUP_PARENTS = {"triggers", "actions", "field details"}


def _duplicate_section_offenders(text: str):
    cur_h2 = None
    bad = []
    for lvl, title in _HEADING.findall(text):
        t = title.strip().lower()
        if len(lvl) == 2:
            cur_h2 = t
        elif len(lvl) == 3 and t in ("triggers", "actions"):
            if cur_h2 in _DUP_PARENTS:
                bad.append(f"### {title} under ## {cur_h2}")
    return bad


def test_no_duplicated_trigger_action_sections():
    offenders = []
    for p in _connector_docs():
        for hit in _duplicate_section_offenders(p.read_text(encoding="utf-8")):
            offenders.append(f"{p.name}: {hit}")
    assert not offenders, (
        "duplicated Triggers/Actions sections (generated H2 + legacy H3 — "
        "consolidate into the H2 tables, keep hand notes as their own section):\n"
        + "\n".join(offenders)
    )
