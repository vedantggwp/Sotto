# Sotto

**Local voice control for macOS.** Push-to-talk dictation and 30+ system commands, powered by Whisper AI running entirely on-device.

No cloud. No latency. No data leaves your Mac.

<p align="center">
  <img src="assets/demo.gif" alt="Sotto demo — hold hotkey, speak, text appears" width="700" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple" />
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/whisper-faster--whisper-FF6F00?style=flat-square" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
</p>

---

## How It Works

Hold a hotkey. Speak. Release. Sotto transcribes your speech locally using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2), classifies the intent with sub-millisecond regex parsing, and either types the text at your cursor or executes a system command.

The entire pipeline runs in a single process with no network calls.

```
Microphone → Audio Engine (16kHz) → Whisper AI → Intent Parser → Executor
                                                                    ↓
                                                          Keyboard / AppleScript
```

## Features

- **Push-to-talk and always-listening modes** with configurable hotkeys
- **30+ voice commands**: app control, volume, brightness, clipboard, tabs, search
- **Dictation**: speak naturally, text appears at your cursor
- **Dynamic Island HUD**: native macOS overlay shows transcription feedback
- **Menubar app**: lives in the system tray, no Dock icon
- **Metal GPU acceleration** on Apple Silicon via CTranslate2
- **Multiple Whisper models**: tiny, base, small, medium, large-v3

## Quick Start

```bash
git clone https://github.com/vedantggwp/Sotto.git
cd Sotto
python -m venv venv
source venv/bin/activate
pip install -e .

# Menubar app
sotto

# CLI mode
sotto --cli
```

**Default hotkey:** `Cmd+Shift+Space` (hold to record, release to transcribe)

### macOS Permissions

Sotto requires two permissions in **System Settings > Privacy & Security**:

| Permission | Why |
|-----------|-----|
| Accessibility | Global hotkey capture + keyboard simulation |
| Microphone | Audio recording |

## Architecture

```
sotto/
├── main.py                  # Application coordinator + state machine
├── config.py                # Pydantic config + YAML persistence (~/.sotto/)
│
├── core/
│   ├── audio.py             # Threaded mic capture (sounddevice, 16kHz/512 blocks)
│   ├── transcriber.py       # faster-whisper with lazy model loading
│   ├── command_parser.py    # Compiled regex intent classifier
│   ├── executor.py          # pynput keyboard sim + AppleScript system control
│   └── hotkeys.py           # Global hotkey listener (PTT + toggle modes)
│
├── ui/
│   ├── menubar.py           # rumps menubar integration
│   ├── notch.py             # Dynamic Island-style HUD overlay (PyObjC)
│   ├── overlay.py           # Overlay factory with terminal fallback
│   └── settings.py          # Native preferences window (PyObjC)
│
└── utils/
    ├── logging.py           # Rotating file logger
    └── permissions.py       # macOS permission checks
```

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| `faster-whisper` over `openai-whisper` | 4x faster inference, lower memory, CTranslate2 backend |
| Regex parsing over ML classifier | Sub-millisecond, deterministic, no model loading overhead |
| `pynput` for keyboard simulation | Cross-app text injection without clipboard pollution |
| `rumps` for menubar | Native NSStatusItem with minimal code |
| PyObjC for HUD overlay | Real `NSWindow` with continuous corner curves, spring animations |
| Single process, no server | Menubar utilities don't need HTTP/WebSocket infrastructure |

## Voice Commands

### App Control
```
"open Safari"          "quit Slack"           "switch to Finder"
```

### System
```
"volume up/down"       "mute" / "unmute"      "volume 50"
"brightness up/down"   "screenshot"           "lock screen"
```

### Text Editing
```
"copy" / "paste" / "cut"    "undo" / "redo"       "select all"
"delete that"               "new line"            "new paragraph"
```

### Navigation
```
"scroll up/down"       "go back/forward"      "new tab" / "close tab"
```

### Search
```
"search [query]"       → Spotlight
"google [query]"       → Default browser
```

## Configuration

Config: `~/.sotto/config.yaml` | Logs: `~/.sotto/logs/sotto.log`

```yaml
mode: push_to_talk

hotkeys:
  push_to_talk: "<cmd>+<shift>+<space>"
  toggle_listening: "<cmd>+<shift>+l"

transcription:
  model: small.en
  language: en
  device: auto

feedback:
  overlay_enabled: true
  sound_enabled: true
```

## Development

```bash
source venv/bin/activate
sotto --cli --debug          # CLI with debug output
sotto --model small.en       # Specific model
pytest tests/                # Run tests
ruff check .                 # Lint
```

### Adding Commands

1. Add a regex pattern to `COMMAND_PATTERNS` in `core/command_parser.py`
2. Add a handler method to `CommandExecutor._handlers` in `core/executor.py`

## Tech Stack

| Component | Library |
|-----------|---------|
| Speech-to-text | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) |
| Audio capture | [sounddevice](https://github.com/spatialaudio/python-sounddevice) (PortAudio) |
| Keyboard control | [pynput](https://github.com/moses-palmer/pynput) |
| Menubar | [rumps](https://github.com/jaredks/rumps) |
| Native UI | [PyObjC](https://github.com/ronaldoussoren/pyobjc) |
| Config | [Pydantic](https://github.com/pydantic/pydantic) + YAML |

## Troubleshooting

**Hotkey not responding:** Grant your terminal Accessibility permission, then restart Sotto.

**No audio captured:** Grant Microphone permission. If already granted, remove and re-add the permission entry.

**Low accuracy:** Use a larger model (`--model small.en` or `--model medium.en`). Reduce background noise.

**Permission still failing after granting:** Remove the app from the permission list, re-add it, then restart.

## License

MIT
