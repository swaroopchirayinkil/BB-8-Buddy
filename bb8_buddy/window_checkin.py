"""
Floating 3D BB-8 companion & question check-in window using WebKit2GTK.
Features:
- Transparent frameless window positioned in bottom-right corner
- 3D rolling BB-8 droid waiting in the corner
- Interactive speech bubble question with text input when clicked or check-in due
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import cairo
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, Gdk, WebKit2, GLib


class CheckInWindow:
    def __init__(
        self,
        ui_dir: Path,
        on_save_entry: Callable[[Dict[str, Any]], None],
        on_open_dashboard: Callable[[], None],
        audio_manager: Any,
        db: Any,
        config: Any,
    ):
        self.ui_dir = ui_dir
        self.html_path = ui_dir / "checkin.html"
        self.on_save_entry = on_save_entry
        self.on_open_dashboard = on_open_dashboard
        self.audio_manager = audio_manager
        self.db = db
        self.config = config

        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("BB-8 Buddy")
        self.window.set_default_size(280, 330)
        self.window.set_resizable(False)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_decorated(False)
        self.window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.window.set_app_paintable(True)

        # Set RGBA Visual unconditionally whenever available
        self._setup_transparency()

        self.window.connect("delete-event", lambda w, e: self.hide())
        self.window.connect("draw", self._on_window_draw)
        self.window.connect("button-press-event", self._on_button_press)

        # WebKit WebView
        self.webview = WebKit2.WebView()
        self.webview.set_app_paintable(True)

        # Set completely transparent background on WebView
        rgba = Gdk.RGBA(0.0, 0.0, 0.0, 0.0)
        self.webview.set_background_color(rgba)

        # CSS Provider to eliminate any GTK background, borders, or shadows
        css_provider = Gtk.CssProvider()
        try:
            css_provider.load_from_data(b"""
                window, .background, decoration, webview {
                    background-color: rgba(0, 0, 0, 0);
                    background-image: none;
                    border: none;
                    box-shadow: none;
                    outline: none;
                }
            """)
            self.window.get_style_context().add_provider(
                css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self.webview.get_style_context().add_provider(
                css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"[BB-8 Checkin] Note on CSS provider: {e}", file=sys.stderr)

        settings = self.webview.get_settings()
        settings.set_enable_developer_extras(False)

        # IPC Handler
        self.ucm = self.webview.get_user_content_manager()
        self.ucm.register_script_message_handler("bb8")
        self.ucm.connect("script-message-received::bb8", self._on_js_message)

        self.window.add(self.webview)
        self.is_loaded = False
        self.webview.connect("load-changed", self._on_load_changed)

        uri = f"file://{self.html_path.resolve()}"
        self.webview.load_uri(uri)

    def _setup_transparency(self) -> None:
        def on_screen_changed(widget, old_screen):
            screen = widget.get_screen()
            visual = screen.get_rgba_visual()
            if visual is not None:
                widget.set_visual(visual)

        self.window.connect("screen-changed", on_screen_changed)
        on_screen_changed(self.window, None)

    def _on_window_draw(self, widget: Gtk.Widget, cr: cairo.Context) -> bool:
        # Clear the Cairo surface to 100% alpha transparency
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    def _on_load_changed(self, webview: WebKit2.WebView, event: WebKit2.LoadEvent) -> None:
        if event == WebKit2.LoadEvent.FINISHED:
            self.is_loaded = True
            self._send_initial_state()

    def _on_button_press(self, widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        # Drag window when holding Shift or Alt key
        if event.button == 1 and (event.state & (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.MOD1_MASK)):
            self.window.begin_move_drag(
                event.button, int(event.x_root), int(event.y_root), event.time
            )
            return True
        return False

    def position_in_corner(self, width: int = 280, height: int = 330) -> None:
        """Positions window in bottom-right corner of screen."""
        screen = self.window.get_screen()
        display = screen.get_display()
        monitor = display.get_primary_monitor() or (display.get_monitor(0) if display.get_n_monitors() > 0 else None)
        
        if monitor:
            geom = monitor.get_geometry()
            x = geom.x + geom.width - width - 20
            y = geom.y + geom.height - height - 44
        else:
            x = screen.get_width() - width - 20
            y = screen.get_height() - height - 44

        self.window.resize(width, height)
        self.window.move(max(0, x), max(0, y))

    def refresh_state(self) -> None:
        self._send_initial_state()

    def _send_initial_state(self) -> None:
        last = self.db.get_last_entry()
        mic_status = self.audio_manager.get_status()
        state = {
            "last_entry": last,
            "sound_enabled": self.config.sound_enabled,
            "mic_status": mic_status,
            "interval_minutes": self.config.interval_minutes,
            "character_size": self.config.get("character_size", "small"),
        }
        js_code = f"if (window.initBB8) {{ window.initBB8({json.dumps(state)}); }}"
        self.eval_js(js_code)

    def _on_js_message(self, manager: Any, js_result: Any) -> None:
        try:
            val_str = js_result.get_js_value().to_string()
            data = json.loads(val_str)
            action = data.get("action")

            if action == "save":
                text = data.get("text", "")
                tags = data.get("tags", [])
                source = data.get("source", "text")
                self.on_save_entry({
                    "text": text,
                    "tags": tags,
                    "audio_path": None, # Audio is strictly converted to text and deleted
                    "source": source,
                })

            elif action == "close":
                self.hide()

            elif action == "open_dashboard":
                self.on_open_dashboard()

            elif action == "start_recording":
                ok, msg, path = self.audio_manager.start_recording()
                res = {"ok": ok, "message": msg, "path": path}
                self.eval_js(f"if (window.onRecordingStarted) {{ window.onRecordingStarted({json.dumps(res)}); }}")

            elif action == "stop_recording":
                ok, msg, transcript, path = self.audio_manager.stop_recording()
                res = {"ok": ok, "message": msg, "transcript": transcript, "path": path}
                self.eval_js(f"if (window.onRecordingStopped) {{ window.onRecordingStopped({json.dumps(res)}); }}")

            elif action == "toggle_sound":
                val = bool(data.get("enabled", True))
                self.config.set("sound_enabled", val)

            elif action == "request_state":
                self._send_initial_state()

        except Exception as e:
            print(f"[BB-8 Checkin] JS message error: {e}", file=sys.stderr)

    def eval_js(self, script: str) -> None:
        try:
            self.webview.run_javascript(script, None, None, None)
        except Exception as e:
            print(f"[BB-8 Checkin] Eval JS error: {e}", file=sys.stderr)

    def show(self, ask: bool = False) -> None:
        """Shows the floating window. If ask=True, opens the question bubble."""
        self.position_in_corner()
        self.window.show_all()
        self.window.present()
        if self.is_loaded:
            self._send_initial_state()
            if ask:
                self.eval_js("if (window.openCheckinQuestion) { window.openCheckinQuestion(); }")

    def hide(self) -> bool:
        self.window.hide()
        return True
