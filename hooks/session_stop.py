#!/usr/bin/env python3
"""Stop hook: Claudeの応答完了ごとにclosingメッセージを表示する。

Stop hookはセッション中にClaude が応答を返すたびに発火する（セッション終了時だけではない）。

- stdinからClaude CodeのHook JSONを受け取る
- /tmp/shibally_{session_id}.json からセッション開始時刻を読み取り、経過時間を計算
- stderrにclosingメッセージを出力、exit 2で表示
- stop_hook_activeフラグで再実行時はスキップ（exit 2による再発火防止）
- フィードバック収集（設定に応じて）
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from message_picker import (  # noqa: E402
    get_session_tags,
    load_config,
    pick_message,
)


def _format_duration(minutes: float) -> str:
    """経過時間を人間が読める形式にする。"""
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if hours > 0:
        return f"{hours}時間{mins}分"
    return f"{mins}分"


def _load_session_data(session_id: str) -> dict | None:
    """tmpfileからセッションデータを読み込み、ファイルを削除する。"""
    tmp_path = Path(tempfile.gettempdir()) / f"shibally_{session_id}.json"
    if not tmp_path.exists():
        return None
    try:
        with open(tmp_path, encoding="utf-8") as f:
            data = json.load(f)
        tmp_path.unlink(missing_ok=True)
        return data
    except Exception:
        tmp_path.unlink(missing_ok=True)
        return None


def _record_feedback(message: str, feedback: str, config: dict) -> None:
    """フィードバックをlog.jsonlに記録する。"""
    feedback_dir = Path(__file__).parent.parent / "feedback"
    log_path = feedback_dir / "log.jsonl"
    try:
        feedback_dir.mkdir(exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "feedback": feedback,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main() -> None:
    now = datetime.now()
    config = load_config()

    # stdinからHook入力を読み取る
    session_id = "unknown"
    hook_input = {}
    try:
        hook_input = json.load(sys.stdin)
        session_id = hook_input.get("session_id", session_id)
    except Exception:
        pass

    # stop_hook_activeなら再実行 → スキップして終了させる
    if hook_input.get("stop_hook_active"):
        sys.exit(0)

    # closing表示設定を確認
    display = config.get("display", {})
    if not display.get("closing_always", True):
        sys.exit(0)

    # セッション経過時間を計算
    duration_minutes = None
    session_data = _load_session_data(session_id)
    if session_data and "start_time" in session_data:
        try:
            start_time = datetime.fromisoformat(session_data["start_time"])
            delta = now - start_time
            duration_minutes = delta.total_seconds() / 60
        except Exception:
            pass

    # セッション状態タグ
    session_tags = get_session_tags(duration_minutes) if duration_minutes is not None else None

    # メッセージを選択・表示
    message = pick_message(
        "closing.json",
        config=config,
        now=now,
        duration_minutes=duration_minutes,
        session_tags=session_tags,
    )
    if message:
        print(f"\n✨ shibally: {message}\n", file=sys.stderr)
        sys.exit(2)  # exit 2 → stderrをユーザーに表示

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # どんなエラーが起きてもブロックしない
        sys.exit(0)
