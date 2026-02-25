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

# ── Shared Terminal system dependencies ───────────────────────────────────
echo "Installing shared-terminal system dependencies..."
apt-get update
apt-get install -y --no-install-recommends tmux
apt-get clean
rm -rf /var/lib/apt/lists/*

# ttyd is not in Kali repos on all architectures — download the pre-built binary
# from GitHub releases instead.  Supports x86_64, aarch64 (Apple/AWS ARM), and armv7.
ARCH=$(uname -m)
case "$ARCH" in
  x86_64)  TTYD_ARCH="x86_64" ;;
  aarch64) TTYD_ARCH="aarch64" ;;
  armv7l)  TTYD_ARCH="arm" ;;
  *)       TTYD_ARCH="x86_64"; echo "Warning: unknown arch $ARCH, falling back to x86_64 ttyd" ;;
esac
echo "Downloading ttyd for $TTYD_ARCH..."
curl -fsSL -o /usr/local/bin/ttyd \
    "https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.${TTYD_ARCH}"
chmod +x /usr/local/bin/ttyd
echo "Shared-terminal system dependencies installed (ttyd $(ttyd --version 2>&1 || echo '?'))."

# ── OpenCode CLI ──────────────────────────────────────────────────────────
echo "Installing OpenCode CLI..."
curl -fsSL https://opencode.ai/install | bash
echo 'export PATH=/root/.opencode/bin:$PATH' >> /root/.bashrc
echo "OpenCode installed ($(/root/.opencode/bin/opencode --version 2>&1 || echo 'version unknown'))."

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