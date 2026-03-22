use tauri::{Manager, Emitter};
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
