import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugin"


def test_api_helper_bundled():
    p = PLUGIN / "scripts" / "workato-api.py"
    assert p.exists(), "plugin must bundle scripts/workato-api.py (39 references in skills/rules/docs)"
    text = p.read_text(encoding="utf-8")
    assert re.search(r'^__version__ = "\d+\.\d+\.\d+"', text, re.M), "helper needs a __version__ stamp"


def test_api_helper_version_flag():
    out = subprocess.run(
        [sys.executable, str(PLUGIN / "scripts" / "workato-api.py"), "--version"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0
    assert re.match(r"workato-api\.py \d+\.\d+\.\d+", out.stdout.strip())


def test_ensure_workatoignore_bundled():
    p = PLUGIN / "scripts" / "ensure-workatoignore.sh"
    assert p.exists()
    assert p.stat().st_mode & 0o111, "must be executable"


def test_workatoignore_template_bundled():
    p = PLUGIN / "templates" / "workatoignore.template"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    for token in ("specs/", "DESIGN.md"):
        assert token in text
