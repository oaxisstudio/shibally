# 🔗 shibally

**AIに縛られて、人生を取り戻す。**

shibally（縛り + ally）は、Claude Code用のデジタル健康管理hooksです。
設定した時間外にセッションを始めると「ほんとにやる？」と聞いてくる。
セッション終了時には、画面の外の人生を思い出させてくれる。

> AIとの対話の間に生活をやるんじゃなくて、生活を充実させるためにAIを使おう。

## なぜ作ったか

AI疲れには2種類ある。

1. AIの進化が速すぎてキャッチアップに疲れる
2. AIの仕事が速すぎて、人間が休みなく判断を迫られ続けて疲れる

shiballyが扱うのは主に2つ目。気づいたら深夜、気づいたら休日が溶けている。
それを止めてくれるのがAIだという、シュールなセルフケアツール。

## セットアップ

### 1. shiballyを配置

```bash
git clone https://github.com/oaxisstudio/shibally.git ~/.shibally
```

### 2. 設定ファイルを作成

```bash
cp ~/.shibally/config.example.yaml ~/.shibally/config.yaml
```

`config.yaml` を自分の生活に合わせて編集：

```yaml
schedule:
  workdays: ["mon", "tue", "wed", "thu", "fri"]
  work_hours:
    start: "09:00"
    end: "17:00"
  emergency_hours:
    start: "23:00"
    end: "05:00"

persona:
  type: "parent" # parent | single | couple | student
  humor_level: "high" # low | medium | high
```

### 3. Claude Codeのsettings.jsonにhooksを追加

`~/.claude/settings.json` に以下を追加：

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.shibally/hooks/session_start.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.shibally/hooks/session_stop.py"
          }
        ]
      }
    ]
  }
}
```

### 4. 動作確認

時間外にClaude Codeを起動すると、こんなメッセージが出る：

```
🔗 shibally: 今 23:15 だけど…ほんとにやる？明日の自分に任せない？
```

## Optional: CLAUDE.md連携

Claudeの振る舞い自体にも健康配慮を反映させたい場合は、[CLAUDE.md連携ガイド](docs/claude-md-integration.md)を参照してください。

## メッセージのカスタマイズ

`messages/nudge.json`（セッション開始時）と `messages/closing.json`（終了時）を編集して、自分に刺さるメッセージを追加できます。

フォーマットの詳細は [メッセージフォーマットガイド](docs/message-format.md) を参照。

## 設定リファレンス

| 設定                           | 説明                         | デフォルト  |
| ------------------------------ | ---------------------------- | ----------- |
| `schedule.workdays`            | 稼働曜日                     | mon-fri     |
| `schedule.work_hours`          | 稼働時間帯                   | 09:00-17:00 |
| `schedule.emergency_hours`     | 深夜帯（強めメッセージ）     | 23:00-05:00 |
| `persona.type`                 | 属性（メッセージ選択に使用） | universal   |
| `persona.humor_level`          | メッセージの毒舌度           | medium      |
| `display.closing_always`       | 毎セッション終了時に表示     | true        |
| `display.max_messages_per_day` | 1日の最大表示回数            | 5           |
| `display.cooldown_minutes`     | 表示間隔の最小値             | 30          |
| `feedback.enabled`             | FBを聞くか                   | true        |
| `feedback.ask_frequency`       | FB頻度                       | every_3rd   |

## ライセンス

MIT
