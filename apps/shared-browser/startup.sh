#!/bin/bash

# Shared Browser Startup Script
set -e

APP_DIR="/a0/apps/shared-browser"
SCREEN_WIDTH=1280
SCREEN_HEIGHT=720
VNC_PORT=5900
WEBSOCKIFY_PORT=6081
FLASK_PORT=${PORT:-9003}
APP_NAME="shared-browser"

echo "🚀 Starting Shared Browser on port $FLASK_PORT..."

# Kill any existing processes from a previous run
pkill -f "Xvfb :99" 2>/dev/null || true
pkill -f "x11vnc.*:99" 2>/dev/null || true
pkill -f "websockify.*${WEBSOCKIFY_PORT}" 2>/dev/null || true
sleep 1

# Install noVNC if not present (first run only)
NOVNC_DIR="$APP_DIR/static/noVNC"
if [ ! -f "$NOVNC_DIR/core/rfb.js" ]; then
    echo "📥 Installing noVNC..."
    mkdir -p "$APP_DIR/static"
    # Try copying from image-baked location first (no internet needed)
    if [ -f "/git/agent-zero/apps/shared-browser/static/noVNC/core/rfb.js" ]; then
        cp -r /git/agent-zero/apps/shared-browser/static/noVNC "$NOVNC_DIR"
        echo "✓ noVNC copied from image"
    else
        git clone --depth=1 https://github.com/novnc/noVNC "$NOVNC_DIR"
        echo "✓ noVNC cloned from GitHub"
    fi
fi

export DISPLAY=:99

# 1. Virtual display
echo "📺 Starting Xvfb..."
Xvfb :99 -screen 0 ${SCREEN_WIDTH}x${SCREEN_HEIGHT}x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!
sleep 2

# 2. VNC server
echo "🖥️  Starting x11vnc..."
x11vnc -display :99 -forever -shared -rfbport $VNC_PORT -nopw -quiet &
X11VNC_PID=$!
sleep 2

# 3. Chromium
echo "🌐 Starting Chromium..."
DISPLAY=:99 chromium \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --no-first-run \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --start-maximized \
    --window-size=${SCREEN_WIDTH},${SCREEN_HEIGHT} \
    --remote-debugging-port=9222 \
    --remote-allow-origins=* \
    about:blank &
CHROMIUM_PID=$!
sleep 3

# 4. WebSocket bridge
echo "🔌 Starting websockify..."
websockify ${WEBSOCKIFY_PORT} localhost:${VNC_PORT} &
WEBSOCKIFY_PID=$!
sleep 1

echo "✅ All services started"
echo "   Xvfb:       PID $XVFB_PID"
echo "   x11vnc:     PID $X11VNC_PID"
echo "   Chromium:   PID $CHROMIUM_PID"
echo "   websockify: PID $WEBSOCKIFY_PID (port $WEBSOCKIFY_PORT)"

# 5. Flask (blocking — keeps the process alive)
echo "🐍 Starting Flask on port $FLASK_PORT..."
cd "$APP_DIR"
exec python app.py
