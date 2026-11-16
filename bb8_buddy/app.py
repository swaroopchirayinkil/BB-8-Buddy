"""
Main application coordinator for BB-8 Buddy.
Orchestrates tray, timers, idle detection, check-in window, dashboard, and events.
"""

from __future__ import annotations
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from bb8_buddy.audio import AudioManager
from bb8_buddy.config import Config, get_xdg_data_dir
from bb8_buddy.db import Database
from bb8_buddy.idle import IdleDetector
from bb8_buddy.notifications import NotificationManager
from bb8_buddy.single_instance import SingleInstanceLock
from bb8_buddy.tray import TrayIcon
from bb8_buddy.window_checkin import CheckInWindow
from bb8_buddy.window_dashboard import DashboardWindow


class BB8App:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(__file__).resolve().parent.parent
        self.ui_dir = self.root_dir / "ui"
        self.assets_dir = self.root_dir / "assets"
        self.icon_path = str(self.assets_dir / "icons" / "bb8-buddy.svg")

        # Core subsystems
        self.config = Config()
        self.db = Database()
        self.idle_detector = IdleDetector()
        self.audio_manager = AudioManager()
        self.notification_manager = NotificationManager(icon_path=self.icon_path)

        # Timer state
        self._elapsed_minutes = 0
        self._timer_id: Optional[int] = None
        self._last_checkin_time = datetime.now(timezone.utc)

        # Single instance lock
        self.lock = SingleInstanceLock(callback=self._handle_ipc_command)

        # Windows and UI (lazily created after Gtk.init)
        self.tray: Optional[TrayIcon] = None
        self.checkin_win: Optional[CheckInWindow] = None
        self.dashboard_win: Optional[DashboardWindow] = None

    def start(self, initial_action: Optional[str] = None) -> int:
        """
        Main entry point. Runs single-instance check and starts GTK loop.
        """
        if not self.lock.acquire():
            # Already running! Send command to running instance and exit
            target_cmd = initial_action or "checkin"
            self.lock.send_command(target_cmd)
            print(f"[BB-8 Buddy] Already running. Sent '{target_cmd}' command to active instance.")
            return 0

        # Initialize GTK
        Gtk.init(None)

        # Create windows
        self.checkin_win = CheckInWindow(
            ui_dir=self.ui_dir,
            on_save_entry=self._on_entry_saved,
            on_open_dashboard=self.show_dashboard,
            audio_manager=self.audio_manager,
            db=self.db,
            config=self.config,
        )

        self.dashboard_win = DashboardWindow(
            ui_dir=self.ui_dir,
            db=self.db,
            config=self.config,
            on_trigger_checkin=self.show_checkin,
            on_settings_changed=self._on_settings_changed,
        )

        # Create Tray Icon
        self.tray = TrayIcon(
            app_name="BB-8 Buddy",
            icon_path=self.icon_path,
            on_checkin=self.show_checkin,
            on_dashboard=self.show_dashboard,
            on_change_interval=self._on_change_interval,
            on_mute=self._on_mute,
            on_mute_tomorrow=self._on_mute_tomorrow,
            on_unmute=self._on_unmute,
            on_toggle_presence=self._on_toggle_presence,
            on_toggle_sound=self._on_toggle_sound,
            on_quit=self.quit,
            config=self.config,
        )

        # Handle system signals
        signal.signal(signal.SIGINT, lambda *_: GLib.idle_add(self.quit))
        signal.signal(signal.SIGTERM, lambda *_: GLib.idle_add(self.quit))

        # Start 60-second periodic timer
        self._timer_id = GLib.timeout_add_seconds(60, self._on_timer_tick)
        self._update_tray_status()

        # Handle initial action or launch in corner waiting mode
        if initial_action == "checkin":
            GLib.idle_add(lambda: self.show_checkin(ask=True))
        elif initial_action == "dashboard":
            GLib.idle_add(self.show_dashboard)
        else:
            # Initially start with small 3D BB-8 animation rolling and waiting in corner of the screen
            GLib.idle_add(lambda: self.show_checkin(ask=False))

        # Gtk Main loop
        Gtk.main()
        return 0

    def _handle_ipc_command(self, cmd: str) -> None:
        if cmd == "checkin":
            self.show_checkin()
        elif cmd == "dashboard":
            self.show_dashboard()
        elif cmd == "quit":
            self.quit()

    def _on_timer_tick(self) -> bool:
        """
        Fires every 60 seconds. Checks mute status, idle status, and intervals.
        """
        self._elapsed_minutes += 1
        interval = self.config.interval_minutes

        if self.config.is_muted():
            self._update_tray_status("Muted")
            return True

        # Check smart idle pause
        if self.config.smart_pause_enabled:
            idle_thresh = self.config.idle_threshold_minutes
            if self.idle_detector.is_idle(idle_thresh):
                self._update_tray_status("Idle (Paused)")
                return True

        remaining = max(0, interval - self._elapsed_minutes)
        self._update_tray_status(f"Next in {remaining}m")

        if self._elapsed_minutes >= interval:
            self._elapsed_minutes = 0
            self._trigger_timed_checkin()

        return True

    def _trigger_timed_checkin(self) -> None:
        # Show gentle notification
        if self.config.notifications_enabled:
            greetings = [
                "Hey! What are you working on right now?",
                "Quick check-in — still on the same thing?",
                "Beep-boop! What's happening right now?",
                "Whirrr! What has your focus?",
            ]
            import random
            greeting = random.choice(greetings)
            self.notification_manager.show(
                title="BB-8 Buddy",
                body=greeting,
                urgency="normal",
            )

        # Show checkin question bubble directly from 3D BB-8
        self.show_checkin(ask=True)

    def show_checkin(self, ask: bool = True) -> None:
        if self.checkin_win:
            self.checkin_win.show(ask=ask)

    def show_dashboard(self) -> None:
        if self.dashboard_win:
            self.dashboard_win.show()

    def _on_entry_saved(self, entry_data: Dict[str, Any]) -> None:
        self.db.add_entry(
            text=entry_data["text"],
            tags=entry_data.get("tags", []),
            audio_path=entry_data.get("audio_path"),
            source=entry_data.get("source", "text"),
        )
        self._last_checkin_time = datetime.now(timezone.utc)
        self._elapsed_minutes = 0
        self._update_tray_status()

        if self.dashboard_win and self.dashboard_win.is_loaded:
            self.dashboard_win.refresh_data()
        if self.checkin_win and self.checkin_win.is_loaded:
            self.checkin_win.refresh_state()

    def _on_change_interval(self, minutes: int) -> None:
        self.config.interval_minutes = minutes
        self._elapsed_minutes = 0
        self._update_tray_status()

    def _on_mute(self, hours: float) -> None:
        self.config.mute_for_hours(hours)
        self._update_tray_status("Muted")
        if self.tray:
            self.tray.refresh_menu()

    def _on_mute_tomorrow(self) -> None:
        self.config.mute_until_tomorrow()
        self._update_tray_status("Muted until morning")
        if self.tray:
            self.tray.refresh_menu()

    def _on_unmute(self) -> None:
        self.config.unmute()
        self._elapsed_minutes = 0
        self._update_tray_status()
        if self.tray:
            self.tray.refresh_menu()

    def _on_toggle_presence(self) -> None:
        new_mode = "floating" if self.config.presence_mode == "tray" else "tray"
        self.config.presence_mode = new_mode
        if new_mode == "floating":
            self.show_checkin()
        if self.tray:
            self.tray.refresh_menu()

    def _on_toggle_sound(self) -> None:
        self.config.set("sound_enabled", not self.config.sound_enabled)
        if self.tray:
            self.tray.refresh_menu()

    def _on_settings_changed(self) -> None:
        if self.checkin_win:
            self.checkin_win.refresh_state()
        if self.tray:
            self.tray.refresh_menu()
        self._update_tray_status()

    def _update_tray_status(self, custom_msg: Optional[str] = None) -> None:
        if not self.tray:
            return
        if custom_msg:
            self.tray.update_status_text(custom_msg)
        else:
            remaining = max(0, self.config.interval_minutes - self._elapsed_minutes)
            self.tray.update_status_text(f"Every {self.config.interval_minutes}m (Next: {remaining}m)")

    def quit(self) -> None:
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
        self.lock.release()
        Gtk.main_quit()

