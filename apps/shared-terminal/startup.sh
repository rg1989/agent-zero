#!/bin/bash

# Shared Terminal Startup Script — ttyd + persistent tmux session
set -e

TERM_PORT=${PORT:-9004}

echo "Starting Shared Terminal on port $TERM_PORT..."

# Kill any stale ttyd on this port
pkill -f "ttyd" 2>/dev/null || true
fuser -k ${TERM_PORT}/tcp 2>/dev/null || true
sleep 1

# Pre-create the shared tmux session so the AI can inject commands via
# tmux send-keys even before a browser connects. The -d flag detaches
# immediately; the || true suppresses the "session already exists" error.
tmux new-session -d -s shared 2>/dev/null || true

echo "Starting ttyd on port $TERM_PORT..."
# ttyd forks tmux new-session -A -s shared for every new browser connection.
# The -A flag means "attach if the session already exists, create if not" so
# every browser tab and the AI all share the same live shell.
exec ttyd \
    --port "$TERM_PORT" \
    --interface 127.0.0.1 \
    --writable \
    tmux new-session -A -s shared
