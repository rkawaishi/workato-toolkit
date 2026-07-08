import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / "plugin" / "mcp" / "docs-overlay"),
)

import assets  # noqa: E402

from conftest import PLUGIN  # noqa: E402


def test_known_assets_resolve_to_existing_files():
    for name in ("workato-api.py", "ensure-workatoignore.sh", "workatoignore.template"):
        p = assets.asset_path(PLUGIN, name)
        assert Path(p).is_file(), f"{name} -> {p}"
        assert Path(p).is_absolute()


def test_unknown_asset_rejected():
    out = assets.asset_path(PLUGIN, "nope.txt")
    assert out.startswith("UNKNOWN ASSET"), out
    assert "workato-api.py" in out  # error lists valid names


def test_traversal_rejected():
    out = assets.asset_path(PLUGIN, "../scripts/workato-api.py")
    assert out.startswith("UNKNOWN ASSET")


def test_resolved_assets_stay_under_plugin_root():
    root = PLUGIN.resolve()
    for name in assets.ASSETS:
        p = Path(assets.asset_path(root, name))
        assert p.is_relative_to(root), f"{name} escapes the plugin root: {p}"


# Format-spec rules the builder / references depend on. A subagent cannot load
# always-on rules, so it must reach these through the asset-path tool (issue #22).
FORMAT_RULE_ASSETS = (
    "rules/workato-recipe-format.md",
    "rules/workato-agentic-format.md",
    "rules/workato-connector-sdk.md",
    "rules/workato-project-structure.md",
    "rules/workato-page-components.md",
)


def test_format_rule_assets_resolve_to_existing_files():
    for name in FORMAT_RULE_ASSETS:
        p = assets.asset_path(PLUGIN, name)
        assert not p.startswith("UNKNOWN ASSET"), p
        assert Path(p).is_file(), f"{name} -> {p}"
        assert Path(p).is_absolute()
