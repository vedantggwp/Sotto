"""
Sotto Overlay Window
Floating feedback window showing transcription results.
"""

import threading
import time
from typing import Optional


class Overlay:
    """
    Floating overlay window for showing transcription feedback.
    Uses native macOS APIs via PyObjC.
    """
    
    def __init__(self, duration: float = 2.0, position: str = "top-center"):
        """
        Initialize the overlay.
        
        Args:
            duration: How long the overlay stays visible (seconds)
            position: Screen position (top-center, top-right, bottom-center, etc.)
        """
        self.duration = duration
        self.position = position
        self._window = None
        self._text_field = None
        self._hide_timer = None
        self._initialized = False
        
    def _init_window(self):
        """Initialize the native window (lazy loading)"""
        if self._initialized:
            return
            
        try:
            from AppKit import (
                NSWindow, NSWindowStyleMaskBorderless, NSBackingStoreBuffered,
                NSFloatingWindowLevel, NSTextField, NSColor, NSFont,
                NSScreen, NSMakeRect, NSTextAlignmentCenter, NSView,
                NSApplication
            )
            from Quartz import kCGWindowLevelFloating
            
            # Get screen dimensions
            screen = NSScreen.mainScreen()
            screen_frame = screen.frame()
            screen_width = screen_frame.size.width
            screen_height = screen_frame.size.height
            
            # Window dimensions
            window_width = 500
            window_height = 60
            
            # Calculate position
            if "center" in self.position:
                x = (screen_width - window_width) / 2
            elif "right" in self.position:
                x = screen_width - window_width - 20
            else:
                x = 20
            
            if "top" in self.position:
                y = screen_height - window_height - 80  # Below menubar
            elif "bottom" in self.position:
                y = 100
            else:
                y = screen_height / 2
            
            # Create window
            rect = NSMakeRect(x, y, window_width, window_height)
            self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                rect,
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False
            )
            
            # Configure window
            self._window.setLevel_(NSFloatingWindowLevel)
            self._window.setOpaque_(False)
            self._window.setBackgroundColor_(NSColor.clearColor())
            self._window.setIgnoresMouseEvents_(True)
            self._window.setCollectionBehavior_(1 << 0)  # Can join all spaces
            
            # Create content view with rounded background
            content_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, window_width, window_height))
            content_view.setWantsLayer_(True)
            content_view.layer().setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.1, 0.9).CGColor())
            content_view.layer().setCornerRadius_(12)
            
            # Create text field
            self._text_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(20, 10, window_width - 40, window_height - 20)
            )
            self._text_field.setStringValue_("")
            self._text_field.setBezeled_(False)
            self._text_field.setDrawsBackground_(False)
            self._text_field.setEditable_(False)
            self._text_field.setSelectable_(False)
            self._text_field.setAlignment_(NSTextAlignmentCenter)
            self._text_field.setTextColor_(NSColor.whiteColor())
            self._text_field.setFont_(NSFont.systemFontOfSize_weight_(18, 0.3))
            
            content_view.addSubview_(self._text_field)
            self._window.setContentView_(content_view)
            
            self._initialized = True
            
        except ImportError as e:
            print(f"Could not initialize overlay (PyObjC not available): {e}")
            self._initialized = False
        except Exception as e:
            print(f"Error initializing overlay: {e}")
            self._initialized = False
    
    def show(self, text: str, icon: str = ""):
        """
        Show the overlay with text.
        
        Args:
            text: Text to display
            icon: Optional emoji icon to prepend
        """
        if not self._initialized:
            self._init_window()
        
        if not self._initialized or not self._window:
            # Fallback: print to console
            print(f"[Sotto] {icon} {text}")
            return
        
        try:
            # Cancel any pending hide timer
            if self._hide_timer:
                self._hide_timer.cancel()
            
            # Update text
            display_text = f"{icon} {text}" if icon else text
            self._text_field.setStringValue_(display_text)
            
            # Show window
            self._window.orderFront_(None)
            
            # Set timer to hide
            self._hide_timer = threading.Timer(self.duration, self.hide)
            self._hide_timer.start()
            
        except Exception as e:
            print(f"Error showing overlay: {e}")
    
    def hide(self):
        """Hide the overlay"""
        if self._window:
            try:
                self._window.orderOut_(None)
            except:
                pass
    
    def show_listening(self):
        """Show listening indicator"""
        self.show("Listening...", "🎤")
    
    def show_transcription(self, text: str):
        """Show transcription result"""
        self.show(text, "📝")
    
    def show_command(self, command: str):
        """Show command execution"""
        self.show(f"Command: {command}", "⚡")
    
    def show_error(self, error: str):
        """Show error message"""
        self.show(f"Error: {error}", "❌")
    
    def show_success(self, message: str):
        """Show success message"""
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


def create_overlay(duration: float = 2.0, position: str = "top-center") -> Overlay:
    """
    Create an overlay instance.
    Falls back to SimpleOverlay if PyObjC is not available.
    """
    try:
        import AppKit
        return Overlay(duration, position)
    except ImportError:
        print("[Sotto] PyObjC not available, using simple terminal overlay")
        return SimpleOverlay(duration, position)
