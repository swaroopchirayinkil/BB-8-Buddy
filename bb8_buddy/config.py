"""
Configuration management for BB-8 Buddy.
Adheres to XDG Base Directory specification.
"""

from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def get_xdg_data_dir() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        path = Path(data_home) / "bb8-buddy"
    else:
        path = Path.home() / ".local" / "share" / "bb8-buddy"
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = Path("/tmp/bb8-buddy-data")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_xdg_config_dir() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        path = Path(config_home) / "bb8-buddy"
    else:
        path = Path.home() / ".config" / "bb8-buddy"
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback = Path("/tmp/bb8-buddy-config")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_audio_dir() -> Path:
    audio_dir = get_xdg_data_dir() / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir


DEFAULT_CONFIG: Dict[str, Any] = {
    "interval_minutes": 30,
    "idle_threshold_minutes": 10,
    "smart_pause_enabled": True,
    "presence_mode": "tray",  # "tray" or "floating"
    "sound_enabled": True,
    "notifications_enabled": True,
    "character_size": "small",  # "compact", "small", "medium", "large"
    "muted_until": None,  # ISO8601 string or None
    "theme": "dark",  # "dark", "light", or "system"
    "window_pos_x": -1,
    "window_pos_y": -1,
    "custom_tags": ["#work", "#break", "#learning", "#meeting", "#personal"],
}


class Config:
    def __init__(self, config_path: Optional[Path] = None):
        if config_path:
            self.config_file = Path(config_path)
            self.config_dir = self.config_file.parent
        else:
            self.config_dir = get_xdg_config_dir()
            self.config_file = self.config_dir / "config.json"
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
            except Exception as e:
                print(f"[BB-8 Config] Warning loading config: {e}", file=sys.stderr)
        else:
            self.save()

    def save(self) -> None:
        try:
            temp_file = self.config_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            temp_file.replace(self.config_file)
        except Exception as e:
            print(f"[BB-8 Config] Error saving config: {e}", file=sys.stderr)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()

    def update(self, updates: Dict[str, Any]) -> None:
        self.data.update(updates)
        self.save()

    @property
    def interval_minutes(self) -> int:
        val = self.data.get("interval_minutes", 30)
        return max(1, int(val))

    @interval_minutes.setter
    def interval_minutes(self, val: int) -> None:
        self.set("interval_minutes", max(1, int(val)))

    @property
    def idle_threshold_minutes(self) -> int:
        val = self.data.get("idle_threshold_minutes", 10)
        return max(1, int(val))

    @property
    def smart_pause_enabled(self) -> bool:
        return bool(self.data.get("smart_pause_enabled", True))

    @property
    def presence_mode(self) -> str:
        return str(self.data.get("presence_mode", "tray"))

    @presence_mode.setter
    def presence_mode(self, mode: str) -> None:
        if mode in ("tray", "floating"):
            self.set("presence_mode", mode)

    @property
    def sound_enabled(self) -> bool:
        return bool(self.data.get("sound_enabled", True))

    @property
    def notifications_enabled(self) -> bool:
        return bool(self.data.get("notifications_enabled", True))

    def is_muted(self) -> bool:
        muted_until = self.data.get("muted_until")
        if not muted_until:
            return False
        try:
            until_dt = datetime.fromisoformat(muted_until)
            now = datetime.now(timezone.utc)
            if until_dt.tzinfo is None:
                until_dt = until_dt.replace(tzinfo=timezone.utc)
            if now < until_dt:
                return True
            else:
                self.set("muted_until", None)
                return False
        except Exception:
            self.set("muted_until", None)
            return False

    def mute_for_hours(self, hours: float) -> datetime:
        from datetime import timedelta
        until = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.set("muted_until", until.isoformat())
        return until

    def mute_until_tomorrow(self) -> datetime:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        tomorrow_morning = (now + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        self.set("muted_until", tomorrow_morning.isoformat())
        return tomorrow_morning

    def unmute(self) -> None:
        self.set("muted_until", None)

    def add_custom_tag(self, tag: str) -> None:
        tag = tag.strip()
        if not tag.startswith("#"):
            tag = f"#{tag}"
        tags = list(self.data.get("custom_tags", []))
        if tag and tag not in tags:
            tags.append(tag)
            self.set("custom_tags", tags)
