#!/usr/bin/env bash
# One-command setup for Sotto development
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Sotto Setup ==="

# Check prerequisites
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.11+"
    exit 1
fi
if ! command -v pnpm &>/dev/null; then
    echo "ERROR: pnpm not found. Install: npm install -g pnpm"
    exit 1
fi
if ! command -v cargo &>/dev/null; then
    echo "ERROR: cargo not found. Install: https://rustup.rs"
    exit 1
fi

# Check portaudio (macOS)
if [[ "$(uname)" == "Darwin" ]] && ! brew list portaudio &>/dev/null 2>&1; then
    echo "Installing portaudio (required by sounddevice)..."
    brew install portaudio
fi

# Python environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]" --quiet

# Build sidecar binary
echo "Building sidecar binary (this takes a few minutes)..."
bash scripts/build_sidecar.sh

# Frontend dependencies
echo "Installing frontend dependencies..."
cd sotto-ui
pnpm install --frozen-lockfile 2>/dev/null || pnpm install

echo ""
echo "=== Setup complete! ==="
echo "Run: cd sotto-ui && pnpm tauri dev"
