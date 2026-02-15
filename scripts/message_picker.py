"""メッセージ選択ロジック。

時間帯・属性・humor_level・セッション状態に基づいてメッセージをフィルタし、
ランダムに1つ選択する。テンプレート変数の展開も行う。
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# デフォルト設定（config.yamlが存在しない場合に使用）
DEFAULT_CONFIG = {
    "schedule": {
        "workdays": ["mon", "tue", "wed", "thu", "fri"],
        "work_hours": {"start": "09:00", "end": "17:00"},
        "emergency_hours": {"start": "23:00", "end": "05:00"},
    },
    "persona": {
        "type": "parent",
        "humor_level": "medium",
    },
    "display": {
        "nudge_on_weekend": True,
        "closing_always": True,
        "max_messages_per_day": 5,
        "cooldown_minutes": 30,
    },
    "feedback": {
        "enabled": True,
        "ask_frequency": "every_3rd",
    },
}

DAY_MAP = {
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}

DAY_OF_WEEK_JA = {
    0: "月曜日",
    1: "火曜日",
    2: "水曜日",
    3: "木曜日",
    4: "金曜日",
    5: "土曜日",
    6: "日曜日",
}


def load_config() -> dict[str, Any]:
    """config.yamlを読み込む。存在しなければデフォルト設定を返す。"""
    config_path = Path.home() / ".shibally" / "config.yaml"
    if not config_path.exists():
        return DEFAULT_CONFIG

    try:
        import yaml  # type: ignore[import-untyped]

        with open(config_path, encoding="utf-8") as f:
            user_config = yaml.safe_load(f)
        if not isinstance(user_config, dict):
            return DEFAULT_CONFIG
        # デフォルトとマージ（ユーザー設定で上書き）
        return _deep_merge(DEFAULT_CONFIG, user_config)
    except ImportError:
        # PyYAMLがない場合、簡易パーサーで読み込み
        return _parse_yaml_simple(config_path)
    except Exception:
        return DEFAULT_CONFIG


def _deep_merge(base: dict, override: dict) -> dict:
    """辞書を再帰的にマージする。"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _parse_yaml_simple(path: Path) -> dict[str, Any]:
    """PyYAMLなしでconfig.yamlを簡易パースする。"""
    config: dict[str, Any] = {}
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        stack: list[tuple[int, dict]] = [(-1, config)]

        for line in lines:
            stripped = line.split("#")[0].rstrip()
            if not stripped:
                continue

            indent = len(line) - len(line.lstrip())
            if ":" not in stripped:
                continue

            key, _, value = stripped.strip().partition(":")
            key = key.strip()
            value = value.strip()

            # インデントスタックを巻き戻す
            while len(stack) > 1 and indent <= stack[-1][0]:
                stack.pop()

            parent = stack[-1][1]

            if value == "":
                # ネストされた辞書
                new_dict: dict[str, Any] = {}
                parent[key] = new_dict
                stack.append((indent, new_dict))
            else:
                parent[key] = _parse_yaml_value(value)

        return _deep_merge(DEFAULT_CONFIG, config)
    except Exception:
        return DEFAULT_CONFIG


def _parse_yaml_value(value: str) -> Any:
    """YAML値を簡易的にPythonオブジェクトに変換する。"""
    # 文字列（クォート付き）
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    # 配列
    if value.startswith("[") and value.endswith("]"):
        items = value[1:-1].split(",")
        return [_parse_yaml_value(item.strip()) for item in items if item.strip()]
    # ブール値
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    # 数値
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def load_messages(message_file: str) -> list[dict[str, Any]]:
    """メッセージJSONファイルを読み込む。"""
    messages_dir = Path(__file__).parent.parent / "messages"
    path = messages_dir / message_file
    try:
        with open(path, encoding="utf-8") as f:
            messages = json.load(f)
        return messages
    except Exception:
        return []


def get_time_tags(now: Optional[datetime] = None, config: Optional[dict] = None) -> list[str]:
    """現在時刻からタグを判定する。"""
    if now is None:
        now = datetime.now()
    if config is None:
        config = load_config()

    tags: list[str] = []
    schedule = config.get("schedule", {})
    workdays = schedule.get("workdays", DEFAULT_CONFIG["schedule"]["workdays"])

    current_day = DAY_MAP.get(now.weekday(), "")
    current_time = now.strftime("%H:%M")

    # 稼働曜日外 → weekend
    if current_day not in workdays:
        tags.append("weekend")

    # 稼働時間
    work_start = schedule.get("work_hours", {}).get("start", "09:00")
    work_end = schedule.get("work_hours", {}).get("end", "17:00")

    if current_day in workdays and work_start <= current_time < work_end:
        tags.append("work_hours")
    else:
        if "weekend" not in tags:
            tags.append("after_hours")

    # 深夜帯判定
    em_start = schedule.get("emergency_hours", {}).get("start", "23:00")
    em_end = schedule.get("emergency_hours", {}).get("end", "05:00")

    if em_start > em_end:
        # 23:00-05:00のような日をまたぐケース
        if current_time >= em_start or current_time < em_end:
            tags.append("late_night")
    else:
        if em_start <= current_time < em_end:
            tags.append("late_night")

    # 朝判定
    if "05:00" <= current_time < "09:00":
        tags.append("morning")

    return tags


def is_off_hours(now: Optional[datetime] = None, config: Optional[dict] = None) -> bool:
    """現在時刻が稼働時間外かどうか判定する。"""
    tags = get_time_tags(now, config)
    return "work_hours" not in tags


def get_session_tags(duration_minutes: float) -> list[str]:
    """セッション経過時間からタグを判定する。"""
    tags: list[str] = []
    if duration_minutes < 30:
        tags.append("short_session")
    if duration_minutes >= 120:
        tags.append("long_session")
    if duration_minutes >= 240:
        tags.append("marathon_session")
    return tags


def filter_messages(
    messages: list[dict[str, Any]],
    time_tags: list[str],
    config: Optional[dict] = None,
    session_tags: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """メッセージをフィルタする。

    1. 時間帯タグで絞り込み
    2. 属性タグで絞り込み（universalは常に含む）
    3. humor_levelに応じてsavageを除外
    4. セッション状態タグで絞り込み（closing時のみ）
    5. 残った候補からランダムに1つ選択（この関数ではフィルタまで）
    """
    if config is None:
        config = load_config()

    persona_type = config.get("persona", {}).get("type", "parent")
    humor_level = config.get("persona", {}).get("humor_level", "medium")

    filtered = []
    for msg in messages:
        msg_tags = msg.get("tags", [])

        # 1. 時間帯タグでフィルタ
        time_tag_types = {"work_hours", "after_hours", "late_night", "weekend", "morning"}
        msg_time_tags = [t for t in msg_tags if t in time_tag_types]
        if msg_time_tags:
            # メッセージに時間帯タグがある場合、少なくとも1つが現在の時間帯と一致する必要がある
            if not any(t in time_tags for t in msg_time_tags):
                continue

        # 2. 属性タグでフィルタ
        persona_tag_types = {"universal", "parent", "single", "couple", "student", "engineer"}
        msg_persona_tags = [t for t in msg_tags if t in persona_tag_types]
        if msg_persona_tags:
            # universalまたはユーザーの属性タイプと一致する必要がある
            if "universal" not in msg_persona_tags and persona_type not in msg_persona_tags:
                continue

        # 3. humor_levelに応じてsavageを除外
        if humor_level in ("low", "medium") and msg.get("severity") == "savage":
            continue

        # 4. セッション状態タグでフィルタ（session_tagsが指定されている場合）
        if session_tags is not None:
            session_tag_types = {"short_session", "long_session", "marathon_session"}
            msg_session_tags = [t for t in msg_tags if t in session_tag_types]
            if msg_session_tags:
                if not any(t in session_tags for t in msg_session_tags):
                    continue

        filtered.append(msg)

    return filtered


def render_message(
    text: str,
    now: Optional[datetime] = None,
    duration_minutes: Optional[float] = None,
) -> str:
    """テンプレート変数を展開する。"""
    if now is None:
        now = datetime.now()

    text = text.replace("{{time}}", now.strftime("%H:%M"))
    text = text.replace("{{day_of_week}}", DAY_OF_WEEK_JA.get(now.weekday(), ""))

    if duration_minutes is not None:
        hours = int(duration_minutes // 60)
        minutes = int(duration_minutes % 60)
        if hours > 0:
            duration_str = f"{hours}時間{minutes}分"
        else:
            duration_str = f"{minutes}分"
        text = text.replace("{{duration}}", duration_str)

    return text


def pick_message(
    message_file: str,
    config: Optional[dict] = None,
    now: Optional[datetime] = None,
    duration_minutes: Optional[float] = None,
    session_tags: Optional[list[str]] = None,
) -> Optional[str]:
    """メッセージを選択し、テンプレート変数を展開して返す。

    候補がない場合はNoneを返す。
    """
    if config is None:
        config = load_config()
    if now is None:
        now = datetime.now()

    messages = load_messages(message_file)
    if not messages:
        return None

    time_tags = get_time_tags(now, config)
    filtered = filter_messages(messages, time_tags, config, session_tags)

    # duration_minutesがNoneのとき、{{duration}}を含むメッセージを除外
    if duration_minutes is None:
        filtered = [m for m in filtered if "{{duration}}" not in m.get("text", "")]

    if not filtered:
        # フィルタ結果が空の場合、universalメッセージからフォールバック
        filtered = [
            m
            for m in messages
            if "universal" in m.get("tags", [])
            and not (
                config.get("persona", {}).get("humor_level", "medium") in ("low", "medium")
                and m.get("severity") == "savage"
            )
        ]
        if duration_minutes is None:
            filtered = [m for m in filtered if "{{duration}}" not in m.get("text", "")]

    if not filtered:
        return None

    chosen = random.choice(filtered)
    return render_message(chosen["text"], now, duration_minutes)
