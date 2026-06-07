import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = REPO / "rules"

EXPECTED_RULES = {
    "org-knowledge-overlay",
    "workato-agentic-format",
    "workato-cli-autonomy",
    "workato-cli",
    "workato-connector-sdk",
    "workato-deployment-flow",
    "workato-page-components",
    "workato-project-structure",
    "workato-recipe-format",
}

def test_all_rules_present():
    found = {p.stem for p in RULES.glob("*.md")}
    assert found == EXPECTED_RULES, f"missing/extra: {EXPECTED_RULES ^ found}"

def test_rules_nonempty_with_heading():
    for stem in EXPECTED_RULES:
        text = (RULES / f"{stem}.md").read_text(encoding="utf-8")
        assert len(text) > 200, f"{stem}.md too short"
        assert re.search(r"^# .+", text, re.MULTILINE), f"{stem}.md has no top heading"
