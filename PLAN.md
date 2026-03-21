# Sotto Rebuild Plan

## Expert Consensus

Two independent reviews (AI systems architect + production systems engineer) reached identical conclusions:

1. **The Python core pipeline is solid** — audio → Whisper → regex parser → executor is architecturally correct
2. **The web UI layer is wrong** — sotto-ui/ (React + Tauri + GSAP), server.py (FastAPI + WebSocket) solve a problem that doesn't exist
3. **The app is a menubar utility** — comparable to Superwhisper, Wispr Flow, CleanShot X, Raycast

## What to Keep

| File | Status | Notes |
|------|--------|-------|
| `sotto/core/audio.py` | Keep + fix | Add threading lock, fix bare `except:` |
| `sotto/core/transcriber.py` | Keep | Lazy loading, beam_size=1, correct |
| `sotto/core/command_parser.py` | Keep | Pre-compiled regex, sub-ms parsing |
| `sotto/core/executor.py` | Keep + fix | **CRITICAL: Fix AppleScript injection** |
| `sotto/core/hotkeys.py` | Keep | PTT + toggle modes work |
| `sotto/config.py` | Keep + fix | Fix mutable singleton, clean_data smell |
| `sotto/main.py` | Keep + fix | Add locks for `_is_listening`, serialize `_process_audio` |
| `sotto/ui/menubar.py` | Keep | rumps works correctly |
| `sotto/ui/notch.py` | Keep + fix | Fix window level, animation timing, bare except |
| `sotto/ui/overlay.py` | Keep + simplify | Remove redundant overlay classes |
| `sotto/utils/logging.py` | Keep | Rotating file logger, correct |
| `sotto/utils/permissions.py` | Keep | macOS permission checks |

## What to Delete

| Path | Reason |
|------|--------|
| `sotto-ui/` (entire directory) | Wrong architecture. React dashboard for a menubar utility. |
| `sotto/server.py` | FastAPI bridge exists only for the web UI. No web UI = no server. |
| `sotto/server_main.py` | Entry point for deleted server. |
| `sotto/ui/commands_window.py` | Dead code, hardcoded mock data, crashes at runtime (not NSObject). |
| `sotto/commands/registry.py` | Disconnected from parser. Duplicate definitions. Dead code. |
| `SOTTO-UI-PLAN.md` | Plan for the wrong architecture. |
| `landing/index.html` | Marketing page, separate concern. |

## The Correct Architecture

```
                    ┌──────────────────────────────┐
                    │       macOS Menubar           │
                    │   ┌──────────────────────┐   │
                    │   │   rumps.App (icon)    │   │
                    │   │   Start/Stop, Mode,   │   │
                    │   │   Model, Settings,    │   │
                    │   │   Quit                │   │
                    │   └──────────┬───────────┘   │
                    └──────────────┼───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │        Sotto Engine           │
                    │                               │
                    │   Hotkey ──→ AudioEngine      │
                    │              ──→ Transcriber  │
                    │              ──→ Parser       │
                    │              ──→ Executor     │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼───────────────┐
                    │   NotchHUD (PyObjC overlay)   │
                    │   "Listening..." → "Done ✅"  │
                    └──────────────────────────────┘

                    ┌─────────────────────────────┐
                    │  Settings (PyObjC NSWindow)  │
                    │  Mode, Hotkey, Model, Save   │
                    └─────────────────────────────┘
```

One process. No HTTP. No WebSocket. No React. No Tauri. Ships as `.app` via PyInstaller.

## Execution Phases

### Wave 1: Security + Threading Fixes (ship immediately)
1. Fix AppleScript injection in `executor.py` — sanitize all interpolated strings
2. Add `threading.Lock` to `AudioEngine` protecting `_is_recording` / `_audio_buffer`
3. Add lock/queue around `_process_audio` in `main.py` to prevent concurrent keyboard sim
4. Fix `_is_listening` race condition with proper lock
5. Fix all bare `except:` → `except Exception:`

### Wave 2: Delete + Simplify
1. Delete `sotto-ui/` directory
2. Delete `server.py`, `server_main.py`
3. Delete `commands_window.py`, `commands/registry.py`
4. Delete `SOTTO-UI-PLAN.md`, `landing/`
5. Simplify `overlay.py` — remove `HUDOverlay` and `NotificationOverlay`, keep `SimpleOverlay` as fallback
6. Fix `notch.py` — window level to `NSFloatingWindowLevel + 1`, proper spring timing

### Wave 3: Settings Window + Polish
1. Rebuild `settings.py` — proper `NSObject` subclass OR WKWebView with single HTML file
2. Wire `menubar.py` → `set_listening` state updates
3. Clean up `config.py` — fix `clean_data` smell, document PyObjC string handling
4. PyInstaller `.app` bundle test
