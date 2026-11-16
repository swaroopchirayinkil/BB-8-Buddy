"""
Desktop notification management for BB-8 Buddy.
Uses libnotify via GObject Introspection with fallback to notify-send CLI.
"""

from __future__ import annotations
import shutil
import subprocess
import sys
from typing import Optional

_HAS_NOTIFY = False
try:
    import gi
    gi.require_version("Notify", "0.7")
    from gi.repository import Notify
    _HAS_NOTIFY = True
except Exception:
    _HAS_NOTIFY = False


class NotificationManager:
    def __init__(self, icon_path: Optional[str] = None):
        self.icon_path = icon_path or "dialog-information"
        self._notify_initialized = False
        self._notify_send_bin = shutil.which("notify-send")
        self._init_notify()

    def _init_notify(self) -> None:
        global _HAS_NOTIFY
        if _HAS_NOTIFY and not self._notify_initialized:
            try:
                Notify.init("BB-8 Buddy")
                self._notify_initialized = True
            except Exception as e:
                print(f"[BB-8 Notify] Libnotify init error: {e}", file=sys.stderr)
                _HAS_NOTIFY = False

    def show(
        self,
        title: str = "BB-8 Buddy",
        body: str = "Hey! What are you working on right now?",
        urgency: str = "normal",  # low, normal, critical
        icon: Optional[str] = None,
    ) -> bool:
        """
        Sends a desktop notification.
        """
        use_icon = icon or self.icon_path

        # 1. Try gi Notify
        if _HAS_NOTIFY and self._notify_initialized:
            try:
                notification = Notify.Notification.new(title, body, use_icon)
                # Map urgency
                if urgency == "low":
                    notification.set_urgency(Notify.Urgency.LOW)
                elif urgency == "critical":
                    notification.set_urgency(Notify.Urgency.CRITICAL)
                else:
                    notification.set_urgency(Notify.Urgency.NORMAL)
                notification.show()
                return True
            except Exception as e:
                print(f"[BB-8 Notify] Libnotify show error: {e}", file=sys.stderr)

        # 2. Fallback to notify-send CLI
        if self._notify_send_bin:
            try:
                cmd = [
                    self._notify_send_bin,
                    "-a", "BB-8 Buddy",
                    "-u", urgency,
                    "-i", use_icon,
                    title,
                    body,
                ]
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            except Exception as e:
                print(f"[BB-8 Notify] notify-send error: {e}", file=sys.stderr)

        return False

