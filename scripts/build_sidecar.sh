#!/usr/bin/env bash
# Build the Python sidecar as a standalone binary for Tauri
set -euo pipefail
cd "$(dirname "$0")/.."

source venv/bin/activate

# Build single-file binary
pyinstaller \
  --name sotto-engine \
  --onefile \
  --noconfirm \
  --clean \
  --hidden-import=faster_whisper \
  --hidden-import=sounddevice \
  --hidden-import=pynput \
  --hidden-import=numpy \
  --hidden-import=pydantic \
  --hidden-import=pydantic_settings \
  --hidden-import=yaml \
  sotto/sidecar.py

# Copy to Tauri sidecar location
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  TARGET="aarch64-apple-darwin"
elif [ "$ARCH" = "x86_64" ]; then
  TARGET="x86_64-apple-darwin"
else
  echo "Unsupported architecture: $ARCH"
  exit 1
fi

mkdir -p sotto-ui/src-tauri/binaries
cp dist/sotto-engine "sotto-ui/src-tauri/binaries/sotto-engine-${TARGET}"
echo "Sidecar built: sotto-ui/src-tauri/binaries/sotto-engine-${TARGET}"
