---
status: done
---

# workato-toolkit P1: 配布スケルトン Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新規 public GitHub repo `workato-toolkit` を作り、共有ツリー型の骨格 + CC/Cursor/Codex の plugin manifest + サンプル skill を置き、3エディタで install でき skill が起動する状態にする。

**Architecture:** リポジトリ root 自体が plugin(共有ツリー型)。各エディタの manifest が同じ root(`source: "./"`)を指す。skills/docs 等のコピーは作らない。manifest の妥当性は Python/pytest で自動検証し、実機 install は手動チェックリストで確認する。

**Tech Stack:** Git / GitHub CLI (`gh`) / Python 3 + pytest / Markdown (SKILL.md) / JSON manifests

**親 spec:** `superpowers/2026-06-07-workato-toolkit-plugin-distribution-design.md`(MVP=CC+Cursor+Codex 先行, Gemini 後追い)

**前提:** `gh` が認証済み(`gh auth status` が OK)。owner は `rkawaishi`(必要なら読み替え)。作業ディレクトリは `workato-dev-kit` と同階層に `workato-toolkit` を clone する想定(`/Users/ryotaro/workspace/workato-toolkit`)。

---

## File Structure(P1 で作成/変更するファイル)

新 repo `workato-toolkit/` 内:
- `.claude-plugin/marketplace.json` — CC marketplace 定義(plugin source=`./`)
- `.claude-plugin/plugin.json` — CC plugin manifest
- `.cursor-plugin/marketplace.json` — Cursor marketplace 定義
- `.cursor-plugin/plugin.json` — Cursor plugin manifest
- `.codex-plugin/plugin.json` — Codex plugin manifest
- `.agents/plugins/marketplace.json` — Codex marketplace 定義
- `skills/ping/SKILL.md` — install 確認用サンプル skill
- `tests/test_manifests.py` — manifest/skill 妥当性検証(pytest)
- `README.md` — 3エディタの install 手順(スタブ)
- `LICENSE` — MIT(旧 repo から複製)
- `.gitignore` — Python 用
- `docs/`, `bin/`, `agents/`, `rules/`, `hooks/`, `mcp/` は **P2 以降**で追加(P1 では作らない)

---

## Task 1: GitHub repo 作成と初期化

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/README.md`
- Create: `/Users/ryotaro/workspace/workato-toolkit/.gitignore`
- Create: `/Users/ryotaro/workspace/workato-toolkit/LICENSE`

- [ ] **Step 1: GitHub に public repo を作成して clone**

Run:
```bash
cd /Users/ryotaro/workspace
gh repo create rkawaishi/workato-toolkit \
  --public \
  --description "Workato development toolkit for AI coding agents (Claude Code / Cursor / Codex / Gemini)" \
  --clone
cd workato-toolkit
```
Expected: `/Users/ryotaro/workspace/workato-toolkit` が作成され空 repo が clone される。

- [ ] **Step 2: LICENSE を旧 repo から複製**

Run:
```bash
cp /Users/ryotaro/workspace/workato-dev-kit/LICENSE /Users/ryotaro/workspace/workato-toolkit/LICENSE
```
Expected: MIT LICENSE がコピーされる。

- [ ] **Step 3: `.gitignore` を作成**

Create `/Users/ryotaro/workspace/workato-toolkit/.gitignore`:
```gitignore
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
.venv/
```

- [ ] **Step 4: README スタブを作成**

Create `/Users/ryotaro/workspace/workato-toolkit/README.md`:
```markdown
# workato-toolkit

Workato (enterprise iPaaS) development toolkit for AI coding agents, distributed as a native plugin/extension.
Targets Claude Code, Cursor, Codex CLI (Gemini CLI to follow).

> Status: MVP scaffolding (P1). See the design spec in workato-dev-kit `superpowers/`.

## Install (MVP: CC / Cursor / Codex)

### Claude Code
```
/plugin marketplace add rkawaishi/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
```

### Codex CLI
```
codex plugin marketplace add rkawaishi/workato-toolkit
codex plugin add workato-toolkit
```

### Cursor
Add via the Cursor plugin marketplace, or for local dev reference the repo with `@local`.

After install, run the `ping` skill to verify the toolkit is loaded.

## License
MIT
```

- [ ] **Step 5: 初期コミット**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
git add LICENSE .gitignore README.md
git commit -m "chore: scaffold workato-toolkit repo (LICENSE, gitignore, README stub)"
```
Expected: 初期コミットが作成される。

---

## Task 2: archcore-ai/plugin の実 manifest を参照して root-plugin の形を確定

実在の3エディタ plugin(`archcore-ai/plugin`)の manifest 実体を確認し、特に **Codex marketplace の `source` 表現**(`.agents/plugins/marketplace.json` から repo root の plugin を指す書式)を本 plan の値と突き合わせる。spec §6.2 の未確定(Codex/Cursor manifest 詳細・root 指定)を潰す。

**Files:** なし(調査のみ。結果は Task 4–6 の manifest に反映)

- [ ] **Step 1: archcore の manifest 4種を取得して確認**

Run:
```bash
for f in .claude-plugin/marketplace.json .claude-plugin/plugin.json \
         .cursor-plugin/plugin.json .codex-plugin/plugin.json \
         .agents/plugins/marketplace.json; do
  echo "===== $f ====="
  gh api "repos/archcore-ai/plugin/contents/$f" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null || echo "(not found)"
done
```
Expected: 各 manifest の中身が表示される。特に `.agents/plugins/marketplace.json` の `plugins[].source`(repo root を指す書式)と `.cursor-plugin/plugin.json` の component pointer の書式を確認する。

- [ ] **Step 2: 差分があれば Task 4–6 の manifest 値を archcore に合わせて修正する旨をメモ**

archcore の `source` 書式が本 plan の値(下記 Task で定義)と異なる場合、**archcore の実値を正**として Task 4–6 を調整する。取得できない/曖昧な場合は本 plan の値で進め、Task 7 の実機 install で確認する。

---

## Task 3: manifest/skill 検証テスト(失敗する状態から)

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/tests/test_manifests.py`

- [ ] **Step 1: 失敗するテストを書く**

Create `/Users/ryotaro/workspace/workato-toolkit/tests/test_manifests.py`:
```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_manifests.py -v
```
Expected: 全テストが FAIL(manifest/skill 未作成のため `missing manifest: ...` / skill なし)。

- [ ] **Step 3: コミット**

Run:
```bash
git add tests/test_manifests.py
git commit -m "test: add manifest and sample-skill validation tests (failing)"
```

---

## Task 4: Claude Code manifest

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/.claude-plugin/marketplace.json`
- Create: `/Users/ryotaro/workspace/workato-toolkit/.claude-plugin/plugin.json`

- [ ] **Step 1: CC marketplace.json を作成**

Create `.claude-plugin/marketplace.json`:
```json
{
  "name": "workato-toolkit",
  "owner": { "name": "rkawaishi", "url": "https://github.com/rkawaishi/workato-toolkit" },
  "plugins": [
    {
      "name": "workato-toolkit",
      "source": "./",
      "description": "Workato development toolkit for AI coding agents"
    }
  ]
}
```

- [ ] **Step 2: CC plugin.json を作成**

Create `.claude-plugin/plugin.json`:
```json
{
  "name": "workato-toolkit",
  "version": "0.0.1",
  "description": "Workato development toolkit for AI coding agents (skills, docs, hooks)",
  "author": { "name": "rkawaishi" }
}
```

- [ ] **Step 3: CC のテストを実行して PASS を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_manifests.py::test_cc_marketplace tests/test_manifests.py::test_cc_plugin -v
```
Expected: 2件 PASS。

- [ ] **Step 4: コミット**

Run:
```bash
git add .claude-plugin/
git commit -m "feat: add Claude Code plugin manifests (source ./)"
```

---

## Task 5: Cursor manifest

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/.cursor-plugin/marketplace.json`
- Create: `/Users/ryotaro/workspace/workato-toolkit/.cursor-plugin/plugin.json`

- [ ] **Step 1: Cursor marketplace.json を作成**

Create `.cursor-plugin/marketplace.json`:
```json
{
  "name": "workato-toolkit",
  "owner": { "name": "rkawaishi", "url": "https://github.com/rkawaishi/workato-toolkit" },
  "plugins": [
    {
      "name": "workato-toolkit",
      "source": "./",
      "description": "Workato development toolkit for AI coding agents"
    }
  ]
}
```

- [ ] **Step 2: Cursor plugin.json を作成**

Create `.cursor-plugin/plugin.json`:
```json
{
  "name": "workato-toolkit",
  "description": "Workato development toolkit for AI coding agents",
  "skills": "skills/"
}
```

- [ ] **Step 3: Cursor のテストを実行して PASS を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_manifests.py::test_cursor_marketplace tests/test_manifests.py::test_cursor_plugin -v
```
Expected: 2件 PASS。

- [ ] **Step 4: コミット**

Run:
```bash
git add .cursor-plugin/
git commit -m "feat: add Cursor plugin manifests"
```

---

## Task 6: Codex manifest

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/.codex-plugin/plugin.json`
- Create: `/Users/ryotaro/workspace/workato-toolkit/.agents/plugins/marketplace.json`

- [ ] **Step 1: Codex plugin.json を作成**

Create `.codex-plugin/plugin.json`:
```json
{
  "name": "workato-toolkit",
  "version": "0.0.1",
  "description": "Workato development toolkit for AI coding agents",
  "skills": "./skills/"
}
```

- [ ] **Step 2: Codex marketplace.json を作成**

Create `.agents/plugins/marketplace.json`(Task 2 で archcore の実値を確認した場合はそれに合わせる。`source.path` は repo root を指す):
```json
{
  "name": "workato-toolkit",
  "interface": { "displayName": "Workato Toolkit" },
  "plugins": [
    {
      "name": "workato-toolkit",
      "source": { "source": "local", "path": "./" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

- [ ] **Step 3: Codex のテストを実行して PASS を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_manifests.py::test_codex_plugin tests/test_manifests.py::test_codex_marketplace -v
```
Expected: 2件 PASS。

- [ ] **Step 4: コミット**

Run:
```bash
git add .codex-plugin/ .agents/
git commit -m "feat: add Codex plugin and marketplace manifests"
```

---

## Task 7: サンプル skill `ping`

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/skills/ping/SKILL.md`

- [ ] **Step 1: ping skill を作成**

Create `skills/ping/SKILL.md`:
```markdown
---
name: ping
description: Smoke-test skill for workato-toolkit. Confirms the toolkit is installed and a skill can load in the current editor. Use to verify installation after running marketplace add + install.
---

# /ping — workato-toolkit インストール確認

このスキルは workato-toolkit が正しく install され、skill がロードされているかを確認するためのスモークテストです。

呼ばれたら、以下を報告してください:

1. 「workato-toolkit がロードされています」と明示する。
2. 実行中のエディタ名(分かる範囲で: Claude Code / Cursor / Codex)。
3. このスキルのファイル位置が判別できれば、その plugin root パス。

実際の Workato 開発機能(recipe 生成・docs 参照など)は後続のスキルで提供されます。
```

- [ ] **Step 2: skill テストを実行して PASS を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_manifests.py::test_sample_skill_present -v
```
Expected: 1件 PASS。

- [ ] **Step 3: 全テストを実行して全 PASS を確認**

Run:
```bash
python3 -m pytest tests/test_manifests.py -v
```
Expected: 7件すべて PASS。

- [ ] **Step 4: コミット & push**

Run:
```bash
git add skills/ping/SKILL.md
git commit -m "feat: add ping smoke-test skill"
git push -u origin main
```
Expected: GitHub に push される(以降のエディタ install が GitHub 経由で可能になる)。

---

## Task 8: 実機 install 検証(手動チェックリスト)

自動化できない部分。各エディタで marketplace 追加 + install し、`ping` skill が起動することを確認する。失敗したら対象エディタの manifest を修正(Task 2 の archcore 実値を参照)。

**Files:** なし(検証のみ。修正が出たら該当 manifest を編集→ Task 3 のテスト再実行→コミット)

- [ ] **Step 1: Claude Code で検証**

CC で実行:
```
/plugin marketplace add rkawaishi/workato-toolkit
/plugin install workato-toolkit@workato-toolkit
/reload-plugins
```
その後 `ping` skill を起動し、「workato-toolkit がロードされています」と応答することを確認。
Expected: skill が一覧に出て起動・応答する。

- [ ] **Step 2: Codex CLI で検証**

Codex で実行:
```
codex plugin marketplace add rkawaishi/workato-toolkit
codex plugin add workato-toolkit
```
セッションで `ping`(Codex では `$ping` 表記)を起動し応答を確認。
Expected: skill が起動・応答する。

- [ ] **Step 3: Cursor で検証**

Cursor の plugin marketplace 経由(または local dev は `@local` 参照)で install し、`ping` を起動して応答を確認。
Expected: skill が起動・応答する。

- [ ] **Step 4: 結果を記録**

3エディタの結果(成功/要修正)を `README.md` の Status 行、または GitHub issue に記録。修正が発生した場合は該当 manifest を直し、`python3 -m pytest tests/test_manifests.py -v` を再実行して全 PASS を確認後にコミット & push。

---

## Self-Review(この plan の確認)

- **spec カバレッジ(P1 範囲)**: 共有ツリー骨格(root=plugin)=Task 4–7 / CC・Cursor・Codex manifest=Task 4–6 / サンプル skill で install 検証=Task 7–8 / `dist/` 複製を作らない=ファイル構成どおり(skills は1式のみ)。Gemini・docs-overlay MCP・コンテンツ移植・常時ルール・学習・CI/release は **P2 以降**(本 plan のスコープ外で正しい)。
- **placeholder**: なし(各 manifest/skill/test の中身を全記載)。Task 2 のみ調査タスクだが、出力(archcore 実値)を Task 4–6 に反映する具体手順を明記。
- **型/名称整合**: plugin 名は全 manifest で `workato-toolkit`。marketplace 名も `workato-toolkit`。CC install は `workato-toolkit@workato-toolkit`(plugin@marketplace)。テストの assert と manifest のフィールド名が一致(`owner.name` / `source` / `policy.installation` / `category` / `version` / `description`)。
- **既知の不確実点**: Codex marketplace の `source.path`(`.agents/plugins/` から root を指す書式)は Task 2 で archcore 実値に合わせる。Cursor の install slash 構文は実機(Task 8 Step 3)で確認。
