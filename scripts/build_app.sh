#!/bin/bash
set -e

# Sotto Build Script
echo "🏗️  Building Sotto.app..."

# 1. Cleaning up
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# 2. Installing dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# 3. Building App
echo "🔨 Running PyInstaller..."
pyinstaller Sotto.spec

# 4. Finalizing
if [ -d "dist/Sotto.app" ]; then
    echo "✅ Build successful!"
    echo "📍 App location: dist/Sotto.app"
    echo ""
    echo "To run:"
    echo "open dist/Sotto.app"
else
    echo "❌ Build failed - Sotto.app not found."
    exit 1
fi
