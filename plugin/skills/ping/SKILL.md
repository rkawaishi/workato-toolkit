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
