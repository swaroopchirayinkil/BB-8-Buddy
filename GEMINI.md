# GEMINI.md – AI Coding Agent Architecture & Context

This file documents the architecture, design decisions, and core constraints of **BB-8 Buddy** to provide immediate context for coding agents and contributors.

---

## 1. Project Purpose & Philosophy

**BB-8 Buddy** is a local-first, gentle productivity companion for Linux desktops. It runs unobtrusively in the background, rolls out an interactive 3D BB-8 droid at customizable intervals, and helps users track their focus without cloud dependencies, subscriptions, or telemetry.

### Core Constraints
- **100% Local & Private**: All data is stored in a local SQLite database (`~/.local/share/bb8-buddy/bb8_buddy.db`). No telemetry, no external API calls at runtime.
- **Ultra-Lightweight Footprint**: The compiled `.deb` package must remain strictly under 10 MB (currently ~230 KB). Avoid heavy runtimes (no Electron, no Chromium bundles).
- **Standards Compliant**: Strictly follows the XDG Base Directory specification (`~/.local/share/bb8-buddy` for data, `~/.config/bb8-buddy` for settings).

---

## 2. Technology Stack

- **Runtime & Host**: Python 3.10+ with standard library SQLite, Unix sockets, and PyGObject bindings.
- **Window Management & Desktop Integration**: GTK 3 (`Gtk.Window`, Cairo alpha transparency, `Gtk.StatusIcon` / AppIndicator).
- **Web Interface Hosting**: WebKit2GTK 4.1 (`WebKit2.WebView`, `WebKit2.UserContentManager`).
- **3D Character Engine**: Procedural Three.js character rendered offline via bundled `ui/shared/three.min.js`.
- **Audio Synthesizer**: Procedural 8-bit astromech chiptune sound synthesis via standard Web Audio API (`ui/shared/bb8_audio.js`).

---

## 3. Directory Layout & Module Responsibilities

```
bb8-buddy/
├── AGENTS.md                  # Coding agent instructions and conventions
├── GEMINI.md                  # Architectural context and system constraints
├── Makefile                   # Developer convenience targets (test, run, deb)
├── README.md                  # User-facing documentation & install guides
├── package-deb.sh             # Debian packaging build script
│
├── bin/
│   └── bb8-buddy              # Executable entrypoint / CLI argument parser
│
├── bb8_buddy/                 # Core Python application package
│   ├── app.py                 # Application orchestrator, main loop, periodic timer
│   ├── audio.py               # Microphone discovery, local WAV recording & STT detection
│   ├── config.py              # XDG configuration management & defaults
│   ├── db.py                  # SQLite database layer, duration calculator & analytics
│   ├── idle.py                # X11 (libXss) & Wayland idle detection
│   ├── notifications.py       # Desktop notifications via libnotify / D-Bus
│   ├── single_instance.py     # Unix domain socket single-instance enforcement & IPC
│   ├── tray.py                # System tray icon & contextual quick actions
│   ├── window_checkin.py      # Floating transparent GTK window for 3D BB-8 & check-in prompt
│   └── window_dashboard.py    # GTK window for telemetry dashboard, filters & settings
│
├── ui/                        # WebKit front-end web views
│   ├── checkin.html/.css/.js  # 3D BB-8 companion & quick response speech bubble
│   ├── dashboard.html/.css/.js# Main telemetry dashboard, stats, feed & settings
│   └── shared/                # Shared front-end assets
│       ├── bb8_3d.js          # Procedural Three.js BB-8 character & animation controller
│       ├── bb8_audio.js       # Procedural Web Audio chiptune synthesizer
│       ├── three.min.js       # Offline bundled Three.js library
│       └── bb8.svg            # Vector droid icons
│
├── debian/                    # Debian package metadata (control, changelog, rules)
├── dist/                      # Pre-built distribution packages (*.deb)
├── examples/                  # Reference demos and prototypes
└── tests/                     # Automated unit test suite
    ├── run_tests.py           # Test runner
    ├── test_components.py     # Audio, notifications & idle detection tests
    ├── test_config.py         # Settings & interval configuration tests
    └── test_db.py             # SQLite CRUD, duration & analytics tests
```

---

## 4. Inter-Process Communication (IPC)

### Between WebKit and Python
Communication between the HTML/JS frontend and Python uses WebKit's native `UserContentManager` message handlers:

1. **Check-In Window Handler** (`bb8`):
   - Handled in `window_checkin.py` via `script-message-received::bb8`.
   - Actions: `save`, `close`, `open_dashboard`, `start_recording`, `stop_recording`, `toggle_sound`, `request_state`.
2. **Dashboard Window Handler** (`bb8_dash`):
   - Handled in `window_dashboard.py` via `script-message-received::bb8_dash`.
   - Actions: `refresh`, `filter`, `save_entry`, `delete_entry`, `checkin_now`, `save_settings`, `export_csv`, `export_markdown`, `close`.

### Between Application Instances
When `bb8-buddy` is invoked while already running:
- The secondary process attempts to connect to `~/.local/share/bb8-buddy/bb8.sock`.
- It transmits CLI commands (`checkin`, `dashboard`, `quit`) to the primary daemon and exits immediately without spawning duplicate windows.

---

## 5. Development & Verification Workflows

```bash
# Run unit tests
python3 tests/run_tests.py

# Launch check-in companion directly
python3 bin/bb8-buddy --checkin

# Launch telemetry dashboard directly
python3 bin/bb8-buddy --dashboard

# Rebuild Debian package
./package-deb.sh
```
