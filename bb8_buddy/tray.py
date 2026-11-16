"""
System tray management for BB-8 Buddy.
Uses AyatanaAppIndicator3 with fallback to Gtk.StatusIcon.
"""

from __future__ import annotations
import sys
from typing import Any, Callable, Dict, Optional

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_HAS_APP_INDICATOR = False
try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as appindicator
    _HAS_APP_INDICATOR = True
except Exception:
    try:
        gi.require_version("AppIndicator3", "0.1")
        from gi.repository import AppIndicator3 as appindicator
        _HAS_APP_INDICATOR = True
    except Exception:
        _HAS_APP_INDICATOR = False


class TrayIcon:
    def __init__(
        self,
        app_name: str,
        icon_path: str,
        on_checkin: Callable[[], None],
        on_dashboard: Callable[[], None],
        on_change_interval: Callable[[int], None],
        on_mute: Callable[[float], None],
        on_mute_tomorrow: Callable[[], None],
        on_unmute: Callable[[], None],
        on_toggle_presence: Callable[[], None],
        on_toggle_sound: Callable[[], None],
        on_quit: Callable[[], None],
        config: Any,
    ):
        self.app_name = app_name
        self.icon_path = icon_path
        self.on_checkin = on_checkin
        self.on_dashboard = on_dashboard
        self.on_change_interval = on_change_interval
        self.on_mute = on_mute
        self.on_mute_tomorrow = on_mute_tomorrow
        self.on_unmute = on_unmute
        self.on_toggle_presence = on_toggle_presence
        self.on_toggle_sound = on_toggle_sound
        self.on_quit = on_quit
        self.config = config

        self.indicator: Optional[Any] = None
        self.status_icon: Optional[Gtk.StatusIcon] = None
        self.menu: Gtk.Menu = Gtk.Menu()
        self.status_item: Optional[Gtk.MenuItem] = None

        self._build_menu()
        self._init_tray()

    def _build_menu(self) -> None:
        self.menu = Gtk.Menu()

        # Status item (non-clickable header)
        self.status_item = Gtk.MenuItem(label="🤖 BB-8 Buddy: Active")
        self.status_item.set_sensitive(False)
        self.menu.append(self.status_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Check in now
        checkin_item = Gtk.MenuItem(label="⚡ Check In Now")
        checkin_item.connect("activate", lambda _: self.on_checkin())
        self.menu.append(checkin_item)

        # Open Dashboard
        dash_item = Gtk.MenuItem(label="📊 Open Dashboard")
        dash_item.connect("activate", lambda _: self.on_dashboard())
        self.menu.append(dash_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Interval Submenu
        interval_item = Gtk.MenuItem(label="⏱️ Check-In Interval")
        interval_menu = Gtk.Menu()

        current_interval = self.config.interval_minutes
        for mins in [15, 30, 45, 60]:
            label = f"{mins} minutes"
            if mins == current_interval:
                label += " ✓"
            sub_item = Gtk.MenuItem(label=label)
            sub_item.connect("activate", lambda _, m=mins: self._on_interval_selected(m))
            interval_menu.append(sub_item)

        custom_item = Gtk.MenuItem(label="Custom Interval...")
        custom_item.connect("activate", lambda _: self._on_custom_interval())
        interval_menu.append(custom_item)

        interval_item.set_submenu(interval_menu)
        self.menu.append(interval_item)

        # Mute / Snooze Submenu
        mute_item = Gtk.MenuItem(label="🔕 Mute / Pause")
        mute_menu = Gtk.Menu()

        m1_item = Gtk.MenuItem(label="Mute for 1 hour")
        m1_item.connect("activate", lambda _: self.on_mute(1.0))
        mute_menu.append(m1_item)

        m2_item = Gtk.MenuItem(label="Mute for 2 hours")
        m2_item.connect("activate", lambda _: self.on_mute(2.0))
        mute_menu.append(m2_item)

        mt_item = Gtk.MenuItem(label="Mute until tomorrow morning")
        mt_item.connect("activate", lambda _: self.on_mute_tomorrow())
        mute_menu.append(mt_item)

        unmute_item = Gtk.MenuItem(label="Unmute / Resume")
        unmute_item.connect("activate", lambda _: self.on_unmute())
        mute_menu.append(unmute_item)

        mute_item.set_submenu(mute_menu)
        self.menu.append(mute_item)

        # Presence Mode Toggle
        is_floating = self.config.presence_mode == "floating"
        presence_label = "📍 Desktop Widget: On" if is_floating else "📍 Desktop Widget: Off"
        self.presence_item = Gtk.MenuItem(label=presence_label)
        self.presence_item.connect("activate", lambda _: self.on_toggle_presence())
        self.menu.append(self.presence_item)

        # Sound Toggle
        sound_label = "🔊 Sound Effects: On" if self.config.sound_enabled else "🔇 Sound Effects: Off"
        self.sound_item = Gtk.MenuItem(label=sound_label)
        self.sound_item.connect("activate", lambda _: self.on_toggle_sound())
        self.menu.append(self.sound_item)

        self.menu.append(Gtk.SeparatorMenuItem())

        # Quit
        quit_item = Gtk.MenuItem(label="🚪 Quit BB-8 Buddy")
        quit_item.connect("activate", lambda _: self.on_quit())
        self.menu.append(quit_item)

        self.menu.show_all()

    def _init_tray(self) -> None:
        if _HAS_APP_INDICATOR:
            try:
                self.indicator = appindicator.Indicator.new(
                    "bb8_buddy",
                    self.icon_path,
                    appindicator.IndicatorCategory.APPLICATION_STATUS,
                )
                self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
                self.indicator.set_menu(self.menu)
                return
            except Exception as e:
                print(f"[BB-8 Tray] AppIndicator init failed: {e}", file=sys.stderr)

        # Fallback to Gtk.StatusIcon
        try:
            self.status_icon = Gtk.StatusIcon()
            self.status_icon.set_from_file(self.icon_path)
            self.status_icon.set_tooltip_text("BB-8 Buddy")
            self.status_icon.connect("popup-menu", self._on_status_icon_popup)
            self.status_icon.connect("activate", lambda _: self.on_checkin())
            self.status_icon.set_visible(True)
        except Exception as e:
            print(f"[BB-8 Tray] StatusIcon init failed: {e}", file=sys.stderr)

    def _on_status_icon_popup(self, icon: Gtk.StatusIcon, button: int, time: int) -> None:
        self.menu.popup(None, None, None, icon, button, time)

    def update_status_text(self, text: str) -> None:
        if self.status_item:
            self.status_item.set_label(f"🤖 {text}")
        if self.status_icon:
            self.status_icon.set_tooltip_text(f"BB-8 Buddy: {text}")

    def refresh_menu(self) -> None:
        self._build_menu()
        if self.indicator:
            self.indicator.set_menu(self.menu)

    def _on_interval_selected(self, minutes: int) -> None:
        self.on_change_interval(minutes)
        self.refresh_menu()

    def _on_custom_interval(self) -> None:
        dialog = Gtk.Dialog(
            title="Set Custom Interval",
            parent=None,
            flags=Gtk.DialogFlags.MODAL,
            buttons=(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK,
                Gtk.ResponseType.OK,
            ),
        )
        dialog.set_default_size(280, 120)
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_border_width(15)

        lbl = Gtk.Label(label="Check in every (minutes):")
        box.pack_start(lbl, False, False, 0)

        spin = Gtk.SpinButton.new_with_range(1, 480, 1)
        spin.set_value(float(self.config.interval_minutes))
        box.pack_start(spin, False, False, 0)

        dialog.show_all()
        res = dialog.run()
        if res == Gtk.ResponseType.OK:
            val = int(spin.get_value())
            self.on_change_interval(val)
            self.refresh_menu()
        dialog.destroy()

