---
status: done
---

# workato-toolkit P2: docs-overlay MCP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The MCP server build may consult superpowers:mcp-builder.

**Goal:** plugin に同梱する Python(FastMCP)製 docs-overlay MCP を実装し、kit docs(plugin 同梱)と project の `org/docs/` を org-wins で重ねて返すツールを提供。CC で MCP がロードされツール呼び出しできる状態にする。

**Architecture:** コアの overlay ロジックは FastMCP 非依存の純関数(`overlay.py`)に分離して TDD する。`server.py` は FastMCP でラップし、kit docs を自身の `__file__`(plugin 同梱 `docs/`)から、org docs を cwd/`git rev-parse` から解決する。各エディタの MCP 起動定義(`.mcp.json` 等)で `uv run --with fastmcp` 起動する。

**Tech Stack:** Python 3 / FastMCP / pytest / JSON(MCP config)/ Git

**親 spec:** `superpowers/2026-06-07-workato-toolkit-plugin-distribution-design.md`(§4.5 docs-overlay MCP)
**前提 repo:** `/Users/ryotaro/workspace/workato-toolkit`(P1 完了・main に push 済)。owner=`rkawaishi`。`uv` と `python3` が利用可能(Step で確認)。

---

## File Structure(P2 で作成/変更)

- `mcp/docs-overlay/overlay.py`(新規)— 純関数 `resolve_doc(kit_dir, org_dir, rel)` / `list_docs(kit_dir, org_dir, prefix)`。I/O は引数の dir のみ。env/FastMCP 非依存。
- `mcp/docs-overlay/server.py`(新規)— FastMCP サーバ。kit_dir/org_dir を解決し、overlay.py を呼ぶ tool を2つ公開。
- `tests/test_overlay.py`(新規)— overlay.py の単体テスト(tmp fixture)。
- `.mcp.json`(新規)— CC 用 MCP 起動定義(plugin root 自動発見)。
- `.codex.mcp.json`(新規)— Codex 用 MCP 起動定義。
- `.codex-plugin/plugin.json`(変更)— `"mcpServers": "./.codex.mcp.json"` を追加。
- `docs/connectors/_index.md`, `docs/connectors/example.md`(新規・最小 fixture)— MCP が返す中身(本格 docs は P3 で移植)。
- 単一責務: overlay.py=ロジック、server.py=配線、test=検証、各 mcp config=起動。

---

## Task 1: feature ブランチ作成

**Files:** なし(ブランチ操作)

- [ ] **Step 1: 最新 main から feature ブランチを作成**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
git checkout main && git pull --ff-only
git checkout -b feat/p2-docs-overlay-mcp
```
Expected: `feat/p2-docs-overlay-mcp` に切り替わる。

- [ ] **Step 2: 前提ツール確認**

Run:
```bash
python3 --version && (uv --version || echo "UV_MISSING")
```
Expected: python3 のバージョンが出る。`uv` が無い(`UV_MISSING`)場合は BLOCKED として報告(`.mcp.json` の起動方式を pip/python に切替える判断が必要)。

---

## Task 2: overlay コアロジック(TDD)

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/tests/test_overlay.py`
- Create: `/Users/ryotaro/workspace/workato-toolkit/mcp/docs-overlay/overlay.py`

- [ ] **Step 1: 失敗するテストを書く**

Create `tests/test_overlay.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp" / "docs-overlay"))

import overlay  # noqa: E402


def _setup(tmp_path):
    kit = tmp_path / "kit"
    org = tmp_path / "org"
    (kit / "connectors").mkdir(parents=True)
    (org / "connectors").mkdir(parents=True)
    return kit, org


def test_kit_only(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("KIT slack", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/slack.md")
    assert "KIT slack" in out
    assert "NOT FOUND" not in out


def test_org_only(tmp_path):
    kit, org = _setup(tmp_path)
    (org / "connectors" / "internal.md").write_text("ORG internal", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/internal.md")
    assert "ORG internal" in out


def test_both_org_marked_authoritative(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("KIT slack base", encoding="utf-8")
    (org / "connectors" / "slack.md").write_text("ORG slack override", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/slack.md")
    assert "ORG slack override" in out
    assert "KIT slack base" in out
    # org section appears before kit section (authoritative first)
    assert out.index("ORG slack override") < out.index("KIT slack base")


def test_missing(tmp_path):
    kit, org = _setup(tmp_path)
    out = overlay.resolve_doc(kit, org, "connectors/nope.md")
    assert "NOT FOUND" in out


def test_appends_md_extension(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("KIT slack", encoding="utf-8")
    out = overlay.resolve_doc(kit, org, "connectors/slack")
    assert "KIT slack" in out


def test_path_traversal_blocked(tmp_path):
    kit, org = _setup(tmp_path)
    out = overlay.resolve_doc(kit, org, "../secret.md")
    assert "INVALID PATH" in out


def test_org_dir_none(tmp_path):
    kit, _ = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("KIT slack", encoding="utf-8")
    out = overlay.resolve_doc(kit, None, "connectors/slack.md")
    assert "KIT slack" in out


def test_list_docs_union(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("k", encoding="utf-8")
    (org / "connectors" / "internal.md").write_text("o", encoding="utf-8")
    (kit / "logic.md").write_text("k", encoding="utf-8")
    paths = overlay.list_docs(kit, org, prefix="connectors/")
    assert "connectors/slack.md" in paths
    assert "connectors/internal.md" in paths
    assert "logic.md" not in paths  # prefix filter
    assert paths == sorted(paths)  # sorted, deduped


def test_list_docs_dedup(tmp_path):
    kit, org = _setup(tmp_path)
    (kit / "connectors" / "slack.md").write_text("k", encoding="utf-8")
    (org / "connectors" / "slack.md").write_text("o", encoding="utf-8")
    paths = overlay.list_docs(kit, org)
    assert paths.count("connectors/slack.md") == 1
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_overlay.py -v
```
Expected: import エラー or 全 FAIL(`overlay.py` 未作成)。

- [ ] **Step 3: overlay.py を実装**

Create `mcp/docs-overlay/overlay.py`:
```python
"""Pure docs-overlay logic: merge kit docs with org docs (org wins).

No FastMCP / env dependency — callers pass resolved directories.
"""
from pathlib import Path
from typing import Optional


def _norm(rel: str) -> Optional[str]:
    """Normalize a relative doc path. Return None if it escapes the root."""
    rel = rel.strip().lstrip("/")
    if not rel.endswith(".md"):
        rel = rel + ".md"
    parts = [p for p in Path(rel).parts if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return str(Path(*parts)) if parts else None


def _read(base: Optional[Path], rel: str) -> Optional[str]:
    if base is None:
        return None
    p = base / rel
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return None


def resolve_doc(kit_dir: Path, org_dir: Optional[Path], rel: str) -> str:
    """Return the doc for `rel`, applying the org overlay (org wins on conflict).

    - both present: org section first (authoritative), then kit baseline.
    - only one present: return it.
    - neither: NOT FOUND sentinel.
    - path traversal: INVALID PATH sentinel.
    """
    norm = _norm(rel)
    if norm is None:
        return f"INVALID PATH: {rel!r} (path traversal is not allowed)"

    kit_text = _read(kit_dir, norm)
    org_text = _read(org_dir, norm)

    if kit_text is None and org_text is None:
        return f"NOT FOUND: {norm} (checked kit docs and org/docs)"

    if org_text is not None and kit_text is not None:
        return (
            f"# {norm} (org overlay applied — the org version overrides the kit on conflict)\n\n"
            f"## Organization (authoritative — org/docs/{norm})\n\n{org_text}\n\n"
            f"## Kit baseline (docs/{norm})\n\n{kit_text}\n"
        )

    if org_text is not None:
        return f"# {norm} (org-only — no kit baseline)\n\n{org_text}\n"

    return kit_text


def list_docs(kit_dir: Path, org_dir: Optional[Path], prefix: str = "") -> list:
    """List available doc paths (union of kit + org), sorted & deduped, filtered by prefix."""
    found = set()
    for base in (kit_dir, org_dir):
        if base is None or not base.is_dir():
            continue
        for p in base.rglob("*.md"):
            rel = str(p.relative_to(base))
            if rel.startswith(prefix):
                found.add(rel)
    return sorted(found)
```

- [ ] **Step 4: テストを実行して全 PASS を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_overlay.py -v
```
Expected: 9件すべて PASS。

- [ ] **Step 5: コミット**

Run:
```bash
git add tests/test_overlay.py mcp/docs-overlay/overlay.py
git commit -m "feat(mcp): add docs-overlay core logic (org-wins merge) with tests"
```

---

## Task 3: FastMCP サーバ(配線)

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/mcp/docs-overlay/server.py`

- [ ] **Step 1: server.py を実装**

Create `mcp/docs-overlay/server.py`:
```python
"""docs-overlay MCP server (FastMCP).

- kit docs: resolved from this file's location (<plugin_root>/docs) — editor-agnostic.
- org docs: resolved from the user's project (cwd / git toplevel) at org/docs.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

import overlay  # same directory

HERE = Path(__file__).resolve()
KIT_DOCS = HERE.parents[2] / "docs"  # <plugin_root>/docs


def _find_org_docs() -> Optional[Path]:
    start = Path(os.getcwd())
    root = start
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            root = Path(out.stdout.strip())
    except Exception:
        pass
    candidate = root / "org" / "docs"
    return candidate if candidate.is_dir() else None


mcp = FastMCP("workato-docs")


@mcp.tool()
def workato_docs_lookup(path: str) -> str:
    """Look up a Workato knowledge-base doc by relative path (e.g. 'connectors/slack.md').

    Returns the kit doc merged with the organization overlay (org/docs) when present;
    the organization version overrides the kit baseline on conflict. Use this instead
    of reading docs files directly.
    """
    return overlay.resolve_doc(KIT_DOCS, _find_org_docs(), path)


@mcp.tool()
def workato_docs_list(prefix: str = "") -> list:
    """List available Workato doc paths (kit + org overlay), optionally filtered by prefix
    (e.g. 'connectors/')."""
    return overlay.list_docs(KIT_DOCS, _find_org_docs(), prefix)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: サーバが import/起動できることをスモーク確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
uv run --with fastmcp python -c "import sys; sys.path.insert(0,'mcp/docs-overlay'); import server; print('OK', server.KIT_DOCS)"
```
Expected: `OK .../workato-toolkit/docs` と表示(FastMCP が `uv` 経由で解決され、import が通る)。失敗時は BLOCKED 報告。

- [ ] **Step 3: コミット**

Run:
```bash
git add mcp/docs-overlay/server.py
git commit -m "feat(mcp): add FastMCP docs-overlay server (kit via __file__, org via git toplevel)"
```

---

## Task 4: MCP 起動定義 + 最小 docs fixture

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/.mcp.json`
- Create: `/Users/ryotaro/workspace/workato-toolkit/.codex.mcp.json`
- Modify: `/Users/ryotaro/workspace/workato-toolkit/.codex-plugin/plugin.json`
- Create: `/Users/ryotaro/workspace/workato-toolkit/docs/connectors/_index.md`
- Create: `/Users/ryotaro/workspace/workato-toolkit/docs/connectors/example.md`

- [ ] **Step 1: CC 用 `.mcp.json` を作成**(plugin root 自動発見)

Create `.mcp.json`:
```json
{
  "mcpServers": {
    "workato-docs": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp", "python", "${CLAUDE_PLUGIN_ROOT}/mcp/docs-overlay/server.py"]
    }
  }
}
```

- [ ] **Step 2: Codex 用 `.codex.mcp.json` を作成**

Create `.codex.mcp.json`:
```json
{
  "mcpServers": {
    "workato-docs": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp", "python", "${PLUGIN_ROOT}/mcp/docs-overlay/server.py"]
    }
  }
}
```

- [ ] **Step 3: `.codex-plugin/plugin.json` に mcpServers ポインタを追加**

`.codex-plugin/plugin.json` を次の内容に更新(`mcpServers` 行を追加):
```json
{
  "name": "workato-toolkit",
  "version": "0.0.1",
  "description": "Workato development toolkit for AI coding agents",
  "skills": "./skills/",
  "mcpServers": "./.codex.mcp.json"
}
```

- [ ] **Step 4: 最小 docs fixture を作成**

Create `docs/connectors/_index.md`:
```markdown
# Connectors index (kit canonical)

This is the kit-canonical connector knowledge base. Full content is migrated in P3.

- example — sample connector doc for MCP verification
```

Create `docs/connectors/example.md`:
```markdown
# example connector (kit baseline)

Sample connector doc used to verify the docs-overlay MCP returns kit content.

## Triggers
- new_item — fires on a new item.

## Actions
- create_item — creates an item.
```

- [ ] **Step 5: 既存テスト一式が壊れていないことを確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest -v
```
Expected: `tests/test_manifests.py`(7)+ `tests/test_overlay.py`(9)= 16件 PASS。
(注: `.codex-plugin/plugin.json` 変更後も `test_codex_plugin` は name/version/description を見るだけなので PASS のまま。)

- [ ] **Step 6: コミット**

Run:
```bash
git add .mcp.json .codex.mcp.json .codex-plugin/plugin.json docs/
git commit -m "feat(mcp): wire docs-overlay MCP for CC/Codex + add minimal docs fixture"
```

---

## Task 5: 実機 install 検証(CC・手動)

自動化不可。CC で plugin を更新し、MCP サーバがロードされ tool が呼べることを確認する。

**Files:** なし(検証のみ。修正が出たら該当ファイルを直し Task 2/4 のテスト再実行→コミット)

- [ ] **Step 1: branch を push して CC で更新**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
git push -u origin feat/p2-docs-overlay-mcp
```
(注: CC の marketplace は通常 default branch を見る。検証のため一時的に main へ出したくない場合は、ローカル marketplace 追加で検証してもよい。標準手順は PR マージ後に main で再検証。ここでは「ローカルパスの marketplace」で branch を検証する:)

CC で実行:
```
/plugin marketplace add /Users/ryotaro/workspace/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
/reload-plugins
```
Expected: `/reload-plugins` の出力で **plugin MCP servers が 1 以上**になる(P1 時点は 0 だった)。

- [ ] **Step 2: MCP tool を呼び出して確認**

CC で `workato-docs` の `workato_docs_lookup` を `path="connectors/example.md"` で呼ぶ(または「workato-docs の example connector を引いて」と依頼)。
Expected: `docs/connectors/example.md` の中身(「example connector (kit baseline)」)が返る。`workato_docs_list("connectors/")` で `connectors/_index.md` と `connectors/example.md` が返る。

- [ ] **Step 3: 結果記録**

成功/失敗を報告。`uv` 不在や FastMCP 解決失敗が出たら、`.mcp.json` の起動方式(例: `python3 -m pip install --user fastmcp` 前提の `python3` 直接起動)へ切替えて再検証。

---

## Task 6: PR 作成

**Files:** なし(PR 操作)

- [ ] **Step 1: ブランチを push(未 push なら)して PR を作成**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
git push -u origin feat/p2-docs-overlay-mcp 2>/dev/null || true
gh pr create --base main --head feat/p2-docs-overlay-mcp \
  --title "P2: docs-overlay MCP (kit + org/docs, org-wins)" \
  --body "$(cat <<'EOF'
## What
Adds the docs-overlay MCP server (Python/FastMCP) bundled in the plugin.

- `mcp/docs-overlay/overlay.py` — pure org-wins merge logic (kit docs + project org/docs), path-traversal guarded.
- `mcp/docs-overlay/server.py` — FastMCP server; kit docs from `__file__` (editor-agnostic), org docs from cwd/git toplevel.
- `.mcp.json` (CC) + `.codex.mcp.json` (Codex) launch via `uv run --with fastmcp`.
- minimal `docs/` fixture (full migration in P3).

## Tests
- `tests/test_overlay.py` — 9 unit tests (kit-only / org-only / both / missing / traversal / list union+dedup).
- Full suite green (manifests 7 + overlay 9).

## Verification
- CC: MCP server loads (plugin MCP servers >= 1), `workato_docs_lookup` returns kit doc.

Refs design spec §4.5.
EOF
)"
```
Expected: PR が作成され URL が返る。

- [ ] **Step 2: PR URL を報告**

PR URL を共有。bugbot/レビュー後にマージ → main で最終検証(任意)。

---

## Self-Review(この plan の確認)

- **spec カバレッジ(§4.5)**: docs-overlay MCP が kit docs + org/docs を org-wins merge=Task2(`resolve_doc`)/ kit docs を `__file__` で解決=Task3 / org docs を cwd・`git rev-parse` で解決=Task3(`_find_org_docs`)/ `.mcp.json`・`.codex.mcp.json` の per-editor 起動=Task4 / skill はファイル直読みせず tool 呼び出し=tool 名 `workato_docs_lookup`・`workato_docs_list` を提供(skill 側の置換は P3)。
- **placeholder**: なし(overlay.py / server.py / test / 各 config / fixture の中身を全記載)。
- **型/名称整合**: 純関数 `resolve_doc(kit_dir, org_dir, rel)` / `list_docs(kit_dir, org_dir, prefix)` はテスト・server.py 双方で同シグネチャ。tool 名 `workato_docs_lookup` / `workato_docs_list` は server.py と Task5 検証で一致。sentinel 文字列 `NOT FOUND` / `INVALID PATH` はテストと overlay.py で一致。
- **既知の不確実点**: (1) `uv` 前提(Task1 Step2 で確認、無ければ起動方式切替)。(2) Cursor の MCP 配線は本 plan では未対応(CC/Codex のみ)。Cursor MCP は P3 以降 or 別タスクで `.cursor-plugin/plugin.json` の `mcpServers` を検証して追加。(3) CC marketplace の branch 検証はローカルパス marketplace で実施(default branch 依存を回避)。
- **スコープ**: P2 は MCP 機構のみ。docs 本体移植・skill の参照置換・常時ルール・学習は P3/P4。
