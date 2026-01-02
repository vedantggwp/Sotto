"""
Sotto Menubar Application
Native macOS menubar interface using rumps.
"""

import rumps
from typing import Optional, Callable
from ..config import get_config, SottoConfig


class SottoMenubar(rumps.App):
    """
    Menubar application for Sotto.
    Provides quick access to controls and status.
    """

    # Icons
    ICON_IDLE = "🎤"
    ICON_LISTENING = "🔴"
    ICON_PROCESSING = "⏳"

    # Available models
    MODELS = ["tiny.en", "base.en", "small.en", "medium.en", "large-v3"]

    def __init__(
        self,
        on_toggle_listening: Optional[Callable] = None,
        on_mode_change: Optional[Callable[[str], None]] = None,
        on_model_change: Optional[Callable[[str], None]] = None,
        on_quit: Optional[Callable] = None
    ):
        """
        Initialize the menubar app.

        Args:
            on_toggle_listening: Callback when listening is toggled
            on_mode_change: Callback when mode changes
            on_model_change: Callback when model changes
            on_quit: Callback when quitting
        """
        # Use emoji as the menubar title/icon
        super().__init__(self.ICON_IDLE, quit_button=None)

        self.config = get_config()
        self._on_toggle_listening = on_toggle_listening
        self._on_mode_change = on_mode_change
        self._on_model_change = on_model_change
        self._on_quit = on_quit
        self._is_listening = False

        self._setup_menu()
    
    def _setup_menu(self):
        """Setup the menu items"""
        # Status with hotkey info
        hotkey = self.config.hotkeys.push_to_talk.replace("<", "").replace(">", "").replace("+", " + ")
        self.status_item = rumps.MenuItem(f"Ready ({hotkey})")
        self.status_item.set_callback(None)

        # Listening toggle
        self.listen_item = rumps.MenuItem(
            "Start Listening",
            callback=self._toggle_listening
        )

        # Mode selection
        self.mode_menu = rumps.MenuItem("Mode")
        self.push_to_talk_item = rumps.MenuItem(
            "Push to Talk",
            callback=lambda _: self._set_mode("push_to_talk")
        )
        self.always_listening_item = rumps.MenuItem(
            "Always Listening",
            callback=lambda _: self._set_mode("always_listening")
        )

        # Mark current mode
        if self.config.mode == "push_to_talk":
            self.push_to_talk_item.state = 1
        else:
            self.always_listening_item.state = 1

        self.mode_menu.add(self.push_to_talk_item)
        self.mode_menu.add(self.always_listening_item)

        # Model selection submenu
        self.model_menu = rumps.MenuItem("Model")
        self._model_items = {}
        for model in self.MODELS:
            item = rumps.MenuItem(model, callback=self._on_model_select)
            if model == self.config.transcription.model:
                item.state = 1
            self._model_items[model] = item
            self.model_menu.add(item)

        # Settings
        self.settings_item = rumps.MenuItem("Settings...", callback=self._open_settings)

        # Commands help
        self.commands_item = rumps.MenuItem("View Commands", callback=self._show_commands)

        # Quit
        self.quit_item = rumps.MenuItem("Quit Sotto", callback=self._quit)

        # Build menu
        self.menu = [
            self.status_item,
            None,  # Separator
            self.listen_item,
            self.mode_menu,
            self.model_menu,
            None,  # Separator
            self.commands_item,
            self.settings_item,
            None,  # Separator
            self.quit_item
        ]
    
    def _toggle_listening(self, _):
        """Toggle listening state"""
        if self._on_toggle_listening:
            self._on_toggle_listening()

    def _set_mode(self, mode: str):
        """Set the listening mode"""
        self.config.mode = mode
        self.config.save()

        # Update menu checkmarks
        self.push_to_talk_item.state = 1 if mode == "push_to_talk" else 0
        self.always_listening_item.state = 1 if mode == "always_listening" else 0

        if self._on_mode_change:
            self._on_mode_change(mode)

    def _on_model_select(self, sender):
        """Handle model selection from menu"""
        model = sender.title
        self.config.transcription.model = model
        self.config.save()

        # Update checkmarks
        for name, item in self._model_items.items():
            item.state = 1 if name == model else 0

        # Notify callback
        if self._on_model_change:
            self._on_model_change(model)

        rumps.notification(
            title="Sotto",
            subtitle="Model Changed",
            message=f"Switched to {model} (restart may be required)"
        )

    def _open_settings(self, _):
        """Open settings window"""
        from .settings import show_settings_window
        show_settings_window(self.config, on_save=self._on_settings_saved)

    def _on_settings_saved(self, config):
        """Handle settings saved callback"""
        self.config = config

        # Update mode checkmarks
        self.push_to_talk_item.state = 1 if config.mode == "push_to_talk" else 0
        self.always_listening_item.state = 1 if config.mode == "always_listening" else 0

        # Update model checkmarks
        for name, item in self._model_items.items():
            item.state = 1 if name == config.transcription.model else 0

        # Update status with new hotkey
        hotkey = config.hotkeys.push_to_talk.replace("<", "").replace(">", "").replace("+", " + ")
        self.status_item.title = f"Ready ({hotkey})"

        if self._on_mode_change:
            self._on_mode_change(config.mode)
    
    def _show_commands(self, _):
        """Show available commands"""
        # Comprehensive command list
        commands_text = """Voice Commands:

🔊 VOLUME & SYSTEM
• "volume up" / "volume down"
• "volume 50" or "set volume to 80"
• "mute" / "unmute"
• "brightness up" / "brightness down"
• "screenshot"
• "lock" or "lock screen"

📱 APPS
• "open [app name]" - Open an app
• "quit [app name]" - Quit an app
• "switch to [app name]" - Switch to app
• "close window"

✂️ TEXT EDITING
• "select all" / "copy" / "cut" / "paste"
• "undo" / "redo"
• "delete that" - Delete last dictation
• "delete word" / "delete line"
• "new line" / "tab" / "backspace"

🧭 NAVIGATION
• "scroll up" / "scroll down"
• "page up" / "page down"
• "back" / "forward"
• "new tab" / "close tab"
• "next tab" / "previous tab"

🔍 SEARCH
• "search [query]" - Spotlight search
• "google [query]" - Google search
• "find [text]" - Find in app

⏸️ CONTROL
• "stop" - Stop listening

💡 TIP: Speak clearly after pressing hotkey"""

        rumps.alert(
            title="Sotto Voice Commands",
            message=commands_text,
            ok="Got it!"
        )
    
    def _quit(self, _):
        """Quit the application"""
        if self._on_quit:
            self._on_quit()
        rumps.quit_application()
    
    # Public methods for updating state
    
    def set_listening(self, is_listening: bool):
        """Update the listening state"""
        self._is_listening = is_listening
        
        if is_listening:
            self.title = self.ICON_LISTENING
            self.status_item.title = "Status: Listening..."
            self.listen_item.title = "Stop Listening"
        else:
            self.title = self.ICON_IDLE
            self.status_item.title = "Status: Idle"
            self.listen_item.title = "Start Listening"
    
    def set_processing(self):
        """Show processing state"""
        self.title = self.ICON_PROCESSING
        self.status_item.title = "Status: Processing..."
    
    def show_notification(self, title: str, message: str, subtitle: str = ""):
        """Show a notification"""
        rumps.notification(
            title=title,
            subtitle=subtitle,
            message=message
        )
    
    def update_status(self, status: str):
        """Update the status text"""
        self.status_item.title = f"Status: {status}"
