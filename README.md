# 🎙️ Sotto

> *Your personal voice butler for macOS*

**Sotto** (*Italian for "under" - as in "sotto voce", speaking softly*) is a lightweight, near-zero latency voice control and dictation app for macOS. Control your Mac with your voice, dictate text, and execute commands - all processed locally for maximum privacy and speed.

![macOS](https://img.shields.io/badge/macOS-000000?style=flat&logo=apple&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## ✨ Features

- 🚀 **Near-Zero Latency** - Local Whisper inference with Metal acceleration on Apple Silicon
- 🔒 **100% Private** - All processing happens on your Mac, nothing sent to the cloud
- 🎤 **Push-to-Talk & Always Listening** - Choose your preferred input mode
- ⚡ **Smart Command Detection** - Automatically distinguishes commands from dictation
- 🖥️ **Native macOS Integration** - Menubar app with system-level keyboard control
- 📝 **Voice Dictation** - Type anywhere using your voice
- 🎛️ **Customizable Hotkeys** - Configure your own keyboard shortcuts
- 🪟 **Visual Feedback** - Floating overlay shows what Sotto heard

---

## 🎬 Demo

```
You: "Open Safari"           → Safari launches
You: "Hello world"           → Types "Hello world" at cursor
You: "Volume down"           → System volume decreases  
You: "Search for weather"    → Opens Spotlight with "weather"
You: "Delete that"           → Removes last dictated text
```

---

## 📋 Requirements

- **macOS** 12.0+ (Monterey or later)
- **Apple Silicon** (M1/M2/M3/M4) - Recommended for best performance
- **Python** 3.9+
- **Microphone access**
- **Accessibility permissions** (for keyboard control)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/sotto.git
cd sotto
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Download the Whisper model

```bash
python scripts/download_model.py base.en
```

### 5. Run Sotto

```bash
python -m sotto.main
```

Or in CLI mode (no menubar):
```bash
python -m sotto.main --cli
```

---

## 🗣️ Voice Commands

### System Commands
| Say | Action |
|-----|--------|
| "Volume up/down" | Adjust volume |
| "Mute/Unmute" | Toggle mute |
| "Brightness up/down" | Adjust brightness |
| "Screenshot" | Take a screenshot |
| "Lock screen" | Lock your Mac |

### App Commands
| Say | Action |
|-----|--------|
| "Open [app name]" | Launch an application |
| "Quit [app name]" | Close an application |
| "Switch to [app name]" | Activate an application |
| "Close window" | Close current window |
| "New tab" / "Close tab" | Tab management |

### Text Editing
| Say | Action |
|-----|--------|
| "Select all" | Select all text |
| "Copy" / "Cut" / "Paste" | Clipboard operations |
| "Undo" / "Redo" | Undo/redo actions |
| "Delete that" | Delete last dictation |
| "New line" | Press Enter |

### Navigation
| Say | Action |
|-----|--------|
| "Scroll up/down" | Scroll the page |
| "Go back/forward" | Browser navigation |
| "Page up/down" | Large scroll |

### Search
| Say | Action |
|-----|--------|
| "Search for [query]" | Spotlight search |
| "Google [query]" | Web search |
| "Find [text]" | Find in current app |

### Sotto Control
| Say | Action |
|-----|--------|
| "Stop listening" | Pause voice input |
| "Command mode" | Switch to push-to-talk |
| "Dictation mode" | Switch to always listening |

---

## ⚙️ Configuration

Sotto stores its configuration in `~/.sotto/config.yaml`:

```yaml
mode: push_to_talk  # or "always_listening"

hotkeys:
  push_to_talk: "<cmd>+<shift>+<space>"
  toggle_listening: "<cmd>+<shift>+l"

transcription:
  model: base.en
  language: en

feedback:
  overlay_enabled: true
  overlay_duration: 2.0
```

---

## 🏗️ Architecture

```
sotto/
├── core/
│   ├── audio.py          # Low-latency audio capture
│   ├── transcriber.py    # Whisper speech-to-text
│   ├── command_parser.py # Intent classification
│   └── executor.py       # Command execution
├── commands/
│   └── registry.py       # Command definitions
├── ui/
│   ├── menubar.py        # macOS menubar app
│   └── overlay.py        # Visual feedback window
├── config.py             # Configuration management
└── main.py               # Application entry point
```

### Key Design Decisions

1. **Local Processing** - Uses `faster-whisper` with CoreML/Metal for fast inference
2. **Pattern-Based Parsing** - Regex command detection for <5ms latency (no ML classification delay)
3. **Hybrid Input Modes** - Push-to-talk for precision, always-listening for hands-free
4. **Native Integration** - PyObjC for true macOS native UI components

---

## 📊 Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| Audio capture | <20ms | ~15ms |
| Transcription | <200ms | ~100-150ms* |
| Command execution | <50ms | ~30ms |
| **Total latency** | **<300ms** | **~150-200ms** |

*On Apple Silicon with `base.en` model

---

## 🛠️ Development

### Setup development environment

```bash
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Code formatting

```bash
black sotto/
flake8 sotto/
```

---

## 🔮 Roadmap

- [ ] Native Swift app (App Store ready)
- [ ] Shortcuts.app integration
- [ ] Custom command scripting
- [ ] Multi-language support
- [ ] Voice profiles
- [ ] Wake word detection ("Hey Sotto")
- [ ] Context-aware commands

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition model
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Optimized Whisper inference
- [rumps](https://github.com/jaredks/rumps) - macOS menubar apps
- [pynput](https://github.com/moses-palmer/pynput) - Keyboard control

---

## 📄 License

MIT License - feel free to use this project however you like!

---

## 👤 Author

**Ved**

- GitHub: [@yourusername](https://github.com/yourusername)

---

<p align="center">
  Made with ❤️ for the Mac community
</p>
