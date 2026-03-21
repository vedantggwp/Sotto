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
                            // Cmd+Shift+S → toggle pill visibility
                            tauri_plugin_global_shortcut::Code::KeyS => {
                                if let Some(pill) = app.get_webview_window("pill") {
                                    if pill.is_visible().unwrap_or(false) {
                                        let _ = pill.hide();
                                    } else {
                                        let _ = pill.show();
                                    }
                                }
                            }
                            // Cmd+Shift+D → cycle demo states
                            tauri_plugin_global_shortcut::Code::KeyD => {
                                let _ = app.emit("sotto://demo-cycle", ());
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
        .invoke_handler(tauri::generate_handler![show_pill, hide_pill, show_settings])
        .setup(|app| {
            // Register global shortcuts
            use tauri_plugin_global_shortcut::GlobalShortcutExt;

            // Cmd+Shift+S → toggle pill
            let _ = app.global_shortcut().register("CmdOrCtrl+Shift+S");
            // Cmd+Shift+D → cycle demo states
            let _ = app.global_shortcut().register("CmdOrCtrl+Shift+D");
            // Cmd+, → settings (standard macOS convention)
            let _ = app.global_shortcut().register("CmdOrCtrl+Shift+Comma");

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
                            app.exit(0);
                        }
                        _ => {}
                    }
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Sotto");
}
