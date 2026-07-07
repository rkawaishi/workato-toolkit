---
status: draft
---

# 運用ライフサイクルの完備 — dev→本番→運用の通しユーザストーリー 設計書

- 日付: 2026-07-07
- 状態: **draft — ユーザレビュー待ち**(前 spec『workato-integration-skills』が
  レビュー未済のまま実装された反省から、本 spec は承認までステータスを上げない)
- 背景: ユーザ指摘「レシピのスタート、ジョブログ取得などが不足。開発して本番に
  乗せるまでのユーザストーリーを描いたか」。点検の結果、既存ストーリー(前 spec §2)は
  **「作る」側が厚く「動かす・運用する」側が薄い**と確認した。

## 1. 通しユーザストーリー(dev → 本番 → 運用)

前 spec のフェーズ0〜5 を拡張し、欠けていた運用側を S5〜S8 として追加する。
記法: ✅=充足 / △=手段はあるがワークフロー未整備 / ❌=手段なし

### フェーズ2.5 — テスト実行(dev)【新設】

| # | ストーリー | 現状 |
|---|---|---|
| S5-1 | push したレシピに**テストデータを流して** end-to-end を確認したい(webhook へ POST、Workflow App フォーム送信、ポーリングトリガーの待機) | ❌ `--test` は「失敗ジョブの有無を見る」だけで、能動的にジョブを発生させる手段が未整理 |
| S5-2 | テスト結果(ジョブの入出力)を見て期待値と突き合わせたい | △ `jobs get` はあるが照合ワークフローなし |

### フェーズ4.5 — 稼働操作(dev)【新設】

| # | ストーリー | 現状 |
|---|---|---|
| S6-1 | push とは独立に、レシピを**起動/停止/再起動**したい(単独・プロジェクト一括) | △ `/push-project --start` のフラグとヘルパー `recipes start/stop <id>` に埋没。一級のスキルなし |
| S6-2 | プロジェクトのレシピ稼働状態を一覧したい | △ `recipes list` の出力を読むだけ |

### フェーズ5 — 障害対応・診断(dev)【S4 を再定義】

| # | ストーリー | 現状 |
|---|---|---|
| S7-1 | 失敗ジョブを**検知→原因分類→修正提案**まで一気にやってほしい | △ `jobs list/get/tail` は CLI 止まり。診断ワークフローなし(前 spec は /diagnose-jobs を「充足」として見送り — 本 spec で判断を覆す) |
| S7-2 | 提案を承認したら**修正→再 push→再起動→再検証**のサイクルを回してほしい | △ push-project §7 に手順記述のみ |

### フェーズ6 — 昇格後の検証・本番調査(test/prod、読取専用)【新設】

| # | ストーリー | 現状 |
|---|---|---|
| S8-1 | deploy 後、**test/prod でジョブが正常に流れているか**確認したい(deploy status ではなく業務の稼働確認) | ❌ |
| S8-2 | 本番障害時に、**読取専用**で prod のジョブログ・レシピ定義を調査し、dev と diff したい | △ `pull --profile` の記述のみ(前 spec S3-5 のまま未実装) |
| S8-3 | 悪い昇格を**戻したい**(ロールバック) | ❌ ストーリー自体が存在しなかった |

## 2. ギャップ → 追加・変更するもの

### 新スキル(3)

| スキル | 担うストーリー | 概要 |
|---|---|---|
| **`/run-recipes`** | S6-1, S6-2 | `status`(既定・稼働一覧)/ `start` / `stop` / `restart`、`--id <id>` / `--all` / `--project <name>`。実行はヘルパー `recipes start/stop`(dev ガード内蔵)経由。test/prod プロファイル下では hook(#10)が拒否する — スキルは理由を説明し `/deploy-project` へ誘導 |
| **`/diagnose-jobs`** | S7-1, S7-2, S5-2 | `jobs list --status failed` → `jobs get` でエラー本文 → 原因分類(datapill 参照 / connection 未認証 / フィールド不一致 / 外部 API)→ **既定で修正→再 push→`/run-recipes restart`→再検証まで実行し、green になるまでループ**(dev 限定)。`--no-fix` で診断・提案のみに抑制。connection 未認証・外部 API 起因などエージェントが直せないものは分類してユーザーへ。`tail` モードで追従監視 |
| **`/inspect-env`** | S8-1, S8-2 | `<test\|prod>` を対象に**読取専用**で: ジョブ健全性サマリ(直近 N 件の成否)、レシピ稼働状態、`pull --profile` を scratch ディレクトリへ→ dev との diff。**書込系コマンドを一切呼ばない**ことをスキル冒頭で宣言し、読取専用キー(/issue-api-keys の test/prod キー)の使用を前提とする |

### 既存の変更(2)

| 対象 | 変更 |
|---|---|
| `/push-project` | `--test` を S5-1 対応に強化: アセット型別のテストデータ投入手順(webhook トリガー→URL へ curl POST、Workflow App→フォーム送信を依頼、ポーリング→次回ポーリングを待つ/`recipes poll-now` の有無は実機確認)を明記し、投入→`/diagnose-jobs` へ接続。起動系の記述は `/run-recipes` への参照に置換(重複を持たない) |
| `/deploy-project` | `rollback` の**手順**を追加: Workato Deploy API に逆方向ロールバックが存在するかは実機確認(Open Question)。無い場合の正規手順=「git 上の直前リリース状態を dev に復元 → 再昇格」を checklist 化。prod ガードは既存のまま |

### スキル化を見送るもの(理由つき)

- 常駐監視・定期ヘルスチェック — プラグインはオンデマンド実行が前提。恒常監視は Workato 側のアラート/外部監視の領分(`/inspect-env` を手動・定期に叩く運用は可)
- connection 管理 / properties — 前 spec の判断を維持(CLI で充足)

## 3. 決定事項と前提(レビューで覆す前提で明文化)

1. **自動修正の範囲(ユーザ確認済み 2026-07-07)**: `/diagnose-jobs` は**既定で自動修正と再 push まで実行**する(dev 限定)。修正できない分類(connection 認証、外部 API 側、権限)はユーザーへ引き渡す。診断のみに抑えたいときは `--no-fix`。test/prod への修正は常に deploy 経由(hook の dev ガード #10 が物理的に下支え)
2. **読取専用の担保は2層**: スキル記述(書込コマンド不使用)+ 権限(test/prod キーは読取専用 — /issue-api-keys のマトリクス)。hook の dev ガード(#10)が第3層として書込系を物理ブロック
3. スキル名は動詞-名詞規約: `/run-recipes` `/diagnose-jobs` `/inspect-env`(#16 の接頭辞判断が出たら追従)
4. S5-1 のテストデータ投入は**独立スキルにしない**(push 直後の文脈に強く従属するため `/push-project --test` の一部)

## 4. Open Questions(実機で確認 — issue #32 Phase A と同じセッションで)

- [ ] Deploy API にロールバック(過去 deployment の再適用)があるか
- [ ] ポーリングトリガーを即時発火させる手段(`poll now` 相当)の有無
- [ ] webhook トリガーの URL 取得方法(recipe 定義から機械的に得られるか)
- [ ] `jobs list` の test/prod プロファイルでの読取可否(読取専用キーで通るか)

## 5. テスト戦略

- 既存流儀: スキル構造ガード(EXPECTED_SKILLS、frontmatter、MCP 言及、bare パス禁止)は自動適用
- `/run-recipes`: 「ヘルパー経由で実行する」「raw CLI の start/stop を書かない」ガード
- `/diagnose-jobs`: 「修正サイクルは dev 限定」「test/prod には触れない」文言ガード + `--no-fix` の存在
- `/inspect-env`: 「書込系コマンド(push/start/stop/deploy run)を含まない」全走査ガード
- ヘルパー拡張が要る場合(poll-now 等)は tests/helper/ にユニット追加

## 6. 実装順

1. 本 spec のユーザレビュー(**status: draft → active はレビュー後**)
2. `/run-recipes`(最小・独立)→ 3. `/diagnose-jobs` → 4. `/inspect-env` → 5. push-project/deploy-project の改修(Open Questions の実機回答後)
