# workato-toolkit: plugin/extension 配布への移行 設計 (spec)

- 日付: 2026-06-07
- 対象: Workato Dev Kit を AI コーディングエージェント向け **plugin/extension** として配布する新リポジトリ `workato-toolkit`
- ステータス: 設計合意済み(実装 plan は別途)

## 1. 背景と目的

現行 `workato-dev-kit` は **git submodule + `setup.sh`** で、ユーザーの workspace repo に symlink/copy を張る方式で配布している。対象は Claude Code / Cursor / Codex CLI / Gemini CLI の4エディタで、`sync_agents.py` が canonical(`framework/claude/`)から各エディタ版を生成している。

2026年前半に4エディタすべてが **plugin/extension + marketplace 機構**を備えた(Codex は 2026-03 に marketplace 公開、Gemini は extensions、Cursor は独自 plugin、CC は plugin)。これにより、submodule + symlink の煩雑な導入を **各エディタのネイティブな1コマンド導入**に置き換えられる。

### 方針(確定事項)

- **現 `workato-dev-kit` の開発は停止(凍結)**。今後の開発は新規リポジトリ **`workato-toolkit`** でのみ行う。
- `workato-toolkit` は **canonical(共通 source)兼 配布元**の単一アクティブ repo。旧 repo からの cross-repo publish パイプラインは作らない。
- **マルチエディタ(4エディタ)維持**。各エディタのネイティブ plugin/extension として配布する。
- **共有ツリー型**。リポジトリ root 自体が plugin で、`skills/` `docs/` `bin/` `agents/`(md)は **コピーせず1式を全エディタで共有**する。各エディタの manifest が同じ共有 dir(`source: "./"`)を指す。実在の複数エディタ plugin(archcore-ai/plugin, hiivmind/plugin-portability, kdoroszewicz/cursor-plugins-claude 等)の慣行に倣う。
- **エディタ別 `dist/` の複製は作らない**(§2「共有 vs 既約差分」参照)。派生が必要なのは hooks(3種)・Cursor `.mdc`・Codex agent `.toml`・各 context ファイルだけで、これらは手書き維持か極小生成で対応。
- 段階的な「併設(submodule と plugin の両立)」はしない。クリーンに plugin ネイティブへ移行する。

### 非目標 (out of scope)

- 旧 repo の sync_agents.py を拡張して別 repo へ publish する仕組み(不要)。
- エディタ別 `dist/{claude,codex,cursor,gemini}` への skills/docs 複製生成(不要。共有ツリー型を採用)。
- 既存 submodule ユーザーの自動移行ツール(ドキュメント誘導で対応)。

## 2. なぜ plugin が適合するか / 制約

### 適合する点

- 導入/更新 UX: `marketplace add` → `install` → `update` の数コマンド。symlink/copy の脆弱性(特に Cursor)が解消。
- バンドル: skills / agents / hooks / 大量の docs(316コネクタ等)をすべて同梱し、plugin-root 変数で参照可能。
- 1 repo が4エディタ同時の marketplace になれる(各 marketplace 定義ファイルのパスが衝突しない)。

### 共有できるもの vs 既約的にエディタ別

実在の複数エディタ plugin の調査結果、本体の大半は1式共有でき、コピーが要るのは極小の派生ファイルだけ。

| 要素 | 共有1式 | エディタ別(小・既約) |
|---|---|---|
| skills(`SKILL.md`) | ✅(開放標準 Agent Skills を全エディタが同一ファイルで読む) | — |
| docs / bin(hook 実体スクリプト) | ✅ | — |
| agents | md は共有 | Codex のみ `.toml` も併置 |
| hooks | スクリプト本体は共有 | `hooks.json` を3種(plugin-root 変数名・イベント名 casing が違う) |
| 常時ルール | 本文は共有 | Cursor `.mdc`、Gemini `GEMINI.md`、CC/Codex は hook |
| manifest / marketplace | — | 各エディタ1つずつ(極小・既約) |

**鍵となる設計ルール**: plugin-root 変数は **hooks / `.mcp.json` のコマンド文字列だけ**に閉じ込め、`SKILL.md` 本文には書かない。skill フォルダ直下の付随ファイルは相対参照でよい。**共有 `docs/` 知識ベースへの参照は docs-overlay MCP 経由**に統一する(決定: §4.5)— skill 本文の素の相対パスは「ユーザー cwd」基準に解決され同梱 docs を指さず、plugin-root 変数はエディタ別だが、MCP は4エディタ共通だから。これが「単一 SKILL.md 共有」と知識ベース参照を両立させる核心。

### エディタ別の差分(manifest / hooks / sidecar に限定)

| 差分 | CC | Codex | Cursor | Gemini |
|---|---|---|---|---|
| marketplace 定義 | `.claude-plugin/marketplace.json` (repo root) | `.agents/plugins/marketplace.json` | `.cursor-plugin/marketplace.json` | URL + `--ref` で install(専用 marketplace ファイルなし) |
| plugin manifest | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` | `.cursor-plugin/plugin.json` | `gemini-extension.json` |
| plugin-root 変数 | `${CLAUDE_PLUGIN_ROOT}` | `$PLUGIN_ROOT` / `$PLUGIN_DATA` | 相対パス | `${extensionPath}` |
| 常時ルール配信 | SessionStart hook | SessionStart hook | `.mdc`(`alwaysApply`) | `GEMINI.md`(`contextFileName`)で自動ロード |
| skill/command 癖 | そのまま | slash `/foo` → `$foo` 書き換え | `.mdc` rules | TOML コマンド |

### 残る制約 / トレードオフ

- **permissions**: plugin は `permissions.deny`(`*.key` 等の読取拒否リスト)を配れない(少なくとも CC)。credential guard の **hook は同梱可**(これが主ガード)。deny リストは install ドキュメントにスニペット掲載。
- **版固定**: Gemini は `--ref`(commit/tag)で pin 可。CC/Codex は marketplace/tag 単位で submodule の SHA pin よりやや緩い。→ tag リリース運用で担保。
- **常時ルール**: CC/Codex は plugin から CLAUDE.md/AGENTS.md を注入できない → SessionStart hook で注入。
- **org overlay / 成果物**: `org/docs/` と `projects/` はユーザー repo 側。`org/docs/` の参照は docs-overlay MCP(§4.5)が cwd/`git rev-parse` で解決して吸収するため skill 側は project-dir を意識しない。

## 3. アーキテクチャ

共有ツリー型。`src/`→`dist/` の二重構造を持たず、**リポジトリ root 自体が plugin**。各エディタの manifest が同じ共有 dir(`source: "./"`)を指す。

```
workato-toolkit/  (canonical 兼 配布元 / リポジトリ root = plugin 本体)
├── .claude-plugin/{marketplace.json, plugin.json}   # CC    : source "./"(skills/ agents/ hooks/ を規約で自動発見)
├── .cursor-plugin/plugin.json                        # Cursor: "skills":"skills/","rules":"rules/" ...
├── .codex-plugin/plugin.json                         # Codex : "skills":"./skills/","hooks":"./hooks/codex.hooks.json"
├── .agents/plugins/marketplace.json                  # Codex/AGENTS 流の discovery
├── gemini-extension.json                             # Gemini(配置は §6 の検証事項)
├── .mcp.json / .codex.mcp.json                       # docs-overlay MCP の起動定義(plugin-root 変数差のみ・極小 per-editor)
│
├── skills/<name>/SKILL.md        # ★ 共有1式。docs は docs-overlay MCP を呼ぶ(ファイル直読み/plugin-root 変数なし)
├── docs/                         # ★ 共有1式(知識ベース: コネクタ/logic/platform/patterns)。MCP が読む
├── mcp/docs-overlay/             # ★ 共有1式(docs-overlay MCP サーバ実体。kit docs + project の org/docs を merge)
├── bin/  (or scripts/)           # ★ 共有1式(hook 実体スクリプト: credential guard / validate / session-start-rules)
├── agents/<name>.md              # 共有(md)。Codex 用に <name>.toml を併置
├── rules/<name>.md               # 常時ルール本文(共有)。Cursor 用に <name>.mdc を併置
├── hooks/{hooks.json, cursor.hooks.json, codex.hooks.json}  # 3種・極小(変数名/イベント casing 差のみ)
├── CLAUDE.md / AGENTS.md / GEMINI.md   # context(本文は共有・@include か symlink)
├── .github/workflows/
│   ├── sync-check.yml            # 派生ファイル(.mdc/.toml/context/hooks)の整合検知
│   └── release.yml               # tag 時にリリース
└── README.md                     # 4エディタ分の install 手順
```

### データフロー

1. 開発者は共有ツリー(`skills/` `docs/` `bin/` `agents/*.md` `rules/*.md`)を編集。**コピー先はない**。
2. 派生ファイルだけを揃える(手書き、または旧 `sync_agents.py` の縮小版で生成):
   - `rules/*.md` → Cursor `rules/*.mdc`
   - `agents/*.md` → Codex `agents/*.toml`
   - 常時ルール → `CLAUDE.md` / `AGENTS.md` / `GEMINI.md`
   - `hooks/{hooks,cursor.hooks,codex.hooks}.json`(plugin-root 変数・イベント casing をエディタ別に)
3. すべて1リポジトリにコミット。CI は派生ファイルの整合だけ検証(skills/docs は生成物でないため検査対象外)。
4. ユーザーは各エディタのコマンドで marketplace 追加 + install(同じ共有ツリーを読む)。

### コンポーネントの責務

- **共有ツリー(`skills/` `docs/` `bin/` `agents/*.md` `rules/*.md`)**: 唯一の真実。全エディタが同一ファイルを読む。コピーなし。
- **manifest 群(`.claude-plugin/` 他)**: repo を4エディタの marketplace/extension にする入口。共有 dir を指すだけ。
- **派生ファイル(`.mdc`/`.toml`/context/hooks 3種)**: 数ファイルのみ。手書き維持か極小生成。`sync-check.yml` で整合を担保。
- **hooks**: credential guard(全エディタ同梱・実体は `bin/` 共有)+ CC/Codex 向け SessionStart ルール注入。

## 4. 常時ルールの配信

- **CC / Codex**: `bin/session-start-rules`(共有スクリプト)を hooks から呼び、SessionStart で `rules/` 由来の常時ルールを context 注入(現 `setup.sh` の CLAUDE.md import の置き換え)。
- **Cursor**: `rules/*.md` を `.mdc`(`alwaysApply: true`)へ展開(現 `workato-project.mdc` 相当)。
- **Gemini**: 常時ルールを `GEMINI.md` として出力し `contextFileName` で自動ロード。

## 4.5 docs/org overlay と組織ナレッジ共有(docs-overlay MCP)【C の結論】

共有範囲は **チーム内(1 workspace repo)**(ユーザー確認 2026-06-07)。組織横断の共有や org 専用 plugin は今回スコープ外。これにより #1(同梱 docs の参照方式)も本節の MCP で解決する。

仕組み:
- **kit docs**: plugin 同梱(`<plugin>/docs/`、読み取り専用)。
- **org docs**: ユーザーの workspace/project repo の `org/docs/` に置き、**git でチーム共有**(現行どおり。`docs/` 階層をミラーし衝突時は org が勝つ)。
- **docs-overlay MCP**(plugin 同梱、`.mcp.json` で起動)が両者を仲介:
  - `workato_docs_lookup(path)` 等で、plugin 同梱 docs + project の `org/docs/<path>` を読み、**org-wins** でマージして返す。
  - plugin docs の場所は MCP 起動コマンドに各エディタの plugin-root 変数(`${CLAUDE_PLUGIN_ROOT}` / `$PLUGIN_ROOT` / `${extensionPath}`)を渡して解決。per-editor の `.mcp.json` は極小(archcore の `.mcp.json` / `.codex.mcp.json` と同型)。
  - project の `org/docs/` は MCP の cwd / `git rev-parse --show-toplevel` で解決(Codex/Cursor に project-dir 変数が無い問題=§6.2.3 を吸収)。
- **読み取り規約の置き換え**: skill 本文の「`@docs/X` と `@org/docs/X` を両方読む」を **MCP ツール呼び出し1回**に置換。skill はファイル直読みせず tool を呼ぶ → 4エディタ共通、相対パス解決問題を回避。
- **学習書き戻し**: `/learn-recipe` `/learn-pattern` は project 側 `org/docs/<path>` へ通常の Write で書く(plugin は読み取り専用)。MCP 経由の write tool は任意。

効果: #1(kit docs 参照)・C(overlay)・学習書き戻し を1機構で解決。per-editor 生成は `.mcp.json`(+ 既存 hooks 3種)に限定され、**skills は完全共有のまま**。

## 5. 移行と運用

- **配布範囲 / ローンチ姿勢**（ユーザー確認 2026-06-07）: **public OSS** として公開（誰でも install 可)。**MVP 優先（早期）**で段階公開し、MVP スコープは実証済みの **CC + Cursor + Codex の3エディタ先行**、**Gemini は実機検証（§6.2.4）後に追加**。エンタープライズ特有要件（厳密な版固定・監査・SSO 等）は**今回は重視しない**ため、版固定は tag リリース程度で可。
- **成功指標（KPI）**: 組織内の採用率／ナレッジ共有の活用度／導入の容易さ（測定方法・目標値は別途）。
- **MVP スコープ（確定 2026-06-07）**: 対象エディタ = **CC + Cursor + Codex 先行、Gemini は §6.2.4 検証後に追加**。機能 = 共有ツリー + 各 manifest + 常時ルール配信 + credential guard hook に加え、**docs-overlay MCP と学習サイクル（`/learn-*`）も MVP に含める**（ナレッジ共有が価値の柱のため）。
- 旧 `workato-dev-kit`: README とトップに **deprecation 告知 + `workato-toolkit` への誘導**を追加。コードは凍結(緊急セキュリティ修正を除き変更しない)。
- 初期コンテンツ: 旧 repo の skills / rules / agents / hooks / docs を `workato-toolkit` の共有ツリー(`skills/` `rules/` `agents/` `bin/` `docs/`)へ移植して起点とする。移植時に skill 本文の `@docs/...` `@org/docs/...` 参照を **docs-overlay MCP の tool 呼び出し**(§4.5)へ置換する(素の相対パスは cwd 基準に解決され同梱 docs を指さないため不可)。
- 版固定: `workato-toolkit` を semver tag でリリース。README に各エディタの pin 方法(Gemini `--ref` 等)を明記。
- credential 安全性: guard hook を全パッケージに同梱。`permissions.deny` スニペットを install ドキュメントに掲載。
- CI: `sync-check.yml`(派生ファイル `.mdc`/`.toml`/context/hooks の整合検知)、`release.yml`(tag リリース)。

## 6. 技術調査の結果と要設計判断

### 6.1 調査で確定した事実(2026-06 時点)

| 項目 | 結果 | 出典/根拠 |
|---|---|---|
| Gemini install 単位 | `gemini extensions install <org>/<repo>` は **root の `gemini-extension.json` + root `skills/`** を読む。`--ref <tag/commit>` で版固定可。**サブディレクトリ install は不可前提**(root 必須) | geminicli.com/docs/extensions(verified) |
| manifest 共存 | 各エディタは自分の manifest だけ読み他を無視 → **1 repo に4種 manifest 共存可**(CC/Cursor/Codex は archcore-ai/plugin で実証。Gemini 込みの4種同居は inferred) | archcore-ai/plugin(verified 3種) |
| project-dir 変数 | CC `${CLAUDE_PROJECT_DIR}` / Gemini `${workspacePath}` は**あり**。**Codex/Cursor は無し**(Codex は `PLUGIN_ROOT`/`PLUGIN_DATA` のみ) | 各公式 doc(verified) |
| Codex manifest | `.codex-plugin/plugin.json` 必須=`name`/`version`/`description`(skills 同梱時 `skills` も)。marketplace は `.agents/plugins/marketplace.json`(`source` object・`policy`・`category` 必須) | developers.openai.com/codex(verified) |
| Cursor manifest | `.cursor-plugin/plugin.json` 必須=`name` のみ。marketplace は `name`/`owner`/`plugins[]`(`source` は文字列 `"./"` 可) | cursor.com/docs + zoom/skills(verified) |
| 共有 `skills/` 読み取り | CC/Cursor/Codex は共有 root `skills/` を manifest 経由で読む(archcore で実証)。**Gemini 込みの実例は未発見(inferred)** | archcore-ai/plugin |

### 6.2 要設計判断(残る論点)

1. **【決定済】同梱 docs の参照方法 → (a) docs-overlay MCP**(ユーザー確認 2026-06-07)。skill 本文の素の相対パスは cwd 基準で同梱 docs を指さず、plugin-root 変数はエディタ別で「単一 SKILL.md 共有」と衝突するため、**MCP 経由参照**を採用。詳細は §4.5。skills はファイル直読みせず tool を呼ぶので完全共有のまま。
2. **チーム/組織導入**: 「repo にコミットした設定で自動導入」は**実質 CC のみ**(`extraKnownMarketplaces`+`enabledPlugins`、ただし既知不具合 #32606 あり)。Codex は repo-root marketplace の自動 discovery 止まり、Cursor は管理ダッシュボード配布、Gemini は手動 install。→ **中〜大企業の組織展開は「README の install コマンド明示 + 任意で軽量 setup スクリプト」を現実解**とする(§顧客=組織利用に直結)
3. **【解決】org overlay の project-dir 解決**: docs-overlay MCP(§4.5)が project 側 `org/docs/` を cwd / `git rev-parse --show-toplevel` で解決するため、Codex/Cursor に project-dir 変数が無い問題は MCP 内で吸収。skill 側は project-dir を意識しない
4. **Gemini の同居実機確認**: Gemini 込み4種 manifest 同居 + 共有 `skills/` 読み取りは未実証。plan で最小 repo を作り実機検証。崩れる場合は **Gemini だけ別ブランチ/repo** に分離(fallback)

## 7. 受け入れ基準(完了の定義)

- `skills/` `docs/` `bin/` `agents/*.md` はコピーなしの1式で、4エディタ全てが共有して読む(`dist/` は存在しない)。
- 派生ファイル(`.mdc`/`.toml`/context/hooks 3種)が共有 source と整合している。
- 4エディタそれぞれで marketplace 追加 + install が成功し、skills/agents/hooks/常時ルール/docs 参照が動作する。
- credential guard hook が全エディタで発火する。
- CI が派生ファイルのドリフトを検知する。
- 旧 repo に deprecation 告知が入っている。
