"""
Sotto Overlay Window
Floating HUD feedback window showing transcription results.
"""

import threading
import time
from typing import Optional
import queue


class HUDOverlay:
    """
    Native macOS floating HUD overlay using PyObjC.
    Thread-safe: can be called from any thread.
    """

    def __init__(self, duration: float = 2.0, position: str = "top-center"):
        self.duration = duration
        self.position = position
        self._window = None
        self._text_field = None
        self._hide_timer = None
        self._initialized = False
        self._lock = threading.Lock()

    def _ensure_initialized(self):
        """Initialize window on first use (must be called from main thread)"""
        if self._initialized:
            return True

        try:
            from AppKit import (
                NSWindow, NSWindowStyleMaskBorderless, NSBackingStoreBuffered,
                NSFloatingWindowLevel, NSTextField, NSColor, NSFont,
                NSScreen, NSMakeRect, NSTextAlignmentCenter, NSView,
                NSApplication, NSVisualEffectView, NSVisualEffectBlendingModeBehindWindow,
                NSVisualEffectMaterialHUDWindow, NSVisualEffectStateActive
            )
            # Note: kCGWindowLevelFloating is not needed - using NSFloatingWindowLevel instead

            # Get screen dimensions
            screen = NSScreen.mainScreen()
            if not screen:
                return False
            screen_frame = screen.frame()
            screen_width = screen_frame.size.width
            screen_height = screen_frame.size.height

            # Window dimensions
            window_width = 400
            window_height = 50

            # Calculate position
            if "center" in self.position:
                x = (screen_width - window_width) / 2
            elif "right" in self.position:
                x = screen_width - window_width - 20
            else:
                x = 20

            if "top" in self.position:
                y = screen_height - window_height - 100  # Below menubar
            elif "bottom" in self.position:
                y = 100
            else:
                y = screen_height / 2

            # Create borderless window
            rect = NSMakeRect(x, y, window_width, window_height)
            self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                rect,
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False
            )

            # Configure window
            self._window.setLevel_(NSFloatingWindowLevel + 1)  # Above other floating windows
            self._window.setOpaque_(False)
            self._window.setBackgroundColor_(NSColor.clearColor())
            self._window.setIgnoresMouseEvents_(True)
            self._window.setCollectionBehavior_(1 << 0)  # Can join all spaces
            self._window.setHasShadow_(True)

            # Create visual effect view for blur background (dark style)
            effect_view = NSVisualEffectView.alloc().initWithFrame_(
                NSMakeRect(0, 0, window_width, window_height)
            )
            # Use dark material for consistent appearance
            effect_view.setMaterial_(NSVisualEffectMaterialHUDWindow)
            effect_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
            effect_view.setState_(NSVisualEffectStateActive)
            # Force dark appearance for consistent white text
            from AppKit import NSAppearance
            dark_appearance = NSAppearance.appearanceNamed_("NSAppearanceNameVibrantDark")
            if dark_appearance:
                effect_view.setAppearance_(dark_appearance)
            effect_view.setWantsLayer_(True)
            effect_view.layer().setCornerRadius_(12)
            effect_view.layer().setMasksToBounds_(True)
            # Add subtle border
            effect_view.layer().setBorderWidth_(0.5)
            effect_view.layer().setBorderColor_(NSColor.grayColor().CGColor())

            # Create text field
            self._text_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(15, 10, window_width - 30, window_height - 20)
            )
            self._text_field.setStringValue_("")
            self._text_field.setBezeled_(False)
            self._text_field.setDrawsBackground_(False)
            self._text_field.setEditable_(False)
            self._text_field.setSelectable_(False)
            self._text_field.setAlignment_(NSTextAlignmentCenter)
            self._text_field.setTextColor_(NSColor.whiteColor())
            self._text_field.setFont_(NSFont.systemFontOfSize_weight_(16, 0.5))  # Slightly bolder

            effect_view.addSubview_(self._text_field)
            self._window.setContentView_(effect_view)

            self._initialized = True
            return True

        except Exception as e:
            print(f"[Sotto] HUD init error: {e}")
            return False

    def _show_on_main_thread(self, text: str):
        """Actually show the window (called on main thread)"""
        if not self._ensure_initialized():
            print(f"[Sotto] {text}")
            return

        try:
            # Cancel pending hide timer
            if self._hide_timer:
                self._hide_timer.cancel()
                self._hide_timer = None

            # Update text and show
            self._text_field.setStringValue_(text)
            self._window.orderFrontRegardless()

            # Schedule hide
            self._hide_timer = threading.Timer(self.duration, self._hide_on_main_thread)
            self._hide_timer.daemon = True
            self._hide_timer.start()

        except Exception as e:
            print(f"[Sotto] {text}")

    def _hide_on_main_thread(self):
        """Hide the window"""
        try:
            if self._window:
                # Dispatch to main thread
                from Foundation import NSObject
                from PyObjCTools import AppHelper
                AppHelper.callAfter(lambda: self._window.orderOut_(None))
        except:
            pass

    def show(self, text: str, icon: str = ""):
        """
        Show the overlay with text (thread-safe).
        Can be called from any thread.
        """
        display_text = f"{icon} {text}".strip() if icon else text

        try:
            from PyObjCTools import AppHelper
            # Dispatch to main thread
            AppHelper.callAfter(lambda: self._show_on_main_thread(display_text))
        except ImportError:
            # Fallback to print
            print(f"[Sotto] {display_text}")
        except Exception as e:
            print(f"[Sotto] {display_text}")

    def hide(self):
        """Hide the overlay (thread-safe)"""
        try:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(self._hide_on_main_thread)
        except:
            pass

    def show_listening(self):
        self.show("Listening...", "🎤")

    def show_transcription(self, text: str):
        self.show(text, "📝")

    def show_command(self, command: str):
        self.show(f"{command}", "⚡")

    def show_error(self, error: str):
        self.show(f"{error}", "❌")

    def show_success(self, message: str):
        self.show(message, "✅")


class NotificationOverlay:
    """
    Fallback overlay using macOS notifications via osascript.
    Works reliably from any thread but is rate-limited and intrusive.
    """

    def __init__(self, duration: float = 2.0, position: str = "top-center"):
        self.duration = duration
        self._last_message = ""
        self._last_time = 0
        self._min_interval = 0.5

    def _notify(self, title: str, message: str):
        """Send a macOS notification via osascript"""
        import subprocess
        import time as t

        now = t.time()
        if now - self._last_time < self._min_interval:
            return
        self._last_time = now

        message = message.replace('"', '\\"')
        title = title.replace('"', '\\"')

        script = f'display notification "{message}" with title "{title}"'
        try:
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=2)
        except Exception:
            pass

    def show(self, text: str, icon: str = ""):
        display_text = f"{icon} {text}" if icon else text
        if display_text != self._last_message:
            self._last_message = display_text
            self._notify("Sotto", display_text)
            print(f"[Sotto] {display_text}")

    def hide(self):
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
    Priority: HUDOverlay (native HUD) > NotificationOverlay > SimpleOverlay
    """
    import sys

    if sys.platform == "darwin":
        # Try native HUD overlay first (best UX)
        try:
            from AppKit import NSApplication
            # Check if we have an app running (GUI mode)
            app = NSApplication.sharedApplication()
            if app is not None:
                return HUDOverlay(duration, position)
        except ImportError:
            pass
        except Exception:
            pass

        # Fall back to notifications
        return NotificationOverlay(duration, position)

    # Non-macOS: terminal output
    return SimpleOverlay(duration, position)
