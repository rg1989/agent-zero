#!/bin/bash
set -e

# Paths
SOURCE_DIR="/git/agent-zero"
TARGET_DIR="/a0"

# Copy repository files from image to /a0, updating files newer in the image.
# Bind mounts declared in docker-compose.yml (webui/, apps/, python/, prompts/)
# shadow the copied files at runtime — this ensures non-mounted paths (e.g.,
# run_ui.py, requirements.txt) are always up to date from the image.
echo "Syncing files from $SOURCE_DIR to $TARGET_DIR (update-newer)..."
cp -ru --no-preserve=ownership,mode "$SOURCE_DIR/." "$TARGET_DIR"
