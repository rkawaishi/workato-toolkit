# P3c: rules / agents / hooks 移植 + 派生生成 + sync-check CI 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 旧 `workato-dev-kit/framework/claude/{rules,agents,hooks,settings.json}` を新 toolkit の共有ツリー（`rules/` `agents/` `bin/` `hooks/`）へ移植し、派生ファイル（Cursor `.mdc` / Codex agent `.toml` / 常時ルール context `CLAUDE.md`・`AGENTS.md`・`GEMINI.md` / hooks json 3種 + SessionStart 配線）を1つの生成器から作り、`sync-check.yml` でドリフトを検知する。

**Architecture:** 共有ツリー型（design §3）。canonical source は `rules/*.md`・`agents/*.md`・`bin/*.sh`（手編集）。`scripts/sync_derived.py` がそこから派生ファイルを生成（旧 `scripts/sync_agents.py` の縮小版 — skills は P3b で1式共有済なので per-editor skill 生成は不要、rules/agent/context のみ）。skills 本文の `@.claude/rules/X.md` は常時配信される前提で「`X` ルール（常時）」参照へ全エディタ共通で書換（per-editor 書換なし＝skills 共有を維持）。credential guard hook は全エディタ同梱。

**Tech Stack:** Python 3（生成器・テスト pytest）、bash（hook 実体）、JSON（hooks/manifest）、TOML（Codex agent）、GitHub Actions（CI）。

**移植元（凍結・read-only。改変厳禁）:**
- `/Users/ryotaro/workspace/workato-dev-kit/framework/claude/rules/*.md`（9本）
- `/Users/ryotaro/workspace/workato-dev-kit/framework/claude/agents/workato-builder.md`（1本）
- `/Users/ryotaro/workspace/workato-dev-kit/framework/claude/hooks/{block-credential-read.sh,validate-before-push.sh,sync-docs-after-sdk-push.sh}`（3本）
- `/Users/ryotaro/workspace/workato-dev-kit/framework/credential-patterns.txt`
- `/Users/ryotaro/workspace/workato-dev-kit/framework/claude/settings.json`（hooks/permissions の参照仕様）
- `/Users/ryotaro/workspace/workato-dev-kit/scripts/sync_agents.py`（生成ロジックの母体。pure helper を流用）
- `/Users/ryotaro/workspace/workato-dev-kit/framework/codex/agents/workato-builder.toml`（Codex `.toml` の期待フォーマット実例）

**スコープ外（明示）:**
- 学習 WRITE サイクル（`/learn-*` の `org/docs/` 書込み、auto-learn/sync-connectors の kit docs 書込み再設計）= **P4**。
- SessionStart hook の **実機 runtime 検証**（実際に context 注入されるか）= P4 / 実機検証。本 plan は成果物生成と静的整合テストまで。
- `permissions.deny` スニペット・`.cursorignore`/`.codexignore`/`.geminiignore` の install ドキュメント掲載 = **P5**（README）。
- 旧 submodule/`setup.sh` 前提の install 手順記述 = **P5**。
- Gemini 実機同居検証（design §6.2.4）= 後続。本 plan は `GEMINI.md` 生成までは行う（MVP context）。

**全体方針メモ（実装者向け）:**
- すべての git/ファイル操作の前に `git rev-parse --show-toplevel` で `/Users/ryotaro/workspace/workato-toolkit` に居ることを確認（旧 repo 誤操作防止）。
- ブランチ: `feat/p3c-rules-agents-hooks-derived` を `main` から作成してから着手。
- コミット trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`。
- テストは `tests/test_rules_agents_hooks_migration.py` に集約（既存 `test_*_migration.py` と同様の整合テスト方式）。

---

### Task 1: rules（9本）を `rules/` へ移植 + 整合テスト

**Files:**
- Create: `rules/org-knowledge-overlay.md`, `rules/workato-agentic-format.md`, `rules/workato-cli-autonomy.md`, `rules/workato-cli.md`, `rules/workato-connector-sdk.md`, `rules/workato-deployment-flow.md`, `rules/workato-page-components.md`, `rules/workato-project-structure.md`, `rules/workato-recipe-format.md`（旧 repo から verbatim コピー）
- Test: `tests/test_rules_agents_hooks_migration.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_rules_agents_hooks_migration.py
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
        # 本文に少なくとも1つの '# ' 見出しがある（生成器が description を取れる）
        assert re.search(r"^# .+", text, re.MULTILINE), f"{stem}.md has no top heading"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `cd /Users/ryotaro/workspace/workato-toolkit && python3 -m pytest tests/test_rules_agents_hooks_migration.py -v`
Expected: FAIL（`rules/` が存在しない）

- [ ] **Step 3: rules を verbatim コピー**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
test "$(git rev-parse --show-toplevel)" = "/Users/ryotaro/workspace/workato-toolkit" || { echo "WRONG REPO"; exit 1; }
mkdir -p rules
cp /Users/ryotaro/workspace/workato-dev-kit/framework/claude/rules/*.md rules/
ls -1 rules/
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py -v`
Expected: PASS（2 tests）

- [ ] **Step 5: コミット**

```bash
git add rules/ tests/test_rules_agents_hooks_migration.py
git commit -m "feat(rules): migrate 9 workato rules to shared rules/ (P3c)"
```

---

### Task 2: agent（workato-builder）を `agents/` へ移植

**Files:**
- Create: `agents/workato-builder.md`（旧 repo から verbatim コピー）
- Test: `tests/test_rules_agents_hooks_migration.py`（追記）

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_rules_agents_hooks_migration.py に追記
AGENTS = REPO / "agents"

def test_agent_md_present():
    md = AGENTS / "workato-builder.md"
    assert md.is_file(), "agents/workato-builder.md missing"
    text = md.read_text(encoding="utf-8")
    # YAML frontmatter に name/description がある
    assert text.startswith("---"), "agent md missing frontmatter"
    assert re.search(r"^name: workato-builder\s*$", text, re.MULTILINE)
    assert re.search(r"^description: ", text, re.MULTILINE)
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py::test_agent_md_present -v`
Expected: FAIL

- [ ] **Step 3: agent を verbatim コピー**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
mkdir -p agents
cp /Users/ryotaro/workspace/workato-dev-kit/framework/claude/agents/workato-builder.md agents/
```

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py::test_agent_md_present -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add agents/ tests/test_rules_agents_hooks_migration.py
git commit -m "feat(agents): migrate workato-builder agent to shared agents/ (P3c)"
```

---

### Task 3: hook 実体スクリプト3本 + credential-patterns.txt を移植 + パス解決を修正

**背景:** 旧 `block-credential-read.sh` は `PATTERNS_FILE="$(dirname "$SCRIPT_PATH")/../../credential-patterns.txt"` で patterns を解決していた（旧レイアウト `framework/claude/hooks/` から `../../` = `framework/`）。新レイアウトでは hook を `bin/` に置き、`credential-patterns.txt` を repo root に置くので、相対は `../credential-patterns.txt`（`bin/` → repo root）に変える。**この1行だけが移植時の必要改変**。他は verbatim。

**Files:**
- Create: `bin/block-credential-read.sh`, `bin/validate-before-push.sh`, `bin/sync-docs-after-sdk-push.sh`, `credential-patterns.txt`
- Modify: `bin/block-credential-read.sh`（patterns パス1行）
- Test: `tests/test_rules_agents_hooks_migration.py`（追記）

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_rules_agents_hooks_migration.py に追記
import os, subprocess, json

BIN = REPO / "bin"
PATTERNS = REPO / "credential-patterns.txt"

EXPECTED_HOOKS = {
    "block-credential-read.sh",
    "validate-before-push.sh",
    "sync-docs-after-sdk-push.sh",
}

def test_hook_scripts_present_and_executable():
    for name in EXPECTED_HOOKS:
        p = BIN / name
        assert p.is_file(), f"bin/{name} missing"
        assert os.access(p, os.X_OK), f"bin/{name} not executable"

def test_credential_patterns_present():
    assert PATTERNS.is_file(), "credential-patterns.txt missing at repo root"
    body = PATTERNS.read_text(encoding="utf-8")
    for pat in ("master.key", "settings.yaml", "*.key", "*.pem"):
        assert pat in body, f"pattern {pat} missing"

def test_block_hook_resolves_patterns_from_repo_root():
    # bin/ から見た patterns 相対は ../credential-patterns.txt
    src = (BIN / "block-credential-read.sh").read_text(encoding="utf-8")
    assert "/../credential-patterns.txt" in src, "patterns path not adjusted for bin/ layout"
    assert "/../../credential-patterns.txt" not in src, "old framework/ relative path still present"

def test_block_hook_blocks_cat_master_key():
    # 実際に発火: Bash で `cat master.key` を流すと exit 2（ブロック）になる
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "cat master.key"},
    })
    r = subprocess.run(
        ["bash", str(BIN / "block-credential-read.sh")],
        input=payload, capture_output=True, text=True,
    )
    assert r.returncode == 2, f"expected block (exit 2), got {r.returncode}: {r.stderr}"

def test_block_hook_allows_plain_command():
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
    })
    r = subprocess.run(
        ["bash", str(BIN / "block-credential-read.sh")],
        input=payload, capture_output=True, text=True,
    )
    assert r.returncode == 0, f"expected allow (exit 0), got {r.returncode}: {r.stderr}"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py -k "hook or credential or block" -v`
Expected: FAIL

- [ ] **Step 3: hook 3本 + patterns をコピーし、パスを修正**

```bash
cd /Users/ryotaro/workspace/workato-toolkit
mkdir -p bin
cp /Users/ryotaro/workspace/workato-dev-kit/framework/claude/hooks/block-credential-read.sh bin/
cp /Users/ryotaro/workspace/workato-dev-kit/framework/claude/hooks/validate-before-push.sh bin/
cp /Users/ryotaro/workspace/workato-dev-kit/framework/claude/hooks/sync-docs-after-sdk-push.sh bin/
cp /Users/ryotaro/workspace/workato-dev-kit/framework/credential-patterns.txt credential-patterns.txt
chmod +x bin/*.sh
```

`bin/block-credential-read.sh` の patterns 解決行を Edit で1箇所修正:

```
# 変更前
PATTERNS_FILE="$(dirname "$SCRIPT_PATH")/../../credential-patterns.txt"
# 変更後
PATTERNS_FILE="$(dirname "$SCRIPT_PATH")/../credential-patterns.txt"
```

同ファイル内のコメント `framework/credential-patterns.txt` への言及（メッセージ文 `kit/framework/credential-patterns.txt` 等）は機能に影響しないが、`credential-patterns.txt` 表記へ揃える（deny メッセージの可読性のため）。具体的には deny() 内の `see kit/framework/credential-patterns.txt` を `see credential-patterns.txt` に、ヘッダコメントの `framework/credential-patterns.txt` を `credential-patterns.txt` に置換。

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py -k "hook or credential or block" -v`
Expected: PASS（5 tests）

- [ ] **Step 5: コミット**

```bash
git add bin/ credential-patterns.txt tests/test_rules_agents_hooks_migration.py
git commit -m "feat(hooks): migrate credential-guard/validate/sync-docs hooks to bin/ + repo-root patterns (P3c)"
```

---

### Task 4: `scripts/sync_derived.py` を作成（共有 helper + rules→.mdc 生成）

**背景:** 旧 `scripts/sync_agents.py` から **pure helper を verbatim 流用**し、skills 生成部は削除（P3b で skills は1式共有済）。本タスクでは helper + rules→`.mdc`（個別9本 + 集約 `workato-project.mdc`）まで実装。agent→.toml は Task 5、context は Task 6 で追記。

**Files:**
- Create: `scripts/sync_derived.py`
- Test: `tests/test_derived_sync.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_derived_sync.py
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

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

def test_per_rule_mdc_generated():
    _run_generator()
    mdc_dir = REPO / "rules"
    for stem in ("workato-recipe-format", "workato-cli", "org-knowledge-overlay"):
        mdc = mdc_dir / f"{stem}.mdc"
        assert mdc.is_file(), f"{stem}.mdc not generated"
        head = mdc.read_text(encoding="utf-8").splitlines()
        assert head[0] == "---"
        assert any(l.startswith("description: ") for l in head[:6])
        assert any(l.startswith("alwaysApply: false") for l in head[:6])

def test_aggregate_mdc_always_apply():
    _run_generator()
    agg = REPO / "rules" / "workato-project.mdc"
    assert agg.is_file(), "aggregate workato-project.mdc not generated"
    text = agg.read_text(encoding="utf-8")
    assert "alwaysApply: true" in text.splitlines()[:8]
    # 各ルールの本文が取り込まれている（代表見出しで確認）
    assert "Workato Recipe JSON Format" in text
    assert "org-knowledge-overlay" in text or "Knowledge" in text
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_derived_sync.py -v`
Expected: FAIL（`scripts/sync_derived.py` が無い）

- [ ] **Step 3: `scripts/sync_derived.py` を作成**

まず pure helper を旧 repo から **verbatim 移植**する（これらは副作用なしの純関数。旧 `scripts/sync_agents.py` 内の定義をそのまま使う）:
`split_frontmatter`, `first_heading`, `extract_paths`, `extract_field`, `trim_trailing_newlines`, `demote_headings`, `_HEADING_RE`, `_PATH_LINE_RE`, `_toml_str`。

その上で、新レイアウト用の本体を書く:

```python
#!/usr/bin/env python3
"""sync_derived.py — Generate per-editor derived files from canonical shared source.

Canonical source (hand-edited):
    rules/*.md   → rules/*.mdc  (Cursor; per-rule alwaysApply:false)
                 → rules/workato-project.mdc  (Cursor aggregate, alwaysApply:true)
    agents/*.md  → agents/*.toml  (Codex)
    rules/*.md   → CLAUDE.md / AGENTS.md / GEMINI.md  (always-on context)

Reduced from the legacy scripts/sync_agents.py: skills are a single shared
tree here (migrated in P3b), so per-editor skill generation is gone — only
rules, the agent, and context files are derived.

Run from repo root:  python3 scripts/sync_derived.py
CI (sync-check.yml) runs this then `git diff --exit-code` to detect drift.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = REPO_ROOT / "rules"
AGENTS_DIR = REPO_ROOT / "agents"

# ---- pure helpers: copy verbatim from
#      /Users/ryotaro/workspace/workato-dev-kit/scripts/sync_agents.py ----
#   split_frontmatter, first_heading, _PATH_LINE_RE, extract_paths,
#   extract_field, trim_trailing_newlines, _HEADING_RE, demote_headings,
#   _toml_str
# (paste their definitions here unchanged)


# ---- rules → per-rule .mdc (Cursor) ----
def sync_rules_mdc() -> None:
    for src in sorted(RULES_DIR.glob("*.md")):
        text = src.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        desc = first_heading(body)
        if not desc:
            print(f"WARN: no heading in {src.stem}, skipping")
            continue
        globs = ",".join(extract_paths(fm))
        body_trimmed = trim_trailing_newlines(body)
        out = (
            "---\n"
            f"description: {desc}\n"
            f'globs: "{globs}"\n'
            "alwaysApply: false\n"
            "---\n"
            f"{body_trimmed}\n"
        )
        (RULES_DIR / f"{src.stem}.mdc").write_text(out, encoding="utf-8")
        print(f"  ✓ rules/{src.stem}.mdc")


# ---- rules → aggregate workato-project.mdc (Cursor always-on) ----
AGGREGATE_DESC = (
    "Project-wide context for the Workato toolkit. "
    "Applies whenever Workato-related files are being edited."
)

def sync_aggregate_mdc() -> None:
    parts = [
        "---",
        f"description: {AGGREGATE_DESC}",
        'globs: ""',
        "alwaysApply: true",
        "---",
        "",
        "<!-- AUTO-GENERATED by scripts/sync_derived.py — DO NOT EDIT MANUALLY.",
        "     Source: rules/*.md -->",
        "",
        "# Workato Toolkit — Always-On Rules",
        "",
    ]
    for src in sorted(RULES_DIR.glob("*.md")):
        _, body = split_frontmatter(src.read_text(encoding="utf-8"))
        parts.append(demote_headings(trim_trailing_newlines(body), levels=1))
        parts.append("")
    (RULES_DIR / "workato-project.mdc").write_text(
        "\n".join(parts) + "\n", encoding="utf-8"
    )
    print("  ✓ rules/workato-project.mdc (aggregate)")


def main() -> None:
    sync_rules_mdc()
    sync_aggregate_mdc()


if __name__ == "__main__":
    main()
```

注意: `sync_rules_mdc` は `rules/*.md` を glob するので、生成物 `*.mdc` は対象外（拡張子違い）。集約は個別 `.md` のみを読む。

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_derived_sync.py -v`
Expected: PASS（4 tests）

- [ ] **Step 5: 生成物を確認してコミット**

```bash
python3 scripts/sync_derived.py
git add scripts/sync_derived.py rules/*.mdc tests/test_derived_sync.py
git commit -m "feat(derived): add sync_derived.py + generate Cursor .mdc rules (P3c)"
```

---

### Task 5: 生成器に agent→`.toml`（Codex）を追加

**背景:** Codex は agent を TOML で受ける。期待フォーマットは旧 `framework/codex/agents/workato-builder.toml`（`name` / `description` / `developer_instructions = '''...'''`）。description 内の slash command 参照（`/create-recipe` 等）は Codex 流の `$create-recipe` へ書換（旧 `.toml` 実例がそうなっている）。本文（developer_instructions）も同様に `/foo`→`$foo`。

**Files:**
- Modify: `scripts/sync_derived.py`
- Modify: `tests/test_derived_sync.py`

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_derived_sync.py に追記
def test_agent_toml_generated():
    _run_generator()
    toml = REPO / "agents" / "workato-builder.toml"
    assert toml.is_file(), "agents/workato-builder.toml not generated"
    text = toml.read_text(encoding="utf-8")
    assert text.startswith('name = "workato-builder"')
    assert "description = " in text
    assert "developer_instructions = '''" in text
    # slash → dollar rewrite が description に効いている
    assert "$create-recipe" in text
    assert "/create-recipe" not in text
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_derived_sync.py::test_agent_toml_generated -v`
Expected: FAIL

- [ ] **Step 3: 生成器に `.toml` 生成を追加**

`scripts/sync_derived.py` に、既知の skill 名から slash→$ パターンを作る関数（旧 `sync_agents.py` の `_build_codex_slash_pattern` を流用、ただし skills を `REPO_ROOT/"skills"` から読む）と、agent→toml 生成を追加:

```python
SKILLS_DIR = REPO_ROOT / "skills"

def _known_skill_names() -> set[str]:
    if not SKILLS_DIR.is_dir():
        return set()
    return {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}

# _build_codex_slash_pattern: copy verbatim from sync_agents.py
# (reads a set of names, returns a compiled regex or None)

def sync_agent_toml() -> None:
    slash = _build_codex_slash_pattern(_known_skill_names())
    for src in sorted(AGENTS_DIR.glob("*.md")):
        text = src.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        name = extract_field(fm, "name") or src.stem
        desc = extract_field(fm, "description") or ""
        body_trimmed = trim_trailing_newlines(body)
        if slash is not None:
            desc = slash.sub(r"$\1", desc)
            body_trimmed = slash.sub(r"$\1", body_trimmed)
        out = (
            f"name = {_toml_str(name)}\n"
            f"description = {_toml_str(desc)}\n"
            f"developer_instructions = '''\n"
            f"{body_trimmed}\n"
            f"'''\n"
        )
        (AGENTS_DIR / f"{src.stem}.toml").write_text(out, encoding="utf-8")
        print(f"  ✓ agents/{src.stem}.toml")
```

`main()` に `sync_agent_toml()` を追加。

注意: `AGENTS_DIR.glob("*.md")` は `.toml` を拾わない。`developer_instructions` は TOML の multi-line literal string（`'''...'''`）。本文に `'''` が現れないことを前提（旧 agent 本文には無い。万一含むなら basic string へフォールバックする必要があるが、現状不要 — YAGNI）。

- [ ] **Step 4: テストが通ることを確認 + TOML として妥当か検証**

Run: `python3 -m pytest tests/test_derived_sync.py::test_agent_toml_generated -v`
Expected: PASS

追加で TOML パース検証（Python 3.11+ の tomllib があれば）:
```bash
python3 scripts/sync_derived.py
python3 -c "import tomllib,sys; tomllib.load(open('agents/workato-builder.toml','rb')); print('toml ok')" 2>/dev/null || echo "tomllib unavailable (3.10-); skip"
```

- [ ] **Step 5: コミット**

```bash
python3 scripts/sync_derived.py
git add scripts/sync_derived.py agents/*.toml tests/test_derived_sync.py
git commit -m "feat(derived): generate Codex agent .toml from agents/*.md (P3c)"
```

---

### Task 6: 生成器に常時ルール context（`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`）を追加

**背景:** design §4 — 常時ルールは Cursor=`.mdc`、Gemini=`GEMINI.md`(`contextFileName` 自動ロード)、CC/Codex=SessionStart hook で注入。3つの context ファイルは **rules を起点に生成した共有本文**で、`bin/session-start-rules`（Task 7）が CC/Codex 向けに emit する元データも兼ねる。**旧 `framework/claude/CLAUDE.md` の submodule/setup.sh 前提の構造記述は使わない**（plugin 配布では誤り。install 手順は P5 の README）。代わりに plugin 向けの最小ヘッダ + rules 本文を生成する。3ファイルは同一本文（差は最初の見出し行のみ）。

**Files:**
- Modify: `scripts/sync_derived.py`
- Modify: `tests/test_derived_sync.py`

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_derived_sync.py に追記
def test_context_files_generated():
    _run_generator()
    for name in ("CLAUDE.md", "AGENTS.md", "GEMINI.md"):
        f = REPO / name
        assert f.is_file(), f"{name} not generated"
        text = f.read_text(encoding="utf-8")
        assert "AUTO-GENERATED by scripts/sync_derived.py" in text
        # rules 本文が入っている
        assert "Workato Recipe JSON Format" in text
        # 旧 submodule 前提の記述が紛れ込んでいない
        assert "git submodule update --remote kit" not in text
        assert "bash kit/setup.sh" not in text
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_derived_sync.py::test_context_files_generated -v`
Expected: FAIL

- [ ] **Step 3: 生成器に context 生成を追加**

```python
CONTEXT_INTRO = """\
Workato development toolkit for AI coding agents. The rules below are the
always-on knowledge base for building on Workato (recipes, Workflow Apps,
AI agents, custom connectors). They are delivered automatically: Cursor via
alwaysApply .mdc, Gemini via this GEMINI.md (contextFileName), Claude Code /
Codex via the SessionStart hook (bin/session-start-rules).

Knowledge-base documents (connectors, logic, platform, patterns) are NOT in
this file — fetch them through the docs-overlay MCP tools
`workato_docs_lookup(path)` / `workato_docs_list(prefix)` (org overrides win).
"""

def _context_body() -> str:
    parts = [
        "<!-- AUTO-GENERATED by scripts/sync_derived.py — DO NOT EDIT MANUALLY.",
        "     Source: rules/*.md -->",
        "",
        CONTEXT_INTRO,
    ]
    for src in sorted(RULES_DIR.glob("*.md")):
        _, body = split_frontmatter(src.read_text(encoding="utf-8"))
        parts.append(demote_headings(trim_trailing_newlines(body), levels=1))
        parts.append("")
    return "\n".join(parts)

def sync_context() -> None:
    body = _context_body()
    titles = {
        "CLAUDE.md": "# Workato Toolkit — Claude Code Context",
        "AGENTS.md": "# Workato Toolkit — Agent Context",
        "GEMINI.md": "# Workato Toolkit — Gemini Context",
    }
    for fname, title in titles.items():
        (REPO_ROOT / fname).write_text(title + "\n\n" + body + "\n", encoding="utf-8")
        print(f"  ✓ {fname}")
```

`main()` に `sync_context()` を追加。

注意: rules 本文は `# ` 見出しを含むので `demote_headings(levels=1)` で `## ` 以下へ落とし、context の `# タイトル` 1つだけが H1 になるようにする（集約 `.mdc` と同方針）。

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_derived_sync.py -v`
Expected: PASS（全テスト）

- [ ] **Step 5: コミット**

```bash
python3 scripts/sync_derived.py
git add scripts/sync_derived.py CLAUDE.md AGENTS.md GEMINI.md tests/test_derived_sync.py
git commit -m "feat(derived): generate CLAUDE.md/AGENTS.md/GEMINI.md always-on context (P3c)"
```

---

### Task 7: `bin/session-start-rules` を作成（CC/Codex SessionStart 注入スクリプト）

**背景:** design §4/§65 — CC/Codex は plugin から CLAUDE.md/AGENTS.md を自動注入できないので、SessionStart hook で常時ルールを context へ注入する。スクリプトは plugin-root（`${CLAUDE_PLUGIN_ROOT}` / `$PLUGIN_ROOT`）配下の `AGENTS.md` を読み、SessionStart hook が期待する JSON（`hookSpecificOutput.additionalContext`）を stdout に出す。plugin-root 変数は hooks json（Task 8）から環境変数として渡る。

**Files:**
- Create: `bin/session-start-rules`
- Modify: `tests/test_rules_agents_hooks_migration.py`

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_rules_agents_hooks_migration.py に追記
def test_session_start_rules_emits_context():
    script = BIN / "session-start-rules"
    assert script.is_file() and os.access(script, os.X_OK), "bin/session-start-rules missing/!x"
    # plugin root を repo root に見立てて実行（AGENTS.md は Task 6 で生成済の前提）
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(REPO))
    r = subprocess.run(["bash", str(script)], input="{}", capture_output=True, text=True, env=env)
    assert r.returncode == 0, f"script failed: {r.stderr}"
    out = json.loads(r.stdout)
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "Workato Recipe JSON Format" in ctx, "rule content not injected"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py::test_session_start_rules_emits_context -v`
Expected: FAIL

- [ ] **Step 3: `bin/session-start-rules` を作成**

```bash
#!/bin/bash
# session-start-rules — SessionStart hook (Claude Code / Codex).
#
# Emits the toolkit's always-on rules as SessionStart additionalContext so the
# rules are loaded without a committed CLAUDE.md (plugins cannot auto-inject one).
# The rule content lives in AGENTS.md (generated by scripts/sync_derived.py from
# rules/*.md). Plugin root is passed via ${CLAUDE_PLUGIN_ROOT} (CC) or
# $PLUGIN_ROOT (Codex).

cat >/dev/null  # drain hook stdin (unused)

ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
if [ -z "$ROOT" ]; then
  # Fall back to the script's own location (bin/ -> repo root).
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi

CONTEXT_FILE="$ROOT/AGENTS.md"
if [ ! -f "$CONTEXT_FILE" ]; then
  # Nothing to inject; emit empty object so the hook is a no-op.
  echo '{}'
  exit 0
fi

CONTEXT_FILE="$CONTEXT_FILE" python3 <<'PY'
import json, os
with open(os.environ["CONTEXT_FILE"], encoding="utf-8") as f:
    content = f.read()
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": content,
    }
}))
PY
exit 0
```

```bash
chmod +x bin/session-start-rules
```

注意: SessionStart の出力契約（`hookSpecificOutput.additionalContext`）は Claude Code 仕様。Codex の SessionStart 対応有無/契約差は **runtime 検証 TODO**（旧 repo に Codex SessionStart の実例なし）。Codex が未対応なら Task 8 の `codex.hooks.json` から SessionStart を外す（P4 実機検証で確定）。

- [ ] **Step 4: テストが通ることを確認**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py::test_session_start_rules_emits_context -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add bin/session-start-rules tests/test_rules_agents_hooks_migration.py
git commit -m "feat(hooks): add session-start-rules to inject always-on rules (CC/Codex) (P3c)"
```

---

### Task 8: hooks json 3種を作成（`hooks/hooks.json` / `cursor.hooks.json` / `codex.hooks.json`）

**背景:** design §2 — hooks 実体は共有（`bin/`）、json は3種でエディタ別（plugin-root 変数名・イベント名 casing 差）。
- **CC** (`hooks/hooks.json`): `${CLAUDE_PLUGIN_ROOT}`。Events: PreToolUse(Bash→validate, Bash|Read|Edit|Write|NotebookEdit|Grep|Glob→credential), PostToolUse(Bash→sync-docs), SessionStart(→session-start-rules)。matcher は旧 `settings.json` 準拠。
- **Codex** (`hooks/codex.hooks.json`): `$PLUGIN_ROOT`。matcher `^Bash$`（旧 codex/hooks.json 準拠）。PreToolUse(credential)。SessionStart は runtime 検証 TODO 付きで含める。
- **Cursor** (`hooks/cursor.hooks.json`): `version:1`、イベント lowercase（`postToolUse`/`preToolUse`）、matcher `Shell`、相対パス `./bin/...`（旧 cursor/hooks.json 準拠）。Cursor は常時ルールを `.mdc` で配るので SessionStart 不要。credential は preToolUse(Shell) + sync-docs は postToolUse(Shell)。

**Files:**
- Create: `hooks/hooks.json`, `hooks/codex.hooks.json`, `hooks/cursor.hooks.json`
- Modify: `tests/test_rules_agents_hooks_migration.py`

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_rules_agents_hooks_migration.py に追記
HOOKS = REPO / "hooks"

def _load(name):
    return json.loads((HOOKS / name).read_text(encoding="utf-8"))

def test_cc_hooks_json():
    d = _load("hooks.json")
    blob = json.dumps(d)
    assert "${CLAUDE_PLUGIN_ROOT}" in blob, "CC must use ${CLAUDE_PLUGIN_ROOT}"
    assert "$PLUGIN_ROOT" not in blob.replace("${CLAUDE_PLUGIN_ROOT}", "")
    h = d["hooks"]
    assert "PreToolUse" in h and "PostToolUse" in h and "SessionStart" in h
    assert "block-credential-read.sh" in blob
    assert "validate-before-push.sh" in blob
    assert "sync-docs-after-sdk-push.sh" in blob
    assert "session-start-rules" in blob

def test_codex_hooks_json():
    d = _load("codex.hooks.json")
    blob = json.dumps(d)
    assert "$PLUGIN_ROOT" in blob, "Codex must use $PLUGIN_ROOT"
    assert "${CLAUDE_PLUGIN_ROOT}" not in blob
    assert "block-credential-read.sh" in blob

def test_cursor_hooks_json():
    d = _load("cursor.hooks.json")
    assert d.get("version") == 1
    h = d["hooks"]
    # lowercase event names
    assert any(k in h for k in ("postToolUse", "preToolUse"))
    blob = json.dumps(d)
    assert "Shell" in blob  # Cursor matcher
    assert "${CLAUDE_PLUGIN_ROOT}" not in blob and "$PLUGIN_ROOT" not in blob

def test_all_hook_paths_resolve_to_real_scripts():
    for name in ("hooks.json", "codex.hooks.json", "cursor.hooks.json"):
        blob = json.dumps(_load(name))
        for script in ("block-credential-read.sh", "sync-docs-after-sdk-push.sh"):
            if script in blob:
                assert (BIN / script).is_file()
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py -k hooks_json -v`
Expected: FAIL

- [ ] **Step 3: 3つの json を作成**

`hooks/hooks.json`（CC）:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/bin/validate-before-push.sh" }
        ]
      },
      {
        "matcher": "Bash|Read|Edit|Write|NotebookEdit|Grep|Glob",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/bin/block-credential-read.sh" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/bin/sync-docs-after-sdk-push.sh" }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/bin/session-start-rules" }
        ]
      }
    ]
  }
}
```

`hooks/codex.hooks.json`（Codex）:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^Bash$",
        "hooks": [
          { "type": "command", "command": "$PLUGIN_ROOT/bin/block-credential-read.sh" }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "$PLUGIN_ROOT/bin/session-start-rules" }
        ]
      }
    ]
  }
}
```
（コメント: Codex の SessionStart 対応は runtime 検証 TODO。未対応なら P4 で SessionStart ブロックを削除。`.json` はコメント不可なので、本注記は plan/PR コメントで管理。）

`hooks/cursor.hooks.json`（Cursor）:
```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "matcher": "Shell",
        "command": "./bin/block-credential-read.sh",
        "type": "command"
      }
    ],
    "postToolUse": [
      {
        "matcher": "Shell",
        "command": "./bin/sync-docs-after-sdk-push.sh",
        "type": "command"
      }
    ]
  }
}
```

- [ ] **Step 4: テストが通ることを確認 + 全 json の妥当性**

Run: `python3 -m pytest tests/test_rules_agents_hooks_migration.py -k hooks_json -v`
Expected: PASS（4 tests）

```bash
for f in hooks/*.json; do python3 -c "import json,sys; json.load(open('$f')); print('ok', '$f')"; done
```

- [ ] **Step 5: コミット**

```bash
git add hooks/ tests/test_rules_agents_hooks_migration.py
git commit -m "feat(hooks): add CC/Codex/Cursor hooks.json (plugin-root vars + event casing) (P3c)"
```

---

### Task 9: skills 内の `@.claude/rules/X.md` 参照を「常時ルール」参照へ書換

**背景:** 常時ルールは全エディタで自動配信される（Task 6-8）ので、skills は rule を path 直読みせず**名前で参照**すればよい。design §49 の「skill 本文に plugin-root 変数を書かない・素の相対パスは cwd 基準で同梱物を指さない」に従い、`@.claude/rules/X.md` 形式を排除する。全エディタ共通の文言にするので per-editor 書換は不要（skills 共有を維持）。

対象（P3c 着手時点の grep 結果。実装時に再 grep して網羅）:
- `skills/create-genie/SKILL.md`（workato-agentic-format, workato-recipe-format, workato-project-structure ×2）
- `skills/learn-pattern/SKILL.md`（org-knowledge-overlay）
- `skills/create-recipe/SKILL.md`（workato-recipe-format, workato-project-structure）
- `skills/create-connector/SKILL.md`（workato-connector-sdk）
- `skills/onboard/SKILL.md`（org-knowledge-overlay）
- `skills/create-workflow-app/SKILL.md`（workato-agentic-format, workato-project-structure）
- `skills/learn-recipe/SKILL.md`（org-knowledge-overlay）
- `skills/push-project/SKILL.md`（workato-deployment-flow）

**書換ルール（文言）:** `` `@.claude/rules/<name>.md` `` → `` the `<name>` rule (always-on) ``。文脈で自然な英語になるよう前後を整える（例: `following @.claude/rules/workato-project-structure.md` → `following the \`workato-project-structure\` rule (always-on)`）。意味は不変。

**Files:**
- Modify: 上記8 SKILL.md
- Modify: `tests/test_skills_migration.py`（既存 P3b テストに禁止パターン追加）

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_skills_migration.py に追記（既存 FORBIDDEN とは別の新規ガード）
import re as _re
from pathlib import Path as _Path
_SKILLS = _Path(__file__).resolve().parent.parent / "skills"
_RULES_REF = _re.compile(r"@\.claude/rules/")

def test_no_claude_rules_path_refs():
    offenders = []
    for skill in _SKILLS.glob("*/SKILL.md"):
        if _RULES_REF.search(skill.read_text(encoding="utf-8")):
            offenders.append(skill.parent.name)
    assert not offenders, f"@.claude/rules/ refs remain in: {offenders}"

def test_rules_referenced_by_name():
    # 書換後は rule 名がバッククォート付きで言及される（最低限の正のガード）
    text = (_SKILLS / "create-recipe" / "SKILL.md").read_text(encoding="utf-8")
    assert "`workato-recipe-format`" in text
    assert "always-on" in text
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_skills_migration.py -k "claude_rules or referenced_by_name" -v`
Expected: FAIL

- [ ] **Step 3: 8つの SKILL.md を Edit**

実装時にまず再 grep:
```bash
grep -rn '@\.claude/rules/' skills/
```
各ヒットを上記「書換ルール」に従い Edit。例（create-recipe/SKILL.md:162, :186）:
- `- \`@.claude/rules/workato-recipe-format.md\`` → `- the \`workato-recipe-format\` rule (always-on)`
- `Follow \`@.claude/rules/workato-project-structure.md\`:` → `Follow the \`workato-project-structure\` rule (always-on):`

全ヒットを潰すまで繰り返す。

- [ ] **Step 4: テストが通ることを確認 + grep が空**

Run: `python3 -m pytest tests/test_skills_migration.py -v && grep -rn '@\.claude/rules/' skills/ ; echo "grep exit: $?"`
Expected: PASS、grep は何も出さず exit 1（=ヒットなし）

- [ ] **Step 5: コミット**

```bash
git add skills/ tests/test_skills_migration.py
git commit -m "refactor(skills): replace @.claude/rules path refs with always-on rule names (P3c)"
```

---

### Task 10: manifest を配線（agents / hooks / rules を各エディタへ宣言）

**背景:** 派生物を各エディタが拾えるよう plugin manifest を更新。CC は規約自動発見（`agents/` `hooks/hooks.json` を root から）。Codex/Cursor は明示宣言が要る場合がある。

調査確定事項（design §6.1）に基づく最小宣言:
- **CC** `.claude-plugin/plugin.json`: 規約で `agents/`・`hooks/hooks.json` を自動発見するが、明示の `hooks` フィールドを足して確実化（runtime 検証 TODO）。
- **Codex** `.codex-plugin/plugin.json`: 既に `skills`/`mcpServers` あり。`agents`（`./agents/`）と `hooks`（`./hooks/codex.hooks.json`）を追記。
- **Cursor** `.cursor-plugin/plugin.json`: 既に `skills` あり。`rules`（`rules/`）と `hooks`（`hooks/cursor.hooks.json`）を追記。

**Files:**
- Modify: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`
- Modify: `tests/test_manifests.py`（既存）

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_manifests.py に追記
import json as _json
from pathlib import Path as _P
_R = _P(__file__).resolve().parent.parent

def _m(p):
    return _json.loads((_R / p).read_text(encoding="utf-8"))

def test_codex_manifest_declares_agents_hooks():
    d = _m(".codex-plugin/plugin.json")
    assert d.get("agents") == "./agents/"
    assert d.get("hooks") == "./hooks/codex.hooks.json"

def test_cursor_manifest_declares_rules_hooks():
    d = _m(".cursor-plugin/plugin.json")
    assert d.get("rules") == "rules/"
    assert d.get("hooks") == "hooks/cursor.hooks.json"

def test_cc_manifest_declares_hooks():
    d = _m(".claude-plugin/plugin.json")
    assert d.get("hooks") == "./hooks/hooks.json"
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_manifests.py -k "declares" -v`
Expected: FAIL

- [ ] **Step 3: 3 manifest を Edit**

`.claude-plugin/plugin.json` に `"hooks": "./hooks/hooks.json"` を追加。
`.codex-plugin/plugin.json` に `"agents": "./agents/"`, `"hooks": "./hooks/codex.hooks.json"` を追加。
`.cursor-plugin/plugin.json` に `"rules": "rules/"`, `"hooks": "hooks/cursor.hooks.json"` を追加。

（各キー名は調査確定の最小集合。実機での正確なキー名は runtime 検証 TODO。崩れたら P4/P5 で修正。）

- [ ] **Step 4: テストが通ることを確認 + 全 manifest 妥当**

Run: `python3 -m pytest tests/test_manifests.py -v`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add .claude-plugin/ .codex-plugin/ .cursor-plugin/ tests/test_manifests.py
git commit -m "feat(manifests): declare agents/hooks/rules pointers per editor (P3c)"
```

---

### Task 11: `.github/workflows/sync-check.yml` で派生ドリフトを検知

**背景:** design §3/§5 — 派生ファイル（`.mdc`/`.toml`/context）は生成物なので、source 変更後に再生成し忘れるとドリフトする。CI で `python3 scripts/sync_derived.py` を走らせ `git diff --exit-code` で差分があれば fail。skills/docs は生成物でないため検査対象外。

**Files:**
- Create: `.github/workflows/sync-check.yml`
- Test: `tests/test_derived_sync.py`（ドリフトなしの確認テストを追加 — CI と同じ不変条件をローカルでも担保）

- [ ] **Step 1: 失敗するテストを追記**

```python
# tests/test_derived_sync.py に追記
def test_derived_files_in_sync_with_source():
    """生成器を走らせても tracked な派生物に差分が出ない（= コミット済が最新）。"""
    import subprocess
    _run_generator()
    r = subprocess.run(
        ["git", "status", "--porcelain",
         "rules/", "agents/", "CLAUDE.md", "AGENTS.md", "GEMINI.md"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    # *.md/*.sh などの source 変更は無視し、生成物（.mdc/.toml/context）の差分のみ検査
    drift = [l for l in r.stdout.splitlines()
             if l.endswith(".mdc") or l.endswith(".toml")
             or l.split()[-1] in ("CLAUDE.md", "AGENTS.md", "GEMINI.md")]
    assert not drift, f"derived files out of sync: {drift}"

def test_sync_check_workflow_exists():
    wf = REPO / ".github" / "workflows" / "sync-check.yml"
    assert wf.is_file()
    text = wf.read_text(encoding="utf-8")
    assert "scripts/sync_derived.py" in text
    assert "git diff --exit-code" in text
```

- [ ] **Step 2: テストが失敗することを確認**

Run: `python3 -m pytest tests/test_derived_sync.py -k "in_sync or workflow_exists" -v`
Expected: FAIL（workflow 未作成）。`test_derived_files_in_sync` は Task 4-6 を正しくコミットしていれば既に PASS する場合あり。

- [ ] **Step 3: `.github/workflows/sync-check.yml` を作成**

```yaml
name: sync-check

on:
  pull_request:
  push:
    branches: [main]

jobs:
  derived-files:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Regenerate derived files
        run: python3 scripts/sync_derived.py
      - name: Fail if derived files drifted from source
        run: |
          git diff --exit-code -- rules/ agents/ CLAUDE.md AGENTS.md GEMINI.md \
            || { echo "::error::Derived files out of sync. Run 'python3 scripts/sync_derived.py' and commit."; exit 1; }
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install test deps
        run: pip install pytest
      - name: Run tests
        run: python3 -m pytest tests/ -v
```

- [ ] **Step 4: テストが通ることを確認 + 全テスト緑**

Run: `python3 -m pytest tests/ -v`
Expected: PASS（全テスト）

```bash
# YAML 妥当性
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/sync-check.yml')); print('yaml ok')" 2>/dev/null || echo "pyyaml unavailable; skip"
```

- [ ] **Step 5: コミット**

```bash
git add .github/workflows/sync-check.yml tests/test_derived_sync.py
git commit -m "ci: add sync-check.yml to detect derived-file drift (P3c)"
```

---

## 完了後

- 全タスク完了後、ブランチ全体の最終レビュー（subagent-driven-development の final code reviewer）を実施。
- local `/code-review`（`main...HEAD`）でブランチ差分をレビュー。
- PR 作成 → マージ（`feat/p3c-rules-agents-hooks-derived` → `main`）。PR body 末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)`。
- runtime 検証 TODO（PR コメント / handover に記録）: ① Codex SessionStart 対応有無、② 各 manifest の hooks/agents/rules キー名の実機受理、③ CC `${CLAUDE_PLUGIN_ROOT}` 注入の発火、④ Cursor `.mdc` alwaysApply / `hooks` 受理。崩れた項目は P4 実機検証 or P5 で修正。

## Self-Review（writing-plans）

- **Spec coverage:** rules移植(T1)/agent移植(T2)/hooks移植+パス修正(T3)/生成器(T4-6: .mdc・aggregate・.toml・context)/SessionStart注入(T7)/hooks json 3種(T8)/@.claude/rules解決(T9)/manifest配線(T10)/sync-check CI(T11) — handover P3c の全項目を網羅。
- **Placeholder scan:** 新規成果物（生成器本体・hooks json・session-start-rules・context生成・sync-check.yml・mdc/toml フォーマット）は実コードを記載。verbatim コピー（rules/agent/hook 実体）は具体的 source パス指定（旧 repo の実在ファイル）+ 整合テストで担保 — placeholder ではない。
- **Type consistency:** テストファイルは `tests/test_rules_agents_hooks_migration.py`（移植系）と `tests/test_derived_sync.py`（生成系）、既存 `test_skills_migration.py`/`test_manifests.py` への追記で一貫。生成器関数名 `sync_rules_mdc`/`sync_aggregate_mdc`/`sync_agent_toml`/`sync_context` と `main()` 登録が一致。plugin-root 変数は CC=`${CLAUDE_PLUGIN_ROOT}`/Codex=`$PLUGIN_ROOT`/Cursor=相対 で design §2 表と一致。
