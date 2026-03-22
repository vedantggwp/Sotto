# Sotto End-to-End Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Python voice engine to the Tauri v2 UI shell so Sotto is a fully working macOS voice control app — press hotkey, see waveform animate with real audio, get transcription typed at cursor.

**Architecture:** Tauri v2 spawns the Python engine as a sidecar binary (PyInstaller). They communicate via stdin/stdout JSON messages. The Rust layer relays events between the sidecar and React frontends. The Python engine handles audio capture, Whisper transcription, and keyboard execution. The React pill shows real-time audio levels and state transitions.

**Tech Stack:** Tauri v2 (Rust), React 19 + TypeScript, Python 3.11 (faster-whisper, sounddevice, pynput), PyInstaller, Vite, Tailwind v4

---

## File Structure

### New files to create
| File | Responsibility |
|------|---------------|
| `sotto/sidecar.py` | Sidecar entry point — stdin/stdout JSON protocol, dispatches to engine |
| `sotto/protocol.py` | Message types and JSON serialization for IPC |
| `sotto-ui/src/lib/store.ts` | Zustand store for app state (recording state, audio level, config) |
| `sotto-ui/src-tauri/src/sidecar.rs` | Rust module: spawn sidecar, read stdout, write stdin, relay events |
| `tests/test_protocol.py` | Tests for the JSON protocol |
| `tests/test_sidecar.py` | Tests for sidecar entry point |
| `scripts/build_sidecar.sh` | PyInstaller build script for the sidecar binary |

### Existing files to modify
| File | Change |
|------|--------|
| `sotto-ui/src-tauri/src/lib.rs` | Import sidecar module, spawn on setup, relay events |
| `sotto-ui/src-tauri/Cargo.toml` | Add serde_json for message parsing |
| `sotto-ui/src/pill/Pill.tsx` | Remove demo simulation, consume real engine events |
| `sotto-ui/src/pill/AudioDots.tsx` | No changes needed (already RAF-based) |
| `sotto-ui/src/settings/Settings.tsx` | Wire dropdowns to invoke commands that write config |
| `sotto-ui/src/lib/engine.ts` | Already has event listener structure — just needs real events |
| `sotto-ui/src-tauri/tauri.conf.json` | Add sidecar binary path to shell scope |
| `sotto/main.py` | Extract engine logic into a reusable class (sidecar imports it) |
| `pyproject.toml` | Add sidecar entry point |

---

## Phase 1: JSON Protocol + Sidecar Entry Point

### Task 1: Define the IPC Protocol

**Files:**
- Create: `sotto/protocol.py`
- Create: `tests/test_protocol.py`

- [ ] **Step 1: Write failing test for protocol messages**

```python
# tests/test_protocol.py
import json
from sotto.protocol import (
    StateChangeMsg, AudioLevelMsg, TranscriptionMsg,
    CommandMsg, encode_message, decode_command
)

def test_state_change_encodes_to_json():
    msg = StateChangeMsg(state="listening")
    line = encode_message(msg)
    parsed = json.loads(line)
    assert parsed["type"] == "state_change"
    assert parsed["state"] == "listening"

def test_audio_level_encodes():
    msg = AudioLevelMsg(level=0.73)
    line = encode_message(msg)
    parsed = json.loads(line)
    assert parsed["type"] == "audio_level"
    assert parsed["level"] == 0.73

def test_transcription_encodes():
    msg = TranscriptionMsg(text="hello world")
    line = encode_message(msg)
    parsed = json.loads(line)
    assert parsed["type"] == "transcription"
    assert parsed["text"] == "hello world"

def test_decode_start_command():
    line = json.dumps({"command": "start_recording"})
    cmd = decode_command(line)
    assert cmd.command == "start_recording"

def test_decode_set_config():
    line = json.dumps({"command": "set_config", "key": "model", "value": "small.en"})
    cmd = decode_command(line)
    assert cmd.command == "set_config"
    assert cmd.key == "model"
    assert cmd.value == "small.en"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ved/Terminal-Sotto/Sotto && source venv/bin/activate && pytest tests/test_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sotto.protocol'`

- [ ] **Step 3: Implement protocol.py**

```python
# sotto/protocol.py
"""JSON protocol for Tauri <-> Python sidecar communication."""
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional

# Engine -> Tauri (stdout)
@dataclass(frozen=True)
class StateChangeMsg:
    state: str  # idle, listening, transcribing, formatting, done
    type: str = "state_change"

@dataclass(frozen=True)
class AudioLevelMsg:
    level: float  # 0.0 - 1.0
    type: str = "audio_level"

@dataclass(frozen=True)
class TranscriptionMsg:
    text: str
    type: str = "transcription"

@dataclass(frozen=True)
class ErrorMsg:
    error: str
    type: str = "error"

# Tauri -> Engine (stdin)
@dataclass(frozen=True)
class CommandMsg:
    command: str  # start_recording, stop_recording, set_config, get_config, quit
    key: Optional[str] = None
    value: Optional[str] = None

def encode_message(msg) -> str:
    """Encode a message dataclass to a JSON line."""
    return json.dumps(asdict(msg))

def decode_command(line: str) -> CommandMsg:
    """Decode a JSON line into a CommandMsg."""
    data = json.loads(line.strip())
    return CommandMsg(
        command=data["command"],
        key=data.get("key"),
        value=data.get("value"),
    )

def send(msg) -> None:
    """Write a message to stdout (toward Tauri)."""
    sys.stdout.write(encode_message(msg) + "\n")
    sys.stdout.flush()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocol.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add sotto/protocol.py tests/test_protocol.py
git commit -m "feat: JSON IPC protocol for Tauri-Python sidecar communication"
```

---

### Task 2: Sidecar Entry Point

**Files:**
- Create: `sotto/sidecar.py`
- Create: `tests/test_sidecar.py`

- [ ] **Step 1: Write failing test for sidecar message loop**

```python
# tests/test_sidecar.py
import json
import io
from unittest.mock import patch, MagicMock
from sotto.sidecar import handle_command

def test_handle_start_recording():
    engine = MagicMock()
    engine.audio.is_recording.return_value = False
    result = handle_command(engine, "start_recording")
    engine.audio.start_recording.assert_called_once()
    assert result == "listening"

def test_handle_stop_recording():
    engine = MagicMock()
    import numpy as np
    engine.audio.stop_recording.return_value = np.zeros(16000, dtype=np.float32)
    engine.transcriber.transcribe.return_value = "hello"
    result = handle_command(engine, "stop_recording")
    engine.audio.stop_recording.assert_called_once()
    assert result == "done"

def test_handle_quit():
    engine = MagicMock()
    result = handle_command(engine, "quit")
    assert result == "quit"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sidecar.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement sidecar.py**

```python
# sotto/sidecar.py
"""Sidecar entry point for Tauri IPC."""
import sys
import threading
import numpy as np
from .config import ensure_directories, get_config
from .core.audio import AudioEngine
from .core.transcriber import Transcriber
from .core.command_parser import CommandParser, IntentType
from .core.executor import CommandExecutor
from .protocol import (
    StateChangeMsg, AudioLevelMsg, TranscriptionMsg, ErrorMsg,
    decode_command, send,
)

class SidecarEngine:
    """Minimal engine for sidecar mode — no UI, no hotkeys."""

    def __init__(self):
        ensure_directories()
        self.config = get_config()
        self.audio = AudioEngine()
        self.transcriber = Transcriber(
            model_name=self.config.transcription.model,
            device=self.config.transcription.device,
            compute_type=self.config.transcription.compute_type,
        )
        self.parser = CommandParser()
        self.executor = CommandExecutor()
        self._audio_level_thread = None

    def preload(self):
        """Load Whisper model eagerly."""
        self.transcriber.load_model()
        send(StateChangeMsg(state="idle"))

def handle_command(engine, command: str, key=None, value=None) -> str:
    """Handle a single command. Returns the resulting state."""
    if command == "start_recording":
        if not engine.audio.is_recording():
            engine.audio.start_recording(on_audio=_on_audio_chunk)
        return "listening"

    elif command == "stop_recording":
        audio = engine.audio.stop_recording()
        if len(audio) < 1600:  # Less than 0.1s
            return "idle"
        send(StateChangeMsg(state="transcribing"))
        text = engine.transcriber.transcribe(audio)
        if text and text.strip():
            send(TranscriptionMsg(text=text))
            intent = engine.parser.parse(text)
            if intent.type == IntentType.DICTATION:
                engine.executor.type_text(intent.text)
            else:
                engine.executor.execute(intent)
        return "done"

    elif command == "set_config":
        if key == "model":
            engine.config.transcription.model = value
        return "idle"

    elif command == "quit":
        return "quit"

    return "idle"

def _on_audio_chunk(chunk: np.ndarray):
    """Callback: compute RMS level and send to Tauri."""
    rms = float(np.sqrt(np.mean(chunk ** 2)))
    level = min(1.0, rms / 0.1)  # Normalize: 0.1 RMS = full scale
    send(AudioLevelMsg(level=level))

def main():
    """Main sidecar loop: read stdin commands, write stdout events."""
    engine = SidecarEngine()
    engine.preload()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            cmd = decode_command(line)
            state = handle_command(engine, cmd.command, cmd.key, cmd.value)
            send(StateChangeMsg(state=state))
            if state == "quit":
                break
        except Exception as e:
            send(ErrorMsg(error=str(e)))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_sidecar.py -v`
Expected: All 3 PASS

- [ ] **Step 5: Commit**

```bash
git add sotto/sidecar.py tests/test_sidecar.py
git commit -m "feat: sidecar entry point for Tauri IPC"
```

---

## Phase 2: PyInstaller Binary

### Task 3: Build Sidecar Binary

**Files:**
- Create: `scripts/build_sidecar.sh`
- Modify: `pyproject.toml` (add script entry point)

- [ ] **Step 1: Add entry point to pyproject.toml**

Add under `[project.scripts]`:
```toml
sotto-sidecar = "sotto.sidecar:main"
```

- [ ] **Step 2: Create build script**

```bash
#!/usr/bin/env bash
# scripts/build_sidecar.sh
set -euo pipefail
cd "$(dirname "$0")/.."

source venv/bin/activate

# Build single-file binary
pyinstaller \
  --name sotto-engine \
  --onefile \
  --noconfirm \
  --clean \
  --hidden-import=faster_whisper \
  --hidden-import=sounddevice \
  --hidden-import=pynput \
  sotto/sidecar.py

# Copy to Tauri sidecar location
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  TARGET="aarch64-apple-darwin"
elif [ "$ARCH" = "x86_64" ]; then
  TARGET="x86_64-apple-darwin"
fi

mkdir -p sotto-ui/src-tauri/binaries
cp dist/sotto-engine "sotto-ui/src-tauri/binaries/sotto-engine-${TARGET}"
echo "Sidecar built: sotto-ui/src-tauri/binaries/sotto-engine-${TARGET}"
```

- [ ] **Step 3: Run the build**

Run: `chmod +x scripts/build_sidecar.sh && bash scripts/build_sidecar.sh`
Expected: Binary at `sotto-ui/src-tauri/binaries/sotto-engine-aarch64-apple-darwin`

- [ ] **Step 4: Test the binary manually**

Run: `echo '{"command":"quit"}' | ./dist/sotto-engine`
Expected: JSON output with `{"type":"state_change","state":"idle"}` then exits

- [ ] **Step 5: Commit**

```bash
git add scripts/build_sidecar.sh pyproject.toml
git commit -m "feat: PyInstaller sidecar build script"
```

---

## Phase 3: Rust Sidecar Spawning

### Task 4: Wire Rust to Spawn and Communicate with Sidecar

**Files:**
- Create: `sotto-ui/src-tauri/src/sidecar.rs`
- Modify: `sotto-ui/src-tauri/src/lib.rs`
- Modify: `sotto-ui/src-tauri/tauri.conf.json`

- [ ] **Step 1: Update tauri.conf.json shell plugin scope**

Replace the plugins section:
```json
"plugins": {
  "shell": {
    "open": true,
    "sidecar": true,
    "scope": [
      {
        "name": "binaries/sotto-engine",
        "sidecar": true,
        "args": true
      }
    ]
  }
}
```

- [ ] **Step 2: Create sidecar.rs**

```rust
// sotto-ui/src-tauri/src/sidecar.rs
use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;
use std::sync::Mutex;

pub struct SidecarState {
    stdin_writer: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
}

impl SidecarState {
    pub fn new() -> Self {
        Self {
            stdin_writer: Mutex::new(None),
        }
    }
}

pub fn spawn_sidecar(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let sidecar_command = app.shell().sidecar("binaries/sotto-engine")?;
    let (mut rx, child) = sidecar_command.spawn()?;

    // Store child for stdin writing
    app.state::<SidecarState>().stdin_writer.lock().unwrap().replace(child);

    // Read stdout in background, emit events to frontend
    let app_handle = app.clone();
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    if let Ok(msg) = serde_json::from_str::<serde_json::Value>(&line_str) {
                        let _ = app_handle.emit("sotto://engine", &msg);
                    }
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[sidecar stderr] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Terminated(_) => {
                    eprintln!("[sidecar] process terminated");
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(())
}

pub fn send_to_sidecar(state: &SidecarState, msg: &str) -> Result<(), String> {
    let mut guard = state.stdin_writer.lock().map_err(|e| e.to_string())?;
    if let Some(child) = guard.as_mut() {
        child.write((msg.to_string() + "\n").as_bytes())
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

- [ ] **Step 3: Update lib.rs to spawn sidecar and add commands**

Add `mod sidecar;` at top. In setup(), call `sidecar::spawn_sidecar`. Add Tauri commands:
```rust
#[tauri::command]
fn engine_command(state: tauri::State<'_, sidecar::SidecarState>, command: String) -> Result<(), String> {
    let msg = serde_json::json!({"command": command}).to_string();
    sidecar::send_to_sidecar(&state, &msg)
}
```

Register `SidecarState` with `app.manage(sidecar::SidecarState::new())`.

- [ ] **Step 4: Build and test**

Run: `source ~/.cargo/env && cd sotto-ui && pnpm tauri build`
Expected: Compiles clean

- [ ] **Step 5: Commit**

```bash
git add sotto-ui/src-tauri/src/sidecar.rs sotto-ui/src-tauri/src/lib.rs sotto-ui/src-tauri/tauri.conf.json
git commit -m "feat: Rust sidecar spawning with stdin/stdout IPC"
```

---

## Phase 4: Wire Frontend to Real Engine

### Task 5: Remove Demo Simulation, Connect Real Events

**Files:**
- Modify: `sotto-ui/src/pill/Pill.tsx`
- Modify: `sotto-ui/src/lib/engine.ts`

- [ ] **Step 1: Update Pill.tsx — remove demo simulation**

Remove the `useEffect` that simulates audio levels (the `Math.sin` one).
Remove the click-to-cycle-states `useEffect`.
Keep the engine connection `useEffect` — it already listens to `sotto://engine` events.
Set initial state to `"idle"` instead of `"listening"`.

- [ ] **Step 2: Update engine.ts — add command sending**

```typescript
import { invoke } from "@tauri-apps/api/core";

export async function sendCommand(command: string) {
  await invoke("engine_command", { command });
}
```

- [ ] **Step 3: Wire global shortcuts to engine commands**

In lib.rs, change the Cmd+Shift+S handler to send `start_recording`/`stop_recording` to the sidecar instead of toggling pill visibility. The pill visibility is now driven by state change events from the engine.

- [ ] **Step 4: Build and test end-to-end**

Run: `pnpm tauri build`
Launch app. Press Cmd+Shift+S. Speak. Watch pill animate with real audio. See text appear at cursor.

- [ ] **Step 5: Commit**

```bash
git add sotto-ui/src/pill/Pill.tsx sotto-ui/src/lib/engine.ts sotto-ui/src-tauri/src/lib.rs
git commit -m "feat: wire frontend to real Python engine via sidecar IPC"
```

---

## Phase 5: Settings Persistence

### Task 6: Wire Settings to Config

**Files:**
- Modify: `sotto-ui/src/settings/Settings.tsx`
- Modify: `sotto-ui/src-tauri/src/lib.rs`

- [ ] **Step 1: Add Tauri commands for config read/write**

```rust
#[tauri::command]
fn get_config() -> Result<serde_json::Value, String> {
    // Read ~/.sotto/config.yaml and return as JSON
}

#[tauri::command]
fn set_config(key: String, value: String, state: tauri::State<'_, sidecar::SidecarState>) -> Result<(), String> {
    // Write to ~/.sotto/config.yaml AND send set_config to sidecar
    let msg = serde_json::json!({"command": "set_config", "key": key, "value": value}).to_string();
    sidecar::send_to_sidecar(&state, &msg)
}
```

- [ ] **Step 2: Wire Settings dropdowns to invoke set_config**

Each `<Select>` onChange calls `invoke("set_config", { key: "model", value: selected })`.

- [ ] **Step 3: Load config on settings mount**

`useEffect` calls `invoke("get_config")` and populates dropdown values.

- [ ] **Step 4: Test — change model in settings, verify sidecar receives it**

- [ ] **Step 5: Commit**

```bash
git add sotto-ui/src/settings/Settings.tsx sotto-ui/src-tauri/src/lib.rs
git commit -m "feat: settings persistence via config.yaml + sidecar sync"
```

---

## Phase 6: Polish

### Task 7: App Icon + Pill Positioning

**Files:**
- Replace: `sotto-ui/src-tauri/icons/*`
- Modify: `sotto-ui/src-tauri/src/lib.rs` (pill position from config)

- [ ] **Step 1: Design proper app icon** — amber circle with sound wave motif, export to all required sizes (16, 32, 64, 128, 256, 512, icns, ico)

- [ ] **Step 2: Implement pill positioning** — read position from config, use tauri-plugin-positioner or manual window.set_position() to place pill at configured location

- [ ] **Step 3: Commit**

### Task 8: Error Handling + Edge Cases

- [ ] **Step 1: Handle sidecar crash** — detect terminated event, show error state on pill (red border), attempt restart
- [ ] **Step 2: Handle no microphone permission** — detect from sidecar, show system prompt
- [ ] **Step 3: Handle Whisper model not downloaded** — detect, show download progress
- [ ] **Step 4: Commit**

### Task 9: Remove Legacy PyObjC UI

**Files:**
- Delete: `sotto/ui/notch.py`
- Delete: `sotto/ui/overlay.py`
- Delete: `sotto/ui/settings.py`
- Keep: `sotto/ui/menubar.py` (fallback for CLI-only mode)

- [ ] **Step 1: Delete old UI files, update imports**
- [ ] **Step 2: Verify CLI mode still works: `python -m sotto.main --cli`**
- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove legacy PyObjC UI layer, replaced by Tauri"
```

---

## Critical Path Summary

```
Task 1 (protocol) ──→ Task 2 (sidecar.py) ──→ Task 3 (PyInstaller) ──→ Task 4 (Rust wire) ──→ Task 5 (frontend) ──→ WORKING DEMO
                                                                                                                        │
                                                                                              Task 6 (settings) ───────┘
                                                                                              Task 7 (polish) ──────────┘
                                                                                              Task 8 (errors) ──────────┘
                                                                                              Task 9 (cleanup) ─────────┘
```

Tasks 1-5 are sequential (each depends on the previous). Tasks 6-9 are independent and can be parallelized after Task 5.

**Estimated effort:** Tasks 1-5 = one session. Tasks 6-9 = one session. Total: 2 sessions to fully working app.
