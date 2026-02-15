# shibally

Claude Code用のデジタル健康管理hooks。設定した時間外にセッションを始めると確認メッセージを表示し、セッション終了時には心身の健康を思い出させるメッセージを表示する。

## コンセプト

「AIとの対話の間に生活する」のではなく「生活を充実させるためにAIを活用する」。
shibally（縛り + ally）は、適度に縛ることでユーザーの生活を守る味方。

## アーキテクチャ

### 使用するHookイベント

| Hook           | タイミング       | 役割                                    |
| -------------- | ---------------- | --------------------------------------- |
| `SessionStart` | セッション開始時 | 時間外ならnudgeメッセージをstderrに表示 |
| `Stop`         | セッション終了時 | closingメッセージをstderrに表示         |

### 設計原則

- **ブロックしない**: メッセージ表示時はexit code 2（stderrをユーザーに表示）、それ以外はexit code 0。SessionStartはexit 2でもブロック不可なので安全。Stopはstop_hook_activeフラグで再実行時スキップ
- **セッション時間管理**: SessionStartでtmpfileにタイムスタンプ保存 → Stopで差分計算
- **属性別メッセージ**: config.yamlのpersona設定に基づきメッセージをフィルタ
- **日本語のみ**: 初期バージョンは日本語メッセージのみ対応

### ディレクトリ構成

```
shibally/
├── CLAUDE.md                  # このファイル
├── README.md                  # セットアップガイド
├── LICENSE                    # MIT
├── CREDITS.md                 # インスピレーション元
├── config.example.yaml        # 設定テンプレート
├── hooks/
│   ├── session_start.py       # SessionStart hook
│   └── session_stop.py        # Stop hook
├── scripts/
│   └── message_picker.py      # メッセージ選択ロジック
├── messages/
│   ├── nudge.json             # 時間外開始時メッセージ
│   └── closing.json           # セッション終了時メッセージ
├── feedback/
│   └── .gitkeep               # FBログ格納先（log.jsonlはgitignore）
└── docs/
    ├── claude-md-integration.md  # CLAUDE.md連携ガイド（オプション）
    └── message-format.md         # メッセージ追加ガイド
```

### ファイル間の依存関係

```
session_start.py → config.yaml（時間帯判定）
                 → message_picker.py（メッセージ選択）
                 → messages/nudge.json（メッセージデータ）
                 → /tmp/shibally_{session_id}.json（タイムスタンプ書き込み）

session_stop.py  → config.yaml（表示設定判定）
                 → message_picker.py（メッセージ選択）
                 → messages/closing.json（メッセージデータ）
                 → /tmp/shibally_{session_id}.json（タイムスタンプ読み取り・削除）
                 → feedback/log.jsonl（FB記録、ask_frequencyに従う）
```

## 開発ガイドライン

- Python 3.9+ 標準ライブラリのみ（外部依存なし）
- hookスクリプトはstdinからJSONを受け取り、stderrにメッセージ出力
- exit codeは常に0（ブロック禁止）
- config.yamlが存在しない場合はデフォルト値で動作する
- メッセージJSONのスキーマは docs/message-format.md を参照

## Optional: CLAUDE.md連携

ユーザーが自分のプロジェクトのCLAUDE.mdに以下を追加すると、Claudeの振る舞いにも健康配慮が反映される。これはhooksとは独立したオプション機能。

詳細は docs/claude-md-integration.md を参照。
