"""
Sotto Command Executor
Executes system commands on macOS using keyboard simulation and AppleScript.
"""

import subprocess
import time
from typing import Optional, Callable, Dict, Any
from pynput.keyboard import Key, Controller as KeyboardController


class CommandExecutor:
    """
    Execute commands on macOS.
    Uses a combination of keyboard simulation and AppleScript for system control.
    """
    
    def __init__(self, on_status: Optional[Callable[[str], None]] = None):
        """
        Initialize the executor.
        
        Args:
            on_status: Callback for status messages
        """
        self.keyboard = KeyboardController()
        self._on_status = on_status
        self._last_dictation = ""  # For "delete that" functionality
        
        # Map command names to handler methods
        self._handlers: Dict[str, Callable] = {
            # App commands
            "open_app": self._open_app,
            "quit_app": self._quit_app,
            "switch_app": self._switch_app,
            "close_window": self._close_window,
            
            # System commands
            "volume": self._volume,
            "brightness": self._brightness,
            "screenshot": self._screenshot,
            "lock_screen": self._lock_screen,
            "sleep": self._sleep,
            
            # Text editing
            "select_all": self._select_all,
            "copy": self._copy,
            "cut": self._cut,
            "paste": self._paste,
            "undo": self._undo,
            "redo": self._redo,
            "delete_last": self._delete_last,
            "delete_word": self._delete_word,
            "delete_line": self._delete_line,
            "new_line": self._new_line,
            "tab": self._tab,
            "space": self._space,
            "backspace": self._backspace,
            "escape": self._escape,
            
            # Navigation
            "scroll": self._scroll,
            "page": self._page,
            "navigate": self._navigate,
            
            # Tabs
            "new_tab": self._new_tab,
            "close_tab": self._close_tab,
            "switch_tab": self._switch_tab,
            
            # Search
            "search": self._search,
            "search_google": self._search_google,
            "find": self._find,
            
            # Punctuation
            "insert_punctuation": self._insert_punctuation,
        }
    
    def _status(self, message: str):
        """Send status message"""
        if self._on_status:
            self._on_status(message)
        print(f"[Executor] {message}")
    
    def execute(self, command_name: str, args: Dict[str, Any] = None) -> bool:
        """
        Execute a command.
        
        Args:
            command_name: Name of the command to execute
            args: Command arguments
            
        Returns:
            True if command executed successfully
        """
        if args is None:
            args = {}
        
        handler = self._handlers.get(command_name)
        if handler:
            try:
                handler(**args)
                return True
            except Exception as e:
                self._status(f"Error executing {command_name}: {e}")
                return False
        else:
            self._status(f"Unknown command: {command_name}")
            return False
    
    def type_text(self, text: str):
        """Type text (dictation)"""
        if not text:
            return
        
        self._last_dictation = text
        
        # Type the text character by character for reliability
        # Using pynput for keyboard simulation
        self.keyboard.type(text)
        self._status(f"Typed: {text}")
    
    def _run_applescript(self, script: str) -> Optional[str]:
        """Run an AppleScript and return output"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception as e:
            self._status(f"AppleScript error: {e}")
            return None
    
    def _press_key(self, key):
        """Press and release a key"""
        self.keyboard.press(key)
        self.keyboard.release(key)
    
    def _hotkey(self, *keys):
        """Press a keyboard shortcut"""
        # Press all modifier keys
        for key in keys[:-1]:
            self.keyboard.press(key)
        
        # Press and release the main key
        self._press_key(keys[-1])
        
        # Release all modifier keys in reverse order
        for key in reversed(keys[:-1]):
            self.keyboard.release(key)
        
        time.sleep(0.05)  # Small delay after hotkey
    
    # === App Commands ===
    
    def _open_app(self, app: str):
        """Open an application"""
        self._status(f"Opening {app}")
        self._run_applescript(f'tell application "{app}" to activate')
    
    def _quit_app(self, app: str):
        """Quit an application"""
        self._status(f"Quitting {app}")
        self._run_applescript(f'tell application "{app}" to quit')
    
    def _switch_app(self, app: str):
        """Switch to an application"""
        self._status(f"Switching to {app}")
        self._run_applescript(f'tell application "{app}" to activate')
    
    def _close_window(self):
        """Close the current window"""
        self._status("Closing window")
        self._hotkey(Key.cmd, 'w')
    
    # === System Commands ===
    
    def _volume(self, action: str):
        """Control volume"""
        self._status(f"Volume {action}")
        if action == "up":
            self._run_applescript("set volume output volume ((output volume of (get volume settings)) + 10)")
        elif action == "down":
            self._run_applescript("set volume output volume ((output volume of (get volume settings)) - 10)")
        elif action == "mute":
            self._run_applescript("set volume with output muted")
        elif action == "unmute":
            self._run_applescript("set volume without output muted")
    
    def _brightness(self, action: str):
        """Control brightness"""
        self._status(f"Brightness {action}")
        if action == "up":
            # Use keyboard to increase brightness
            self._press_key(Key.f2)  # Brightness up on most Macs
        elif action == "down":
            self._press_key(Key.f1)  # Brightness down on most Macs
    
    def _screenshot(self):
        """Take a screenshot"""
        self._status("Taking screenshot")
        self._hotkey(Key.cmd, Key.shift, '3')
    
    def _lock_screen(self):
        """Lock the screen"""
        self._status("Locking screen")
        self._hotkey(Key.cmd, Key.ctrl, 'q')
    
    def _sleep(self):
        """Put Mac to sleep"""
        self._status("Going to sleep")
        self._run_applescript('tell application "System Events" to sleep')
    
    # === Text Editing Commands ===
    
    def _select_all(self):
        """Select all"""
        self._status("Select all")
        self._hotkey(Key.cmd, 'a')
    
    def _copy(self):
        """Copy selection"""
        self._status("Copy")
        self._hotkey(Key.cmd, 'c')
    
    def _cut(self):
        """Cut selection"""
        self._status("Cut")
        self._hotkey(Key.cmd, 'x')
    
    def _paste(self):
        """Paste"""
        self._status("Paste")
        self._hotkey(Key.cmd, 'v')
    
    def _undo(self):
        """Undo"""
        self._status("Undo")
        self._hotkey(Key.cmd, 'z')
    
    def _redo(self):
        """Redo"""
        self._status("Redo")
        self._hotkey(Key.cmd, Key.shift, 'z')
    
    def _delete_last(self):
        """Delete the last dictation"""
        if self._last_dictation:
            self._status(f"Deleting: {self._last_dictation}")
            # Select and delete the last dictated text
            for _ in range(len(self._last_dictation)):
                self._press_key(Key.backspace)
            self._last_dictation = ""
        else:
            self._status("Nothing to delete")
    
    def _delete_word(self):
        """Delete the previous word"""
        self._status("Delete word")
        self._hotkey(Key.alt, Key.backspace)
    
    def _delete_line(self):
        """Delete the current line"""
        self._status("Delete line")
        self._hotkey(Key.cmd, Key.backspace)
    
    def _new_line(self):
        """Insert new line"""
        self._press_key(Key.enter)
    
    def _tab(self):
        """Insert tab"""
        self._press_key(Key.tab)
    
    def _space(self):
        """Insert space"""
        self._press_key(Key.space)
    
    def _backspace(self):
        """Backspace"""
        self._press_key(Key.backspace)
    
    def _escape(self):
        """Press escape"""
        self._press_key(Key.escape)
    
    # === Navigation Commands ===
    
    def _scroll(self, direction: str):
        """Scroll the page"""
        self._status(f"Scroll {direction}")
        if direction == "up":
            self._press_key(Key.up)
            self._press_key(Key.up)
            self._press_key(Key.up)
        else:
            self._press_key(Key.down)
            self._press_key(Key.down)
            self._press_key(Key.down)
    
    def _page(self, direction: str):
        """Page up/down"""
        self._status(f"Page {direction}")
        if direction == "up":
            self._press_key(Key.page_up)
        else:
            self._press_key(Key.page_down)
    
    def _navigate(self, direction: str):
        """Browser back/forward"""
        self._status(f"Navigate {direction}")
        if direction == "back":
            self._hotkey(Key.cmd, '[')
        else:
            self._hotkey(Key.cmd, ']')
    
    # === Tab Commands ===
    
    def _new_tab(self):
        """Open new tab"""
        self._status("New tab")
        self._hotkey(Key.cmd, 't')
    
    def _close_tab(self):
        """Close current tab"""
        self._status("Close tab")
        self._hotkey(Key.cmd, 'w')
    
    def _switch_tab(self, direction: str):
        """Switch to next/previous tab"""
        self._status(f"{direction.capitalize()} tab")
        if direction == "next":
            self._hotkey(Key.cmd, Key.shift, ']')
        else:
            self._hotkey(Key.cmd, Key.shift, '[')
    
    # === Search Commands ===
    
    def _search(self, query: str):
        """Search using Spotlight"""
        self._status(f"Search: {query}")
        self._hotkey(Key.cmd, Key.space)
        time.sleep(0.2)
        self.keyboard.type(query)
    
    def _search_google(self, query: str):
        """Search Google"""
        self._status(f"Google: {query}")
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        self._run_applescript(f'open location "{url}"')
    
    def _find(self, text: str):
        """Find in current app"""
        self._status(f"Find: {text}")
        self._hotkey(Key.cmd, 'f')
        time.sleep(0.1)
        self.keyboard.type(text)
    
    # === Punctuation ===
    
    def _insert_punctuation(self, char: str):
        """Insert punctuation character"""
        self.keyboard.type(char)
