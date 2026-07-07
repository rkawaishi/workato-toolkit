---
status: done
---

# 設計: Claude Code 専用化と plugin/ 物理隔離(配布物 / 開発基盤の分離)

- 日付: 2026-07-06
- ステータス: ユーザー承認済み(会話上で設計承認。本文書はその書き起こし)
- 前提コミット: `d8a335e`(P5 マージ済み、v0.1.0 tag **未発行** = 利用者ゼロ)

## 1. 背景と目的

このリポジトリは Workato 開発ツールキットをエディタネイティブのプラグインとして配布する。
一方で、**このプラグイン自体を開発するためのツール・ルール・ドキュメント**もこのリポジトリに
蓄積していくが、現状の構成には「開発側の居場所」が用意されていない:

- **root の `CLAUDE.md` を製品(生成物)が占有している。** プラグイン配布モデルでは利用者は
  リポジトリの `CLAUDE.md` を読まない(`bin/session-start-rules` が `AGENTS.md` を SessionStart で
  注入する)。つまり root `CLAUDE.md` の実質唯一の読者は「このリポジトリを開発する Claude Code
  セッション」なのに、中身は Workato 利用者向けルール 49KB で、開発ルール(真ソースは
  `rules/*.md`、sync 手順、pytest、リリースフロー)が一切届かない。issue #6(49KB 警告)と同根。
- **開発ドキュメント(設計 spec / 実装プラン / handover)が未コミット。** メインチェックアウトの
  `superpowers/`(untracked)と `.claude/handovers/`(ローカル)に散在している。`docs/` は
  docs-overlay MCP がそのまま利用者に配信する製品ツリーなので、開発文書を置けない。
- 配布物と開発ツールが root に混在し、境界が暗黙。

あわせて方針転換として **Claude Code を唯一の公式サポート対象**とし、Cursor / Codex / Gemini
対応は一旦保留(凍結)する。

## 2. 決定事項(ユーザー判断)

| # | 論点 | 決定 |
|---|---|---|
| D1 | サポート対象 | **Claude Code 専用**。他エディタは一旦保留 |
| D2 | 他エディタ資材の扱い | **凍結**(生成停止・ファイル温存)。削除しない |
| D3 | ディレクトリ構成 | **方針B: 配布物を `plugin/` サブディレクトリに物理隔離** |

### 凍結(frozen)の定義

- 内容の保守・自動生成・動作保証を**停止**する。テストも内容ドリフトを検査しない。
- ただし**本移行に伴う機械的なパス修正のみ1回限り実施**する(marketplace の `source` 書き換え、
  `git mv` によるディレクトリ移動)。これをしないと凍結資材が「古い」ではなく「壊れた」状態で残るため。
- 以後は触らない。復活時は `scripts/sync_derived.py` の生成対象に戻し、実機再検証してから解凍する。

## 3. 境界原則

> **`plugin/` の下 = 利用者に届くもの。root = 開発者のためのもの。**

- `plugin/` がプラグインルート(インストール後の `${CLAUDE_PLUGIN_ROOT}`)になる。
- root には開発ツール(`scripts/` `tests/` `.github/`)、開発ドキュメント(`dev/`)、
  開発セッション用コンテキスト(`CLAUDE.md`)、マーケットプレイス定義(`.claude-plugin/marketplace.json`
  — マーケットプレイスはリポジトリ root で解決されるため root 必須)を置く。

## 4. 新ディレクトリ構成

```
workato-toolkit/                      ← リポジトリ root = 開発空間
├── .claude-plugin/
│   └── marketplace.json              # source: "./" → "./plugin" に変更
├── plugin/                           # ★配布物 = プラグイン本体
│   ├── .claude-plugin/plugin.json    # プラグイン manifest(移動のみ・無修正)
│   ├── skills/                       # 21 スキル(移動のみ)
│   ├── docs/                         # 製品ナレッジベース(移動のみ。docs-overlay MCP が配信)
│   ├── rules/                        # 真ソース *.md 9本 +(凍結)*.mdc
│   ├── agents/                       # *.md +(凍結)*.toml
│   ├── bin/                          # hook スクリプト4本(移動のみ)
│   ├── hooks/                        # hooks.json +(凍結)cursor/codex 変種
│   ├── mcp/docs-overlay/             # MCP サーバ(移動のみ・無修正)
│   ├── .mcp.json                     # 利用者向け MCP 定義(移動のみ・無修正)
│   ├── AGENTS.md                     # ★唯一の生成継続物(SessionStart hook のペイロード)
│   ├── GEMINI.md                     # 凍結(生成停止)
│   ├── credential-patterns.txt       # (移動のみ)
│   ├── .cursor-plugin/plugin.json    # 凍結(移動のみ)
│   ├── .codex-plugin/plugin.json     # 凍結(移動のみ)
│   └── .codex.mcp.json               # 凍結(移動のみ)
├── .cursor-plugin/marketplace.json   # 凍結。source を "./plugin" へ1回修正
├── .agents/plugins/marketplace.json  # 凍結。source.path を "./plugin" へ1回修正
├── CLAUDE.md                         # ★手書き・このリポジトリの開発ルール(生成廃止)
├── .mcp.json                         # ★新規・開発セッション用(plugin/ 配下の server.py を相対起動)
├── dev/                              # ★新規・開発ドキュメント(コミットする)
│   ├── specs/                        # 設計 spec(本文書を含む)
│   ├── plans/                        # 実装プラン
│   └── handovers/                    # セッション引き継ぎ
├── scripts/sync_derived.py           # 縮小(§6)
├── tests/                            # パス更新 + 凍結前提へ調整(§7)
├── .github/workflows/                # sync-check.yml / release.yml(対象縮小)
├── README.md  LICENSE  .gitignore
```

## 5. 移動・変更マッピング

| 現在 | 移行後 | 種別 |
|---|---|---|
| `skills/` `docs/` `bin/` `mcp/` `credential-patterns.txt` | `plugin/` 配下へ | `git mv` のみ |
| `rules/`(*.md + 凍結 *.mdc) | `plugin/rules/` | `git mv` のみ |
| `agents/`(*.md + 凍結 *.toml) | `plugin/agents/` | `git mv` のみ |
| `hooks/`(hooks.json + 凍結2種) | `plugin/hooks/` | `git mv` のみ |
| `.mcp.json` | `plugin/.mcp.json` | `git mv`(無修正)。root に開発用 `.mcp.json` を**新規**作成 |
| `.claude-plugin/plugin.json` | `plugin/.claude-plugin/plugin.json` | `git mv` のみ(`"hooks": "./hooks/hooks.json"` は plugin root 相対なので無修正) |
| `.claude-plugin/marketplace.json` | root のまま | `plugins[].source`: `"./"` → `"./plugin"` |
| `AGENTS.md` | `plugin/AGENTS.md` | `git mv` + 生成継続(§6) |
| `GEMINI.md` | `plugin/GEMINI.md` | `git mv` + **生成停止**(凍結) |
| `CLAUDE.md`(生成物) | **廃止** → root に手書き開発コンテキストを新規作成(§8) | 置き換え |
| `.cursor-plugin/plugin.json` | `plugin/.cursor-plugin/plugin.json` | `git mv`(凍結。内部参照 `skills/` 等は plugin root 相対なので整合) |
| `.cursor-plugin/marketplace.json` | root のまま | `plugins[].source`: `"."` → `"./plugin"`(凍結の例外) |
| `.agents/plugins/marketplace.json` | root のまま | `source.path`: `"./"` → `"./plugin"`(凍結の例外) |
| `.codex-plugin/` `.codex.mcp.json` | `plugin/` 配下へ | `git mv`(凍結) |
| `scripts/` `tests/` `.github/` `README.md` `LICENSE` | root のまま | scripts/tests は参照パス更新 |
| メインチェックアウト `superpowers/*-design.md` + `superpowers/specs/*.md`(untracked) | `dev/specs/` | 取り込んでコミット(`.html` は生成ビジュアライズのため対象外) |
| メインチェックアウト `superpowers/*-plan.md`(8本、untracked) | `dev/plans/` | 取り込んでコミット |
| メインチェックアウトの `.claude/handovers/*.md` | `dev/handovers/` | 取り込んでコミット |

### 無修正で動く根拠(検証済み)

- `mcp/docs-overlay/server.py:16` — `KIT_DOCS = HERE.parents[2] / "docs"`。**自ファイル位置基準**
  なので `mcp/` と `docs/` が一緒に `plugin/` へ動けば解決先は `plugin/docs`。
- `bin/session-start-rules` — `${CLAUDE_PLUGIN_ROOT}` → `plugin/`、フォールバックも
  スクリプト位置基準(`bin/..`)。`plugin/AGENTS.md` を正しく見つける。
- `bin/block-credential-read.sh:28` — `credential-patterns.txt` をスクリプト位置基準
  (`dirname/../`)で解決。`bin/` と同時に移動するため整合。
- `hooks/hooks.json` — 参照は `${CLAUDE_PLUGIN_ROOT}/bin/...` で plugin root 基準。無修正。

## 6. `scripts/sync_derived.py` の縮小

- 生成対象を **`plugin/rules/*.md` → `plugin/AGENTS.md` のみ**に縮小。
  - 削除: `sync_rules_mdc()` / `sync_aggregate_mdc()` / `sync_agent_toml()`、
    `CLAUDE.md` / `GEMINI.md` 出力、Codex スラッシュ書き換えヘルパ。
  - 維持: `split_frontmatter` / `demote_headings` / `trim_trailing_newlines`、
    AGENTS.md 見出し `# Workato Toolkit — Agent Context`。
- `CONTEXT_INTRO`(AGENTS.md 冒頭の製品向け文言)から Cursor / Gemini / Codex の配信経路の
  記述を落とし、「delivered automatically via the plugin's SessionStart hook
  (bin/session-start-rules)」に簡素化する(凍結エディタへの言及を製品文から除去)。
  docs-overlay MCP に関する第2段落は維持。

## 7. tests / CI の方針

- 参照パスの基点を `plugin/` に更新(`REPO_ROOT / "skills"` → `REPO_ROOT / "plugin" / "skills"` 等)。
- 多エディタ派生の内容ドリフト検査(`.mdc` / `.toml` / `GEMINI.md` / `CLAUDE.md` の同期検証)は
  **凍結ガードへ置き換える**: 凍結ファイルが存在すること、`sync_derived.py` がそれらを
  再生成**しない**こと(実行前後で凍結ファイルに差分が出ない)を検査。
- `test_manifests.py` は `source: "./plugin"` と新配置を検証する形に更新。
- stale-path 系の全走査ガード(P4/P5 の教訓: 「全スキル/全ファイル走査」の高度で書く)は
  基点を変えて維持する。root `CLAUDE.md`(手書き)は走査対象から除外しない —
  開発文書にも stale パスは混入しうるため、対象に含めたまま新パス規約で検査する。
- CI: `sync-check.yml`(derived-files ジョブ + tests ジョブ)/ `release.yml`(tag 発火)の構造は
  不変。derived-files ジョブの diff スコープを現行の
  `rules/ agents/ CLAUDE.md AGENTS.md GEMINI.md` から `plugin/rules/ plugin/agents/ plugin/AGENTS.md`
  に更新する(CLAUDE.md / GEMINI.md は生成物でなくなるためスコープから外す)。

## 8. root `CLAUDE.md`(手書き・開発コンテキスト)の章立て

数 KB に収める。内容:

1. **このリポジトリは何か** — Workato ツールキットをプラグイン配布するリポジトリ。
   境界原則(`plugin/` = 配布物、root = 開発)。
2. **真ソースと生成物** — 真ソースは `plugin/rules/*.md`。`plugin/AGENTS.md` は生成物
   (直接編集禁止)。編集後は `python3 scripts/sync_derived.py` → `pytest`。
3. **開発フロー** — テストガードの流儀(全走査・高度)、リリースは tag 発火(`release.yml`)、
   version bump の場所(`plugin/.claude-plugin/plugin.json`)。
4. **凍結資材** — 一覧と「触らない」宣言、復活時の手順指針(生成対象へ戻す → 実機検証)。
5. **開発ドキュメント** — spec は `dev/specs/`、プランは `dev/plans/`、handover は
   `dev/handovers/` に保存・コミットする(brainstorming / writing-plans / handover 系スキルの
   保存先はこの宣言が優先)。
6. **検証** — self-install スモーク手順への参照、開発用 `.mcp.json` の説明。

README にも「Repository layout」節(境界原則 + 凍結宣言)を追加する。

## 9. 開発セッションの自己テスト性

- root `.mcp.json`(新規): `plugin/mcp/docs-overlay/server.py` を**リポジトリ相対パス**で起動する
  開発用定義。開発セッションで `workato_docs_lookup` を直接検証できるようにする。
  サーバ名は利用者向けと衝突しないよう `workato-docs-dev` とする(プラグイン併存時の名前衝突回避)。
- self-install スモーク(完了条件の一部): ローカルパスで
  `/plugin marketplace add <repo>` → `/plugin install workato-toolkit@workato-toolkit` →
  `ping` スキル応答 / SessionStart 注入にルール本文 / `workato_docs_lookup("connectors/slack.md")` が
  返る / credential guard が発火する、を確認。

## 10. リスク

| リスク | 扱い |
|---|---|
| `source: "./plugin"` の GitHub リモート解決が実機で通るか | ローカル marketplace add では検証済みにできる。リモートは既存の P6 Phase A(リリースゲート)に検証項目として追加。NG でも調整は marketplace 設定のみでツリー影響なし |
| テストのパス書き換え漏れ | 全走査ガード + pytest green を完了条件に |
| 凍結ファイルの1回修正の漏れ(marketplace source 等) | §5 のマッピング表を実装プランのチェックリストにする |
| 利用者影響 | v0.1.0 tag 未発行・利用者ゼロのため無し。version は 0.1.0 のまま |

## 11. スコープ外

- v0.1.0 tag の発行とリリース実行(P6 Phase C)
- Gemini 対応(P6 Phase B)・Cursor / Codex の解凍
- `workato-dev-kit` リポジトリの deprecation 告知(P6 Phase D)
- GitHub リモートからのインストール実機検証(P6 Phase A — 本設計はローカル検証まで)
- `rules/*.md` の内容再編(常時オン→オンデマンド化などの製品挙動変更。issue #6 の未決部分)

## 12. 完了条件

1. `pytest` green(パス更新後の全ガード含む)。
2. `python3 scripts/sync_derived.py` 実行後に `git diff` が空(ドリフトなし)。
3. §9 の self-install スモークがローカルで通る。
4. root `CLAUDE.md` が手書き開発コンテキストになっている(生成物への言及が正しく、数 KB)。
5. `dev/` に本 spec・既存プラン・handover がコミットされている。
6. 凍結資材が §5 のとおり配置され、README に凍結宣言がある。
