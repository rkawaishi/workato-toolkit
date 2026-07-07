---
status: done
---

# CC-only 化 + plugin/ 物理隔離 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 配布物を `plugin/` に物理隔離し、root を開発空間(手書き CLAUDE.md / dev/ / scripts / tests)にする。Claude Code 専用化し、他エディタ資材は凍結する。

**Architecture:** spec は [dev/specs/2026-07-06-cc-only-plugin-dev-separation-design.md](../specs/2026-07-06-cc-only-plugin-dev-separation-design.md)。境界原則は「`plugin/` の下 = 利用者に届くもの、root = 開発者のためのもの」。`plugin/` 内の相互参照はすべて plugin-root 相対(`${CLAUDE_PLUGIN_ROOT}` / スクリプト位置基準)なので `git mv` だけで動き続ける。root 側の3つの marketplace が `"./plugin"` を指すよう1回だけ修正する。生成物は `plugin/AGENTS.md` のみに縮小。

**Tech Stack:** Python 3.11+(pytest, 標準ライブラリのみ)、bash、git、GitHub Actions。

**前提:**
- 作業ブランチ: `claude/gallant-mahavira-597e63`(worktree)。ベース: `52048b9`。
- テストは常に repo root から `python3 -m pytest tests/ -q` で実行。
- **RED コミットを許容する**(このリポジトリの流儀: P5 の `b917044 test(p5): add release-prep guards (RED)` と同様、ガードを先にコミットし、後続タスクで GREEN にする)。
- 各タスク末尾の「期待されるテスト状態」で進捗を検証すること。

---

### Task 1: dev/ に開発ドキュメントを取り込む

メインチェックアウト(`/Users/ryotaro/workspace/workato-toolkit`)の untracked な設計文書・handover を `dev/` にコミットする。

**Files:**
- Create: `dev/plans/`(既存プラン8本+本プラン)
- Create: `dev/specs/2026-06-07-workato-toolkit-plugin-distribution-design.md`
- Create: `dev/specs/2026-06-07-workato-toolkit-plugin-distribution-prfaq.md`
- Create: `dev/handovers/`(4本)

- [ ] **Step 1: コピー実行**

```bash
mkdir -p dev/plans dev/handovers
cp /Users/ryotaro/workspace/workato-toolkit/superpowers/*-plan.md dev/plans/
cp /Users/ryotaro/workspace/workato-toolkit/superpowers/2026-06-07-workato-toolkit-plugin-distribution-design.md dev/specs/
cp /Users/ryotaro/workspace/workato-toolkit/superpowers/specs/2026-06-07-workato-toolkit-plugin-distribution-prfaq.md dev/specs/
cp /Users/ryotaro/workspace/workato-toolkit/.claude/handovers/*.md dev/handovers/
```

注意: `*.html`(生成ビジュアライズ)は対象外。glob が `.md` のみなので自然に除外される。

- [ ] **Step 2: 取り込み結果を確認**

```bash
ls dev/plans/ | wc -l   # 9 (既存8本 + 本プラン。本プランが未保存なら 8)
ls dev/specs/           # 3 ファイル (本設計 + distribution-design + prfaq)
ls dev/handovers/ | wc -l  # 4
```

- [ ] **Step 3: コミット**

```bash
git add dev/
git commit -m "docs(dev): import untracked design docs, plans, handovers into dev/"
```

---

### Task 2: 新レイアウトを規定するテストガードを書く(RED)

既存テスト7本をすべて新レイアウト(`plugin/` 基点・凍結・CC-only)前提に書き換え、レイアウトガード `tests/test_repo_layout.py` を新設する。このタスク終了時点では大量に FAIL する(= RED)。Task 3〜6 で GREEN にする。

**Files:**
- Create: `tests/test_repo_layout.py`
- Rewrite: `tests/test_derived_sync.py`, `tests/test_manifests.py`, `tests/test_release_p5.py`
- Modify(パス基点のみ): `tests/test_docs_migration.py`, `tests/test_overlay.py`, `tests/test_skills_migration.py`, `tests/test_rules_agents_hooks_migration.py`

- [ ] **Step 1: `tests/test_repo_layout.py` を新規作成**(全文)

```python
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
```

- [ ] **Step 2: `tests/test_derived_sync.py` を全面書き換え**(全文)

```python
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN = REPO / "plugin"


def _run_generator():
    r = subprocess.run(
        ["python3", str(REPO / "scripts" / "sync_derived.py")],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert r.returncode == 0, f"generator failed: {r.stderr}"
    return r


def test_generator_runs_idempotent():
    _run_generator()
    _run_generator()  # 2回目も成功（冪等）


def test_agents_md_generated():
    _run_generator()
    f = PLUGIN / "AGENTS.md"
    assert f.is_file(), "plugin/AGENTS.md not generated"
    text = f.read_text(encoding="utf-8")
    assert "AUTO-GENERATED by scripts/sync_derived.py" in text
    assert "Workato Recipe JSON Format" in text
    assert "SessionStart hook" in text
    # CC-only: 他エディタ配信経路の文言は製品イントロから除去済み
    assert "Gemini via this GEMINI.md" not in text
    assert "alwaysApply .mdc" not in text
    # 旧 submodule 前提の記述が紛れ込んでいない
    assert "git submodule update --remote kit" not in text
    assert "bash kit/setup.sh" not in text


def test_generator_does_not_touch_frozen_or_root_claude_md():
    """凍結資材（.mdc/.toml/GEMINI.md）と root CLAUDE.md は生成器の対象外。"""
    _run_generator()
    r = subprocess.run(
        ["git", "status", "--porcelain",
         "plugin/rules/", "plugin/agents/", "plugin/GEMINI.md", "CLAUDE.md"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    dirty = [l for l in r.stdout.splitlines()
             if l.endswith(".mdc") or l.endswith(".toml")
             or l.split()[-1] in ("plugin/GEMINI.md", "CLAUDE.md")]
    assert not dirty, f"generator touched frozen files: {dirty}"


def test_frozen_assets_still_present():
    frozen = [
        PLUGIN / "GEMINI.md",
        PLUGIN / "agents" / "workato-builder.toml",
        PLUGIN / "hooks" / "cursor.hooks.json",
        PLUGIN / "hooks" / "codex.hooks.json",
        PLUGIN / ".cursor-plugin" / "plugin.json",
        PLUGIN / ".codex-plugin" / "plugin.json",
        PLUGIN / ".codex.mcp.json",
        REPO / ".cursor-plugin" / "marketplace.json",
        REPO / ".agents" / "plugins" / "marketplace.json",
    ]
    for p in frozen:
        assert p.is_file(), f"frozen asset missing: {p}"
    mdc = list((PLUGIN / "rules").glob("*.mdc"))
    assert len(mdc) >= 10, f"frozen .mdc set incomplete: {len(mdc)}"


def test_derived_file_in_sync_with_source():
    """生成器を走らせてもコミット済みの plugin/AGENTS.md に差分が出ない。"""
    _run_generator()
    r = subprocess.run(
        ["git", "status", "--porcelain", "plugin/AGENTS.md"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    assert not r.stdout.strip(), f"plugin/AGENTS.md out of sync: {r.stdout}"


def test_sync_check_workflow_pins_new_scope():
    wf = REPO / ".github" / "workflows" / "sync-check.yml"
    assert wf.is_file()
    text = wf.read_text(encoding="utf-8")
    assert "scripts/sync_derived.py" in text
    assert "git diff --exit-code" in text
    assert "plugin/AGENTS.md" in text, "drift scope must cover the new derived path"
```

- [ ] **Step 3: `tests/test_manifests.py` を全面書き換え**(全文)

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugin"


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


def test_sample_skill_present():
    skill = PLUGIN / "skills" / "ping" / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name:" in text
    assert "description:" in text
```

- [ ] **Step 4: `tests/test_release_p5.py` を書き換え**(全文。GUIDES/manifest のパス変更 + README を CC-only 前提に + release.yml の新スコープを固定)

```python
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDES = ROOT / "plugin" / "docs" / "guides"
README = ROOT / "README.md"

# S4 legacy distribution tokens — must be gone from user-facing docs. Covers the
# old submodule/setup.sh model AND old per-editor workspace paths (rules/skills
# lived under .claude/ .cursor/ .gemini/ .agents/ via symlink/copy); under the
# plugin model those live inside the plugin, reached via always-on rules / the MCP.
_LEGACY = re.compile(
    r"submodule|setup\.sh|sync_agents\.py|framework/|@local"
    r"|@\.claude/|\.claude/(?:rules|skills|CLAUDE\.md)|\.cursor/(?:rules|skills)/"
    r"|\.gemini/skills/|\.agents/skills/"
)

EXPECTED_VERSION = "0.1.0"


def _doc_files():
    # root CLAUDE.md（手書き開発コンテキスト）も走査対象に含める — 開発文書にも
    # stale パスは混入しうる（spec §7）。plugin/AGENTS.md は rules 真ソース由来の
    # 既存 stale 参照を含むため対象外（rules 内容の再編は issue #6 / スコープ外）。
    return [README, ROOT / "CLAUDE.md"] + sorted(GUIDES.glob("*.md"))


def test_no_legacy_distribution_refs_in_docs():
    offenders = []
    for p in _doc_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _LEGACY.search(line):
                offenders.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not offenders, "legacy submodule/setup.sh refs remain:\n" + "\n".join(offenders)


def _load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_manifest_versions_bumped_and_consistent():
    cc = _load("plugin/.claude-plugin/plugin.json")["version"]
    codex = _load("plugin/.codex-plugin/plugin.json")["version"]
    cursor = _load("plugin/.cursor-plugin/plugin.json")["version"]
    assert cc == EXPECTED_VERSION, f"CC version {cc} != {EXPECTED_VERSION}"
    assert codex == EXPECTED_VERSION, f"Codex version {codex} != {EXPECTED_VERSION}"
    assert cursor == EXPECTED_VERSION, f"Cursor version {cursor} != {EXPECTED_VERSION}"


def test_release_workflow_shape():
    wf = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "on:" in wf and "tags:" in wf, "release.yml must trigger on tags"
    assert "scripts/sync_derived.py" in wf, "release.yml must verify derived sync"
    assert "pytest" in wf, "release.yml must run the test suite"
    assert "release" in wf.lower(), "release.yml must publish a release"
    assert "plugin/AGENTS.md" in wf, "drift scope must cover the new derived path"


def test_readme_covers_cc_install_and_freeze():
    text = README.read_text(encoding="utf-8")
    # Claude Code is the (only) supported install path
    assert "/plugin marketplace add rkawaishi/workato-toolkit" in text
    assert "/plugin install workato-toolkit@workato-toolkit" in text
    # non-CC editors are explicitly on hold, with no active install steps advertised
    assert "on hold" in text.lower()
    assert "codex plugin marketplace add" not in text
    # security defense-in-depth is documented (editor-agnostic hardening stays)
    assert "permissions" in text and "deny" in text
    assert ".codexignore" in text
```

- [ ] **Step 5: 残り4本のパス基点を修正**(いずれも該当行のみの Edit)

`tests/test_docs_migration.py`:

```python
# 旧
DOCS = REPO / "docs"
...
sys.path.insert(0, str(REPO / "mcp" / "docs-overlay"))
# 新
DOCS = REPO / "plugin" / "docs"
...
sys.path.insert(0, str(REPO / "plugin" / "mcp" / "docs-overlay"))
```

`tests/test_overlay.py`:

```python
# 旧
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp" / "docs-overlay"))
# 新
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugin" / "mcp" / "docs-overlay"))
```

`tests/test_skills_migration.py`:

```python
# 旧
SKILLS = REPO / "skills"
# 新
SKILLS = REPO / "plugin" / "skills"
```

`tests/test_rules_agents_hooks_migration.py`(5箇所):

```python
# 旧 → 新
RULES = REPO / "rules"                      → RULES = REPO / "plugin" / "rules"
BIN = REPO / "bin"                          → BIN = REPO / "plugin" / "bin"
PATTERNS = REPO / "credential-patterns.txt" → PATTERNS = REPO / "plugin" / "credential-patterns.txt"
AGENTS = REPO / "agents"                    → AGENTS = REPO / "plugin" / "agents"
HOOKS = REPO / "hooks"                      → HOOKS = REPO / "plugin" / "hooks"
```

同ファイルの `test_session_start_rules_emits_context` 内:

```python
# 旧
env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(REPO))
# 新
env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(REPO / "plugin"))
```

- [ ] **Step 6: RED を確認**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -5`
Expected: 大量 FAIL(collection error 含む可能性あり — `test_docs_migration.py` は import 時に `plugin/mcp` を sys.path に足すため、移動前は `import overlay` が ModuleNotFoundError で collection error になる。これも RED として正常)。**PASS してはならないテスト**が PASS していたら書き換え漏れ。

なお `test_no_legacy_distribution_refs_in_docs` は、root CLAUDE.md が旧生成物(`@.claude/rules/` 参照を含む)である間は FAIL し続け、Task 5 の手書き化で GREEN になる。

- [ ] **Step 7: RED コミット**

```bash
git add tests/
git commit -m "test(restructure): encode plugin/ layout + freeze + CC-only guards (RED)"
```

---

### Task 3: 物理移動 + marketplace 修正 + 開発用 .mcp.json(コア GREEN)

**Files:**
- Move: `skills/ docs/ rules/ agents/ bin/ hooks/ mcp/ credential-patterns.txt .mcp.json AGENTS.md GEMINI.md .claude-plugin/plugin.json .cursor-plugin/plugin.json .codex-plugin/ .codex.mcp.json` → `plugin/` 配下
- Modify: `.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`, `.agents/plugins/marketplace.json`
- Create: `.mcp.json`(root、開発用)

- [ ] **Step 1: git mv 一括実行**

```bash
mkdir -p plugin/.claude-plugin plugin/.cursor-plugin
git mv skills docs rules agents bin hooks mcp credential-patterns.txt plugin/
git mv .mcp.json plugin/.mcp.json
git mv AGENTS.md plugin/AGENTS.md
git mv GEMINI.md plugin/GEMINI.md
git mv .claude-plugin/plugin.json plugin/.claude-plugin/plugin.json
git mv .cursor-plugin/plugin.json plugin/.cursor-plugin/plugin.json
git mv .codex-plugin plugin/.codex-plugin
git mv .codex.mcp.json plugin/.codex.mcp.json
```

注意: root の `CLAUDE.md` は**動かさない**(Task 5 で手書き版に置き換えるまで旧内容のまま残る)。

- [ ] **Step 2: `.claude-plugin/marketplace.json` の source を修正**

```json
{
  "name": "workato-toolkit",
  "owner": { "name": "rkawaishi", "url": "https://github.com/rkawaishi/workato-toolkit" },
  "plugins": [
    {
      "name": "workato-toolkit",
      "source": "./plugin",
      "description": "Workato development toolkit for AI coding agents"
    }
  ]
}
```

- [ ] **Step 3: `.cursor-plugin/marketplace.json` の source を修正**(凍結の1回限り例外)

`"source": "."` → `"source": "./plugin"`(他フィールドは不変)。

- [ ] **Step 4: `.agents/plugins/marketplace.json` の source.path を修正**(凍結の1回限り例外)

`"source": { "source": "local", "path": "./" }` → `"source": { "source": "local", "path": "./plugin" }`(他フィールドは不変)。

- [ ] **Step 5: root に開発用 `.mcp.json` を新規作成**(全文)

```json
{
  "mcpServers": {
    "workato-docs-dev": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp", "python", "plugin/mcp/docs-overlay/server.py"]
    }
  }
}
```

(プロジェクトスコープの `.mcp.json` は repo root を cwd に起動するため相対パスで良い。サーバ名を `workato-docs-dev` にして、プラグイン併存時の `workato-docs` と衝突させない。)

- [ ] **Step 6: 部分 GREEN を確認**

Run: `python3 -m pytest tests/test_repo_layout.py tests/test_manifests.py tests/test_skills_migration.py tests/test_docs_migration.py tests/test_overlay.py tests/test_rules_agents_hooks_migration.py -q 2>&1 | tail -3`
Expected: `test_repo_layout.py` は **`test_root_claude_md_is_handwritten_dev_context` のみ FAIL**(CLAUDE.md はまだ旧生成物)、他はすべて PASS。

Run: `python3 -m pytest tests/test_derived_sync.py tests/test_release_p5.py -q 2>&1 | tail -3`
Expected: FAIL のまま(生成器と README が未対応)。

- [ ] **Step 7: コミット**

```bash
git add -A
git commit -m "refactor(restructure): move distributed tree under plugin/; point marketplaces at ./plugin; add dev .mcp.json"
```

---

### Task 4: sync_derived.py を縮小し plugin/AGENTS.md を再生成

**Files:**
- Rewrite: `scripts/sync_derived.py`
- Regenerate: `plugin/AGENTS.md`

- [ ] **Step 1: `scripts/sync_derived.py` を全面書き換え**(全文)

```python
#!/usr/bin/env python3
"""sync_derived.py — Generate plugin/AGENTS.md from plugin/rules/*.md.

Claude Code is the only supported editor (dev/specs/2026-07-06, D1/D2), so
the single derived file is plugin/AGENTS.md — the payload injected by
plugin/bin/session-start-rules as SessionStart additionalContext.

Frozen per-editor artifacts are NOT generated or touched anymore:
plugin/rules/*.mdc, plugin/agents/*.toml, plugin/GEMINI.md, the cursor/codex
hooks variants and manifests. To revive an editor, restore its generators
from git history (scripts/sync_derived.py prior to 2026-07) and re-verify
on the real editor.

Run from repo root:  python3 scripts/sync_derived.py
CI (sync-check.yml) runs this then `git diff --exit-code` to detect drift.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPO_ROOT / "plugin"
RULES_DIR = PLUGIN_ROOT / "rules"


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter, body) where both exclude the '---' delimiters.

    The first '---' line opens the frontmatter; the next '---' line closes it.
    If the file does not start with '---', or no closing '---' is found, the
    entire text is treated as body.
    """
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return "", text
    for i in range(1, len(lines)):
        if lines[i] == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
    return "", text


def trim_trailing_newlines(text: str) -> str:
    """Mimic bash command-substitution: strip trailing newlines."""
    return text.rstrip("\n")


_HEADING_RE = re.compile(r"^(#+) ")


def demote_headings(text: str, levels: int = 1) -> str:
    """Increase the heading depth of every Markdown heading by *levels*.

    Lines inside fenced code blocks are left untouched.
    """
    out: list[str] = []
    fence = False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if not fence:
            m = _HEADING_RE.match(line)
            if m:
                line = ("#" * levels) + line
        out.append(line)
    return "\n".join(out)


CONTEXT_INTRO = """\
Workato development toolkit for AI coding agents. The rules below are the
always-on knowledge base for building on Workato (recipes, Workflow Apps,
AI agents, custom connectors). They are delivered automatically via the
plugin's SessionStart hook (bin/session-start-rules).

Knowledge-base documents (connectors, logic, platform, patterns) are NOT in
this file — fetch them through the docs-overlay MCP tools
`workato_docs_lookup(path)` / `workato_docs_list(prefix)` (org overrides win).
"""


def _context_body() -> str:
    parts = [
        "<!-- AUTO-GENERATED by scripts/sync_derived.py — DO NOT EDIT MANUALLY.",
        "     Source: plugin/rules/*.md -->",
        "",
        CONTEXT_INTRO,
    ]
    for src in sorted(RULES_DIR.glob("*.md")):
        _, body = split_frontmatter(src.read_text(encoding="utf-8"))
        parts.append(demote_headings(trim_trailing_newlines(body), levels=1))
        parts.append("")
    return "\n".join(parts)


def sync_context() -> None:
    out = PLUGIN_ROOT / "AGENTS.md"
    out.write_text(
        "# Workato Toolkit — Agent Context\n\n" + _context_body() + "\n",
        encoding="utf-8",
    )
    print("  ok plugin/AGENTS.md")


def main() -> None:
    sync_context()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 生成器を実行して plugin/AGENTS.md を更新**

Run: `python3 scripts/sync_derived.py`
Expected: `  ok plugin/AGENTS.md` のみ出力。`git status --porcelain` の差分が `scripts/sync_derived.py` と `plugin/AGENTS.md` の2ファイルだけであること(凍結 `.mdc` / `.toml` / `GEMINI.md` に差分が出たら失敗)。

- [ ] **Step 3: コミット**(先にコミットする — `test_derived_file_in_sync_with_source` は「コミット済み内容と生成結果の一致」を検査するため、コミット前は必ず FAIL する)

```bash
git add scripts/sync_derived.py plugin/AGENTS.md
git commit -m "refactor(sync): shrink generator to plugin/AGENTS.md only; freeze per-editor outputs"
```

- [ ] **Step 4: derived_sync テストが GREEN**

Run: `python3 -m pytest tests/test_derived_sync.py -q`
Expected: `test_sync_check_workflow_pins_new_scope` **のみ** FAIL(CI は Task 6)、他はすべて PASS。

---

### Task 5: root CLAUDE.md を手書き開発コンテキストに置き換え + README 改稿

**Files:**
- Rewrite: `CLAUDE.md`(root)
- Rewrite: `README.md`

- [ ] **Step 1: root `CLAUDE.md` を全面置き換え**(全文)

```markdown
# workato-toolkit — Development Context

This file is for **developing this repository** and is hand-written — edit it freely.
End users never load it: the plugin delivers its rules via the SessionStart hook
(`plugin/bin/session-start-rules` injects `plugin/AGENTS.md`).

## What this repository is

A Workato development toolkit distributed as a **Claude Code plugin**. Claude Code is
the only officially supported editor; Cursor / Codex / Gemini assets are frozen (below).

## Boundary principle

> **Everything under `plugin/` ships to users. Everything else exists to develop the plugin.**

- `plugin/` — the plugin root (`${CLAUDE_PLUGIN_ROOT}` after install): skills, the
  knowledge base (`plugin/docs/`, served by the docs-overlay MCP), always-on rules,
  agents, hook scripts (`plugin/bin/`), hooks config, MCP server, manifests.
- Repo root — development space: `scripts/`, `tests/`, `.github/`, `dev/`, this file,
  and `.claude-plugin/marketplace.json` (marketplaces resolve from the repo root; its
  `source` points at `./plugin`).

## Source of truth vs generated files

- **Source (edit these):** `plugin/rules/*.md` — the always-on rules.
- **Generated (never edit):** `plugin/AGENTS.md`, regenerated by
  `python3 scripts/sync_derived.py`.
- After editing rules: `python3 scripts/sync_derived.py && python3 -m pytest tests/ -q`.
- CI: `sync-check.yml` fails PRs whose derived file drifted. `release.yml` publishes a
  GitHub Release on `v*` tags. The version lives in `plugin/.claude-plugin/plugin.json`.

## Frozen assets (do not touch)

Cursor / Codex / Gemini support is on hold. These files stay in the tree but are not
generated, maintained, or verified:

- `plugin/rules/*.mdc`, `plugin/agents/*.toml`, `plugin/GEMINI.md`
- `plugin/hooks/cursor.hooks.json`, `plugin/hooks/codex.hooks.json`
- `plugin/.cursor-plugin/plugin.json`, `plugin/.codex-plugin/`, `plugin/.codex.mcp.json`
- `.cursor-plugin/marketplace.json`, `.agents/plugins/marketplace.json` (repo root)

To revive an editor: restore its generators from git history (`scripts/sync_derived.py`
prior to 2026-07), regenerate, and verify on the real editor before advertising support.

## Development documents

- Design specs → `dev/specs/` · implementation plans → `dev/plans/` · session
  handovers → `dev/handovers/`. These locations override any skill defaults
  (e.g. `docs/superpowers/...`).
- Never put development docs under `plugin/docs/` — that tree is product content served
  to users through the docs-overlay MCP.

## Verifying the plugin locally

- Dev MCP: the root `.mcp.json` starts the docs-overlay server (`workato-docs-dev`)
  from `plugin/mcp/docs-overlay/server.py`, so a dev session can call
  `workato_docs_lookup` directly.
- Self-install smoke: `claude plugin marketplace add <repo-path>` →
  `claude plugin install workato-toolkit@workato-toolkit`; verify the `ping` skill,
  SessionStart rule injection, a docs lookup, and the credential guard. Clean up with
  `claude plugin uninstall` / `claude plugin marketplace remove`.
- Tests: `python3 -m pytest tests/ -q`.
```

- [ ] **Step 2: `README.md` を全面置き換え**(全文)

````markdown
# workato-toolkit

Workato (enterprise iPaaS) development toolkit for AI coding agents, distributed as a
native **Claude Code plugin**.

The toolkit bundles skills, the Workato knowledge base (300+ connectors, logic, platform,
patterns), always-on rules, a credential-guard hook, and a docs-overlay MCP server — all
from one shared tree. Nothing to vendor into your repo and nothing to symlink.

> **Editor support:** Claude Code is the only officially supported editor. Cursor /
> Codex CLI / Gemini CLI support is **on hold** — their assets remain in the tree
> (frozen) but are not maintained or verified.

## Install (Claude Code)

```
/plugin marketplace add rkawaishi/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
```

After install, run the `ping` skill to verify the toolkit is loaded.

## Updating

```
/plugin update workato-toolkit
```

Pin to a release tag where you need reproducibility.

## Repository layout

| Path | What it is |
|---|---|
| `plugin/` | **The distributed plugin** — skills, knowledge base (`plugin/docs/`), always-on rules (`plugin/rules/`), hook scripts (`plugin/bin/`), the docs-overlay MCP. Everything under it ships to users. |
| `.claude-plugin/marketplace.json` | Marketplace definition (resolved from the repo root; its `source` points at `./plugin`). |
| `scripts/`, `tests/`, `.github/`, `dev/`, `CLAUDE.md` | Development tooling and documents for building the toolkit itself. Not part of the product surface. |
| Frozen editor assets | `plugin/rules/*.mdc`, `plugin/agents/*.toml`, `plugin/GEMINI.md`, the cursor/codex hooks variants and manifests, `.cursor-plugin/`, `.agents/` — kept for a future revival, not maintained. |

## Security hardening (recommended)

The plugin ships a credential-guard hook that blocks an agent from surfacing secret-file
contents. Because a plugin cannot distribute an editor deny-list, add defense-in-depth to
**your workspace repo**:

### Claude Code — `.claude/settings.json`
```json
{
  "permissions": {
    "deny": [
      "Read(./**/master.key)",
      "Read(./**/settings.yaml)",
      "Read(./**/settings.yaml.enc)",
      "Read(./**/.resource-providers.yml)",
      "Read(./**/.env)",
      "Read(./**/.env.*)",
      "Read(./**/*.key)",
      "Read(./**/*.pem)",
      "Read(./**/*.secret)",
      "Read(./**/*.credential*)"
    ]
  }
}
```

### Other editors — `.codexignore` / `.cursorignore` / `.geminiignore`
If you nonetheless use a frozen editor, create the matching ignore file at your
workspace root:
```gitignore
master.key
settings.yaml
settings.yaml.enc
.resource-providers.yml
.env
.env.*
*.key
*.pem
*.secret
*.credential*
```
> `.workatoenv` is intentionally NOT excluded — it holds only project/folder/workspace IDs (no tokens).

## Documentation

Guides live in [`plugin/docs/guides/`](plugin/docs/guides/). Knowledge-base docs are
served on demand through the docs-overlay MCP (`workato_docs_lookup` / `workato_docs_list`).

## License
MIT
````

- [ ] **Step 3: GREEN 確認**

Run: `python3 -m pytest tests/test_repo_layout.py tests/test_release_p5.py -q`
Expected: FAIL は `test_release_workflow_shape`(release.yml の新スコープ未反映)**の1件のみ**。`test_no_legacy_distribution_refs_in_docs` と `test_root_claude_md_is_handwritten_dev_context` がこのタスクで GREEN になっていること。

- [ ] **Step 4: コミット**

```bash
git add CLAUDE.md README.md
git commit -m "docs(restructure): hand-written dev CLAUDE.md at root; README to CC-only + repository layout"
```

---

### Task 6: CI ワークフローの diff スコープ更新

**Files:**
- Modify: `.github/workflows/sync-check.yml`
- Modify: `.github/workflows/release.yml`

- [ ] **Step 1: `sync-check.yml` の drift 検知行を更新**

```yaml
# 旧
          git diff --exit-code -- rules/ agents/ CLAUDE.md AGENTS.md GEMINI.md \
# 新
          git diff --exit-code -- plugin/rules/ plugin/agents/ plugin/AGENTS.md plugin/GEMINI.md CLAUDE.md \
```

(凍結ファイルと root CLAUDE.md をスコープに含めることで、「生成器がそれらを触らない」ことを CI レベルでも担保する。)

- [ ] **Step 2: `release.yml` の同じ行を同じ内容に更新**

```yaml
# 旧
          git diff --exit-code -- rules/ agents/ CLAUDE.md AGENTS.md GEMINI.md \
# 新
          git diff --exit-code -- plugin/rules/ plugin/agents/ plugin/AGENTS.md plugin/GEMINI.md CLAUDE.md \
```

- [ ] **Step 3: 全テスト GREEN 確認**

Run: `python3 -m pytest tests/ -q`
Expected: **全件 PASS**(0 failed)。FAIL が残る場合は該当タスクに戻る。

- [ ] **Step 4: コミット**

```bash
git add .github/workflows/
git commit -m "ci(restructure): point drift scope at plugin/ derived + frozen paths"
```

---

### Task 7: 最終検証(spec 完了条件の消し込み + self-install スモーク)

**Files:**
- Create: `dev/handovers/`(必要なら)ではなく検証記録: `dev/specs/2026-07-06-cc-only-plugin-dev-separation-design.md` は変更しない。検証結果は本プラン末尾に追記する。

- [ ] **Step 1: spec 完了条件 1–2(pytest / drift)**

```bash
python3 -m pytest tests/ -q          # 全件 PASS
python3 scripts/sync_derived.py && git status --porcelain   # 出力なし(差分ゼロ)
```

- [ ] **Step 2: hook 実挙動の直接確認**

```bash
CLAUDE_PLUGIN_ROOT="$(pwd)/plugin" bash plugin/bin/session-start-rules <<< '{}' | head -c 200
```

Expected: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "# Workato Toolkit — Agent Context...` で始まる JSON。

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"cat master.key"}}' | bash plugin/bin/block-credential-read.sh; echo "exit=$?"
```

Expected: `exit=2`(ブロック)。

- [ ] **Step 3: self-install スモーク(spec 完了条件 3)**

```bash
claude plugin marketplace add "$(pwd)"
claude plugin install workato-toolkit@workato-toolkit
claude plugin list   # workato-toolkit 0.1.0 が見えること
```

その後、新しいセッション(`claude -p` 可)で: `ping` スキルが応答する / SessionStart 注入に「Workato Recipe JSON Format」が含まれる / `workato_docs_lookup("connectors/slack.md")` が本文を返す、を確認。

クリーンアップ:

```bash
claude plugin uninstall workato-toolkit
claude plugin marketplace remove workato-toolkit
```

**フォールバック:** `claude plugin` CLI がこの環境で使えない場合は、スモークを P6 Phase A(リリースゲート)の項目として `dev/plans/2026-06-13-workato-toolkit-p6-runtime-release-roadmap-plan.md` の Phase A リストに追記し、本プランの検証記録に「pending (P6-A)」と明記する。

- [ ] **Step 4: 検証記録を本プランに追記してコミット**

本ファイル末尾に「## 検証記録(YYYY-MM-DD)」節を追加し、Step 1–3 の実行結果(コマンド・結果・pending 事項)を記録する。

```bash
git add dev/plans/2026-07-06-cc-only-plugin-separation-plan.md
git commit -m "docs(dev): record restructure verification results"
```

---

## スコープ外(このプランでやらないこと)

- v0.1.0 tag 発行・GitHub リモートからの install 実機検証(P6 Phase A/C)
- `plugin/docs/guides/` 13本の CC-only 文言刷新(ガイドは凍結エディタの手順を記述したまま。P6 以降で扱う)
- skills が参照する `templates/workatoignore.template` / `templates/gitignore/connectors.gitignore` の不存在問題(既存バグ。別タスク)
- `plugin/rules/workato-deployment-flow.md` 等の rules 真ソースに残る `@.claude/rules/` 参照(生成される plugin/AGENTS.md にも流入する既存の stale 参照。rules 内容の再編 = issue #6 の一部として扱う)
- `rules/*.md` の内容再編(issue #6 の未決部分)

---

## 検証記録(2026-07-07)

| 完了条件 | 結果 |
|---|---|
| 1. pytest 全件 PASS | ✅ 74 passed |
| 2. sync_derived 後 drift ゼロ | ✅(`git status --porcelain` 出力なし) |
| 3a. SessionStart hook 注入 | ✅ `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "# Workato Toolkit — Agent Context...` を確認 |
| 3b. credential guard ブロック | ✅ exit=2(`Blocked by workato-dev-kit credential guard: master.key: ...`) |
| 3c. self-install スモーク | ⚠️ 中止(下記所見参照) |
| 4. root CLAUDE.md 手書き・小型 | ✅(3,095 bytes) |
| 5. dev/ コミット済み | ✅(specs 3 / plans 9 / handovers 4) |
| 6. 凍結資材の配置 + README 宣言 | ✅ |

### 所見

- **Step 3c(self-install スモーク)は安全確認の時点で中止した。** `claude plugin marketplace list` を実行したところ、`workato-toolkit` という名前の marketplace が**既にユーザーの環境に登録済み**であることが判明した(`Source: Directory (/Users/ryotaro/workspace/workato-toolkit)` — メインチェックアウトを指しており、本 worktree ではない)。対応する `claude plugin list` でも `workato-toolkit@workato-toolkit`(version 0.0.1, scope local, Status: ✘ disabled)が既にインストール済みだった。
  - marketplace 名は `.claude-plugin/marketplace.json` の `"name": "workato-toolkit"` にハードコードされており、`marketplace add` 実行時に別名を指定するオプションはない。そのため本 worktree をマーケットプレイスとして追加すると、既存登録(実体のあるメインチェックアウトを指す本物の設定)との名前衝突・上書きリスクがある。
  - タスク指示の安全確認手順(「既に存在する場合はスモークを中止し、その旨を報告」)に従い、`marketplace add` / `install` / `uninstall` / `marketplace remove` は一切実行しなかった。実行したのは読み取り専用の `marketplace list` / `plugin list` のみで、既存登録に副作用は無い(事後に再確認済み: エントリは1件のまま、パスも不変)。
  - **これは「pending (P6-A)」(`claude` CLI が使えない場合のフォールバック)とは異なる状況** — CLI は正常に使え、`claude --version` は `2.1.177 (Claude Code)` を返した。今回中止した理由は CLI の欠如ではなく、既存のユーザー環境との衝突回避のためであり、区別して記録する。
  - **代替検証**として、docs-overlay の解決ロジック単体(プラグインのインストール状態に依存しない直接呼び出し)は実行し、成功を確認した:
    ```
    python3 -c "import sys; sys.path.insert(0, 'plugin/mcp/docs-overlay'); import overlay; from pathlib import Path; print(overlay.resolve_doc(Path('plugin/docs'), None, 'connectors/slack.md')[:200])"
    ```
    → `# Slack connector` から始まる本文を返した(NOT FOUND ではない)。
  - **積み残し:** 実際の `marketplace add` → `install` → 新セッションでの `-p` 挙動確認 → `uninstall` → `marketplace remove` という一連の self-install スモークは、メインチェックアウト側の既存 `workato-toolkit` 登録の扱いをユーザーと合意した上で(例: 一時的に別名でエイリアスする、メインチェックアウト側で検証する等)、別途実施する必要がある。P6 Phase A のリリースゲート項目として引き継ぐことを推奨。
