# Sotto UI Rebuild: Tauri v2 Native Experience

## Reference Implementation: VoiceTypr (github.com/moinulmoin/voicetypr)

Production Superwhisper clone, 334 stars, Tauri v2. This is the proven architecture.

## VoiceTypr's Architecture (what works)

```
Tauri v2 App
├── Main window (800x600, hidden by default, skipTaskbar: true)
│   └── React + Tailwind + shadcn/ui settings panel
├── Pill window (80x40, created dynamically, transparent, always-on-top)
│   └── RecordingPill component (3 audio-reactive dots via framer-motion)
├── Rust backend
│   ├── window_manager.rs — creates/positions pill + main windows
│   ├── state_machine.rs — recording states
│   ├── audio/ — capture
│   └── whisper/ — transcription
└── parakeet-swift sidecar — Apple speech recognition
```

### Key UI Details from VoiceTypr Source

- **RecordingPill**: 4 states (idle → listening → transcribing → formatting)
- **AudioDots**: 3 white dots, center-weighted sensitivity, vertical stretch on audio level
- **Pill positioning**: configurable (top-left/center/right, bottom-left/center/right) with edge offset
- **Pill window**: transparent bg, no decorations, always on top, 80x40px
- **Settings**: full React app with sidebar nav, shadcn/ui components, Geist font
- **Animation**: framer-motion for pill state transitions and dot animations

## Sotto's Approach: Python Engine + Tauri v2 UI Shell

```
┌─────────────────────────────────────────────────┐
│  Tauri v2 App Shell                              │
│                                                   │
│  ┌─────────────┐    ┌──────────────────────┐    │
│  │ Pill Window  │    │  Settings Window      │    │
│  │ (transparent │    │  (React + Tailwind    │    │
│  │  80x40px)    │    │   + shadcn/ui)        │    │
│  │ AudioDots    │    │  Geist font           │    │
│  │ framer-motion│    │  Warm amber palette   │    │
│  └──────────────┘    └──────────────────────┘    │
│                                                   │
│  Rust layer: window management, IPC, tray icon   │
│       │                                           │
│       │  Unix socket / stdin-stdout pipe           │
│       ▼                                           │
│  ┌──────────────────────────────────────────┐    │
│  │  Python Engine (sidecar via PyInstaller)  │    │
│  │  audio.py → transcriber.py → parser →     │    │
│  │  executor.py                              │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### IPC: Tauri ↔ Python Engine

Option A: **Sidecar** — bundle Python as PyInstaller binary, Tauri spawns it, communicate via stdin/stdout JSON
Option B: **Unix domain socket** — Python runs as background process, Tauri connects

VoiceTypr uses sidecar approach with `parakeet-swift`. Same pattern works for Python.

## Design Language: Warm Amber (not cold blue)

| Element | Value |
|---------|-------|
| Accent | `#f59e0b` (amber-500) |
| Recording dot | `#dc6843` (warm terracotta) |
| Success | `#22c55e` (green-500) |
| Background | Warm charcoal `#1a1714` |
| Text | `rgba(255,255,255,0.9)` |
| Dot color | White `rgba(255,255,255,0.95)` |
| Font | Geist (settings), SF Pro (pill) |
| Vibrancy | NSVisualEffectView via window-vibrancy crate |

## Execution Phases

### Phase 1: Tauri v2 Scaffold + Pill Window
1. `pnpm create tauri-app@latest sotto-ui --template react-ts`
2. Configure tauri.conf.json: main window hidden, skipTaskbar, no dock icon
3. Build pill window via Rust window_manager (transparent, borderless, always-on-top)
4. Implement RecordingPill + AudioDots components (port from VoiceTypr patterns)
5. Tray icon with dropdown menu (replaces rumps)

### Phase 2: Python Sidecar Integration
1. Bundle Python engine as PyInstaller single binary
2. Tauri spawns sidecar, communicates via JSON stdin/stdout
3. Events: start_recording, stop_recording, audio_level, transcription_result
4. State machine in Rust mirrors Python state

### Phase 3: Settings Window + Polish
1. Full settings panel in React + shadcn/ui
2. Hotkey configuration, model selection, mode toggle
3. NSVisualEffectView vibrancy via window-vibrancy crate
4. Auto-update via tauri-plugin-updater
5. DMG packaging

## Files to Keep from Current Codebase

All of `sotto/core/` (audio, transcriber, command_parser, executor, hotkeys) — the engine is solid.
`sotto/config.py` — config management.
`sotto/utils/` — logging, permissions.

## Files to Replace

`sotto/ui/` (entire directory) — replaced by Tauri + React
`sotto/main.py` — coordinator logic moves to sidecar entry point
`sotto/ui/menubar.py` — replaced by Tauri tray
`sotto/ui/notch.py` — replaced by pill window
`sotto/ui/settings.py` — replaced by React settings

## Dependencies to Add

- `@anthropic-ai/sdk` — NOT needed (local only)
- `tauri-plugin-positioner` — pill window positioning
- `window-vibrancy` — NSVisualEffectView
- `framer-motion` — pill animations
- `@radix-ui/react-*` via shadcn/ui — settings components
- Geist font
