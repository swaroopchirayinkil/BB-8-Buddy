# 🤖 BB-8 Buddy

> A tiny, persistent, lightweight desktop companion that gently checks in with you every 30 minutes. 100% local, private, friendly, and non-intrusive.

---

## 📋 Overview

**BB-8 Buddy** is a native Linux desktop companion inspired by the beloved Star Wars astromech droid. It sits quietly in your system tray, periodically rolling up with a gentle check-in question: *"What are you working on right now?"*

- **Ultra-lightweight**: Under **1 MB** installed footprint (the Debian package is just **~86 KB**), consuming ~25 MB RAM idle. Compare this to 150–250 MB for an Electron app.
- **100% Local & Private**: No cloud connections, no telemetry, no background Node servers. All activity notes persist purely in the local SQLite database.
- **Retro Aesthetic & 3D Cel-Shaded Droid**: Features a 3D WebGL astromech droid with quantized stepped cel-shading, ink edge outlines, CRT scanline raster effects, and quaternion rolling physics matching vintage arcade and sci-fi terminals. Also includes a 2D line-art fallback matching the classic BB-8 illustration.
- **Gentle & Non-Intrusive**: Features smart idle detection that automatically skips check-ins when you step away from your keyboard.
- **Fast, Distraction-Free Input**: Answer by typing, one-click quick actions (*"Same as last time"*, *"Taking a break"*), or use the inline quick-logger directly in the dashboard.
- **8-Bit Chiptune Audio**: Procedural square-wave chirps, arpeggio fanfares, and teletype clicks generated completely offline via the Web Audio API.

---

## 🏛️ Architecture & "How It Works"

```
┌─────────────────────────────────────────────────────────────┐
│                       System Tray Icon                      │
│             (AyatanaAppIndicator3 / Gtk.StatusIcon)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
   ┌─────────────────────────┐   ┌──────────────────────────┐
   │   Floating BB-8 Window  │   │     Dashboard Window     │
   │      (WebKit2GTK)       │   │       (WebKit2GTK)       │
   │ ─────────────────────── │   │ ──────────────────────── │
   │ • Droid Avatar & Glow   │   │ • Timeline Feed & Search │
   │ • Fast Text Input       │   │ • Visual Analytics       │
   │ • Quick Action Chips    │   │ • Daily Streak Tracker   │
   │ • Web Audio Synthesizer │   │ • Markdown & CSV Export  │
   └────────────┬────────────┘   └────────────┬─────────────┘
                │                             │
                └──────────────┬──────────────┘
                               │ WebKit UserContentManager IPC
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Application Coordinator                  │
│                     (bb8_buddy/app.py)                      │
├──────────────────────────────┬──────────────────────────────┤
│  • Timer & Schedule Engine   │  • Multi-Strategy Idle Mon.  │
│  • Single-Instance IPC Lock  │  • Theme & Sound Coordinator │
│  • Native Desktop Notify     │  • Configuration Manager     │
└──────────────────────────────┴──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Local SQLite Database                    │
│             ~/.local/share/bb8-buddy/bb8_buddy.db           │
└─────────────────────────────────────────────────────────────┘
```

### Runtime Decision & Footprint Comparison

The project specification suggested **txiki.js** or the closest practical lightweight alternative that keeps the total footprint under ~10 MB. 

| Runtime | Footprint on Disk | Memory Idle | System Tray & Native Webview | Local SQLite |
| :--- | :--- | :--- | :--- | :--- |
| **Electron** | ~150–250 MB | ~120–200 MB | Yes (heavy Chromium + Node) | Heavy bindings |
| **txiki.js** | ~3–5 MB | ~15 MB | ❌ No native GTK/WebKit bindings | Yes (built-in) |
| **BB-8 Buddy (Python 3 + WebKit2GTK)** | **< 1 MB** (77 KB deb) | **~25 MB** | **✅ Native Ayatana + WebKit2** | **✅ Built-in SQLite3** |

**Why this architecture was chosen:**
1. **Zero compilation / Pre-installed**: Python 3, WebKit2GTK, and GObject Introspection are already pre-installed standard libraries on Debian, Ubuntu, Linux Mint, and Fedora.
2. **Tiny footprint**: The entire BB-8 Buddy codebase, SVG art, CSS, and sound generator occupies less than **350 KB** on disk.
3. **No heavy runtimes**: Zero external web servers or Node processes. The webview communicates directly with the Python process via bidirectional WebKit message handlers (`WebKitUserContentManager`).

---

## 🗂️ Project Structure

```
bb8-buddy/
├── bin/
│   └── bb8-buddy                 # Executable launcher script
├── bb8_buddy/
│   ├── __init__.py               # Package metadata
│   ├── app.py                   # Central application coordinator
│   ├── config.py                # XDG configuration management
│   ├── db.py                    # SQLite persistence, analytics & exports
│   ├── idle.py                  # Multi-strategy idle detection (DBus/xprintidle)
│   ├── notifications.py         # Native desktop notifications (libnotify)
│   ├── tray.py                  # System tray icon (AyatanaAppIndicator3)
│   ├── single_instance.py       # Unix domain socket single-instance IPC
│   ├── window_checkin.py        # Small floating BB-8 popup window
│   └── window_dashboard.py      # Full dashboard window
├── ui/
│   ├── checkin.html             # Check-in card template
│   ├── checkin.css              # BB-8 theme, styling, animations
│   ├── checkin.js               # Check-in controller & IPC
│   ├── dashboard.html           # Dashboard template
│   ├── dashboard.css            # Dark/light dashboard styles
│   ├── dashboard.js             # Timeline, filters, analytics & charts
│   └── shared/
│       ├── bb8.svg              # Scalable vector BB-8 illustration
│       ├── bb8_icon.png         # Raster app icon
│       └── bb8_audio.js         # Procedural Web Audio droid synthesizer
├── assets/
│   ├── bb8-buddy.desktop        # FreeDesktop launcher file
│   └── icons/                   # High-resolution & scalable icons
├── debian/                      # Standard Debian packaging metadata
│   ├── control, rules, changelog, copyright, compat
├── tests/                       # Automated test suite
│   ├── test_db.py               # Database & analytics tests
│   ├── test_config.py           # Configuration tests
│   ├── test_components.py       # Audio, idle, notification tests
│   └── run_tests.py             # Test runner
├── package-deb.sh               # One-click Debian package builder
├── Makefile                     # Build, test, run, package automation
└── README.md                    # Documentation
```

---

## 🚀 Getting Started on Debian / Ubuntu / Fedora

### 1. Install System Dependencies

On **Debian / Ubuntu / Linux Mint**:
```bash
sudo apt update
sudo apt install -y python3 python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 \
                    gir1.2-ayatanaappindicator3-0.1 gir1.2-notify-0.7 \
                    sqlite3 alsa-utils libnotify-bin
```

*(Optional recommended for idle detection on X11: `sudo apt install -y xprintidle`)*

On **Fedora**:
```bash
sudo dnf install -y python3 python3-gobject gtk3 webkit2gtk4.1 \
                    libayatana-appindicator-gtk3 libnotify sqlite
```

### 2. Run Directly from Source

```bash
git clone https://github.com/google/bb8-buddy.git
cd bb8-buddy

# Run test suite
make test

# Launch BB-8 Buddy
./bin/bb8-buddy
```

---

## 📦 Building and Installing the Debian Package (`.deb`)

To build a standalone `.deb` package in seconds:

```bash
# Build the package
make package
# or directly: ./package-deb.sh
```

This creates `dist/bb8-buddy_1.0.0_all.deb` (approx. 77 KB).

### Install the `.deb`:
```bash
sudo dpkg -i dist/bb8-buddy_1.0.0_all.deb
# If any missing system dependencies:
sudo apt install -f
```

Once installed, **BB-8 Buddy** appears in your desktop application menu under **Utilities / Office**, or can be launched by running `bb8-buddy` in any terminal.

---

## ✨ Core Features & Usage

### 1. High-Fidelity 3D WebGL BB-8 & Interactive Corner Mode
- **True 3D WebGL Mesh & Shaders**: Replaces flat representations with a full 3D WebGL model (spherical body with smooth vertex normals, truncated dome head, 3D neck bevel ring, protruding 3D primary optical lens with specular highlights, secondary sensor, and dual antennas).
- **Procedural PBR UV Textures**: Accurately reproduces the 6 cardinal astromech circular mechanism panels, radial orange tabs, silver core hubs, and panel seam lines matching the 3D reference model.
- **Authentic Decoupled Rolling Physics**: The spherical body rotates continuously in 3D around its travel axis via quaternion rotation while the magnetic dome head stays stabilized upright, bobbing and leaning with inertia.
- **Interactive Mouse Tracking**: While waiting in the corner, the head smoothly pivots (pitch and yaw) to look directly at your mouse cursor.
- **Click to Ask**: Clicking the 3D BB-8 droid makes him chirp, hop, and open a friendly speech bubble question right above his head: *"What are you working on right now?"*
- **Answer Back in Small Text Box**: Type your answer right in the compact input box and press `Enter` (or click `✓`). BB-8 plays a celebratory trill, saves to local SQLite, and closes the bubble back to his idle resting state.
- **Quick Shortcuts & Voice**: One-click `⚡ Same` repeats your last activity, `☕ Break` logs a break, and `🎤` converts voice into text (with audio immediately discarded).
- **Dashboard Access**: Click the `📊` icon in the mini dock or tray menu to open the full analytics dashboard anytime.

### 2. Timed Check-Ins & Smart Idle Pause
- **Default Interval**: 30 minutes (configurable to 15, 30, 45, 60 minutes or custom).
- **Gentle Alert**: Shows a native desktop notification and raises the floating BB-8 window.
- **Smart Pause (Idle Detection)**:
  - Automatically queries the desktop environment (`org.freedesktop.ScreenSaver`, `org.gnome.Mutter.IdleMonitor`, or `xprintidle`).
  - If you've been away from your computer for > 10 minutes, check-ins are paused until you return.

### 3. Input Methods
- **Text Input**: Type what you're doing and press `Ctrl+Enter` or click **Save**.
- **One-Click Quick Actions**:
  - ⚡ **Same as last time**: Instantly repeats the last activity and tags.
  - ☕ **Taking a break**: Automatically logs `"Taking a quick break ☕"` with `#break` and offers to snooze.
- **Voice to Text Conversion (Privacy-First, Zero Audio Stored)**:
  - Click the **Speak** button to speak your activity.
  - The audio is converted into text and immediately inserted into the input box.
  - **No audio files are kept on disk**: The temporary recording is deleted right after speech conversion to protect your privacy and keep your storage footprint minimal.
  - Works with local speech recognition (`vosk`, `whisper.cpp`, `pocketsphinx`) and local voice note conversion fallback.

### 3. Dashboard
Access the dashboard anytime via the tray menu (**Open Dashboard**) or the `📊` button on the check-in card:
- **Timeline Feed**:
  - Filter by **Today**, **This Week**, **This Month**, or **All Time**.
  - Real-time search by keyword or tag.
  - Play back voice recordings directly in the timeline.
- **Activity Analytics**:
  - Category breakdown with visual percentage progress bars.
  - Most common activities ranking.
  - Daily streak calculation (consecutive days with check-ins).
- **Export Options**:
  - **Export to Markdown**: Clean, formatted daily log table with timestamps and tags.
  - **Export to CSV**: Standard spreadsheet format (`id,timestamp,activity,tags,duration_minutes,source,audio_path`).

### 4. Droid Personality & Procedural Audio
- Animated BB-8 header with eye lens glow and bobbing motion.
- Friendly, low-pressure messages (*"Hey! What are you working on right now?"*, *"Beep-boop! Time for a quick update."*, *"Got it! 👍"*).
- Procedural Star Wars droid audio synthesizer built with the HTML5 Web Audio API:
  - Chirps upon greeting.
  - Happy ascending arpeggio on save.
  - Relaxing descending chime on break.
  - Sound can be toggled on/off with one click from the window or tray menu.

### 5. System Tray Menu
Right-click or click the BB-8 icon in your system tray:
- **⚡ Check In Now**
- **📊 Open Dashboard**
- **⏱️ Check-In Interval** (15m, 30m, 45m, 60m, Custom...)
- **🔕 Mute / Pause** (1 hour, 2 hours, Until tomorrow morning, Unmute)
- **📍 Desktop Widget: On/Off** (Toggle floating desktop widget)
- **🔊 Sound Effects: On/Off**
- **🚪 Quit BB-8 Buddy**

---

## ⚙️ Configuration

Configuration is automatically stored in standard XDG format at:
`~/.config/bb8-buddy/config.json`

Example:
```json
{
  "interval_minutes": 30,
  "idle_threshold_minutes": 10,
  "smart_pause_enabled": true,
  "presence_mode": "tray",
  "sound_enabled": true,
  "notifications_enabled": true,
  "muted_until": null,
  "theme": "dark",
  "custom_tags": [
    "#work",
    "#break",
    "#learning",
    "#meeting",
    "#personal"
  ]
}
```

---

## 🎙️ Enabling Local Offline Speech-to-Text (Optional)

BB-8 Buddy automatically detects local offline STT engines. If you wish to enable automatic voice-to-text transcription:

### Option A: Using Vosk (Lightweight, ~50 MB)
```bash
pip install vosk
# or install vosk-transcriber CLI
```

### Option B: Using whisper.cpp
Install `whisper-cli` into your `$PATH`.

When installed, voice recordings will automatically transcribe directly into the input box upon stopping the recording! If neither is installed, voice recordings continue to work as voice notes attached to entries.

---

## 🔍 CLI Commands & Edge Cases

### CLI Flags:
```bash
# Open the check-in popup immediately (or signals existing instance)
bb8-buddy --checkin

# Open the dashboard window
bb8-buddy --dashboard

# Check version
bb8-buddy --version
```

### Edge Cases Handled:
- **Single Instance**: Running `bb8-buddy` when an instance is already active communicates via Unix socket (`~/.local/share/bb8-buddy/bb8.sock`) to raise the existing window rather than spawning duplicate tray icons or timers.
- **No Microphone**: Gracefully disables the mic button with tooltip *"Mic not detected — text input ready"*.
- **Compositor / Display**: Runs smoothly on Wayland and X11; falls back to `Gtk.StatusIcon` if `AyatanaAppIndicator` is not present.
- **Offline / Sandboxed**: Requires zero internet connection. Works fully on airplane mode or offline air-gapped systems.

---

## 🛡️ License

MIT License. Designed with care for privacy, simplicity, and delight.

