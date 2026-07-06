import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugin"

# 配布ツリーは plugin/ 配下に一本化。root に残っていたら境界違反。
MOVED_DIRS = ["skills", "docs", "rules", "agents", "bin", "hooks", "mcp"]


def test_distributed_tree_lives_under_plugin():
    for name in MOVED_DIRS:
        assert (PLUGIN / name).is_dir(), f"plugin/{name} missing"
        assert not (REPO / name).exists(), f"{name}/ must not remain at repo root"
    assert (PLUGIN / "credential-patterns.txt").is_file()
    assert (PLUGIN / ".mcp.json").is_file()
    assert (PLUGIN / ".claude-plugin" / "plugin.json").is_file()
    assert (PLUGIN / "AGENTS.md").is_file()
    assert not (REPO / "AGENTS.md").exists()
    assert not (REPO / "GEMINI.md").exists()
    assert not (REPO / "credential-patterns.txt").exists()


def test_root_claude_md_is_handwritten_dev_context():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert "AUTO-GENERATED" not in text, "root CLAUDE.md must be hand-written dev context"
    assert "plugin/rules/" in text, "must point at the rules source of truth"
    assert "dev/specs/" in text, "must declare the dev-doc locations"
    assert len(text) < 8_000, "dev context must stay small (not the product rule dump)"


def test_cc_marketplace_points_at_plugin_dir():
    m = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert any(p.get("source") == "./plugin" for p in m["plugins"])


def test_frozen_marketplaces_point_at_plugin_dir():
    cursor = json.loads((REPO / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert cursor["plugins"][0]["source"] == "./plugin"
    codex = json.loads((REPO / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
    assert codex["plugins"][0]["source"]["path"] == "./plugin"


def test_dev_docs_home_committed():
    for sub in ("specs", "plans", "handovers"):
        d = REPO / "dev" / sub
        assert d.is_dir() and list(d.glob("*.md")), f"dev/{sub}/ empty or missing"


def test_dev_mcp_json_targets_plugin_server():
    d = json.loads((REPO / ".mcp.json").read_text(encoding="utf-8"))
    args = " ".join(d["mcpServers"]["workato-docs-dev"]["args"])
    assert "plugin/mcp/docs-overlay/server.py" in args
    assert "${CLAUDE_PLUGIN_ROOT}" not in args, "dev entry must not depend on the plugin-root var"


def test_plugin_mcp_json_uses_plugin_root_var():
    d = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
    args = " ".join(d["mcpServers"]["workato-docs"]["args"])
    assert "${CLAUDE_PLUGIN_ROOT}" in args
