#!/bin/bash

# Shared Browser Startup Script — Playwright/CDP native (no VNC stack)
set -e

APP_DIR="/a0/apps/shared-browser"
FLASK_PORT=${PORT:-9003}

echo "Starting Shared Browser on port $FLASK_PORT..."

# Kill any existing processes (also cleans up legacy VNC stack if migrating)
pkill -f "Xvfb :99" 2>/dev/null || true
pkill -f "x11vnc.*:99" 2>/dev/null || true
pkill -f "websockify" 2>/dev/null || true
pkill -f "chromium.*remote-debugging-port=9222" 2>/dev/null || true
# Kill any stale Flask on port 9003 so the new process can bind.
# Use pkill by exact command (reliable) then fuser as fallback.
pkill -f "/opt/venv-a0/bin/python app.py" 2>/dev/null || true
fuser -k 9003/tcp 2>/dev/null || true
sleep 1

# Start Chromium in headless mode with CDP on port 9222.
# Viewport width matches the 420px drawer — websites render their native
# mobile/responsive layout instead of being scaled down from 1920px.
echo "Starting Chromium..."
chromium \
    --headless=new \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --no-first-run \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --window-size=420,800 \
    --remote-debugging-port=9222 \
    --remote-allow-origins=* \
    https://www.google.com &
CHROMIUM_PID=$!
sleep 2

echo "All services started"
echo "   Chromium:  PID $CHROMIUM_PID (CDP on :9222)"

# Flask (blocking — keeps the process alive)
# Use the venv Python so playwright is available for CDP screenshots
echo "Starting Flask on port $FLASK_PORT..."
cd "$APP_DIR"
exec /opt/venv-a0/bin/python app.py
