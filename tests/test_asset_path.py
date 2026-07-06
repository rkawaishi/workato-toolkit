import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent / "plugin" / "mcp" / "docs-overlay"),
)

import assets  # noqa: E402

PLUGIN = Path(__file__).resolve().parent.parent / "plugin"


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
