mod sidecar;

use tauri::{
    Manager, Emitter,
    menu::{Menu, MenuItem},
};

#[tauri::command]
fn show_pill(app: tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("pill") {
        let _ = window.show();
    }
}

#[tauri::command]
fn hide_pill(app: tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("pill") {
        let _ = window.hide();
    }
}

#[tauri::command]
fn show_settings(app: tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("settings") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn engine_command(
    state: tauri::State<'_, sidecar::SidecarState>,
    command: String,
    key: Option<String>,
    value: Option<String>,
) -> Result<(), String> {
    let mut msg = serde_json::json!({"command": command});
    if let Some(k) = key {
        msg["key"] = serde_json::Value::String(k);
    }
    if let Some(v) = value {
        msg["value"] = serde_json::Value::String(v);
    }
    sidecar::send_to_sidecar(&state, &msg.to_string())
}

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
            serde_yml::Value::Number(serde_yml::Number::from(n))
        } else {
            serde_yml::Value::String(value.to_string())
        };
        mapping.insert(yaml_key, yaml_value);
    } else {
        // Recurse into nested mapping
        let entry = mapping
            .entry(yaml_key)
            .or_insert_with(|| serde_yml::Value::Mapping(serde_yml::Mapping::new()));
        set_nested_yaml(entry, &keys[1..], value);
    }
}

/// Track whether we're currently recording so Cmd+Shift+S can toggle
static RECORDING: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
/// Debounce hotkey toggles — epoch millis of last toggle
static LAST_TOGGLE: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_positioner::init())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, shortcut, event| {
                    if event.state() == tauri_plugin_global_shortcut::ShortcutState::Pressed {
                        let key = shortcut.key;
                        match key {
                            // Cmd+Shift+S → toggle recording
                            tauri_plugin_global_shortcut::Code::KeyS => {
                                // Debounce: ignore if < 300ms since last toggle
                                let now = std::time::SystemTime::now()
                                    .duration_since(std::time::UNIX_EPOCH)
                                    .unwrap_or_default()
                                    .as_millis() as u64;
                                let last = LAST_TOGGLE.load(std::sync::atomic::Ordering::SeqCst);
                                if now.saturating_sub(last) < 300 {
                                    return;
                                }
                                LAST_TOGGLE.store(now, std::sync::atomic::Ordering::SeqCst);

                                let was_recording = RECORDING.load(std::sync::atomic::Ordering::SeqCst);
                                let command = if was_recording {
                                    "stop_recording"
                                } else {
                                    "start_recording"
                                };
                                RECORDING.store(!was_recording, std::sync::atomic::Ordering::SeqCst);

                                // Show/hide pill based on recording state
                                if let Some(pill) = app.get_webview_window("pill") {
                                    if was_recording {
                                        // Stopping — pill will hide after "done" state timeout
                                    } else {
                                        let _ = pill.show();
                                    }
                                }

                                // Send command to sidecar
                                let state = app.state::<sidecar::SidecarState>();
                                let msg = serde_json::json!({"command": command}).to_string();
                                let _ = sidecar::send_to_sidecar(&state, &msg);
                            }
                            // Cmd+, → open settings
                            tauri_plugin_global_shortcut::Code::Comma => {
                                if let Some(window) = app.get_webview_window("settings") {
                                    let _ = window.show();
                                    let _ = window.set_focus();
                                }
                            }
                            _ => {}
                        }
                    }
                })
                .build(),
        )
        .manage(sidecar::SidecarState::new())
        .invoke_handler(tauri::generate_handler![
            show_pill, hide_pill, show_settings, engine_command, get_config, set_config_value
        ])
        .setup(|app| {
            // Register global shortcuts
            use tauri_plugin_global_shortcut::GlobalShortcutExt;

            // Cmd+Shift+S → toggle recording
            let _ = app.global_shortcut().register("CmdOrCtrl+Shift+S");
            // Cmd+, → settings (standard macOS convention)
            let _ = app.global_shortcut().register("CmdOrCtrl+Comma");

            // Build tray menu
            let settings_item = MenuItem::with_id(app, "settings", "Settings...", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit Sotto", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&settings_item, &quit_item])?;

            if let Some(tray) = app.tray_by_id("sotto-tray") {
                tray.set_menu(Some(menu))?;
                tray.on_menu_event(move |app, event| {
                    match event.id().as_ref() {
                        "settings" => {
                            if let Some(window) = app.get_webview_window("settings") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "quit" => {
                            // Send quit to sidecar before exiting
                            let state = app.state::<sidecar::SidecarState>();
                            let msg = serde_json::json!({"command": "quit"}).to_string();
                            let _ = sidecar::send_to_sidecar(&state, &msg);
                            app.exit(0);
                        }
                        _ => {}
                    }
                });
            }

            // Spawn sidecar engine
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if let Err(e) = sidecar::spawn_sidecar(&handle) {
                    eprintln!("[sotto] failed to spawn sidecar: {}", e);
                    let error = serde_json::json!({
                        "type": "error",
                        "error": format!("Failed to start engine: {}", e)
                    });
                    let _ = handle.emit("sotto://engine", &error);
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Sotto");
}
