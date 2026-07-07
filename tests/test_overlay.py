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


# --- search + section lookup (issue #14) ---

def test_search_docs_across_kit_and_org(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text(
        "# Slack\npost_message action\n", encoding="utf-8")
    (org / "connectors" / "internal.md").write_text(
        "our internal post_message wrapper\n", encoding="utf-8")
    (kit / "connectors" / "jira.md").write_text("# Jira\ncreate_issue\n", encoding="utf-8")
    hits = overlay.search_docs(kit, org, "post_message")
    joined = "\n".join(hits)
    assert "connectors/slack.md" in joined and "connectors/internal.md" in joined
    assert "connectors/jira.md" not in joined
    # case-insensitive
    assert overlay.search_docs(kit, org, "POST_MESSAGE")


def test_search_docs_prefix_and_cap(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "logic").mkdir()
    (kit / "logic" / "loops.md").write_text("repeat while\n", encoding="utf-8")
    (kit / "connectors" / "slack.md").write_text("repeat here too\n", encoding="utf-8")
    hits = overlay.search_docs(kit, org, "repeat", prefix="logic/")
    assert any("logic/loops.md" in h for h in hits)
    assert not any("connectors/" in h for h in hits)
    # cap: one doc with many matching lines must not flood the result
    (kit / "logic" / "big.md").write_text("hit\n" * 500, encoding="utf-8")
    hits = overlay.search_docs(kit, org, "hit")
    assert len(hits) <= overlay.SEARCH_MAX_RESULTS + 1  # + truncation notice


def test_lookup_section_extracts_heading_block(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text(
        "# Slack\nintro\n## Triggers\ntrig body\n## Actions\nact body\n## Notes\nnote\n",
        encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/slack.md", section="Actions")
    assert "act body" in out
    assert "trig body" not in out and "note" not in out


def test_lookup_section_miss_lists_available_headings(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text(
        "# Slack\n## Triggers\nt\n## Actions\na\n", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/slack.md", section="Nope")
    assert "SECTION NOT FOUND" in out
    assert "Triggers" in out and "Actions" in out  # discoverability


def test_list_docs_posix_paths(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("x", encoding="utf-8")
    paths = overlay.list_docs(kit, org, "")
    assert all("\\" not in p for p in paths)
    assert "connectors/slack.md" in paths


def test_section_ignores_fenced_code_hashes(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "sdk.md").write_text(
        "# Doc\n## Upload\nintro\n```bash\n# Push: create new\ncmd --x\n```\ntail\n## Next\nn\n",
        encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/sdk.md", section="Upload")
    assert "cmd --x" in out and "tail" in out, "fence comment must not end the section"
    assert "## Next" not in out
    miss = overlay.resolve_doc(kit, org, "connectors/sdk.md", section="Zzz")
    assert "Push: create new" not in miss, "fence comments must not appear as headings"


def test_section_header_honest_when_one_side_lacks_it(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "jira.md").write_text("# Jira\n## Triggers\nt\n", encoding="utf-8")
    (org / "connectors" / "jira.md").write_text("## Actions\norg act\n", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/jira.md", section="Actions")
    assert "org act" in out
    assert "no kit baseline" not in out, "kit doc exists — must not claim org-only doc"
    assert "kit doc has no matching section" in out


def test_search_cap_cannot_starve_org_hits(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "big.md").write_text("pagination\n" * 200, encoding="utf-8")
    (org / "connectors" / "ours.md").write_text("org pagination guidance\n", encoding="utf-8")
    hits = overlay.search_docs(kit, org, "pagination")
    assert any("org/docs/connectors/ours.md" in h for h in hits), (
        "org (authoritative) hits must survive the result cap"
    )
