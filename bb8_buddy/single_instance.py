"""
Single-instance enforcement and IPC for BB-8 Buddy using Unix domain sockets.
"""

from __future__ import annotations
import os
import socket
import sys
import threading
from pathlib import Path
from typing import Callable, Optional

from bb8_buddy.config import get_xdg_data_dir


class SingleInstanceLock:
    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.sock_path = str(get_xdg_data_dir() / "bb8.sock")
        self.callback = callback
        self._server_sock: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def acquire(self) -> bool:
        """
        Attempts to become the primary instance.
        If an instance is already running, returns False.
        """
        # Try connecting to existing socket
        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client_sock.connect(self.sock_path)
            # Socket is alive, another instance is running!
            client_sock.close()
            return False
        except (socket.error, FileNotFoundError):
            # No live server responding, clean up stale socket if it exists
            try:
                if os.path.exists(self.sock_path):
                    os.unlink(self.sock_path)
            except Exception:
                pass

        # Create server socket
        try:
            self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._server_sock.bind(self.sock_path)
            self._server_sock.listen(5)
            self._running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            print(f"[BB-8 IPC] Failed to bind instance socket: {e}", file=sys.stderr)
            return True  # Fall back to running if socket creation fails

    def send_command(self, cmd: str) -> bool:
        """
        Sends a command to the running instance (e.g., 'checkin', 'dashboard', 'quit').
        """
        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client_sock.connect(self.sock_path)
            client_sock.sendall(cmd.encode("utf-8"))
            client_sock.close()
            return True
        except Exception as e:
            print(f"[BB-8 IPC] Failed to send command: {e}", file=sys.stderr)
            return False

    def _listen_loop(self) -> None:
        while self._running and self._server_sock:
            try:
                conn, _ = self._server_sock.accept()
                data = conn.recv(1024).decode("utf-8").strip()
                conn.close()
                if data and self.callback:
                    # Invoke callback in GLib main loop if using GTK
                    from gi.repository import GLib
                    GLib.idle_add(self.callback, data)
            except Exception:
                break

    def release(self) -> None:
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None
        try:
            if os.path.exists(self.sock_path):
                os.unlink(self.sock_path)
        except Exception:
            pass

