#!/usr/bin/env python3
"""SessionStart hook: 時間外にセッションを開始した場合、nudgeメッセージを表示する。

- stdinからClaude CodeのHook JSONを受け取る
- 時間外であればstderrにnudgeメッセージを出力
- /tmp/shibally_{session_id}.json にタイムスタンプを保存
- exit codeは常に0（セッションをブロックしない）
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from message_picker import is_off_hours, load_config, pick_message  # noqa: E402


def main() -> None:
    now = datetime.now()
    config = load_config()

    # stdinからHook入力を読み取る
    session_id = "unknown"
    try:
        hook_input = json.load(sys.stdin)
        session_id = hook_input.get("session_id", session_id)
    except Exception:
        pass

    # タイムスタンプをtmpfileに保存
    tmp_path = Path(tempfile.gettempdir()) / f"shibally_{session_id}.json"
    try:
        session_data = {
            "session_id": session_id,
            "start_time": now.isoformat(),
        }
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f)
    except Exception:
        pass

    # 時間外判定
    if not is_off_hours(now, config):
        # 稼働時間内 → メッセージなし
        sys.exit(0)

    # 休日のnudge表示設定を確認
    display = config.get("display", {})
    if not display.get("nudge_on_weekend", True):
        from message_picker import get_time_tags

        tags = get_time_tags(now, config)
        if "weekend" in tags and "late_night" not in tags:
            sys.exit(0)

    # メッセージを選択・表示
    message = pick_message("nudge.json", config=config, now=now)
    if message:
        print(f"\n🌙 shibally: {message}\n", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # どんなエラーが起きてもブロックしない
        sys.exit(0)
