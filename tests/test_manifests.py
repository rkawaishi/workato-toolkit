"""Plugin / marketplace manifest shape and version guards."""
import json
from pathlib import Path

from conftest import PLUGIN, REPO as ROOT

EXPECTED_VERSION = "0.1.0"


def load_json(p: Path):
    assert p.exists(), f"missing manifest: {p}"
    return json.loads(p.read_text(encoding="utf-8"))


def test_cc_marketplace():
    m = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    assert m["name"] == "workato-toolkit"
    assert m["owner"]["name"]
    assert any(p.get("source") == "./plugin" for p in m["plugins"])


def test_cc_plugin():
    p = load_json(PLUGIN / ".claude-plugin" / "plugin.json")
    assert p["name"] == "workato-toolkit"
    assert p["version"]
    assert p["description"]


def test_cursor_marketplace():
    m = load_json(ROOT / ".cursor-plugin" / "marketplace.json")
    assert m["name"] == "workato-toolkit"
    assert m["owner"]["name"]
    assert m["plugins"][0]["source"] == "./plugin"


def test_cursor_plugin():
    p = load_json(PLUGIN / ".cursor-plugin" / "plugin.json")
    assert p["name"] == "workato-toolkit"


def test_codex_plugin():
    p = load_json(PLUGIN / ".codex-plugin" / "plugin.json")
    assert p["name"] == "workato-toolkit"
    assert p["version"]
    assert p["description"]


def test_codex_marketplace():
    m = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert m["name"] == "workato-toolkit"
    entry = m["plugins"][0]
    assert entry["source"]["source"] == "local"
    assert entry["source"]["path"] == "./plugin"
    assert entry["policy"]["installation"]
    assert entry["category"]


def test_codex_manifest_declares_agents_hooks():
    p = load_json(PLUGIN / ".codex-plugin" / "plugin.json")
    assert p.get("agents") == "./agents/"
    assert p.get("hooks") == "./hooks/codex.hooks.json"


def test_cursor_manifest_declares_rules_hooks():
    p = load_json(PLUGIN / ".cursor-plugin" / "plugin.json")
    assert p.get("rules") == "rules/"
    assert p.get("hooks") == "hooks/cursor.hooks.json"


def test_cc_manifest_declares_hooks():
    p = load_json(PLUGIN / ".claude-plugin" / "plugin.json")
    assert p.get("hooks") == "./hooks/hooks.json"


def test_manifest_versions_bumped_and_consistent():
    cc = load_json(PLUGIN / ".claude-plugin" / "plugin.json")["version"]
    codex = load_json(PLUGIN / ".codex-plugin" / "plugin.json")["version"]
    cursor = load_json(PLUGIN / ".cursor-plugin" / "plugin.json")["version"]
    assert cc == EXPECTED_VERSION, f"CC version {cc} != {EXPECTED_VERSION}"
    assert codex == EXPECTED_VERSION, f"Codex version {codex} != {EXPECTED_VERSION}"
    assert cursor == EXPECTED_VERSION, f"Cursor version {cursor} != {EXPECTED_VERSION}"


def test_sample_skill_present():
    skill = PLUGIN / "skills" / "ping" / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---")
    # name: is intentionally absent — the directory name is canonical (#23)
    assert "description:" in text
