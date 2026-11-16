"""
Full Dashboard window for BB-8 Buddy using WebKit2GTK.
Provides timeline view, search/filters, visual analytics, streak tracking, and exports.
"""

from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2, GLib


class DashboardWindow:
    def __init__(
        self,
        ui_dir: Path,
        db: Any,
        config: Any,
        on_trigger_checkin: Callable[[], None],
        on_settings_changed: Optional[Callable[[], None]] = None,
    ):
        self.ui_dir = ui_dir
        self.html_path = ui_dir / "dashboard.html"
        self.db = db
        self.config = config
        self.on_trigger_checkin = on_trigger_checkin
        self.on_settings_changed = on_settings_changed

        self.current_period = "today"
        self.current_tag = None
        self.current_query = None

        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("BB-8 Buddy Dashboard")
        self.window.set_default_size(900, 680)
        self.window.set_position(Gtk.WindowPosition.CENTER)

        # Intercept close event to hide instead of destroy
        self.window.connect("delete-event", lambda w, e: self.hide())

        # WebKit WebView
        self.webview = WebKit2.WebView()
        settings = self.webview.get_settings()
        settings.set_enable_developer_extras(False)

        # IPC Handler
        self.ucm = self.webview.get_user_content_manager()
        self.ucm.register_script_message_handler("bb8_dash")
        self.ucm.connect("script-message-received::bb8_dash", self._on_js_message)

        self.window.add(self.webview)
        self.is_loaded = False
        self.webview.connect("load-changed", self._on_load_changed)

        uri = f"file://{self.html_path.resolve()}"
        self.webview.load_uri(uri)

    def _on_load_changed(self, webview: WebKit2.WebView, event: WebKit2.LoadEvent) -> None:
        if event == WebKit2.LoadEvent.FINISHED:
            self.is_loaded = True
            self.refresh_data()

    def refresh_data(self) -> None:
        if not self.is_loaded:
            return

        start_date = None
        local_now = datetime.now().astimezone()
        if self.current_period == "today":
            local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = local_midnight.astimezone(timezone.utc).isoformat()
        elif self.current_period == "week":
            start_date = (local_now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
        elif self.current_period == "month":
            start_date = (local_now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()

        analytics = self.db.get_analytics(self.current_period)
        entries = self.db.get_entries(
            limit=250,
            start_date=start_date,
            tag=self.current_tag,
            query=self.current_query,
        )
        state = {
            "analytics": analytics,
            "entries": entries,
            "period": self.current_period,
            "config": {
                "interval_minutes": self.config.interval_minutes,
                "idle_threshold_minutes": self.config.idle_threshold_minutes,
                "presence_mode": self.config.presence_mode,
                "sound_enabled": self.config.sound_enabled,
                "notifications_enabled": self.config.notifications_enabled,
                "character_size": self.config.get("character_size", "small"),
                "custom_tags": self.config.get("custom_tags", []),
            },
        }
        js_code = f"if (window.onDashboardData) {{ window.onDashboardData({json.dumps(state)}); }}"
        self.eval_js(js_code)

    def _on_js_message(self, manager: Any, js_result: Any) -> None:
        try:
            val_str = js_result.get_js_value().to_string()
            data = json.loads(val_str)
            action = data.get("action")

            if action == "refresh":
                self.refresh_data()

            elif action == "filter":
                self.current_period = data.get("period", "all")
                self.current_tag = data.get("tag")
                self.current_query = data.get("query")
                self.refresh_data()

            elif action == "save_entry":
                text = (data.get("text") or "").strip()
                if text:
                    tags = data.get("tags") or []
                    source = data.get("source") or "dashboard"
                    self.db.add_entry(text=text, tags=tags, source=source)
                    self.refresh_data()
                    if self.on_settings_changed:
                        self.on_settings_changed()

            elif action == "delete_entry":
                entry_id = int(data.get("id"))
                self.db.delete_entry(entry_id)
                self.refresh_data()

            elif action == "checkin_now":
                self.on_trigger_checkin()

            elif action == "save_settings":
                updates = data.get("settings", {})
                self.config.update(updates)
                self.refresh_data()
                if self.on_settings_changed:
                    self.on_settings_changed()

            elif action == "export_csv":
                csv_content = self.db.export_csv()
                self._save_file_dialog("bb8_buddy_export.csv", csv_content)

            elif action == "export_markdown":
                md_content = self.db.export_markdown()
                self._save_file_dialog("bb8_buddy_export.md", md_content)

            elif action == "close":
                self.hide()

        except Exception as e:
            print(f"[BB-8 Dash] JS message error: {e}", file=sys.stderr)

    def _save_file_dialog(self, default_name: str, content: str) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Export BB-8 Buddy Data",
            parent=self.window,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE,
                Gtk.ResponseType.OK,
            ),
        )
        dialog.set_current_name(default_name)
        dialog.set_do_overwrite_confirmation(True)

        res = dialog.run()
        if res == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if filename:
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content)
                    self.eval_js(f"alert('Export saved successfully to {os.path.basename(filename)}');")
                except Exception as e:
                    self.eval_js(f"alert('Failed to save export: {e}');")
        dialog.destroy()

    def eval_js(self, script: str) -> None:
        try:
            self.webview.run_javascript(script, None, None, None)
        except Exception as e:
            print(f"[BB-8 Dash] Eval JS error: {e}", file=sys.stderr)

    def show(self) -> None:
        self.window.show_all()
        self.window.present()
        self.refresh_data()

    def hide(self) -> bool:
        self.window.hide()
        return True

