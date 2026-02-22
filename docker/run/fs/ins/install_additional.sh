#!/bin/bash
set -e

# install playwright - moved to install A0
# bash /ins/install_playwright.sh "$@"

# searxng - moved to base image
# bash /ins/install_searxng.sh "$@"

# ── Shared Browser system dependencies ────────────────────────────────────
# These are currently in the base image, but we pin them here so our image
# never silently loses them if the base image changes.
echo "Installing shared-browser system dependencies..."
apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    websockify \
    chromium
apt-get clean
rm -rf /var/lib/apt/lists/*
echo "Shared-browser system dependencies installed."

# ── Shared Browser: bake noVNC into the image ──────────────────────────────
# This clone ends up at /git/agent-zero/apps/shared-browser/static/noVNC.
# startup.sh copies from here on first run so no internet access is needed.
NOVNC_TARGET="/git/agent-zero/apps/shared-browser/static/noVNC"
if [ ! -f "$NOVNC_TARGET/core/rfb.js" ]; then
    echo "Installing noVNC into shared-browser..."
    mkdir -p "$(dirname "$NOVNC_TARGET")"
    git clone --depth=1 https://github.com/novnc/noVNC "$NOVNC_TARGET"
    # Remove git metadata — we only need the source files
    rm -rf "$NOVNC_TARGET/.git"
    echo "noVNC installed."
fi