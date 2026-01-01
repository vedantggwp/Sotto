#!/bin/bash
#
# Sotto Installation Script
# One-line installer for Sotto voice control
#

set -e

echo "🎙️ Installing Sotto - Voice Control for macOS"
echo "=============================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ Error: Sotto is only supported on macOS"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Error: Python 3.9+ is required (found: $PYTHON_VERSION)"
    echo "Install with: brew install python@3.11"
    exit 1
fi

echo "✓ Python $PYTHON_VERSION detected"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "📦 Upgrading pip..."
pip install --upgrade pip > /dev/null

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Download model
echo ""
echo "📦 Downloading Whisper model (base.en)..."
echo "   This may take a few minutes..."
python scripts/download_model.py base.en

# Create initial config
echo ""
echo "📝 Creating configuration..."
python -c "from sotto.config import get_config, ensure_directories; ensure_directories(); get_config().save()"

# Done!
echo ""
echo "=============================================="
echo "✅ Sotto installed successfully!"
echo "=============================================="
echo ""
echo "To get started:"
echo ""
echo "  1. Activate the environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Run Sotto:"
echo "     python -m sotto.main"
echo ""
echo "  3. Grant permissions when prompted:"
echo "     - Microphone access"
echo "     - Accessibility (System Preferences → Security)"
echo ""
echo "Default hotkey: Cmd+Shift+Space (push to talk)"
echo ""
echo "Enjoy! 🎉"
