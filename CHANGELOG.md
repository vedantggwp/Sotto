# Changelog

All notable changes to Sotto are documented in this file.

## [0.1.0] - 2026-01-01

### 🎉 Initial Release

First working version of Sotto - voice control for macOS.

### Added

#### Core Features
- **Push-to-Talk Mode**: Hold `Cmd+Shift+Space`, speak, release to transcribe
- **Always-Listening Mode**: Continuous voice detection with auto-transcription
- **Local Whisper AI**: Speech recognition using faster-whisper (no cloud)
- **Smart Command Detection**: Automatically distinguishes commands from dictation

#### Audio System (`core/audio.py`)
- Low-latency microphone capture using sounddevice
- 16kHz sample rate optimized for Whisper
- Threaded recording with callback-based architecture
- Voice Activity Detection (VAD) for silence detection
- Debug logging for troubleshooting

#### Transcription (`core/transcriber.py`)
- faster-whisper integration for optimized inference
- Metal GPU acceleration on Apple Silicon
- Model selection: tiny.en, base.en, small.en, medium.en
- Confidence score reporting

#### Command Parser (`core/command_parser.py`)
- Pattern-based command recognition
- Supported command categories:
  - App control (open, close, switch, quit)
  - System (volume, screenshot, lock screen)
  - Text editing (copy, paste, undo, select all)
  - Navigation (scroll, page up/down, back/forward)
  - Tabs (new tab, close tab, switch tab)
  - Search (spotlight, google)
  - Dictation (fallback for non-commands)

#### Command Executor (`core/executor.py`)
- Keyboard simulation via pynput
- AppleScript integration for system commands
- 30+ built-in commands
- "Delete that" to remove last dictation

#### User Interface
- **Menubar App** (`ui/menubar.py`): System tray integration with rumps
- **Overlay Window** (`ui/overlay.py`): Floating feedback using PyObjC
- Terminal fallback when GUI unavailable

#### Configuration (`config.py`)
- YAML-based configuration at `~/.sotto/config.yaml`
- Customizable hotkeys
- Model selection
- Feedback preferences

### Fixed

#### Debugging Session (Jan 1, 2026)
- Fixed overlay error: `kCGWindowLevelFloating` not found in newer PyObjC
- Added `_init_failed` flag to prevent repeated initialization attempts
- Reduced verbose console output
- Added duplicate message prevention in overlay
- Added debug logging throughout audio pipeline
- Fixed push-to-talk hotkey detection

### Technical Details

#### Dependencies
- `faster-whisper`: Optimized Whisper inference
- `sounddevice`: Cross-platform audio capture
- `pynput`: Global hotkey and keyboard control
- `numpy`: Audio processing
- `rumps`: macOS menubar app
- `PyObjC`: Native macOS APIs

#### Performance
- Model load time: ~0.5s (base.en)
- Transcription time: <1s for typical utterances
- Memory usage: ~500MB with base.en model

### Known Issues
- Overlay window not showing (PyObjC compatibility) - falls back to terminal
- Key repeat spam in debug output when holding hotkey
- Requires manual permission grants (Accessibility, Microphone)

### Future Plans
- [ ] Package as standalone .app bundle
- [ ] Fix native overlay window
- [ ] Add custom command configuration
- [ ] Reduce debug output in release mode
- [ ] Add wake word detection
- [ ] Support for more languages

---

## Development Notes

### File Changes Summary

| File | Purpose | Status |
|------|---------|--------|
| `sotto/main.py` | Main app coordinator | ✅ Working |
| `sotto/config.py` | Configuration management | ✅ Working |
| `sotto/core/audio.py` | Microphone capture | ✅ Working (with debug) |
| `sotto/core/transcriber.py` | Whisper transcription | ✅ Working |
| `sotto/core/command_parser.py` | Intent detection | ✅ Working |
| `sotto/core/executor.py` | Command execution | ✅ Working |
| `sotto/ui/overlay.py` | Feedback overlay | ⚠️ Fallback to terminal |
| `sotto/ui/menubar.py` | Menubar app | ✅ Working |

### Debug Output Added
The following debug prints were added during troubleshooting:
- `[Main] _start_recording called`
- `[Main] Calling audio.start_recording...`
- `[Audio] Starting recording...`
- `[Audio] Starting input stream...`
- `[Audio] Stopping... buffer has X chunks`
- `[Process] Starting transcription of X samples...`
- `[Process] Result: '...' (conf=X.XX)`
- `Key: <key>` for hotkey debugging

These can be removed for production use.
