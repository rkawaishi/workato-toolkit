# workato-toolkit P3a: Knowledge Base Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 旧 `workato-dev-kit` の知識ベース（`docs/` 348 件 + `guides/` 13 件 + `i18n/GLOSSARY.md`）を `workato-toolkit` の共有 `docs/` ツリーへ移植し、docs-overlay MCP が P2 のフィクスチャではなく **実コンテンツ**（317 コネクタ等）を返す状態にする。

**Architecture:** P2 で実装済みの docs-overlay MCP（`mcp/docs-overlay/overlay.py` の `resolve_doc`/`list_docs`）は `docs/` 配下の `*.md` を rglob で読む。よって `docs/` にファイルを置くだけで MCP が自動的に配信する。**サーバ側コードの変更は不要**。移植は (1) P2 フィクスチャ除去 → (2) 旧 `docs/` ツリーをコピー → (3) `guides/` を `docs/guides/` へ、glossary を `docs/i18n/` へ配置、の3手。整合は pytest（移植インテグリティ）+ overlay 純関数の smoke で検証する。

**Tech Stack:** Git / rsync / Python 3 / pytest

**親 spec:** `superpowers/2026-06-07-workato-toolkit-plugin-distribution-design.md`（§4.5 docs-overlay MCP、§5 初期コンテンツ移植）
**前提 repo:** `/Users/ryotaro/workspace/workato-toolkit`（P1+P2 完了・main に merge 済）。owner=`rkawaishi`。
**移植元 repo:** `/Users/ryotaro/workspace/workato-dev-kit`（凍結。read-only として参照）。

---

## スコープと決定事項

- **本 plan の対象（P3a）**: 知識ベースのコンテンツ移植のみ。skills/rules/agents/hooks は P3b/P3c で扱う。
- **guides の配置（決定）**: `guides/*.md`（lifecycle.md 等、エージェントが実行時に参照する）を **`docs/guides/` 配下**へ移植し、MCP 経由で参照可能にする。素のファイル直読みは plugin では cwd 基準になり同梱物を指さないため（spec §2 の鍵ルール）、知識は一律 MCP 配信下（=`docs/`）に置く。human 向け quickstart の README 抽出は P5 で検討（本 plan では `docs/guides/` に含めて移植する）。
- **glossary の配置（決定）**: `i18n/GLOSSARY.md` → `docs/i18n/GLOSSARY.md`（同じく MCP 配信下）。
- **P2 フィクスチャの扱い**: `docs/connectors/_index.md` は旧 repo の実 `_index.md` で**上書き**、`docs/connectors/example.md` は**削除**（移植元に存在しないプレースホルダ）。
- **移植元の期待件数（2026-06-07 実測）**: `docs/` 合計 348（connectors 317 / platform 15 / logic 7 / patterns 6 / connector-sdk 2 / learned-patterns.md 1）、`guides/` 13、glossary 1。移植後 `docs/` 合計 = 348 + 13 + 1 = **362**（example.md フィクスチャ削除後）。

---

## File Structure（P3a で作成/変更）

- `tests/test_docs_migration.py`（新規）— 移植インテグリティ検証。件数・フィクスチャ除去・MCP 純関数 smoke。**唯一責務: 移植の正しさ検証**。
- `docs/connectors/**`（追加 317 件、`_index.md` 上書き、`example.md` 削除）— コネクタ知識ベース。
- `docs/platform/**`, `docs/logic/**`, `docs/patterns/**`, `docs/connector-sdk/**`, `docs/learned-patterns.md`（新規・計 31 件）— その他知識ベース。
- `docs/guides/**`（新規 13 件）— エージェント参照用ガイド（lifecycle 等）。
- `docs/i18n/GLOSSARY.md`（新規 1 件）— 用語集。
- `.gitignore`（変更の可能性）— `__pycache__/` `.pytest_cache/` が未除外なら追加。
- **変更しない**: `mcp/docs-overlay/server.py`, `overlay.py`（既存ロジックで配信可能）。

---

## Task 1: feature ブランチ作成と前提確認

**Files:** なし（ブランチ操作）

- [ ] **Step 1: 最新 main から feature ブランチを作成**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
git checkout main && git pull --ff-only
git checkout -b feat/p3a-knowledge-base-migration
```
Expected: `feat/p3a-knowledge-base-migration` に切り替わる。

- [ ] **Step 2: 移植元 repo の存在と期待件数を確認**

Run:
```bash
OLD=/Users/ryotaro/workspace/workato-dev-kit
test -d "$OLD/docs" && echo "OLD_OK" || echo "OLD_MISSING"
echo "src docs total: $(find "$OLD/docs" -name '*.md' | wc -l | tr -d ' ')"
echo "src connectors: $(find "$OLD/docs/connectors" -name '*.md' | wc -l | tr -d ' ')"
echo "src guides: $(find "$OLD/guides" -name '*.md' | wc -l | tr -d ' ')"
test -f "$OLD/i18n/GLOSSARY.md" && echo "GLOSSARY_OK" || echo "GLOSSARY_MISSING"
```
Expected: `OLD_OK` / `src docs total: 348` / `src connectors: 317` / `src guides: 13` / `GLOSSARY_OK`。件数が違う場合は移植元が更新されているので、以降の Step の期待値を実測値に合わせて報告する（BLOCKED ではない）。

---

## Task 2: 移植インテグリティテスト（TDD・先に失敗させる）

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/tests/test_docs_migration.py`

- [ ] **Step 1: 失敗するテストを書く**

`/Users/ryotaro/workspace/workato-toolkit/tests/test_docs_migration.py`:
```python
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

sys.path.insert(0, str(REPO / "mcp" / "docs-overlay"))
import overlay  # noqa: E402


def test_connectors_migrated():
    n = len(list((DOCS / "connectors").glob("*.md")))
    assert n >= 317, f"expected >=317 connector docs, got {n}"


def test_index_is_real_not_p2_fixture():
    idx = (DOCS / "connectors" / "_index.md").read_text(encoding="utf-8")
    assert "Full content is migrated in P3" not in idx, "still the P2 placeholder _index.md"


def test_p2_example_fixture_removed():
    assert not (DOCS / "connectors" / "example.md").exists(), "P2 fixture example.md must be removed"


def test_platform_logic_patterns_present():
    assert len(list((DOCS / "platform").glob("*.md"))) >= 15
    assert len(list((DOCS / "logic").glob("*.md"))) >= 7
    assert len(list((DOCS / "patterns").rglob("*.md"))) >= 6
    assert len(list((DOCS / "connector-sdk").glob("*.md"))) >= 2
    assert (DOCS / "learned-patterns.md").is_file()


def test_guides_migrated():
    assert len(list((DOCS / "guides").glob("*.md"))) >= 13


def test_glossary_migrated():
    assert (DOCS / "i18n" / "GLOSSARY.md").is_file()


def test_total_docs_count():
    total = len(list(DOCS.rglob("*.md")))
    assert total >= 362, f"expected >=362 md after migration, got {total}"


def test_mcp_serves_real_connector_index():
    out = overlay.resolve_doc(DOCS, None, "connectors/_index.md")
    assert "NOT FOUND" not in out
    assert "Full content is migrated in P3" not in out


def test_mcp_lists_connectors():
    paths = overlay.list_docs(DOCS, None, "connectors/")
    assert len(paths) >= 317, f"MCP list_docs returned {len(paths)} connectors"


def test_mcp_serves_a_guide():
    paths = overlay.list_docs(DOCS, None, "guides/")
    assert len(paths) >= 13
```

- [ ] **Step 2: テストを実行して失敗を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_docs_migration.py -v
```
Expected: FAIL。`test_connectors_migrated`（フィクスチャのみ=2件未満）、`test_p2_example_fixture_removed`（example.md がまだ存在）、`test_total_docs_count` 等が落ちる。

- [ ] **Step 3: テストファイルだけコミット**

Run:
```bash
git add tests/test_docs_migration.py
git commit -m "test(docs): add knowledge-base migration integrity tests (failing)"
```
末尾に `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` を付ける。

---

## Task 3: docs/ 知識ベースの移植

**Files:**
- Delete: `/Users/ryotaro/workspace/workato-toolkit/docs/connectors/example.md`
- Modify(overwrite): `/Users/ryotaro/workspace/workato-toolkit/docs/connectors/_index.md`
- Create: `docs/connectors/*.md`（317）, `docs/platform/**`, `docs/logic/**`, `docs/patterns/**`, `docs/connector-sdk/**`, `docs/learned-patterns.md`

- [ ] **Step 1: P2 フィクスチャ `example.md` を削除**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
git rm docs/connectors/example.md
```
Expected: `rm 'docs/connectors/example.md'`。

- [ ] **Step 2: 旧 docs/ ツリーを rsync でコピー（`_index.md` は実体で上書き）**

Run:
```bash
OLD=/Users/ryotaro/workspace/workato-dev-kit
rsync -a --exclude='.DS_Store' "$OLD/docs/" docs/
```
Expected: エラーなし。`docs/connectors/_index.md` が実コンテンツに置き換わり、`docs/platform/` `docs/logic/` `docs/patterns/` `docs/connector-sdk/` と `docs/learned-patterns.md` が作られる。

- [ ] **Step 3: 件数を確認**

Run:
```bash
echo "connectors: $(find docs/connectors -name '*.md' | wc -l | tr -d ' ')"
echo "docs total: $(find docs -name '*.md' | wc -l | tr -d ' ')"
grep -L "Full content is migrated in P3" docs/connectors/_index.md && echo "INDEX_REAL"
```
Expected: `connectors: 317` / `docs total: 348`（この時点では guides/glossary 未移植）/ `INDEX_REAL`（フィクスチャ文言が無い=実体）。

- [ ] **Step 4: ステージしてコミット**

Run:
```bash
git add docs/
git commit -m "feat(docs): migrate knowledge base (connectors/platform/logic/patterns/sdk) from workato-dev-kit"
```
末尾に Co-Authored-By 行を付ける。

---

## Task 4: guides を docs/guides/ へ移植

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/docs/guides/*.md`（13）

- [ ] **Step 1: guides を docs/guides/ にコピー**

Run:
```bash
OLD=/Users/ryotaro/workspace/workato-dev-kit
mkdir -p docs/guides
rsync -a --exclude='.DS_Store' "$OLD/guides/" docs/guides/
echo "guides: $(find docs/guides -name '*.md' | wc -l | tr -d ' ')"
```
Expected: `guides: 13`。

- [ ] **Step 2: コミット**

Run:
```bash
git add docs/guides
git commit -m "feat(docs): migrate developer guides into docs/guides (MCP-served)"
```
末尾に Co-Authored-By 行を付ける。

---

## Task 5: glossary を docs/i18n/ へ移植

**Files:**
- Create: `/Users/ryotaro/workspace/workato-toolkit/docs/i18n/GLOSSARY.md`

- [ ] **Step 1: glossary をコピー**

Run:
```bash
OLD=/Users/ryotaro/workspace/workato-dev-kit
mkdir -p docs/i18n
cp "$OLD/i18n/GLOSSARY.md" docs/i18n/GLOSSARY.md
test -f docs/i18n/GLOSSARY.md && echo "GLOSSARY_PLACED"
```
Expected: `GLOSSARY_PLACED`。

- [ ] **Step 2: コミット**

Run:
```bash
git add docs/i18n/GLOSSARY.md
git commit -m "feat(docs): migrate terminology glossary into docs/i18n"
```
末尾に Co-Authored-By 行を付ける。

---

## Task 6: 全テスト緑化と MCP smoke 検証

**Files:** なし（検証）。必要なら `.gitignore` を変更。

- [ ] **Step 1: 移植テストを実行して PASS を確認**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
python3 -m pytest tests/test_docs_migration.py -v
```
Expected: 全 PASS。落ちる場合は Task 3〜5 の件数 Step に戻って差分を特定する。

- [ ] **Step 2: 既存スイート全体を実行（回帰がないこと）**

Run:
```bash
python3 -m pytest -q
```
Expected: `tests/test_overlay.py`・`tests/test_manifests.py`・`tests/test_docs_migration.py` すべて PASS。

- [ ] **Step 3: overlay 純関数で実コンテンツ配信を smoke 確認**

Run:
```bash
python3 - <<'PY'
import sys
from pathlib import Path
repo = Path.cwd()
sys.path.insert(0, str(repo / "mcp" / "docs-overlay"))
import overlay
docs = repo / "docs"
print("connectors listed:", len(overlay.list_docs(docs, None, "connectors/")))
print("guides listed:", len(overlay.list_docs(docs, None, "guides/")))
out = overlay.resolve_doc(docs, None, "connectors/_index.md")
print("index NOT FOUND?:", "NOT FOUND" in out)
print("index still fixture?:", "Full content is migrated in P3" in out)
PY
```
Expected: `connectors listed: 317` / `guides listed: 13` / `index NOT FOUND?: False` / `index still fixture?: False`。

- [ ] **Step 4: `__pycache__`/`.pytest_cache` が tracked なら除外**

Run:
```bash
git status --short | grep -E "__pycache__|\.pytest_cache" && echo "NEEDS_IGNORE" || echo "CLEAN"
```
`NEEDS_IGNORE` の場合のみ、`.gitignore` に以下を追記して `git rm -r --cached` で除外:
```bash
printf '\n__pycache__/\n*.pyc\n.pytest_cache/\n' >> .gitignore
git rm -r --cached --ignore-unmatch '**/__pycache__' '.pytest_cache' 2>/dev/null || true
git add .gitignore
git commit -m "chore: ignore python cache artifacts"
```
末尾に Co-Authored-By 行を付ける。`CLEAN` の場合はこの Step をスキップ。

---

## Task 7: push と PR 作成

**Files:** なし（git/PR 操作）

- [ ] **Step 1: ブランチを push**

Run:
```bash
cd /Users/ryotaro/workspace/workato-toolkit
git push -u origin feat/p3a-knowledge-base-migration
```
Expected: リモートに push 成功。

- [ ] **Step 2: PR 作成**

Run:
```bash
gh pr create --base main --head feat/p3a-knowledge-base-migration \
  --title "P3a: migrate knowledge base (docs/guides/glossary) into shared docs tree" \
  --body "$(cat <<'EOF'
## P3a — Knowledge Base Migration

旧 `workato-dev-kit` の知識ベースを `workato-toolkit` の共有 `docs/` ツリーへ移植。docs-overlay MCP（P2）がフィクスチャではなく実コンテンツを返すようになる。

### 移植内容
- `docs/connectors/` 317 件（`_index.md` を実体化、P2 の `example.md` フィクスチャ削除）
- `docs/platform/` 15 / `docs/logic/` 7 / `docs/patterns/` 6 / `docs/connector-sdk/` 2 / `docs/learned-patterns.md`
- `docs/guides/` 13（lifecycle 等、エージェント参照用。MCP 配信下）
- `docs/i18n/GLOSSARY.md`

### 検証
- `tests/test_docs_migration.py`（件数・フィクスチャ除去・MCP 純関数 smoke）
- `pytest -q` 全 PASS
- overlay smoke: connectors=317 / guides=13 / index は実体

サーバ側コード（`mcp/docs-overlay/`）は無変更。次: P3b（skills 移植 + MCP 参照置換）。

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
Expected: PR URL が返る。

- [ ] **Step 3: ユーザーに PR URL を報告し、レビュー/マージ判断を仰ぐ**

---

## Self-Review（plan 作成者によるチェック結果）

**Spec coverage（§5「初期コンテンツ移植」のうち本 plan 担当分）:**
- docs 移植 → Task 3 ✅ / guides 移植 → Task 4 ✅ / glossary → Task 5 ✅ / MCP が実コンテンツ配信 → Task 6 Step 3 ✅。
- skill の `@docs/@org/docs` → MCP 置換、rules/agents/hooks 移植、派生生成、`sync-check.yml` は **本 plan のスコープ外**（P3b/P3c）。spec §5 のこれらは別 plan で担保する旨を冒頭スコープに明記済み。

**Placeholder scan:** TODO/TBD/「適切に処理」等なし。全 Step に実コマンド/実コードあり。

**Type consistency:** テストで使う `overlay.resolve_doc(kit_dir, org_dir, rel)` / `overlay.list_docs(kit_dir, org_dir, prefix)` は P2 実装（`mcp/docs-overlay/overlay.py`）のシグネチャと一致。`docs/` 配下パス（`connectors/_index.md` 等）は MCP の `_norm` 規約（`.md` 補完・`..` 拒否）に適合。

**件数の前提:** 移植元の実測（2026-06-07）に依存。Task 1 Step 2 で再計測し、ズレたら期待値を実測へ合わせる手順を明記済み（テストは `>=` 比較で軽微増加に耐性）。
