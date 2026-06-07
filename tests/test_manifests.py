import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_json(rel):
    p = ROOT / rel
    assert p.exists(), f"missing manifest: {rel}"
    return json.loads(p.read_text(encoding="utf-8"))


def test_cc_marketplace():
    m = load_json(".claude-plugin/marketplace.json")
    assert m["name"] == "workato-toolkit"
    assert m["owner"]["name"]
    assert any(p.get("source") == "./" for p in m["plugins"])


def test_cc_plugin():
    p = load_json(".claude-plugin/plugin.json")
    assert p["name"] == "workato-toolkit"
    assert p["version"]
    assert p["description"]


def test_cursor_marketplace():
    m = load_json(".cursor-plugin/marketplace.json")
    assert m["name"] == "workato-toolkit"
    assert m["owner"]["name"]
    assert m["plugins"]


def test_cursor_plugin():
    p = load_json(".cursor-plugin/plugin.json")
    assert p["name"] == "workato-toolkit"


def test_codex_plugin():
    p = load_json(".codex-plugin/plugin.json")
    assert p["name"] == "workato-toolkit"
    assert p["version"]
    assert p["description"]


def test_codex_marketplace():
    m = load_json(".agents/plugins/marketplace.json")
    assert m["name"] == "workato-toolkit"
    entry = m["plugins"][0]
    assert entry["source"]["source"]
    assert entry["policy"]["installation"]
    assert entry["category"]


def test_sample_skill_present():
    skill = ROOT / "skills" / "ping" / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name:" in text
    assert "description:" in text
