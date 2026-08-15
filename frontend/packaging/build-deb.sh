#!/usr/bin/env bash
# Build a single-file binary with PyInstaller, then wrap it in a .deb with fpm.
set -euo pipefail

VERSION="${VERSION:-1.0.0}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND="$(dirname "$HERE")"
ROOT="$(dirname "$FRONTEND")"
STAGE="$ROOT/build/stage"

rm -rf "$ROOT/build" "$ROOT/dist"
mkdir -p "$STAGE/usr/bin" "$STAGE/usr/share/applications"

pyinstaller \
    --onefile \
    --name vpn-manager \
    --paths "$FRONTEND" \
    --hidden-import tkinter \
    --hidden-import requests \
    --distpath "$ROOT/dist" \
    --workpath "$ROOT/build/pyi" \
    --specpath "$ROOT/build" \
    "$FRONTEND/app.py"

install -m 0755 "$ROOT/dist/vpn-manager" "$STAGE/usr/bin/vpn-manager"

cat > "$STAGE/usr/share/applications/vpn-manager.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=VPN Access Manager
Comment=Manage VPN gateway sessions
Exec=/usr/bin/vpn-manager
Terminal=false
Categories=Network;
DESKTOP

cd "$ROOT"
rm -f "vpn-manager_${VERSION}_amd64.deb"

fpm -s dir -t deb \
    -n vpn-manager \
    -v "$VERSION" \
    -a amd64 \
    --description "Desktop client for the VPN Access Manager" \
    --maintainer "Rayen <rayenbhr31@gmail.com>" \
    --license MIT \
    --depends libxcb1 \
    --depends libx11-6 \
    --depends libxau6 \
    --depends libxdmcp6 \
    -C "$STAGE" \
    -p "vpn-manager_${VERSION}_amd64.deb" \
    usr

echo "built: vpn-manager_${VERSION}_amd64.deb"
