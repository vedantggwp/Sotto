"""
Sotto - Voice Control for macOS
Your personal voice butler for hands-free Mac control.

Copyright (c) 2026 Ved
MIT License
"""

__version__ = "0.1.0"
__author__ = "Ved"
__description__ = "Voice control and dictation for macOS with near-zero latency"

from .config import SottoConfig, get_config
from .core import AudioEngine, Transcriber, CommandParser, CommandExecutor

__all__ = [
    'SottoConfig',
    'get_config',
    'AudioEngine',
    'Transcriber',
    'CommandParser',
    'CommandExecutor',
]
