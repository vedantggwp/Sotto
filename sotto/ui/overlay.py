"""
Sotto Overlay Window
Floating HUD feedback window showing transcription results.
"""


class SimpleOverlay:
    """
    Simple overlay using terminal output (fallback when PyObjC not available).
    """

    def __init__(self, duration: float = 2.0, position: str = "top-center"):
        self.duration = duration
        self._last_message = ""

    def show(self, text: str, icon: str = ""):
        """Show text in terminal"""
        display_text = f"{icon} {text}" if icon else text
        if display_text != self._last_message:
            print(f"[Sotto] {display_text}")
            self._last_message = display_text

    def hide(self):
        """No-op for terminal overlay"""
        pass

    def show_listening(self):
        self.show("Listening...", "🎤")

    def show_transcription(self, text: str):
        self.show(text, "📝")

    def show_command(self, command: str):
        self.show(f"Command: {command}", "⚡")

    def show_error(self, error: str):
        self.show(f"Error: {error}", "❌")

    def show_success(self, message: str):
        self.show(message, "✅")


def create_overlay(duration: float = 2.0, position: str = "top-center"):
    """
    Create an overlay instance.
    Priority: NotchOverlay (Dynamic Island) > SimpleOverlay (terminal fallback)
    """
    import sys

    if sys.platform == "darwin":
        try:
            from AppKit import NSApplication

            app = NSApplication.sharedApplication()
            if app is not None:
                from .notch import NotchOverlay
                return NotchOverlay()
        except ImportError:
            pass
        except Exception as e:
            print(f"[Sotto] Overlay init error: {e}")

    return SimpleOverlay(duration, position)
