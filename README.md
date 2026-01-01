# 🎙️ Sotto - Voice Control for macOS

**Near-zero latency voice control and dictation for macOS using local Whisper AI.**

Sotto lets you control your Mac and type anywhere using your voice. All processing happens locally on your Mac - no cloud required, no data sent anywhere.

## ✨ Features

- **🚀 Low Latency** - Local Whisper AI processing with Metal GPU acceleration
- **🎤 Push-to-Talk** - Hold hotkey, speak, release to transcribe
- **⚡ Smart Commands** - Say "open Safari", "volume up", "copy", etc.
- **📝 Dictation** - Speak and text appears at your cursor
- **🔒 Privacy First** - 100% local, no internet required
- **🎨 macOS Native** - Menubar app with overlay feedback

## 🚀 Quick Start

```bash
cd /Users/ved/Documents/Projects/Sotto
source venv/bin/activate
python -m sotto.main --cli
```

**Default hotkey:** Hold `Cmd+Shift+Space` and speak, release to transcribe.

## 📁 Project Structure

```
Sotto/
├── sotto/                    # Main package
│   ├── __init__.py          # Package exports
│   ├── main.py              # Main application entry point
│   ├── config.py            # Configuration management
│   │
│   ├── core/                # Core functionality
│   │   ├── audio.py         # Microphone capture (sounddevice)
│   │   ├── transcriber.py   # Whisper speech-to-text
│   │   ├── command_parser.py# Intent detection & parsing  
│   │   └── executor.py      # Command execution (keyboard, AppleScript)
│   │
│   ├── commands/            # Command definitions
│   │   └── registry.py      # Voice command registry
│   │
│   └── ui/                  # User interface
│       ├── menubar.py       # macOS menubar app (rumps)
│       └── overlay.py       # Floating feedback window
│
├── scripts/
│   ├── download_model.py    # Download Whisper models
│   └── install.sh           # Setup script
│
├── requirements.txt         # Python dependencies
├── setup.py                # Package setup
└── README.md               # This file
```

## 📦 Components Explained

### `main.py` - Application Core
The heart of Sotto. Coordinates all components:
- Initializes audio, transcriber, parser, executor
- Manages global hotkey listeners (pynput)
- Handles push-to-talk and always-listening modes
- Routes transcriptions to commands or dictation

### `core/audio.py` - Audio Engine
Low-latency microphone capture:
- Uses `sounddevice` for real-time audio capture
- 16kHz sample rate (Whisper's preferred format)
- Threaded recording with callback-based capture
- Voice Activity Detection (VAD) for silence detection

### `core/transcriber.py` - Speech Recognition
Whisper-powered transcription:
- Uses `faster-whisper` (CTranslate2) for speed
- Supports multiple models: tiny, base, small, medium
- Metal GPU acceleration on Apple Silicon
- Returns text with confidence score

### `core/command_parser.py` - Intent Detection
Smart command vs dictation detection:
- Pattern matching for voice commands
- Command prefix detection ("open", "close", "volume", etc.)
- Falls back to dictation for regular speech
- Returns structured intent with parsed arguments

### `core/executor.py` - Command Execution
Executes parsed commands:
- Keyboard simulation via `pynput`
- System control via AppleScript
- Text typing for dictation
- Supports 30+ built-in commands

### `ui/overlay.py` - Visual Feedback
Floating feedback window:
- Shows "Listening...", "Processing...", results
- Native macOS window (PyObjC)
- Falls back to terminal output if unavailable

### `ui/menubar.py` - Menu Bar App
System tray integration:
- Quick access to start/stop listening
- Mode switching (push-to-talk / always listening)
- Status indicator

### `config.py` - Configuration
User settings management:
- Hotkey configuration
- Model selection
- Feedback preferences
- Stored in `~/.sotto/config.yaml`

## 🎤 Voice Commands

### App Control
- "open Safari" / "open Notes" / "open [app]"
- "close window" / "quit Safari"
- "switch to Finder"

### System
- "volume up" / "volume down" / "mute"
- "screenshot"
- "lock screen"

### Text Editing
- "copy" / "paste" / "cut"
- "undo" / "redo"
- "select all"
- "delete that" (deletes last dictation)
- "new line" / "new paragraph"

### Navigation
- "scroll up" / "scroll down"
- "go back" / "go forward"
- "new tab" / "close tab"

### Search
- "search [query]" - Spotlight search
- "google [query]" - Google search

## ⚙️ Configuration

Config file: `~/.sotto/config.yaml`

```yaml
mode: push_to_talk  # or always_listening

hotkeys:
  push_to_talk: "<cmd>+<shift>+<space>"
  toggle_listening: "<cmd>+<shift>+l"

transcription:
  model: base.en    # tiny.en, base.en, small.en, medium.en
  language: en
  device: auto      # auto, cpu, cuda

feedback:
  overlay_enabled: true
  sound_enabled: true
```

## 🔧 Troubleshooting

### Hotkey not working
- Grant Terminal/VS Code **Accessibility** permission
- System Preferences → Privacy & Security → Accessibility

### Microphone not recording
- Grant Terminal **Microphone** permission  
- System Preferences → Privacy & Security → Microphone

### Low transcription quality
- Use a better model: `python -m sotto.main --cli --model small.en`
- Speak clearly and not too fast
- Reduce background noise

## 🛠️ Development

### Run in debug mode
```bash
python -m sotto.main --cli
```

### Run with menubar
```bash
python -m sotto.main
```

### Download a different model
```bash
python scripts/download_model.py small.en
```

## 📄 License

MIT License - Feel free to use and modify.

## 🙏 Credits

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized inference
- [pynput](https://github.com/moses-palmer/pynput) - Keyboard/mouse control
- [sounddevice](https://github.com/spatialaudio/python-sounddevice) - Audio capture
