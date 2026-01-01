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
    
    # Icons (using emoji as placeholder - can be replaced with actual icons)
    ICON_IDLE = "🎤"
    ICON_LISTENING = "🔴"
    ICON_PROCESSING = "⏳"
    
    def __init__(
        self,
        on_toggle_listening: Optional[Callable] = None,
        on_mode_change: Optional[Callable[[str], None]] = None,
        on_quit: Optional[Callable] = None
    ):
        """
        Initialize the menubar app.
        
        Args:
            on_toggle_listening: Callback when listening is toggled
            on_mode_change: Callback when mode changes
            on_quit: Callback when quitting
        """
        super().__init__("Sotto", quit_button=None)
        
        self.config = get_config()
        self._on_toggle_listening = on_toggle_listening
        self._on_mode_change = on_mode_change
        self._on_quit = on_quit
        self._is_listening = False
        
        self._setup_menu()
    
    def _setup_menu(self):
        """Setup the menu items"""
        # Status indicator
        self.status_item = rumps.MenuItem("Status: Idle")
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
        
        rumps.notification(
            title="Sotto",
            subtitle="Mode Changed",
            message=f"Switched to {mode.replace('_', ' ').title()}"
        )
    
    def _open_settings(self, _):
        """Open settings window"""
        # For now, show a notification about hotkeys
        config = get_config()
        rumps.notification(
            title="Sotto Settings",
            subtitle="Current Hotkeys",
            message=f"Push to Talk: {config.hotkeys.push_to_talk}\n"
                    f"Toggle Listening: {config.hotkeys.toggle_listening}"
        )
    
    def _show_commands(self, _):
        """Show available commands"""
        from ..commands.registry import CommandRegistry
        registry = CommandRegistry()
        
        # Create a simple alert with command categories
        commands_text = (
            "Voice Commands:\n\n"
            "• System: volume up/down, screenshot, lock\n"
            "• Apps: open/quit/switch to [app]\n"
            "• Text: copy, paste, undo, delete that\n"
            "• Nav: scroll up/down, new tab, close tab\n"
            "• Search: google [query], search [query]\n\n"
            "Say 'stop' to stop listening"
        )
        
        rumps.alert(
            title="Sotto Commands",
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
