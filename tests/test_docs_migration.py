import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

sys.path.insert(0, str(REPO / "mcp" / "docs-overlay"))
import overlay  # noqa: E402


def test_connectors_migrated():
    n = len(list((DOCS / "connectors").glob("*.md")))
    assert n >= 317, f"expected >=317 connector docs, got {n}"


def test_index_is_real_not_p2_fixture():
    idx = (DOCS / "connectors" / "_index.md").read_text(encoding="utf-8")
    assert "Full content is migrated in P3" not in idx, "still the P2 placeholder _index.md"


def test_p2_example_fixture_removed():
    assert not (DOCS / "connectors" / "example.md").exists(), "P2 fixture example.md must be removed"


def test_platform_logic_patterns_present():
    assert len(list((DOCS / "platform").glob("*.md"))) >= 15
    assert len(list((DOCS / "logic").glob("*.md"))) >= 7
    assert len(list((DOCS / "patterns").rglob("*.md"))) >= 6
    assert len(list((DOCS / "connector-sdk").glob("*.md"))) >= 2
    assert (DOCS / "learned-patterns.md").is_file()


def test_guides_migrated():
    assert len(list((DOCS / "guides").glob("*.md"))) >= 13


def test_glossary_migrated():
    assert (DOCS / "i18n" / "GLOSSARY.md").is_file()


def test_total_docs_count():
    total = len(list(DOCS.rglob("*.md")))
    assert total >= 362, f"expected >=362 md after migration, got {total}"


def test_mcp_serves_real_connector_index():
    out = overlay.resolve_doc(DOCS, None, "connectors/_index.md")
    assert "NOT FOUND" not in out
    assert "Full content is migrated in P3" not in out


def test_mcp_lists_connectors():
    paths = overlay.list_docs(DOCS, None, "connectors/")
    assert len(paths) >= 317, f"MCP list_docs returned {len(paths)} connectors"


def test_mcp_serves_a_guide():
    paths = overlay.list_docs(DOCS, None, "guides/")
    assert len(paths) >= 13
