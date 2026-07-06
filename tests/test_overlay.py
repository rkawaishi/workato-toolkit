import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugin" / "mcp" / "docs-overlay"))

import overlay  # noqa: E402


def _setup(tmp_path):
    kit = tmp_path / "kit"
    org = tmp_path / "org"
    (kit / "connectors").mkdir(parents=True)
    (org / "connectors").mkdir(parents=True)
    return kit, org


def test_kit_only(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("KIT slack", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/slack.md")
    assert "KIT slack" in out
    assert "NOT FOUND" not in out


def test_org_only(tmp_path):
    kit, org = _setup(tmp_path)
    (org / "connectors" / "internal.md").write_text("ORG internal", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/internal.md")
    assert "ORG internal" in out


def test_both_org_marked_authoritative(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("KIT slack base", encoding="utf-8")
    (org / "connectors" / "slack.md").write_text("ORG slack override", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/slack.md")
    assert "ORG slack override" in out
    assert "KIT slack base" in out
    assert out.index("ORG slack override") < out.index("KIT slack base")


def test_missing(tmp_path):
    kit, org = _setup(tmp_path)
    out = overlay.resolve_doc(kit, org, "connectors/nope.md")
    assert "NOT FOUND" in out


def test_appends_md_extension(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("KIT slack", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/slack")
    assert "KIT slack" in out


def test_path_traversal_blocked(tmp_path):
    kit, org = _setup(tmp_path)
    out = overlay.resolve_doc(kit, org, "../secret.md")
    assert "INVALID PATH" in out


def test_org_dir_none(tmp_path):
    kit, _ = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("KIT slack", encoding="utf-8")
    out = overlay.resolve_doc(kit, None, "connectors/slack.md")
    assert "KIT slack" in out


def test_list_docs_union(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("k", encoding="utf-8")
    (org / "connectors" / "internal.md").write_text("o", encoding="utf-8")
    (kit / "logic.md").write_text("k", encoding="utf-8")
    paths = overlay.list_docs(kit, org, prefix="connectors/")
    assert "connectors/slack.md" in paths
    assert "connectors/internal.md" in paths
    assert "logic.md" not in paths
    assert paths == sorted(paths)


def test_list_docs_dedup(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("k", encoding="utf-8")
    (org / "connectors" / "slack.md").write_text("o", encoding="utf-8")
    paths = overlay.list_docs(kit, org)
    assert paths.count("connectors/slack.md") == 1
