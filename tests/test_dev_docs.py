"""Dev-document lifecycle guards (dev/plans/, dev/specs/) — issue #26.

Every plan/spec carries a status so stale documents can't pose as current:
frontmatter `status: draft | active | done | superseded`, with `superseded_by`
required when superseded. Handovers are point-in-time records — no status.
"""
import re

from conftest import REPO

DEV = REPO / "dev"
ALLOWED_STATUS = {"draft", "active", "done", "superseded"}


def _lifecycle_docs():
    docs = sorted((DEV / "plans").glob("*.md")) + sorted((DEV / "specs").glob("*.md"))
    assert docs, "no docs found under dev/plans or dev/specs — layout broken?"
    return docs


def _frontmatter(text, name):
    assert text.startswith("---\n"), f"{name}: missing YAML frontmatter"
    return text.split("---\n", 2)[1]


def test_plans_and_specs_declare_status():
    for p in _lifecycle_docs():
        fm = _frontmatter(p.read_text(encoding="utf-8"), p.name)
        m = re.search(r"^status:\s*(\S+)\s*$", fm, re.MULTILINE)
        assert m, f"{p.name}: frontmatter has no status field"
        assert m.group(1) in ALLOWED_STATUS, (
            f"{p.name}: status {m.group(1)!r} not in {sorted(ALLOWED_STATUS)}"
        )


def test_superseded_docs_name_their_successor():
    for p in _lifecycle_docs():
        fm = _frontmatter(p.read_text(encoding="utf-8"), p.name)
        if re.search(r"^status:\s*superseded\s*$", fm, re.MULTILINE):
            assert re.search(r"^superseded_by:\s*\S+", fm, re.MULTILINE), (
                f"{p.name}: superseded without superseded_by"
            )


def test_dev_readme_documents_the_convention():
    readme = DEV / "README.md"
    assert readme.is_file(), "dev/README.md (doc index + conventions) missing"
    text = readme.read_text(encoding="utf-8")
    for needle in ("status", "superseded", "handover"):
        assert needle in text, f"dev/README.md must document the {needle} convention"


def test_claude_md_points_at_dev_readme():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert "dev/README.md" in text, (
        "CLAUDE.md's development-documents section must point at dev/README.md "
        "for the lifecycle conventions"
    )
