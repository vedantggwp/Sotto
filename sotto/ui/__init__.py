"""
Sotto UI Module
User interface components including menubar (CLI fallback).
Overlay and settings have moved to the Tauri UI layer.
"""

from .menubar import SottoMenubar

__all__ = ["SottoMenubar"]
