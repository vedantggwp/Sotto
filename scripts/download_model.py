#!/usr/bin/env python3
"""
Sotto Model Downloader
Downloads the Whisper model for offline use.
"""

import argparse
import sys
from pathlib import Path


def download_model(model_name: str = "base.en"):
    """
    Download a Whisper model.

    Args:
        model_name: Name of the model to download
    """
    print(f"📦 Downloading Whisper model: {model_name}")
    print("This may take a few minutes depending on your internet connection...\n")

    try:
        from faster_whisper import WhisperModel

        # Download directory
        download_dir = Path.home() / ".sotto" / "models"
        download_dir.mkdir(parents=True, exist_ok=True)

        print(f"📁 Download location: {download_dir}")
        print("⏳ Loading model (this triggers download)...\n")

        # Loading the model will trigger download if not present
        WhisperModel(
            model_name, device="cpu", compute_type="int8", download_root=str(download_dir)
        )

        print(f"\n✅ Model '{model_name}' downloaded successfully!")
        print(f"📍 Location: {download_dir}")

        # Show model info
        print("\n📊 Model Info:")
        print(f"  • Name: {model_name}")
        print("  • Ready for use!")

        return True

    except ImportError:
        print("❌ Error: faster-whisper is not installed.")
        print("Run: pip install faster-whisper")
        return False
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        return False


def list_models():
    """List available models"""
    models = {
        "tiny.en": ("~75MB", "Fastest, English only, lower accuracy"),
        "tiny": ("~75MB", "Fastest, multilingual, lower accuracy"),
        "base.en": ("~150MB", "Good balance, English only (recommended)"),
        "base": ("~150MB", "Good balance, multilingual"),
        "small.en": ("~500MB", "Better accuracy, English only"),
        "small": ("~500MB", "Better accuracy, multilingual"),
        "medium.en": ("~1.5GB", "High accuracy, English only"),
        "medium": ("~1.5GB", "High accuracy, multilingual"),
        "large-v3": ("~3GB", "Best accuracy, multilingual"),
    }

    print("\n📋 Available Whisper Models:\n")
    print(f"{'Model':<15} {'Size':<10} {'Description'}")
    print("-" * 60)

    for name, (size, desc) in models.items():
        print(f"{name:<15} {size:<10} {desc}")

    print("\n💡 Recommendation:")
    print("  • For English: 'base.en' (best speed/accuracy balance)")
    print("  • For other languages: 'base' or 'small'")
    print("  • For maximum accuracy: 'medium.en' or 'large-v3'")


def main():
    parser = argparse.ArgumentParser(description="Download Whisper models for Sotto")
    parser.add_argument(
        "model", nargs="?", default="base.en", help="Model name to download (default: base.en)"
    )
    parser.add_argument("--list", "-l", action="store_true", help="List available models")

    args = parser.parse_args()

    if args.list:
        list_models()
        return 0

    success = download_model(args.model)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
