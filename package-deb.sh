#!/bin/bash
set -euo pipefail

VERSION="1.0.0"
PKG_NAME="bb8-buddy"
DEB_NAME="${PKG_NAME}_${VERSION}_all.deb"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build/deb"
DIST_DIR="${SCRIPT_DIR}/dist"

echo "Building Debian package: ${DEB_NAME}..."

rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/lib/bb8-buddy"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${DIST_DIR}"

# Copy control file
cat > "${BUILD_DIR}/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: Google DeepMind <noreply@google.com>
Depends: python3 (>= 3.8), python3-gi, python3-cairo, gir1.2-gtk-3.0, gir1.2-webkit2-4.1, gir1.2-ayatanaappindicator3-0.1 | gir1.2-appindicator3-0.1, gir1.2-notify-0.7
Recommends: alsa-utils, libnotify-bin, xprintidle, sqlite3
Description: Lightweight, friendly, local-first Linux desktop companion
 BB-8 Buddy is a tiny, persistent desktop companion that gently
 checks in with the user every 30 minutes. All data stays local.
EOF
chmod 755 "${BUILD_DIR}/DEBIAN"
chmod 644 "${BUILD_DIR}/DEBIAN/control"

# Copy postinst script
cat > "${BUILD_DIR}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database -q /usr/share/applications || true
fi
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 755 "${BUILD_DIR}/DEBIAN/postinst"

# Install application files into /usr/lib/bb8-buddy
cp -r "${SCRIPT_DIR}/bb8_buddy" "${BUILD_DIR}/usr/lib/bb8-buddy/"
cp -r "${SCRIPT_DIR}/ui" "${BUILD_DIR}/usr/lib/bb8-buddy/"
cp -r "${SCRIPT_DIR}/assets" "${BUILD_DIR}/usr/lib/bb8-buddy/"

# Create /usr/bin/bb8-buddy launcher
cat > "${BUILD_DIR}/usr/bin/bb8-buddy" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/lib/bb8-buddy/bb8_buddy/app.py "$@"
EOF
# Also support running via module or bin/bb8-buddy wrapper
cat > "${BUILD_DIR}/usr/bin/bb8-buddy" <<'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/lib/bb8-buddy")
from bb8_buddy.app import BB8App
from pathlib import Path

if __name__ == "__main__":
    action = None
    if "--checkin" in sys.argv:
        action = "checkin"
    elif "--dashboard" in sys.argv:
        action = "dashboard"
    app = BB8App(root_dir=Path("/usr/lib/bb8-buddy"))
    sys.exit(app.start(initial_action=action))
EOF
chmod 755 "${BUILD_DIR}/usr/bin/bb8-buddy"

# Install desktop file & icons
cp "${SCRIPT_DIR}/assets/bb8-buddy.desktop" "${BUILD_DIR}/usr/share/applications/"
cp "${SCRIPT_DIR}/assets/icons/bb8-buddy.svg" "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/"

for size in 16 24 32 48 64 128; do
    if [ -f "${SCRIPT_DIR}/assets/icons/bb8-buddy-${size}.png" ]; then
        mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/${size}x${size}/apps"
        cp "${SCRIPT_DIR}/assets/icons/bb8-buddy-${size}.png" "${BUILD_DIR}/usr/share/icons/hicolor/${size}x${size}/apps/bb8-buddy.png"
    fi
done

# Build debian package
dpkg-deb --build --root-owner-group "${BUILD_DIR}" "${DIST_DIR}/${DEB_NAME}"

echo "Successfully built Debian package: ${DIST_DIR}/${DEB_NAME}"
ls -lh "${DIST_DIR}/${DEB_NAME}"
