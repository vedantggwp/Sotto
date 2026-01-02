# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sotto is a macOS voice control and dictation application. It uses local Whisper AI for speech-to-text with a push-to-talk interface. All processing happens locally on the Mac - no cloud services required.

## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run in CLI mode (push-to-talk)
python -m sotto.main --cli

# Run with menubar GUI
python -m sotto.main

# Run with a specific Whisper model
python -m sotto.main --cli --model small.en

# Run with debug output
python -m sotto.main --cli --debug

# Download Whisper models
python scripts/download_model.py base.en

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -e ".[dev]"

# Build standalone .app bundle
pip install pyinstaller
pyinstaller Sotto.spec
# Output: dist/Sotto.app
```

## Architecture

### Data Flow

1. **Audio capture** (`core/audio.py`): `sounddevice` captures 16kHz mono audio via callbacks into a queue
2. **Transcription** (`core/transcriber.py`): `faster-whisper` converts audio to text using Metal GPU acceleration
3. **Intent parsing** (`core/command_parser.py`): Regex patterns classify text as COMMAND, CONTROL, or DICTATION
4. **Execution** (`core/executor.py`): Commands use `pynput` for keyboard simulation and `osascript` for AppleScript

### Main Coordinator

`sotto/main.py` contains the `Sotto` class which:
- Manages the push-to-talk state machine (key press starts recording, release stops and processes)
- Runs always-listening mode with VAD (Voice Activity Detection) for silence detection
- Routes parsed intents to the executor or types dictation text

### Key Classes

- `AudioEngine`: Threaded microphone capture with 512-sample blocks (~32ms latency)
- `VoiceActivityDetector`: Energy-based speech detection with silence timeout
- `Transcriber`: Wrapper around faster-whisper with lazy model loading
- `CommandParser`: Pattern-based intent classification (see `COMMAND_PATTERNS` list)
- `CommandExecutor`: Maps command names to handler methods via `_handlers` dict

### UI Layer

- `ui/overlay.py`: Floating feedback window (tkinter preferred, PyObjC fallback, terminal last resort)
- `ui/menubar.py`: System tray app using `rumps`

### Configuration

User config stored in `~/.sotto/config.yaml`. Managed by Pydantic models in `config.py`.

## Adding New Voice Commands

1. Add regex pattern to `COMMAND_PATTERNS` in `core/command_parser.py`
2. Add handler method to `CommandExecutor._handlers` dict in `core/executor.py`
3. Handler receives extracted args from the regex match

## macOS Permissions Required

The app requires these permissions in System Preferences > Privacy & Security:
- **Accessibility**: For global hotkey listening and keyboard simulation
- **Microphone**: For audio capture
