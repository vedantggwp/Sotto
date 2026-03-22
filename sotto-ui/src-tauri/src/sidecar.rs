use tauri::{Manager, Emitter};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};

pub struct SidecarState {
    stdin_writer: Mutex<Option<tauri_plugin_shell::process::CommandChild>>,
    /// Set to true when kill_sidecar is called intentionally (not a crash).
    /// Checked by the Terminated handler to avoid restarting a killed process.
    intentional_kill: AtomicBool,
}

impl SidecarState {
    pub fn new() -> Self {
        Self {
            stdin_writer: Mutex::new(None),
            intentional_kill: AtomicBool::new(false),
        }
    }
}

pub fn spawn_sidecar(app: &tauri::AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    // Kill any existing sidecar before spawning a new one.
    // This is synchronous — old process is dead before we continue.
    kill_sidecar(app);

    // Clear the intentional_kill flag so crashes on the NEW process trigger restart
    app.state::<SidecarState>()
        .intentional_kill
        .store(false, Ordering::SeqCst);

    let sidecar_command = app.shell().sidecar("binaries/sotto-engine")?;
    let (mut rx, child) = sidecar_command.spawn()?;

    // Store child for stdin writing
    app.state::<SidecarState>()
        .stdin_writer
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
        .replace(child);

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
                CommandEvent::Terminated(status) => {
                    eprintln!("[sidecar] terminated: {:?}", status);

                    // If this was an intentional kill (hot reload, quit), do NOT restart
                    if app_handle.state::<SidecarState>()
                        .intentional_kill
                        .load(Ordering::SeqCst)
                    {
                        eprintln!("[sidecar] intentional kill — not restarting");
                        break;
                    }

                    // Emit error state so Pill shows error icon
                    let error = serde_json::json!({
                        "type": "state_change",
                        "state": "error"
                    });
                    let _ = app_handle.emit("sotto://engine", &error);

                    // Reset RECORDING state so hotkey isn't stuck
                    crate::RECORDING.store(false, std::sync::atomic::Ordering::SeqCst);

                    // Attempt restart with exponential backoff (max 3 retries)
                    let restart_handle = app_handle.clone();
                    tauri::async_runtime::spawn(async move {
                        for attempt in 1..=3u32 {
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
                _ => {}
            }
        }
    });

    Ok(())
}

/// Kill the current sidecar process synchronously.
/// Sends "quit" via stdin for graceful shutdown, then force-kills immediately.
/// The old process is guaranteed dead before this function returns.
pub fn kill_sidecar(app: &tauri::AppHandle) {
    let state = app.state::<SidecarState>();

    // Mark as intentional so the Terminated handler doesn't restart
    state.intentional_kill.store(true, Ordering::SeqCst);

    let mut guard = state
        .stdin_writer
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner());

    if let Some(mut child) = guard.take() {
        // Best-effort graceful quit
        let quit_msg = serde_json::json!({"command": "quit"}).to_string() + "\n";
        let _ = child.write(quit_msg.as_bytes());

        // Force kill immediately — no background thread, no race
        let _ = child.kill();
    }
}

pub fn send_to_sidecar(state: &SidecarState, msg: &str) -> Result<(), String> {
    let mut guard = state.stdin_writer.lock().map_err(|e| e.to_string())?;
    if let Some(child) = guard.as_mut() {
        child
            .write((msg.to_string() + "\n").as_bytes())
            .map_err(|e| e.to_string())?;
    } else {
        return Err("Sidecar not running".to_string());
    }
    Ok(())
}
