# Sotto Hire-Ready Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all critical and high-severity issues identified in the hire-readiness audit so Sotto works end-to-end on first clone, impresses a senior engineer, and can be posted publicly.

**Architecture:** Five independent fix streams touching different file sets. Stream A fixes the broken Rust YAML config bridge using `serde_yaml`. Stream B aligns the state protocol between Python sidecar and React frontend. Stream C fixes the Settings UI. Stream D fixes Python cleanup. Stream E adds a setup script for clone-to-run.

**Tech Stack:** Rust (Tauri v2, serde_yaml), Python 3.11 (Pydantic, PyYAML), TypeScript (React 19), Shell

---

## File Structure

### Files to modify
| File | Change | Stream |
|------|--------|--------|
| `sotto-ui/src-tauri/Cargo.toml` | Add `serde_yml = "0.0.12"` | A |
| `sotto-ui/src-tauri/src/lib.rs` | Replace naive YAML parser with serde_yaml, fix defaults, reset RECORDING on crash, add debounce | A |
| `sotto-ui/src-tauri/src/sidecar.rs` | Backoff restart, fix mutex unwrap, emit RECORDING reset event | A |
| `sotto/sidecar.py` | Change `"processing"` → `"transcribing"`, add `"done"` state before `"idle"` | B |
| `sotto-ui/src/pill/Pill.tsx` | No changes needed (already checks "transcribing" and "done") | B |
| `sotto-ui/src/settings/Settings.tsx` | Fix hotkeys tab to show correct Cmd+Shift+S | C |
| `sotto/ui/menubar.py` | Guard or remove broken `from .settings import` | D |
| `pyproject.toml` | Add `[project.optional-dependencies]` dev section | D |
| `.gitignore` | Remove sidecar binaries exclusion | E |
| `README.md` | Add `portaudio` prerequisite, update setup instructions | E |

### Files to create
| File | Responsibility | Stream |
|------|---------------|--------|
| `scripts/setup.sh` | One-command setup: venv, deps, sidecar build, pnpm install | E |

---

## Stream A: Rust Config Bridge + Sidecar Resilience

### Task 1: Replace Naive YAML Parser with serde_yaml

**Files:**
- Modify: `sotto-ui/src-tauri/Cargo.toml` (add serde_yaml)
- Modify: `sotto-ui/src-tauri/src/lib.rs:47-123` (replace get_config + set_config_value)

**Context:** Python's `config.py` writes nested YAML via Pydantic:
```yaml
mode: push_to_talk
hotkeys:
  push_to_talk: "<cmd>+<shift>+s"
transcription:
  model: small.en
  language: en
  device: auto
  compute_type: int8
feedback:
  audio_enabled: true
  overlay_enabled: true
```

The current Rust parser does `split_once(':')` which flattens this, producing garbage. `set_config_value` does line-by-line prefix matching which corrupts nested keys.

- [ ] **Step 1: Add serde_yaml to Cargo.toml**

In `sotto-ui/src-tauri/Cargo.toml`, add:
```toml
serde_yml = "0.0.12"
```

- [ ] **Step 2: Replace get_config in lib.rs**

Replace lines 47-76 (the `get_config` function) with:

```rust
#[tauri::command]
fn get_config() -> Result<serde_json::Value, String> {
    let config_path = dirs::home_dir()
        .ok_or("No home directory")?
        .join(".sotto")
        .join("config.yaml");

    if !config_path.exists() {
        // Defaults MUST match Python's config.py defaults exactly
        return Ok(serde_json::json!({
            "mode": "push_to_talk",
            "hotkeys": {
                "push_to_talk": "<cmd>+<shift>+<space>",
                "toggle_listening": "<cmd>+<shift>+l",
                "cancel": "<escape>"
            },
            "transcription": {
                "model": "small.en",
                "language": "en",
                "device": "auto",
                "compute_type": "int8"
            },
            "feedback": {
                "audio_enabled": true,
                "overlay_enabled": true,
                "overlay_duration": 2.0,
                "overlay_position": "top-center"
            }
        }));
    }

    let content = std::fs::read_to_string(&config_path)
        .map_err(|e| e.to_string())?;

    let yaml_value: serde_yml::Value = serde_yml::from_str(&content)
        .map_err(|e| format!("Failed to parse config YAML: {}", e))?;

    let json_value = serde_json::to_value(&yaml_value)
        .map_err(|e| format!("Failed to convert config to JSON: {}", e))?;

    Ok(json_value)
}
```

- [ ] **Step 3: Replace set_config_value in lib.rs**

Replace lines 78-123 (the `set_config_value` function) with:

```rust
#[tauri::command]
fn set_config_value(
    state: tauri::State<'_, sidecar::SidecarState>,
    key: String,
    value: String,
) -> Result<(), String> {
    let config_dir = dirs::home_dir()
        .ok_or("No home directory")?
        .join(".sotto");
    std::fs::create_dir_all(&config_dir).map_err(|e| e.to_string())?;

    let config_path = config_dir.join("config.yaml");

    // Load existing config or start fresh
    let mut config: serde_yml::Value = if config_path.exists() {
        let content = std::fs::read_to_string(&config_path)
            .map_err(|e| e.to_string())?;
        serde_yml::from_str(&content)
            .unwrap_or(serde_yml::Value::Mapping(serde_yml::Mapping::new()))
    } else {
        serde_yml::Value::Mapping(serde_yml::Mapping::new())
    };

    // Handle dotted keys like "transcription.model" → nested update
    // Also handle flat keys like "mode" → top-level update
    let parts: Vec<&str> = key.split('.').collect();
    set_nested_yaml(&mut config, &parts, &value);

    // Write back
    let yaml_str = serde_yml::to_string(&config)
        .map_err(|e| format!("Failed to serialize config: {}", e))?;
    std::fs::write(&config_path, yaml_str)
        .map_err(|e| e.to_string())?;

    // Notify sidecar of config change
    let msg = serde_json::json!({"command": "set_config", "key": key, "value": value}).to_string();
    let _ = sidecar::send_to_sidecar(&state, &msg);

    Ok(())
}

fn set_nested_yaml(root: &mut serde_yml::Value, keys: &[&str], value: &str) {
    if keys.is_empty() {
        return;
    }

    let mapping = match root {
        serde_yml::Value::Mapping(m) => m,
        _ => {
            *root = serde_yml::Value::Mapping(serde_yml::Mapping::new());
            match root {
                serde_yml::Value::Mapping(m) => m,
                _ => unreachable!(),
            }
        }
    };

    let yaml_key = serde_yml::Value::String(keys[0].to_string());

    if keys.len() == 1 {
        // Leaf: try to parse as bool/number, fall back to string
        let yaml_value = if value == "true" {
            serde_yml::Value::Bool(true)
        } else if value == "false" {
            serde_yml::Value::Bool(false)
        } else if let Ok(n) = value.parse::<f64>() {
            serde_yml::Value::from(n)
        } else {
            serde_yml::Value::String(value.to_string())
        };
        mapping.insert(yaml_key.clone(), yaml_value);
    } else {
        // Recurse into nested mapping
        let entry = mapping
            .entry(yaml_key.clone())
            .or_insert_with(|| serde_yml::Value::Mapping(serde_yml::Mapping::new()));
        set_nested_yaml(entry, &keys[1..], value);
    }
}
```

- [ ] **Step 4: Verify Rust compiles**

Run: `cd /Users/ved/Terminal-Sotto/Sotto/sotto-ui/src-tauri && export PATH="$HOME/.cargo/bin:$PATH" && cargo check`
Expected: Clean compilation with no errors.

- [ ] **Step 5: Commit**

```bash
git add sotto-ui/src-tauri/Cargo.toml sotto-ui/src-tauri/src/lib.rs
git commit -m "fix: replace naive YAML parser with serde_yaml for nested config support"
```

---

### Task 2: Fix Sidecar Resilience (RECORDING reset, backoff, mutex safety)

**Files:**
- Modify: `sotto-ui/src-tauri/src/sidecar.rs` (all changes)
- Modify: `sotto-ui/src-tauri/src/lib.rs:125-126` (RECORDING reset)

**Problems:**
1. `sidecar.rs:25` — `.unwrap()` on mutex lock panics if poisoned
2. `sidecar.rs:51-58` — Infinite restart loop with no backoff or max retries
3. `lib.rs:126` — RECORDING AtomicBool not reset when sidecar crashes

- [ ] **Step 1: Fix mutex unwrap in sidecar.rs**

Replace line 23-27 in `sidecar.rs`:
```rust
    // Old:
    app.state::<SidecarState>()
        .stdin_writer
        .lock()
        .unwrap()
        .replace(child);
```

With:
```rust
    app.state::<SidecarState>()
        .stdin_writer
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .replace(child);
```

- [ ] **Step 2: Add restart backoff with max retries**

Replace the `CommandEvent::Terminated` block (lines 43-59) with:

```rust
                CommandEvent::Terminated(status) => {
                    eprintln!("[sidecar] terminated: {:?}", status);
                    let error = serde_json::json!({
                        "type": "state_change",
                        "state": "error"
                    });
                    let _ = app_handle.emit("sotto://engine", &error);

                    // Reset RECORDING state so hotkey isn't stuck
                    crate::RECORDING.store(false, std::sync::atomic::Ordering::SeqCst);

                    // Attempt restart with backoff (max 3 retries)
                    let restart_handle = app_handle.clone();
                    tauri::async_runtime::spawn(async move {
                        for attempt in 1..=3 {
                            let delay = std::time::Duration::from_secs(2u64.pow(attempt));
                            tokio::time::sleep(delay).await;
                            match spawn_sidecar(&restart_handle) {
                                Ok(()) => {
                                    eprintln!("[sidecar] restarted on attempt {}", attempt);
                                    return;
                                }
                                Err(e) => {
                                    eprintln!("[sidecar] restart attempt {} failed: {}", attempt, e);
                                }
                            }
                        }
                        eprintln!("[sidecar] all restart attempts failed");
                        let fatal = serde_json::json!({
                            "type": "error",
                            "error": "Engine failed to restart after 3 attempts. Please relaunch Sotto."
                        });
                        let _ = restart_handle.emit("sotto://engine", &fatal);
                    });
                    break;
                }
```

- [ ] **Step 3: Add hotkey debounce in lib.rs**

Add a static for last toggle time near the RECORDING static (around line 125):

```rust
static RECORDING: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
static LAST_TOGGLE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
```

Wrap the KeyS handler body with a debounce check:

```rust
tauri_plugin_global_shortcut::Code::KeyS => {
    // Debounce: ignore if < 300ms since last toggle
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64;
    let last = LAST_TOGGLE.load(std::sync::atomic::Ordering::SeqCst);
    if now - last < 300 {
        return; // debounce
    }
    LAST_TOGGLE.store(now, std::sync::atomic::Ordering::SeqCst);

    // ... rest of toggle logic unchanged
```

- [ ] **Step 4: Verify Rust compiles**

Run: `cd /Users/ved/Terminal-Sotto/Sotto/sotto-ui/src-tauri && export PATH="$HOME/.cargo/bin:$PATH" && cargo check`
Expected: Clean compilation.

- [ ] **Step 5: Commit**

```bash
git add sotto-ui/src-tauri/src/sidecar.rs sotto-ui/src-tauri/src/lib.rs
git commit -m "fix: sidecar resilience — backoff restart, RECORDING reset, mutex safety, debounce"
```

---

## Stream B: Protocol State Alignment

### Task 3: Align State Names Between Python and Frontend

**Files:**
- Modify: `sotto/sidecar.py:121,136` (change state strings)
- Verify: `sotto-ui/src/lib/types.ts:1` (already has correct types)
- Verify: `sotto-ui/src/pill/Pill.tsx:41` (already checks correct names)

**Problem:** Python sidecar sends `"processing"` then `"idle"` after transcription. Frontend Pill.tsx checks for `"transcribing"` and `"done"` — these never arrive. The checkmark and processing spinner are dead UI.

**Protocol alignment:**
| Python sends now | Should send | Frontend expects |
|-----------------|-------------|-----------------|
| `"processing"` | `"transcribing"` | `"transcribing"` ✓ |
| `"idle"` (after transcription) | `"done"` then `"idle"` (via frontend timeout) | `"done"` ✓ |

- [ ] **Step 1: Update sidecar.py stop_recording handler**

In `sotto/sidecar.py`, find the `stop_recording` block (around line 113-137). Change:

Line 121: `send(StateChangeMsg(state="processing"))` → `send(StateChangeMsg(state="transcribing"))`

Line 136: `send(StateChangeMsg(state="idle"))` → `send(StateChangeMsg(state="done"))`

The frontend Pill.tsx already has a timeout that resets `"done"` → `"idle"` after 1800ms. So the Python side should send `"done"` and let the frontend handle the idle transition.

- [ ] **Step 2: Update protocol.py docstring**

In `sotto/protocol.py:21`, update the state comment:
```python
state: str  # "idle" | "listening" | "transcribing" | "done" | "error"
```

- [ ] **Step 3: Fix _apply_config to handle dotted keys from Settings UI**

In `sotto/sidecar.py`, the `_apply_config` function (around line 154-161) checks `if key == "model":`. After the Settings fix (Stream C), the key will arrive as `"transcription.model"`. Update:

```python
def _apply_config(key: str, value: str, engine: SidecarEngine) -> None:
    """Apply a runtime configuration change."""
    # Handle both flat ("model") and dotted ("transcription.model") keys
    leaf_key = key.split(".")[-1] if "." in key else key
    if leaf_key == "model":
        engine.transcriber.unload_model()
        engine.transcriber.model_name = value
```

- [ ] **Step 4: Update tests to match new state names**

In `tests/test_sidecar.py`, update any assertions that check for `"processing"` state to check for `"transcribing"` instead. Update any that check for final `"idle"` to check for `"done"`.

Additionally, add a new test that verifies the state protocol output:

```python
def test_stop_recording_sends_transcribing_then_done_states(capsys):
    """Verify the exact state sequence: transcribing → transcription → done."""
    engine = _make_engine()
    engine.audio.stop_recording.return_value = np.zeros(16000, dtype=np.float32)
    engine.transcriber.transcribe.return_value = ("hello", 0.95)
    engine.parser.parse.return_value = MagicMock(
        intent_type=IntentType.DICTATION, text="hello", command_name=None, command_args=None
    )

    cmd = CommandMsg(command="stop_recording")
    handle_command(cmd, engine)

    captured = capsys.readouterr().out
    lines = [json.loads(line) for line in captured.strip().split("\n") if line.strip()]
    states = [msg["state"] for msg in lines if msg.get("type") == "state_change"]
    assert states == ["transcribing", "done"], f"Expected [transcribing, done], got {states}"
```

Run: `cd /Users/ved/Terminal-Sotto/Sotto && source venv/bin/activate && pytest tests/test_sidecar.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Run full test suite**

Run: `cd /Users/ved/Terminal-Sotto/Sotto && source venv/bin/activate && pytest tests/ -v`
Expected: All tests PASS (including new state protocol test).

- [ ] **Step 6: Verify TypeScript compiles**

Run: `cd /Users/ved/Terminal-Sotto/Sotto/sotto-ui && pnpm exec tsc --noEmit`
Expected: Clean (no changes needed — types already include "transcribing" and "done").

- [ ] **Step 7: Commit**

```bash
git add sotto/sidecar.py sotto/protocol.py tests/test_sidecar.py
git commit -m "fix: align sidecar state names with frontend — transcribing/done now sent correctly"
```

---

## Stream C: Settings UI Fixes

### Task 4: Fix Hotkeys Tab + Settings Config Keys

**Files:**
- Modify: `sotto-ui/src/settings/Settings.tsx:301-314` (hotkeys tab)
- Modify: `sotto-ui/src/settings/Settings.tsx:14-19` (default config)
- Modify: `sotto-ui/src/settings/Settings.tsx:39-43` (updateValue key mapping)

**Problems:**
1. Hotkeys tab shows `Right ⌥` and `⌥ + S` — actual hotkey is `⌘⇧S`
2. Default config `model: "base.en"` doesn't match Python default `"small.en"`
3. Settings sends flat keys like `"model"` but Python config is nested (`transcription.model`). The Rust `set_config_value` now handles dotted keys, so Settings must send `"transcription.model"` not `"model"`.

- [ ] **Step 1: Fix DEFAULT_CONFIG to match Python defaults**

Change `DEFAULT_CONFIG` (line 14-19):
```typescript
const DEFAULT_CONFIG: SottoConfig = {
  mode: "push_to_talk",
  language: "en",
  pill_position: "top-center",
  model: "small.en",
};
```

- [ ] **Step 2: Fix updateValue calls to use dotted keys**

In `GeneralTab`, change the onChange calls:
- `onChange("mode", v)` → stays `onChange("mode", v)` (top-level key)
- `onChange("language", v)` → `onChange("transcription.language", v)`
- `onChange("pill_position", v)` → `onChange("feedback.overlay_position", v)`

In `ModelTab`, change:
- `onChange("model", v)` → `onChange("transcription.model", v)`

- [ ] **Step 3: Fix useConfig to extract nested values**

Update the `useConfig` hook to flatten nested config for the UI:

```typescript
function useConfig() {
  const [config, setConfig] = useState<SottoConfig>(DEFAULT_CONFIG);

  useEffect(() => {
    invoke<Record<string, unknown>>("get_config")
      .then((remote) => {
        const transcription = (remote.transcription as Record<string, string>) || {};
        const feedback = (remote.feedback as Record<string, string>) || {};
        setConfig({
          mode: (remote.mode as string) || DEFAULT_CONFIG.mode,
          language: transcription.language || DEFAULT_CONFIG.language,
          pill_position: feedback.overlay_position || DEFAULT_CONFIG.pill_position,
          model: transcription.model || DEFAULT_CONFIG.model,
        });
      })
      .catch((err) => console.error("Failed to load config:", err));
  }, []);

  const updateValue = (key: string, value: string) => {
    // Update local state using the leaf key name
    const leafKey = key.split(".").pop() || key;
    const stateKeyMap: Record<string, keyof SottoConfig> = {
      mode: "mode",
      language: "language",
      overlay_position: "pill_position",
      model: "model",
    };
    const stateKey = stateKeyMap[leafKey];
    if (stateKey) {
      setConfig((prev) => ({ ...prev, [stateKey]: value }));
    }
    invoke("set_config_value", { key, value }).catch((err) =>
      console.error(`Failed to set ${key}:`, err),
    );
  };

  return { config, updateValue };
}
```

- [ ] **Step 4: Fix mode Select values to use underscores (matching Python)**

In the `GeneralTab` function, change the mode Select options to use underscores (matching Python's `Literal["push_to_talk", "always_listening"]` in `config.py:59`):

```typescript
<Select
  options={[
    { value: "push_to_talk", label: "Push to Talk" },
    { value: "always_listening", label: "Always Listening" },
  ]}
  value={config.mode}
  onChange={(v) => onChange("mode", v)}
/>
```

Also update `DEFAULT_CONFIG`:
```typescript
mode: "push_to_talk",  // underscore, not hyphen — matches Python config.py
```

- [ ] **Step 5: Fix hotkeys tab**

Replace the `HotkeyTab` function (lines 301-315):

```typescript
function HotkeyTab() {
  return (
    <>
      <TabHeader title="Hotkeys" />
      <Card title="Keyboard Shortcuts">
        <SettingRow label="Toggle Recording" description="Start/stop recording">
          <Kbd>⌘ ⇧ S</Kbd>
        </SettingRow>
        <SettingRow label="Open Settings" description="Open this window" isLast>
          <Kbd>⌘ ,</Kbd>
        </SettingRow>
      </Card>
      <Card>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)", lineHeight: 1.6 }}>
          Shortcuts are managed by the system and cannot be customized yet.
        </div>
      </Card>
    </>
  );
}
```

- [ ] **Step 6: Verify TypeScript compiles**

Run: `cd /Users/ved/Terminal-Sotto/Sotto/sotto-ui && pnpm exec tsc --noEmit`
Expected: Clean.

- [ ] **Step 7: Commit**

```bash
git add sotto-ui/src/settings/Settings.tsx
git commit -m "fix: settings UI — correct hotkeys, aligned config keys, matched Python defaults"
```

---

## Stream D: Python Cleanup

### Task 5: Fix Broken Menubar Import + Dev Dependencies

**Files:**
- Modify: `sotto/ui/menubar.py:155-159` (guard deleted import)
- Modify: `pyproject.toml` (add dev deps)

- [ ] **Step 1: Guard the broken settings import in menubar.py**

Replace the `_open_settings` method (around line 155-159):

```python
    def _open_settings(self, _):
        """Open settings window — only available in standalone mode, not sidecar."""
        try:
            from .settings import show_settings_window
            show_settings_window(self.config, on_save=self._on_settings_saved)
        except ImportError:
            # Settings UI has moved to Tauri frontend
            rumps.notification(
                title="Sotto",
                subtitle="Settings",
                message="Settings are available in the Tauri app window (⌘ ,)",
            )
```

- [ ] **Step 2: Add dev optional dependencies to pyproject.toml**

Add after line 28 (`sotto-sidecar = "sotto.sidecar:main"`):

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "black>=23.0",
    "pyinstaller>=6.0",
]
```

- [ ] **Step 3: Verify Python imports still work**

Run: `cd /Users/ved/Terminal-Sotto/Sotto && source venv/bin/activate && python -c "from sotto.main import Sotto; print('OK')"`
Expected: `OK`

Run: `cd /Users/ved/Terminal-Sotto/Sotto && source venv/bin/activate && python -c "from sotto.ui.menubar import SottoMenubar; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Run tests**

Run: `pytest tests/ -v`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add sotto/ui/menubar.py pyproject.toml
git commit -m "fix: guard deleted settings import, add dev dependencies to pyproject.toml"
```

---

## Stream E: Clone-to-Run Distribution

### Task 6: Setup Script + Gitignore Fix + README Prerequisites

**Files:**
- Create: `scripts/setup.sh`
- Modify: `.gitignore:146-147` (remove sidecar binary exclusion)
- Modify: `README.md` (add portaudio prereq, setup script reference)

- [ ] **Step 1: Create setup.sh**

```bash
#!/usr/bin/env bash
# One-command setup for Sotto development
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Sotto Setup ==="

# Check prerequisites
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.11+"
    exit 1
fi
if ! command -v pnpm &>/dev/null; then
    echo "ERROR: pnpm not found. Install: npm install -g pnpm"
    exit 1
fi
if ! command -v cargo &>/dev/null; then
    echo "ERROR: cargo not found. Install: https://rustup.rs"
    exit 1
fi

# Check portaudio (macOS)
if [[ "$(uname)" == "Darwin" ]] && ! brew list portaudio &>/dev/null 2>&1; then
    echo "Installing portaudio (required by sounddevice)..."
    brew install portaudio
fi

# Python environment
echo "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]" --quiet

# Build sidecar binary
echo "Building sidecar binary (this takes a few minutes)..."
bash scripts/build_sidecar.sh

# Frontend dependencies
echo "Installing frontend dependencies..."
cd sotto-ui
pnpm install --frozen-lockfile 2>/dev/null || pnpm install

echo ""
echo "=== Setup complete! ==="
echo "Run: cd sotto-ui && pnpm tauri dev"
```

- [ ] **Step 2: Make setup.sh executable**

Run: `chmod +x scripts/setup.sh`

- [ ] **Step 3: Update .gitignore — remove sidecar binary exclusion**

Remove these two lines from `.gitignore` (lines 146-147):
```
# Sidecar binaries (built locally)
sotto-ui/src-tauri/binaries/
```

The sidecar binary is 66MB. Instead of checking it in, the setup script builds it. But the `binaries/` directory itself should NOT be gitignored — the directory needs to exist for Tauri to find it. Add a `.gitkeep` instead:

Run: `touch sotto-ui/src-tauri/binaries/.gitkeep`

Replace the removed lines with:
```
# Sidecar binaries are built by scripts/setup.sh (too large for git)
sotto-ui/src-tauri/binaries/sotto-engine-*
```

This keeps the directory tracked but ignores the actual 66MB binary.

- [ ] **Step 4: Update README — add prerequisites and setup script**

In the README's Quick Start / setup section, ensure these prerequisites are listed:
- Python 3.11+
- Rust (via rustup)
- pnpm
- portaudio (`brew install portaudio` on macOS)

Add a "Quick Setup" section:
```markdown
### Quick Setup

```bash
git clone https://github.com/vedantggwp/Sotto.git
cd Sotto
bash scripts/setup.sh
cd sotto-ui && pnpm tauri dev
```
```

- [ ] **Step 5: Commit**

```bash
git add scripts/setup.sh .gitignore sotto-ui/src-tauri/binaries/.gitkeep README.md
git commit -m "feat: one-command setup script, fix gitignore for sidecar binaries"
```

---

## Verification Checklist (after all streams complete)

- [ ] **V1: Rust compiles clean**
Run: `cd sotto-ui/src-tauri && cargo check`

- [ ] **V2: TypeScript compiles clean**
Run: `cd sotto-ui && pnpm exec tsc --noEmit`

- [ ] **V3: All Python tests pass**
Run: `source venv/bin/activate && pytest tests/ -v`

- [ ] **V4: Python imports work**
Run: `python -c "from sotto.main import Sotto; from sotto.sidecar import run; print('OK')"`

- [ ] **V5: Sidecar binary responds to quit**
Run: `echo '{"command":"quit"}' | sotto-ui/src-tauri/binaries/sotto-engine-aarch64-apple-darwin 2>/dev/null | head -3`
Expected: JSON output ending with `{"type":"state_change","state":"idle"}`

- [ ] **V6: Config roundtrip works (manual test)**
1. Delete `~/.sotto/config.yaml` if it exists
2. Run `pnpm tauri dev`
3. Open Settings (⌘ ,)
4. Change model to "Medium (769M)"
5. Close settings
6. Check `~/.sotto/config.yaml` — should contain `transcription:\n  model: medium.en` nested properly
7. Reopen settings — should show "Medium (769M)" selected

---

## Critical Path

```
Stream A (Tasks 1-2): Rust config + resilience     ─┐
Stream B (Task 3):    Protocol alignment            ─┤
Stream C (Task 4):    Settings UI                   ─┼── V1-V6 verification ── Push
Stream D (Task 5):    Python cleanup                ─┤
Stream E (Task 6):    Distribution                  ─┘
```

All 5 streams are independent — different files, no conflicts. Can be parallelized as 5 agents.
