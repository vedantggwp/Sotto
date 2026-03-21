"""
Sotto Hotkey Manager
Handles global hotkey detection using pynput.
"""

from typing import Callable, Optional, Set

from pynput import keyboard

from ..utils.logging import get_logger

logger = get_logger("hotkeys")


class HotkeyManager:
    """
    Manages global hotkeys for Sotto.
    Detects Push-to-Talk and Toggle Listening combinations.
    """

    def __init__(
        self,
        ptt_hotkey: str,
        toggle_hotkey: str,
        on_ptt_start: Callable[[], None],
        on_ptt_end: Callable[[], None],
        on_toggle: Callable[[], None],
    ):
        self.ptt_keys = self._parse_hotkey(ptt_hotkey)
        self.toggle_keys = self._parse_hotkey(toggle_hotkey)

        self.on_ptt_start = on_ptt_start
        self.on_ptt_end = on_ptt_end
        self.on_toggle = on_toggle

        self._current_keys: Set[keyboard.Key] = set()
        self._listener: Optional[keyboard.Listener] = None
        self._ptt_active = False

    def start(self):
        """Start the hotkey listener"""
        if self._listener:
            return

        logger.info("Starting hotkey listener...")
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()
        logger.debug(f"Listening for PTT: {self.ptt_keys} | Toggle: {self.toggle_keys}")

    def stop(self):
        """Stop the hotkey listener"""
        if self._listener:
            self._listener.stop()
            self._listener = None
            logger.info("Stopped hotkey listener")

    def _parse_hotkey(self, hotkey_str: str) -> Set:
        """Parse hotkey string (e.g., '<cmd>+<shift>+<space>') to pynput keys"""
        parts = hotkey_str.replace("<", "").replace(">", "").split("+")
        keys = set()
        for part in parts:
            part = part.strip().lower()
            if part == "cmd":
                keys.add(keyboard.Key.cmd)
            elif part == "ctrl":
                keys.add(keyboard.Key.ctrl)
            elif part == "shift":
                keys.add(keyboard.Key.shift)
            elif part == "alt":
                keys.add(keyboard.Key.alt)
            elif part == "space":
                keys.add(keyboard.Key.space)
            elif part == "escape":
                keys.add(keyboard.Key.esc)
            elif len(part) == 1:
                keys.add(keyboard.KeyCode.from_char(part))
            else:
                logger.warning(f"Unknown key in hotkey config: {part}")
        return keys

    def _on_press(self, key):
        """Handle key press"""
        # Add key to current set
        # Note: Canonicalize to handle cleaner key matching
        try:
            if hasattr(key, "char") and key.char:
                # Handle letter keys
                self._current_keys.add(keyboard.KeyCode.from_char(key.char))
            else:
                self._current_keys.add(key)
        except Exception:
            self._current_keys.add(key)

        # Check PTT
        if self.ptt_keys.issubset(self._current_keys):
            if not self._ptt_active:
                self._ptt_active = True
                logger.debug("Push-to-Talk triggered")
                self.on_ptt_start()

        # Check Toggle
        if self.toggle_keys.issubset(self._current_keys):
            # Debounce behavior: only trigger if we haven't handled this combo yet?
            # Or simple trigger. Toggle usually triggers on press.
            # To avoid rapid toggling, we might want a simple debounce or check logic.
            # For now, let's trigger.
            logger.debug("Toggle Listening triggered")
            self.on_toggle()

    def _on_release(self, key):
        """Handle key release"""
        try:
            if hasattr(key, "char") and key.char:
                self._current_keys.discard(keyboard.KeyCode.from_char(key.char))
            else:
                self._current_keys.discard(key)
        except Exception:
            pass

        # Check if PTT was released
        if self._ptt_active:
            if not self.ptt_keys.issubset(self._current_keys):
                self._ptt_active = False
                logger.debug("Push-to-Talk released")
                self.on_ptt_end()
