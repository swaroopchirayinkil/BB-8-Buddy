"""
Idle detection for Linux desktop environments.
Supports:
1. DBus org.freedesktop.ScreenSaver (KDE, XFCE, Cinnamon, etc.)
2. DBus org.gnome.Mutter.IdleMonitor (GNOME Wayland/X11)
3. xprintidle CLI command (Standard X11)
4. Graceful active fallback
"""

from __future__ import annotations
import shutil
import subprocess
import sys
from typing import Optional

# Try importing dbus
try:
    import dbus
    _HAS_DBUS = True
except ImportError:
    _HAS_DBUS = False


class IdleDetector:
    def __init__(self):
        self._xprintidle_path = shutil.which("xprintidle")
        self._dbus_session: Optional[Any] = None
        self._init_dbus()

    def _init_dbus(self) -> None:
        if not _HAS_DBUS:
            return
        try:
            self._dbus_session = dbus.SessionBus()
        except Exception:
            self._dbus_session = None

    def get_idle_seconds(self) -> float:
        """
        Returns the number of seconds the system has been idle.
        Returns 0.0 if idle time cannot be determined.
        """
        # 1. Try DBus ScreenSaver
        if self._dbus_session:
            try:
                ss = self._dbus_session.get_object(
                    "org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver"
                )
                iface = dbus.Interface(ss, "org.freedesktop.ScreenSaver")
                ms = iface.GetSessionIdleTime()
                return float(ms) / 1000.0
            except Exception:
                pass

            # 2. Try GNOME Mutter IdleMonitor
            try:
                mutter = self._dbus_session.get_object(
                    "org.gnome.Mutter.IdleMonitor",
                    "/org/gnome/Mutter/IdleMonitor/Core",
                )
                iface = dbus.Interface(mutter, "org.gnome.Mutter.IdleMonitor")
                ms = iface.GetIdletime()
                return float(ms) / 1000.0
            except Exception:
                pass

        # 3. Try xprintidle CLI
        if self._xprintidle_path:
            try:
                res = subprocess.run(
                    [self._xprintidle_path],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                )
                if res.returncode == 0 and res.stdout.strip().isdigit():
                    ms = int(res.stdout.strip())
                    return float(ms) / 1000.0
            except Exception:
                pass

        return 0.0

    def is_idle(self, threshold_minutes: int) -> bool:
        """
        Returns True if idle time exceeds threshold_minutes.
        """
        if threshold_minutes <= 0:
            return False
        idle_secs = self.get_idle_seconds()
        return idle_secs >= (threshold_minutes * 60.0)

