---
status: done
---

# PR/FAQ レビュー: workato-toolkit — plugin/extension 配布への移行

- 日付: 2026-06-07
- 参照資料: `superpowers/2026-06-07-workato-toolkit-plugin-distribution-design.md`
- ステータス: レビュー待ち

> 注: 本書は参照 spec に**明示的に書かれている内容のみ**を書き起こしたもの。spec に根拠が無い項目は推測で埋めず `⚠️ 未決（要レビュー）` とした。

## 1. プレスリリース（PR）

- **見出し**: `workato-toolkit` — Workato Dev Kit を AI コーディングエージェント向け plugin/extension として配布する新リポジトリ
- **サブ見出し**: Workato を導入している中〜大企業が、組織として Workato 開発を行ううえで（特にナレッジ共有に）有効な形で、4エディタ（Claude Code / Cursor / Codex CLI / Gemini CLI）にネイティブな1コマンドで導入できる
  - 出典: 顧客セグメント・組織利用/ナレッジ共有重視は **ユーザー確認（2026-06-07）** による。spec 本文には未記載のため、spec への反映は別途要
- **日付・場所**: 公開場所 = **public OSS（GitHub の public repo/marketplace、誰でも install 可）**（ユーザー確認 2026-06-07）。ローンチ時期 = **MVP 優先（早期）で段階公開**（具体日は未定）
- **サマリ**: 何を = Workato Dev Kit を `workato-toolkit` という単一リポジトリで plugin/extension 配布する／誰に = 4エディタで Workato 開発する利用者／なぜ = 2026年前半に4エディタすべてが plugin/extension + marketplace 機構を備えたため、submodule + symlink の煩雑な導入をネイティブ1コマンド導入に置き換えられる
- **課題**: 現行は git submodule + `setup.sh` でユーザー repo に symlink/copy を張る方式で、導入が煩雑・symlink の脆弱性（特に Cursor）がある
- **解決**: リポジトリ root 自体を plugin とする「共有ツリー型」を採用。`skills/ docs/ bin/ agents/*.md` をコピーせず1式で全エディタが共有し、各エディタの manifest が同じ共有 dir（`source: "./"`）を指す。1 repo が4エディタ同時の marketplace になり、`marketplace add` → `install` → `update` で導入できる
- **顧客/責任者の声**: ⚠️ 未決（要レビュー）— spec に引用なし（創作しない）
- **入手方法・次の一歩**: 各エディタの marketplace 追加 + install。版固定は Gemini `--ref`（commit/tag）等、`workato-toolkit` を semver tag でリリース
  - ⚠️ 未決（要レビュー）: 各エディタの具体的な install コマンド文字列は spec 未記載（spec では README に4エディタ分の install 手順を載せる、とのみ記載）

## 2. FAQ

### 2.1 顧客 FAQ

1. **誰が顧客か**: Workato を導入している中〜大企業（組織として 4エディタのいずれかで Workato 開発を行う）。出典: ユーザー確認（2026-06-07）
2. **顧客の課題・機会は何か**: submodule + `setup.sh`（symlink/copy）方式の導入の煩雑さと脆弱性（特に Cursor の symlink 解決）。4エディタが plugin/extension 機構を備えたことで、ネイティブ1コマンド導入に置き換えられる機会。加えて、組織として開発知見・ナレッジを共有したいニーズ（出典: ユーザー確認 2026-06-07）
3. **最も重要な顧客便益は何か**: (a) `marketplace add` → `install` → `update` の数コマンドで導入/更新でき、symlink/copy の脆弱性が解消される。(b) 組織での利用に有効であること、特に**ナレッジ共有**（出典: ユーザー確認 2026-06-07 — 具体的な実現方法は ⚠️ 未決、下記「組織ナレッジ共有」参照）
4. **顧客が必要としている根拠は何か**: ⚠️ 未決（要レビュー）— 需要の根拠（ユーザー調査・要望・利用データ等）は spec に記載なし
5. **顧客体験はどのようなものか**: ユーザーは各エディタのコマンドで marketplace 追加 + install を行い、4エディタが同じ共有ツリー（`skills/` `docs/` 等）を読む

### 2.2 社内/ステークホルダー FAQ

- **スコープ**: 新規リポジトリ `workato-toolkit`（canonical 兼 配布元の単一アクティブ repo）／共有ツリー型（`skills/ docs/ bin/ agents/*.md` を1式共有、manifest が `source: "./"`）／4エディタ維持／常時ルールはエディタ別配信（CC/Codex は SessionStart hook、Cursor は `.mdc`、Gemini は `GEMINI.md`）／旧 `workato-dev-kit` は deprecation 告知して凍結
- **非スコープ**: 旧 repo の `sync_agents.py` を拡張して別 repo へ publish する仕組み／エディタ別 `dist/{claude,codex,cursor,gemini}` への skills/docs 複製生成／既存 submodule ユーザーの自動移行ツール／段階的な「併設（submodule と plugin の両立）」
- **代替手段（会話履歴からの下書き / 要確認）**:
  | 代替案 | 内容 | 不採用の理由 |
  |---|---|---|
  | 現行 submodule + `setup.sh` 継続 | 何も変えない | 導入が煩雑・symlink 脆弱性（特に Cursor）が残る。4エディタが plugin 機構を備えた今、ネイティブ導入の利点を逃す |
  | submodule と plugin の併設（段階移行） | 両方式を当面維持 | 二重メンテが恒久化。ユーザー確認で「クリーン移行・旧 repo 凍結」に決定 |
  | canonical はこの repo + 別 repo へ生成 publish（2 repo パイプライン） | 旧 repo を canonical に保つ | cross-repo publish の保守コスト。ユーザー確認で「新 repo を canonical 兼配布元に一本化」に決定 |
  | エディタ別 `dist/` 生成（per-editor 複製） | skills/docs を4エディタ分コピー生成 | 実在 plugin の慣行は共有ツリー型。複製は不要と判明（spec §1・§2） |
  | CC 一本化（他エディタ廃止） | plugin を CC 専用に | ユーザー確認で「4エディタ維持」 |
  - ⚠️ 未決（要レビュー）: 上記の不採用理由づけで妥当か（人が確認）
- **依存**: 各エディタの plugin/extension + marketplace 機構（CC plugin / Codex marketplace〔2026-03 公開〕/ Gemini extensions / Cursor plugin）／開放標準「Agent Skills（`SKILL.md`）」を全エディタが同一ファイルで読むこと／MCP ツール呼び出し（同梱ファイル参照の手段）
- **リスク / 制約**:
  - permissions: plugin は `permissions.deny`（`*.key` 等の読取拒否リスト）を配れない（少なくとも CC）。credential guard hook は同梱可（主ガード）、deny リストは install ドキュメントにスニペット掲載
  - 版固定: Gemini は `--ref` で pin 可だが、CC/Codex は marketplace/tag 単位で submodule の SHA pin よりやや緩い
  - 常時ルール: CC/Codex は plugin から CLAUDE.md/AGENTS.md を注入できない → SessionStart hook で注入
  - org overlay / 成果物: `org/docs/` と `projects/` はユーザー repo 側 = エディタの project-dir（cwd）基準の相対参照で解決（CC は `${CLAUDE_PROJECT_DIR}` 併用）
  - 設計上の前提リスク: `SKILL.md` 本文に plugin-root 変数を書かない（素の相対パス + MCP に限定）ことが共有成立の条件
- **組織ナレッジ共有（重点 / 確定: ユーザー確認 2026-06-07）**: 共有範囲は **チーム内(1 workspace repo)**。組織横断共有・org 専用 plugin は今回スコープ外。実現方式は **docs-overlay MCP**(spec §4.5):
  - kit docs は plugin 同梱(読み取り専用)、org docs は project の `org/docs/` に git 共有(現行どおり、チーム内共有はこれで成立)
  - plugin 同梱の docs-overlay MCP が「kit docs + project の org/docs」を merge(org-wins)して返す。skill はファイル直読みせず MCP tool を呼ぶ → 4エディタ共通、パス解決問題を回避
  - 学習(`/learn-recipe` 等)は project 側 `org/docs/` に Write(plugin は読み取り専用)
  - これにより #1(同梱 docs 参照)・org overlay・学習書き戻し を1機構で解決
- **配布・ローンチ（ユーザー確認 2026-06-07）**: public OSS として公開／MVP 優先（早期）。エンタープライズ特有要件（厳密な版固定・監査・SSO 等）は**今回は重視しない**。→ MVP スコープは実証済みの **CC + Cursor + Codex の3エディタ先行**とし、**Gemini は実機検証後に追加**が妥当（§6.2.4 の fallback と整合。要確認）
- **成功指標（KPI / ユーザー確認 2026-06-07）**: (1) 組織内の採用率（導入企業/ユーザー数・アクティブ数）、(2) ナレッジ共有の活用度（org overlay/学習サイクルでの蓄積・参照量）、(3) 導入の容易さ（install の時間/手順数、submodule+setup.sh からの改善）。加えて spec の「受け入れ基準（完了の定義）」:
  - `skills/ docs/ bin/ agents/*.md` がコピーなし1式で4エディタが共有して読む（`dist/` 不在）
  - 派生ファイル（`.mdc`/`.toml`/context/hooks 3種）が共有 source と整合
  - 4エディタで marketplace 追加 + install が成功し、skills/agents/hooks/常時ルール/docs 参照が動作
  - credential guard hook が全エディタで発火
  - CI が派生ファイルのドリフトを検知
  - 旧 repo に deprecation 告知
- **コスト/工数**: ⚠️ 未決（要レビュー）— 工数・コスト見積りは spec に記載なし
- **セキュリティ**: credential guard hook を全パッケージに同梱（実体は `bin/` 共有）。配れない `permissions.deny` は install ドキュメントにスニペット掲載
- **運用**: semver tag でリリース／`sync-check.yml`（派生ファイルの整合検知）・`release.yml`（tag リリース）／旧 `workato-dev-kit` はコード凍結（緊急セキュリティ修正を除き変更しない）

## 3. レビュー観点チェック

| 観点 | 状態 | 要点（資料から） | 人が確認すべき点 |
|---|---|---|---|
| 顧客 | 記載あり（ユーザー確認で確定） | Workato 導入済みの中〜大企業（組織利用） | エンタープライズ特有の要件（SSO/監査/版固定の厳密性等）を洗い出すか？ |
| 課題 | 記載あり | submodule + setup.sh の煩雑さ・symlink 脆弱性（特に Cursor）＋組織ナレッジ共有ニーズ | この課題の深刻度／頻度の裏付けは要るか？ |
| 価値 | 記載あり（一部 ⚠️ 未決） | ネイティブ1コマンド導入/更新、symlink 脆弱性解消、共有ツリーでコピー不要＋**組織ナレッジ共有** | ナレッジ共有を具体的にどう実現するか（org 共有の仕組み）？ |
| スコープ/非スコープ | 記載あり | 新 repo・共有ツリー・4エディタ維持・旧 repo 凍結 / 併設・dist 複製・自動移行は非スコープ | 旧 repo 凍結のタイミングと既存ユーザー影響は許容か？ |
| リスク | 記載あり | permissions.deny 不可・版固定が緩い・常時ルール注入・org overlay 解決 | 版固定の緩さはエンタープライズ要件を満たすか？ |
| 成功指標 | 記載あり（ユーザー確認で確定） | KPI=採用率／ナレッジ共有の活用度／導入の容易さ＋受け入れ基準6項目 | 各 KPI の測定方法・目標値をどう置くか？ |
| 配布/ローンチ | 記載あり（ユーザー確認で確定） | public OSS／MVP 優先（早期）／エンタープライズ特有要件は非重視 | MVP スコープを CC+Cursor+Codex 先行＋Gemini 後追いにするか？ |
| 依存 | 記載あり | 各エディタ plugin 機構・Agent Skills 標準・MCP | §6 の未確定（特に Gemini）が崩れた場合の代替は？ |
| セキュリティ | 記載あり | guard hook 同梱・deny はスニペット | hook 一本化で資格情報保護は十分か？ |
| 運用 | 記載あり | semver tag・sync-check/release CI・旧 repo 凍結 | 派生ファイルを手書き維持か生成かを決めたか？ |
| コスト/工数 | ⚠️ 未決 | 記載なし | 実装工数の見積りは必要か？ |

## 4. ⚠️ 未決一覧

- [x] 公開場所 → **確定: public OSS（GitHub public）**（ユーザー確認 2026-06-07）。ローンチ日は未定だが **MVP 優先（早期）**
- [x] 対象顧客のセグメント定義 → **確定: Workato 導入済みの中〜大企業（組織利用）**（ユーザー確認 2026-06-07）
- [x] エンタープライズ特有要件 → **確定: 今回は重視しない**（ユーザー確認 2026-06-07）
- [x] ビジネス成功指標（KPI）→ **確定: 採用率／ナレッジ共有の活用度／導入の容易さ**（測定方法・目標値は別途）
- [x] 各エディタの install コマンド → **確定**（CC: `/plugin marketplace add <org>/<repo>` + `/plugin install <name>@<mp>`／Codex: `codex plugin marketplace add <org>/<repo>` + `codex plugin add <name>`／Gemini: `gemini extensions install <org>/<repo> [--ref]`／Cursor: marketplace 経由 or `@local`）。README に整理して掲載
- [x] **組織ナレッジ共有（C）** → **確定: 範囲=チーム内(1 workspace repo)、方式=docs-overlay MCP**(kit docs 同梱 + project の org/docs を MCP が org-wins merge)。spec §4.5。組織横断はスコープ外
- [ ] MVP スコープの確定（CC+Cursor+Codex 先行 ＋ Gemini 後追い、で良いか）
- [ ] KPI の測定方法・目標値
- [ ] 顧客の需要根拠・顧客の声（社内判断/未取得なら「未取得」と明記でも可）
- [ ] コスト/工数の見積り（plan 作成後に概算）
- [ ] 検討した代替案の比較（下記「代替案」節に下書き済み → 要確認）
- [x] §6: Gemini の install 単位 → **確定: root の `gemini-extension.json` + root `skills/`、`--ref` で版固定可、サブディレクトリ install 不可前提**（2026-06 調査）
- [x] §6: Codex / Cursor の project-dir 変数 → **確定: CC `${CLAUDE_PROJECT_DIR}`・Gemini `${workspacePath}` あり、Codex/Cursor は無し**
- [x] §6: Codex / Cursor の manifest 必須/任意フィールド → **確定**（spec §6.1）
- [x] §6: marketplace のチーム共有書式 → **確定: 自動導入は実質 CC のみ（かつ #32606 の不具合）。他は手動/ダッシュボード**
- [~] §6: Gemini 込み4種 manifest 同居 + 共有 `skills/` 読み取り → **未実証**（CC/Cursor/Codex は archcore で実証）。plan で最小 repo 実機検証、崩れたら Gemini 分離
- [x] **同梱 `docs/` の参照方式** → **確定: (a) docs-overlay MCP**（spec §4.5・§6.2.1）
- [x] §6: org overlay の project-dir 解決 → **確定: docs-overlay MCP が cwd/`git rev-parse` で吸収**（skill 側は意識しない）
