"""
Sotto Dynamic Notch UI
Implements a "Dynamic Island" style overlay for macOS using PyObjC.
Reference-accurate clone of DynamicNotchKit / FocusIsland.
"""

import threading
from typing import Optional


class NotchOverlay:
    """
    Dynamic Island style overlay.
    """

    def __init__(self):
        self._window = None
        self._view = None
        self._text_field = None
        self._icon_view = None
        self._initialized = False
        self._is_expanded = False
        self._hide_timer = None

        # Dimensions & Radii (Extracted from DynamicNotchKit)
        # DynamicNotchKit uses:
        # Compact: Height 32, Corner Radius ~16 (Continuous)
        # Expanded: Height ~80+, Corner Radius 24 (Continuous)
        # Animation: .snappy (spring-based)
        
        self.NOTCH_WIDTH_COMPACT = 190
        self.NOTCH_HEIGHT_COMPACT = 32
        self.NOTCH_WIDTH_EXPANDED = 460
        self.NOTCH_HEIGHT_EXPANDED = 90
        
        # Corner radii
        self.CORNER_RADIUS_COMPACT = 16.0
        self.CORNER_RADIUS_EXPANDED = 24.0

    def _ensure_initialized(self):
        """Initialize the notched window (must be on main thread)"""
        if self._initialized:
            return True

        try:
            from AppKit import (
                NSBackingStoreBuffered,
                NSColor,
                NSFloatingWindowLevel,
                NSFont,
                NSMakeRect,
                NSScreen,
                NSTextAlignmentCenter,
                NSTextField,
                NSView,
                NSWindow,
                NSWindowStyleMaskBorderless,
            )
            
            # 1. Get Screen Info
            screen = NSScreen.mainScreen()
            if not screen:
                return False
            
            frame = screen.frame()
            screen_width = frame.size.width
            screen_height = frame.size.height

            # Initial Frame (Compact)
            width = self.NOTCH_WIDTH_COMPACT
            height = self.NOTCH_HEIGHT_COMPACT
            x = (screen_width - width) / 2
            y = screen_height - height - 0  # Flush top

            # 2. Create Window
            self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(x, y, width, height),
                NSWindowStyleMaskBorderless,
                NSBackingStoreBuffered,
                False
            )
            self._window.setLevel_(NSFloatingWindowLevel + 1) # Just above other floating windows
            self._window.setOpaque_(False)
            self._window.setBackgroundColor_(NSColor.clearColor())
            self._window.setIgnoresMouseEvents_(True)
            self._window.setHasShadow_(False) # No shadow for embedded look
            
            # 3. Create Main Container View (Main Logic)
            self._view = NSView.alloc().initWithFrame_(
                NSMakeRect(0, 0, width, height)
            )
            self._view.setWantsLayer_(True)
            self._view.layer().setCornerRadius_(self.CORNER_RADIUS_COMPACT)
            
            # IMPT: Use Continuous Corner Curve for "Squircle" Apple look
            # kCALayerCornerCurveContinuous = "continuous"
            self._view.layer().setCornerCurve_("continuous")
            self._view.layer().setMasksToBounds_(True)
            self._view.layer().setBackgroundColor_(NSColor.blackColor().CGColor())

            # 4. Icon View (Left)
            self._icon_view = NSTextField.alloc().initWithFrame_(
                NSMakeRect(14, 0, 30, height)
            )
            self._icon_view.setStringValue_("🎤")
            self._icon_view.setBezeled_(False)
            self._icon_view.setDrawsBackground_(False)
            self._icon_view.setEditable_(False)
            self._icon_view.setSelectable_(False)
            self._icon_view.setFont_(NSFont.systemFontOfSize_(16))
            self._icon_view.setAutoresizingMask_(4) # MinYMargin
            self._view.addSubview_(self._icon_view)

            # 5. Text Field (Center)
            self._text_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(40, 0, width - 50, height)
            )
            self._text_field.setStringValue_("Ready")
            self._text_field.setBezeled_(False)
            self._text_field.setDrawsBackground_(False)
            self._text_field.setEditable_(False)
            self._text_field.setSelectable_(False)
            self._text_field.setAlignment_(NSTextAlignmentCenter)
            self._text_field.setTextColor_(NSColor.whiteColor())
            self._text_field.setFont_(NSFont.systemFontOfSize_weight_(13, 0.6))
            self._text_field.setAutoresizingMask_(2 | 16)
            self._view.addSubview_(self._text_field)

            self._window.setContentView_(self._view)
            self._initialized = True
            
            # Hidden initially
            self._window.setAlphaValue_(0.0)
            self._window.orderFrontRegardless()
            
            return True

        except Exception as e:
            print(f"[Sotto] Notch init error: {e}")
            return False

    def _animate_frame_on_main_thread(self, target_width, target_height, text, icon, is_expanded):
        """Animate with CASpringAnimation behavior if possible, or CAMediaTimingFunction"""
        if not self._ensure_initialized():
            return

        from AppKit import (
            NSAnimationContext,
            NSMakeRect,
            NSScreen,
            NSFont,
            CAMediaTimingFunction
        )

        # Content Updates
        self._text_field.setStringValue_(text)
        self._icon_view.setStringValue_(icon)

        # Layout Calculation
        screen = NSScreen.mainScreen()
        frame = screen.frame()
        screen_width = frame.size.width
        screen_height = frame.size.height
        
        x = (screen_width - target_width) / 2
        y = screen_height - target_height
        
        target_frame = NSMakeRect(x, y, target_width, target_height)
        target_radius = self.CORNER_RADIUS_EXPANDED if is_expanded else self.CORNER_RADIUS_COMPACT

        # Font Scaling
        if is_expanded:
            self._text_field.setFont_(NSFont.systemFontOfSize_weight_(22, 0.7)) # Bold, Large
        else:
            self._text_field.setFont_(NSFont.systemFontOfSize_weight_(13, 0.6))

        # ANIMATION BLOCK
        NSAnimationContext.beginGrouping()
        context = NSAnimationContext.currentContext()
        context.setDuration_(0.55) # Fluid duration
        
        # Spring timing approximation
        timing = CAMediaTimingFunction.functionWithControlPoints____(0.3, 1.35, 0.3, 1.0)
        context.setTimingFunction_(timing)
        
        # Window Frame
        self._window.animator().setFrame_display_(target_frame, True)
        
        # View Layer
        self._view.animator().setFrame_(NSMakeRect(0, 0, target_width, target_height))
        self._view.layer().setCornerRadius_(target_radius)
        
        # Opacity
        self._window.animator().setAlphaValue_(1.0)
        
        NSAnimationContext.endGrouping()

    def show(self, text: str, icon: str = ""):
        """Show the notch overlay (thread-safe)"""
        is_result = len(text) > 15 or icon in ["✅", "❌", "📝", "⚡"]
        
        try:
            from PyObjCTools import AppHelper
            
            if is_result:
                w, h = self.NOTCH_WIDTH_EXPANDED, self.NOTCH_HEIGHT_EXPANDED
                self._is_expanded = True
            else:
                w, h = self.NOTCH_WIDTH_COMPACT, self.NOTCH_HEIGHT_COMPACT
                self._is_expanded = False
                
            AppHelper.callAfter(lambda: self._animate_frame_on_main_thread(w, h, text, icon, self._is_expanded))
            
            if is_result:
                self._schedule_hide(3.2)
            else:
                self._cancel_hide()

        except ImportError:
            pass

    def _hide_on_main_thread(self):
        if self._window:
            self._window.animator().setAlphaValue_(0.0)

    def hide(self):
        try:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(self._hide_on_main_thread)
        except Exception:
            pass

    def _schedule_hide(self, delay):
        self._cancel_hide()
        self._hide_timer = threading.Timer(delay, self.hide)
        self._hide_timer.daemon = True
        self._hide_timer.start()

    def _cancel_hide(self):
        if self._hide_timer:
            self._hide_timer.cancel()
            self._hide_timer = None

    # Conform to Overlay Interface
    def show_listening(self):
        self.show("Listening", "🔴")

    def show_transcription(self, text: str):
        self.show(text, "📝")

    def show_command(self, command: str):
        self.show(command, "⚡")

    def show_error(self, error: str):
        self.show(error, "❌")

    def show_success(self, message: str):
        self.show(message, "✅")
