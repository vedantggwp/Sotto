# Changelog

All notable changes to Sotto will be documented in this file.

## [0.2.0-beta] - 2025-01-02

### Added
- **GUI Mode**: Full menubar application with system tray icon
- **HUD Overlay**: Native macOS floating overlay showing transcription results and command feedback
- **Settings Window**: Configure mode, hotkey, model, and overlay preferences
- **Volume Control**: "volume up", "volume down", "mute", "unmute", and "volume 50" (percentage)
- **Brightness Control**: "brightness up", "brightness down"
- **App Control**: "open [app]", "quit [app]", "switch to [app]"
- **Text Editing**: "copy", "paste", "undo", "redo", "delete that", "select all"
- **Navigation**: "scroll up/down", "page up/down", "new tab", "close tab"
- **Search**: "google [query]", "search [query]", "find [text]"
- **Screenshot**: "screenshot" command
- **Accessibility Check**: Automatic detection and guidance for required permissions
- **Command List**: View all available commands from menubar

### Changed
- Default model switched to `small.en` for better accuracy
- Improved command parser to handle trailing punctuation from Whisper
- Better error messages and success notifications for executed commands
- Cleaner terminal output with less debug noise

### Fixed
- Config file corruption with Python-specific YAML tags
- HUD overlay import error (removed unused Quartz import)
- Menubar icon now displays correctly
- Overlay now uses dark appearance for better text visibility

## [0.1.0] - 2024-12-XX

### Added
- Initial release
- Local speech-to-text using Whisper AI
- Push-to-talk mode with configurable hotkey (Cmd+Shift+Space)
- Always-listening mode with voice activity detection
- Basic command recognition and execution
- Dictation mode for typing spoken text
- Configuration via ~/.sotto/config.yaml

---

## Roadmap

### Planned for v0.3.0
- [ ] Custom command editor in Settings UI
- [ ] Voice command history
- [ ] Command suggestions/autocomplete
- [ ] Support for more Whisper models
- [ ] Audio input device selection
- [ ] Improved transcription accuracy options

### Future
- [ ] Plugin system for custom integrations
- [ ] Shortcuts app integration
- [ ] AppleScript command support
- [ ] Multi-language support
