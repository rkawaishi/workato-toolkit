# Workato サービス連携スキルの完備 — 設計書

Status: Draft (自律セッションで作成 — ユーザレビュー待ち)
Date: 2026-07-06
Scope: workato-toolkit プラグイン本体（このリポジトリ）

## 1. 背景と目的

workato-toolkit は 21 スキルを同梱するが、「Workato サービスと直接やり取りする」スキル群には
プラグイン化（p5）の際に生じた欠落と、ライフサイクル上の空白が残っている。

**発見した事実（探索結果）:**

1. `scripts/workato-api.py`（API ヘルパー）は skills / rules / docs から **39 箇所**参照されるが、
   プラグインは同梱しておらず、配布経路が存在しない。実体は旧 `workato-dev-kit` リポジトリ
   （2,871 行、jobs / connectors / recipes / **deploy** / sdk / oauth / profile コマンド実装済み）にのみある。
2. 同様に `scripts/ensure-workatoignore.sh`（/pull-project が必須実行）と
   `templates/workatoignore.template`（rules が言及）も未同梱。
3. 環境昇格（dev→test→prod の Deploy）は docs/rules に手順・禁止則があるだけで、スキルが無い。
   dev-kit ヘルパーには `deploy preview/run/status/list`（環境遷移ガード付き）が実装済み。
4. 新規ワークスペース（リポジトリ）セットアップは quickstart の手作業のみ。API クライアント/キーの
   払出しは手段自体が無い（Platform CLI の `api-clients` は **API Platform=外部公開 API 用**であり、
   CLI 自身が使う **Developer API クライアント**の管理は CLI 非対応）。
5. Developer API クライアントの発行仕様は org の prior art（dev-kit `cli-key-broker` プロジェクト +
   `workato_developer_api` カスタムコネクタ）で実機検証済み:
   `POST /api/developer_api_clients` に `name` / `api_privilege_group_id`（UI の Role 相当）/
   `environment`（`DEV`|`TEST`|`PROD`）/ `all_folders` or `folder_ids[]` / `ip_allow_list[]`。
   トークンは**作成時レスポンス（`token.value`）でのみ**取得可能。

本設計は (a) プラグイン利用時のユーザストーリーを整理し、(b) サービス連携スキルを過不足なく定義し、
(c) 環境別権限を持つ API クライアント/キー払出しの設計と実装方針を定める。

## 2. ユーザストーリー整理

前提となる環境運用（ユーザ要件）: **Dev / Staging / Prod** の 3 環境。Dev へは本プラグイン経由で
push する。Staging / Prod へは直接書き込まず **Workato の Deploy 機能**で昇格する。
（Workato の環境 enum は `DEV`/`TEST`/`PROD`。本書では Staging=`TEST` にマップし、org 側の表示名は
設定として記録する。）

### フェーズ 0 — 導入・セットアップ

| # | ストーリー | 現状 |
|---|---|---|
| S0-1 | 管理者として、ワークスペースリポジトリを初期化したい（org/ 構成、.workatoignore、秘匿ファイル deny-list、ヘルパースクリプト）— AI エージェントが即座に作業できる状態にする | ❌ quickstart 手作業のみ。ヘルパー/テンプレートは配布経路なし |
| S0-2 | 管理者として、**環境ごとに権限の異なる API クライアント/キーを払い出したい**（dev=書込可、staging/prod=読取専用）— エージェントが staging/prod に物理的に書き込めないようにする | ❌ 手段なし（ユーザ明示要望） |
| S0-3 | 開発者として、`<org>-dev/test/prod` の CLI プロファイルを登録・検証したい | △ 手順書のみ |
| S0-4 | 管理者として、既存資産からナレッジベースを初期化したい | ✅ `/onboard` |

### フェーズ 1 — 仕様策定〜ビルド（サービス連携ではない）

`/spec` `/clarify` `/plan` `/tasks` `/analyze` `/implement` `/create-recipe` `/create-workflow-app`
`/create-genie` `/create-connector` — ✅ 充足。

### フェーズ 2 — サービス同期（dev 環境）

| # | ストーリー | 現状 |
|---|---|---|
| S2-1 | プロジェクトを pull したい | ✅ `/pull-project`（ただし ensure-workatoignore.sh 欠落で手順が壊れている） |
| S2-2 | 検証付きで push し、レシピ起動・ジョブ確認までしたい | ✅ `/push-project`（ヘルパー欠落で --test 系が壊れている） |
| S2-3 | カスタムコネクタを push/pull したい | ✅ 手順あり（`sdk push/pull` — ヘルパー欠落で壊れている） |
| S2-4 | コネクタメタデータを同期したい | ✅ `/sync-connectors` |
| S2-5 | UI 操作でフィールド情報を収集したい | ✅ `/auto-learn`（CC 専用） |
| S2-6 | レシピ JSON を検証したい | ✅ `/validate-recipe` + PreToolUse hook |

### フェーズ 3 — 環境昇格・リリース

| # | ストーリー | 現状 |
|---|---|---|
| S3-1 | dev→staging を Deploy 機能で昇格し、事前にプレビュー（対象一覧）を見たい | ❌ docs のみ（dev-kit ヘルパーに実装あり） |
| S3-2 | staging→prod は人間の承認を必須にし、エージェントに自動化させたくない | ルールのみ（rules/workato-deployment-flow.md）。スキルとしてのガード未実装 |
| S3-3 | デプロイの状態・履歴を監査したい | ❌（ヘルパー `deploy status/list` 相当） |
| S3-4 | 昇格時の環境差分チェックリスト（connection 再認証、environment properties、Data Table レコード、カスタムコネクタ release）を確実に消化したい | △ docs/platform/environments.md に記載のみ |
| S3-5 | prod の状態を読取専用で確認・diff したい（障害調査） | △ pull --profile の記述のみ |

### フェーズ 4 — 運用

| # | ストーリー | 現状 |
|---|---|---|
| S4-1 | 失敗ジョブを確認し原因を診断したい | ✅ `/push-project --test` + ヘルパー `jobs list/get/tail`（ヘルパー復旧が前提） |
| S4-2 | エージェント用キーをローテーション/失効したい（定期・漏えい時） | ❌ 手段なし |
| S4-3 | 発行済みクライアントとスコープを棚卸し（監査）したい | ❌ 手段なし |

### フェーズ 5 — 学習

`/learn-recipe` `/learn-pattern` `/catalog` — ✅ 充足。

## 3. ギャップ分析 → 必要スキル一覧

### 追加するスキル（3 つ）

| スキル | 担うストーリー | 概要 |
|---|---|---|
| **`/setup-workspace`** | S0-1, S0-3 | ワークスペースリポジトリの一括ブートストラップ。CLI 導入確認 → ヘルパー/テンプレートの実体化（materialize）→ ディレクトリ骨格 → 秘匿 deny-list → プロファイル登録誘導 → 疎通検証。`--update` で同梱スクリプトの鮮度チェック/更新のみ実行。終了時に `/issue-api-keys` と `/onboard` へ誘導 |
| **`/issue-api-keys`** | S0-2, S4-2, S4-3 | Developer API クライアント/キーの設計・払出し・ローテーション・失効・監査。環境別権限マトリクス（§5）を org と合意 → ブートストラップ管理キーで 3 環境分のクライアントを発行 → トークンを keyring に直接登録（stdout に出さない）→ 設計記録を `org/docs/platform/api-clients.md` に書く |
| **`/deploy-project`** | S3-1〜S3-5 | Deploy 機能（Recipe Lifecycle Management API）による昇格。`preview`（読取専用）→ `run --to test`（dev プロファイル時のみ）→ `status`/`list`。**prod への run はスキル内で二重ガード**（test プロファイル必須 + ユーザの明示確認。自動承認は永久禁止）。昇格チェックリスト（S3-4）を毎回提示 |

### スキル以外の追加（インフラ）

| 項目 | 内容 |
|---|---|
| **ヘルパー同梱** | dev-kit の `scripts/workato-api.py` をプラグイン `scripts/workato-api.py` として取り込み（canonical）。`__version__` と `--version` を追加。ヘルパーのテスト群（dev-kit `scripts/tests/` ~4.7k 行）も `tests/` 配下に移植 |
| **ヘルパー拡張** | `api-clients` コマンド群を新設: `list` / `roles`（privilege group 一覧; エンドポイントは実行時プローブ）/ `create`（`--register-profile` でトークンを直接 keyring 保存）/ `delete` / `rotate`。既存規約（--dry-run 必須、環境ガード、help/description 規約）に従う |
| **templates/ 同梱** | `templates/workatoignore.template`（dev-kit から）+ `scripts/ensure-workatoignore.sh` を同梱 |
| **配布メカニズム** | docs-overlay MCP に **`workato_asset_path(name)`** ツールを追加。許可リスト内のファイル（workato-api.py / ensure-workatoignore.sh / workatoignore.template）の**絶対パス**を返す（内容は返さない。パストラバーサル不可）。スキルはこのパスから `cp` でワークスペースへ実体化する。全エディタ共通（MCP はプラグインルートを自己解決済み）。MCP 不通時のフォールバックは GitHub raw の release タグ |

既存参照（`python3 scripts/workato-api.py` = ワークスペース相対）は**全て有効なまま**になる。
ワークスペースコピーは git 管理され、バージョンがリポジトリに固定される（再現性）。

### 追加しないと判断したもの（過剰の抑制）

| 候補 | 判断 | 理由 |
|---|---|---|
| `/diagnose-jobs` | 見送り | `/push-project --test` の修正ループ + ヘルパー `jobs list/get/tail` で充足。独立ワークフローとしての厚みがない |
| `/manage-connections` | 見送り | CLI（connections create/list/get-oauth-url 等）+ `/create-recipe` `/push-project` 内の手順で充足 |
| `/env-diff` | 見送り | `/deploy-project preview` + 読取専用 pull の手順書きで充足 |
| `/properties` | 見送り | CLI で充足。`/deploy-project` のチェックリストから参照 |
| per-developer キー払出し | 見送り | ワークスペースレベルのキーは `/issue-api-keys`。開発者個人単位は org の `cli-key-broker` レシピパターン（Slack ブローカー）の領分。kit doc から関連事例として参照するに留める |

## 4. アプローチ比較

| | A. スキル 3 追加 + ヘルパー同梱（**採用**） | B. 最小: セットアップ 1 スキル + curl 手順 | C. MCP ツール化（key 発行/deploy を MCP サーバ実装） |
|---|---|---|---|
| 39 箇所の既存参照 | 全て復旧 | 壊れたまま | 参照書き換え大量発生 |
| トークン安全性 | keyring 直接保存、stdout 非表示 | curl 出力がトランスクリプトに漏れる | MCP env への固定が必要で運用が硬い |
| エディタ互換 | CLI/ヘルパー中心 = 全エディタ | 同左 | Cursor/Codex の MCP 挙動差リスク |
| 実装コスト | 中（ただし実証済みコードの移植が主） | 小 | 大 |
| 規約適合 | 既存の「ヘルパー + thin skill」路線 | — | 新規路線を持ち込む |

**採用: A。** ヘルパーは実機検証済みコードの移植であり、リスクの大半は「配布メカニズム」に限定される。
それは docs-overlay MCP の 1 ツール追加（数十行）で解決する。

## 5. API クライアント/キーの環境別権限設計（/issue-api-keys の中核）

### 5.1 対象系統

**Developer API クライアント**（`/api/developer_api_clients/*`）。API Platform（v1/v2）や OEM とは別系統
（`docs/platform/workato-api-systems.md` の判断フロー参照。API Platform v1 は 2026-07-01 に完全廃止済み）。

### 5.2 権限マトリクス（既定テンプレート）

権限の実体は Workato UI の「API client role（= `api_privilege_group_id`）」。ロールの API 作成は
非公開のため、**スキルはロール定義チェックリストを提示して UI 作成を誘導**し、作成後にクライアント
発行を API で自動化する（autonomy ルールの「CLI/API でできないことだけユーザに頼む」に適合）。

| 権限カテゴリ | `<org>-agent-dev` (DEV) | `<org>-agent-test` (TEST/Staging) | `<org>-agent-prod` (PROD) |
|---|---|---|---|
| Projects / folders 読取（pull, export） | ✅ | ✅ | ✅ |
| Projects 書込（push / import） | ✅ | ❌ | ❌ |
| Recipes 起動/停止 | ✅ | ❌ | ❌ |
| Connections 作成/更新 | ✅ | ❌ | ❌ |
| Data Tables 作成/変更 | ✅ | ❌ | ❌ |
| Environment properties upsert | ✅ | ❌ | ❌ |
| カスタムコネクタ SDK push / release | ✅ | ❌ | ❌ |
| Jobs 読取（監視・診断） | ✅ | ✅ | ✅ |
| Deployments 読取（status / list） | ✅ | ✅ | ✅ |
| Deployments 作成（次環境への昇格） | ポリシー選択（下記） | ポリシー選択 | ❌ 恒久 |
| API クライアント管理 | ❌ | ❌ | ❌（ブートストラップ管理キーのみ） |

- フォルダスコープ: 既定 `all_folders: true`（エージェントは新規プロジェクトを作る）。org 判断で
  `folder_ids[]` に絞り込み可能。
- IP allow-list: 任意項目としてヒアリング。
- **昇格ポリシー**（org が選び、記録される）:
  - **Policy A（既定・推奨）**: dev キーに Deployments 作成権限を付与。エージェントは
    `/deploy-project run --to test` で dev→staging を Deploy 機能経由で実行できる（直接書込ではなく
    監査可能なマニフェストが残る）。staging→prod は UI で人間が実行・承認。
  - **Policy B（保守的）**: エージェントキーに Deployments 作成権限なし。全昇格を UI で人間が実施。
  - どちらでも **prod への自動承認・承認の代行は禁止**（rules/workato-deployment-flow.md を継承）。

### 5.3 払出しフロー

1. **plan** — 環境モデル検出（統合環境 vs 別ワークスペース: 実行時プローブ）、org 名・表示名マッピング
   （Staging=TEST 等）、ポリシー A/B、スコープ、IP 制限をヒアリングし、発行計画を提示。
2. **ロール準備（UI）** — `Agent Dev`（書込系）と `Agent ReadOnly`（読取系）の 2 ロールの権限チェック
   リストを提示し、UI での作成を依頼。作成後、ロール ID を取得（`api-clients roles` プローブ →
   取得不能なら UI の URL/画面から確認してもらう）。
3. **ブートストラップ** — クライアント発行にはワークスペース管理者権限のキーが 1 つ必要
   （鶏卵問題）。既存の管理者プロファイルがあればそれを使用。無ければ UI での初回発行を誘導。
   完了後の失効（revoke）も選択肢として提示。
4. **発行** — `api-clients create --name <org>-agent-<env> --environment <ENV> --role-id <id>
   --register-profile <org>-<env>` を 3 環境分実行。トークンは keyring に直接保存し、**stdout /
   トランスクリプトに出さない**（keyring 不可時のみ chmod 600 の一時ファイルへ書き、credential-guard
   hook の対象パターンに合致する場所に置く）。
5. **検証** — 各プロファイルで読取疎通（workspace 情報取得）。dev のみ書込疎通。**test/prod プロファイル
   で push が拒否されること**（deployment-flow ガード）をスモークとして明示確認。
6. **記録** — `org/docs/platform/developer-api-clients.md` に設計記録（マトリクス、クライアント名/ID、
   ロール名/ID、ポリシー、ローテーション周期、発行日）を書く。トークンは書かない。

### 5.4 ローテーション / 失効 / 監査

- `rotate`: `regenerate` エンドポイント（実行時プローブ）→ 不可なら delete + create で同名再発行。
  keyring を更新し、記録の発行日を更新。
- `revoke`: クライアント削除 + 記録を revoked に更新。
- `audit`: `api-clients list` と記録を突合し、乖離（野良クライアント、記録漏れ）を報告。

## 6. コンポーネント設計（スキル別）

### 6.1 /setup-workspace

- frontmatter: `allowed-tools: Bash, Read, Write, Edit, Glob, Grep` + `disable-model-invocation: true`
- 手順: (0) git リポジトリ確認 → (1) CLI 存在/バージョン確認（`workato --version`、無ければ pipx 誘導）
  → (2) `workato_asset_path` 経由で `scripts/workato-api.py` / `scripts/ensure-workatoignore.sh` /
  `templates/workatoignore.template` を実体化（既存ならハッシュ比較で更新提案）→ (3) `org/docs/` ほか
  ディレクトリ骨格 → (4) README 記載の秘匿 deny-list（.claude/settings.json / .cursorignore /
  .codexignore）を無ければ配置 → (5) プロファイル未設定なら `workato init` を誘導 → (6) 疎通検証
  （profile show / projects list）→ (7) 次ステップ提示（`/issue-api-keys`, `/pull-project --all`, `/onboard`）
- 冪等。`--update` はステップ (2) のみ。

### 6.2 /issue-api-keys

- §5 のフロー。サブコマンド: `plan`（既定）/ `issue` / `rotate` / `revoke` / `audit`。
- 読むもの: `workato_docs_lookup("platform/workato-api-systems.md")`、同 `platform/developer-api-clients.md`（新設 kit doc）、
  `org/docs/platform/developer-api-clients.md`（org 記録）。
- 書くもの: `org/docs/platform/developer-api-clients.md` のみ（トークンは書かない）。
- ガード: 対象は Developer API のみ。API Platform クライアントを求められたら CLI `workato api-clients`
  （別系統）へ案内して混同を防ぐ。

### 6.3 /deploy-project

- サブコマンド: `preview`（既定）/ `run --to <test|prod>` / `status <id>` / `list`。
- ガード（ヘルパー実装 + スキル記述の二重）: 遷移は (dev→test) / (test→prod) のみ。skip-tier・逆行・
  同一環境は API 呼び出し前に拒否。`--to prod` は `--yes` + ユーザの明示確認 + 承認は UI の人間のみ。
- 毎回、環境差分チェックリスト（connection 再認証 / environment properties / Lookup·Data Table シード /
  カスタムコネクタ release / レシピ起動状態）を提示し、`status --wait` で終端状態まで追跡。
- 読むもの: `workato_docs_lookup("platform/environments.md")`、`patterns/deployment-guide.md`。

### 6.4 docs / rules / tests への波及

| 対象 | 変更 |
|---|---|
| `docs/platform/developer-api-clients.md` | 新設（Developer API クライアント設計ガイド: マトリクステンプレ、ブートストラップ、ローテーション、key-broker パターンへの参照）。名称は Platform CLI の `api-clients`（API Platform 系統）との混同を避ける |
| `docs/platform/environments.md` | Deploy 節から `/deploy-project` を参照 |
| `docs/guides/skills-reference.md` / `lifecycle.md` / `architecture.md` | 3 スキル追記（Setup / Promotion フェーズ新設） |
| `rules/workato-cli.md` | ヘルパーのコマンド表に `deploy` / `api-clients` / `--version` を追記。templates/scripts の実体化に触れる |
| `rules/workato-deployment-flow.md` | 昇格の正規手段として `/deploy-project` を参照（禁止則は不変） |
| `scripts/sync_derived.py` 再生成 | CLAUDE.md / AGENTS.md / GEMINI.md / *.mdc の再生成 |
| `tests/test_skills_migration.py` | `EXPECTED_SKILLS` に 3 スキル追加（ガード群は自動適用） |
| `tests/`（新規） | ヘルパー移植テスト（dev-kit から）+ `api-clients` の引数面/トークン非表示ユニット + `workato_asset_path` の allowlist/存在テスト + templates 同梱テスト |

## 7. 決定事項と前提（自律実行のため質問の代わりに明文化）

1. **Staging=TEST マッピング**: Workato enum は DEV/TEST/PROD。org 表示名は記録で吸収。
2. **統合環境モデルを主経路**にする（prior art の実機検証が根拠）。別ワークスペース型は分岐手順として
   ドキュメント化（環境ごとにブートストラップキーが必要になる）。
3. **プロファイル名は既存規約 `<org>-<env>` を維持**し、エージェント発行トークンをそこへ登録する
  （deployment-flow の `-dev` サフィックス判定と互換）。クライアント名は `<org>-agent-<env>`。
4. **昇格ポリシー既定は A**（dev→staging はエージェント実行可、Deploy 機能経由）。ユーザ文言
   「staging, prod は…デプロイ機能を使って反映」に整合。prod 実行・承認は常に人間。
5. **ヘルパーはワークスペースへ実体化する方式**（プラグイン内から直接実行しない）。既存 39 参照の
   互換維持と、ワークスペース git によるバージョン固定を優先。
6. スキル名は既存の動詞-名詞規約に合わせ `/setup-workspace` `/issue-api-keys` `/deploy-project`。
7. 設計書はリポジトリ直下 `specs/` に置く（`docs/` 配下は docs-overlay MCP が配信対象とするため、
   内部開発文書を混ぜない）。

## 8. Open Questions（実装中に実機/ソースで検証する）

- [ ] privilege group（ロール）一覧のエンドポイント有無（`GET /api/developer_api_client_roles` 相当）。
      無ければ UI からの ID 取得手順に固定。
- [ ] `regenerate`（トークン再発行）エンドポイント有無。無ければ delete+create でローテーション。
- [ ] 統合環境モデルの検出方法（`environment` 属性の受理可否によるプローブで足りるか）。
- [ ] Platform CLI のプロファイル保存形式（keyring service 名 / `~/.workato/profiles` スキーマ）—
      `~/workspace/workato-platform-cli` のソースで確認し、`--register-profile` を CLI 互換で実装。
- [ ] dev-kit ヘルパーテストの import 方式（tests をそのまま移植できるか、パス調整が要るか）。

## 9. テスト戦略

- リポジトリ既存流儀に従い、構造ガードは pytest（RED → 実装）。
- ヘルパー: dev-kit の既存テスト移植 + 新規 `api-clients` のユニット（HTTP モック、トークンが stdout に
  出ないことの検証を含む）。
- MCP: `workato_asset_path` の allowlist・存在・トラバーサル拒否。
- スキル: `EXPECTED_SKILLS` 更新で既存ガード（frontmatter、bare docs パス禁止、MCP 言及必須）が
  自動的に新スキルへ適用される。`/issue-api-keys` と `/deploy-project` には「トークンを echo しない」
  「承認を自動化しない」文言のガードテストを追加。
- 最後に `python3 scripts/sync_derived.py` → 全 pytest → CI 相当のドリフトチェック。
