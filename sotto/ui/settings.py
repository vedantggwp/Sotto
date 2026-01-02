"""
Sotto Settings Window
Native macOS settings panel using PyObjC.
"""

from typing import Callable, Optional
import threading


# Singleton settings window instance
_settings_window = None


class SettingsWindowController:
    """
    Native macOS settings window using PyObjC/AppKit.
    Simple single-view layout with essential settings.
    """

    def __init__(self, config, on_save: Optional[Callable] = None):
        self.config = config
        self.on_save = on_save
        self._window = None
        self._controls = {}

    def show(self):
        """Show the settings window (creates if needed)"""
        try:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(self._show_on_main_thread)
        except ImportError:
            print("[Sotto] Settings window requires PyObjC")

    def _show_on_main_thread(self):
        """Create and show window on main thread"""
        if self._window is None:
            self._create_window()

        if self._window:
            self._window.makeKeyAndOrderFront_(None)
            # Bring app to front
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    def _create_window(self):
        """Create the settings window"""
        try:
            from AppKit import (
                NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
                NSBackingStoreBuffered, NSScreen, NSMakeRect,
                NSTextField, NSPopUpButton, NSButton, NSBox,
                NSFont, NSColor, NSTextAlignmentRight, NSTextAlignmentLeft,
                NSBezelStyleRounded, NSButtonTypeSwitch,
                NSView, NSApplication
            )

            # Window size and position
            width, height = 420, 320
            screen = NSScreen.mainScreen().frame()
            x = (screen.size.width - width) / 2
            y = (screen.size.height - height) / 2

            # Create window
            style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
            self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(x, y, width, height),
                style,
                NSBackingStoreBuffered,
                False
            )
            self._window.setTitle_("Sotto Settings")
            self._window.setReleasedWhenClosed_(False)

            content = self._window.contentView()
            y_pos = height - 50

            # === Mode Selection ===
            y_pos = self._add_label(content, "Mode:", 20, y_pos, width)
            mode_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(120, y_pos - 5, 200, 26), False
            )
            mode_popup.addItemsWithTitles_(["Push to Talk", "Always Listening"])
            if self.config.mode == "always_listening":
                mode_popup.selectItemAtIndex_(1)
            else:
                mode_popup.selectItemAtIndex_(0)
            content.addSubview_(mode_popup)
            self._controls['mode'] = mode_popup
            y_pos -= 45

            # === Push to Talk Hotkey ===
            y_pos = self._add_label(content, "Push to Talk:", 20, y_pos, width)
            hotkey_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(120, y_pos - 3, 200, 24)
            )
            hotkey_field.setStringValue_(self.config.hotkeys.push_to_talk)
            hotkey_field.setFont_(NSFont.systemFontOfSize_(13))
            content.addSubview_(hotkey_field)
            self._controls['hotkey'] = hotkey_field
            y_pos -= 45

            # === Model Selection ===
            y_pos = self._add_label(content, "Model:", 20, y_pos, width)
            model_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
                NSMakeRect(120, y_pos - 5, 200, 26), False
            )
            models = ["tiny.en", "base.en", "small.en", "medium.en", "large-v3"]
            model_popup.addItemsWithTitles_(models)
            # Select current model
            current_model = self.config.transcription.model
            if current_model in models:
                model_popup.selectItemWithTitle_(current_model)
            content.addSubview_(model_popup)
            self._controls['model'] = model_popup
            y_pos -= 45

            # === Separator ===
            separator = NSBox.alloc().initWithFrame_(NSMakeRect(20, y_pos, width - 40, 1))
            separator.setBoxType_(2)  # NSBoxSeparator
            content.addSubview_(separator)
            y_pos -= 25

            # === Overlay Enabled ===
            overlay_check = NSButton.alloc().initWithFrame_(
                NSMakeRect(20, y_pos, 200, 20)
            )
            overlay_check.setButtonType_(NSButtonTypeSwitch)
            overlay_check.setTitle_("Show overlay feedback")
            overlay_check.setState_(1 if self.config.feedback.overlay_enabled else 0)
            content.addSubview_(overlay_check)
            self._controls['overlay_enabled'] = overlay_check
            y_pos -= 35

            # === Custom Commands Note ===
            custom_label = NSTextField.alloc().initWithFrame_(
                NSMakeRect(20, y_pos, width - 40, 18)
            )
            custom_label.setStringValue_("Custom commands: Edit ~/.sotto/config.yaml")
            custom_label.setBezeled_(False)
            custom_label.setDrawsBackground_(False)
            custom_label.setEditable_(False)
            custom_label.setSelectable_(True)
            custom_label.setFont_(NSFont.systemFontOfSize_(11))
            custom_label.setTextColor_(NSColor.secondaryLabelColor())
            content.addSubview_(custom_label)
            y_pos -= 25

            # === Buttons ===
            # Cancel button
            cancel_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(width - 190, 15, 80, 32)
            )
            cancel_btn.setTitle_("Cancel")
            cancel_btn.setBezelStyle_(NSBezelStyleRounded)
            cancel_btn.setTarget_(self)
            cancel_btn.setAction_(b"cancelClicked:")
            content.addSubview_(cancel_btn)

            # Save button
            save_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(width - 100, 15, 80, 32)
            )
            save_btn.setTitle_("Save")
            save_btn.setBezelStyle_(NSBezelStyleRounded)
            save_btn.setKeyEquivalent_("\r")  # Enter key
            save_btn.setTarget_(self)
            save_btn.setAction_(b"saveClicked:")
            content.addSubview_(save_btn)

        except Exception as e:
            print(f"[Sotto] Error creating settings window: {e}")
            import traceback
            traceback.print_exc()

    def _add_label(self, parent, text: str, x: int, y: int, width: int) -> int:
        """Add a label and return current y position"""
        from AppKit import NSTextField, NSFont, NSColor, NSTextAlignmentRight

        label = NSTextField.alloc().initWithFrame_(
            ((x, y - 3), (90, 20))
        )
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setAlignment_(NSTextAlignmentRight)
        label.setFont_(NSFont.systemFontOfSize_(13))
        label.setTextColor_(NSColor.labelColor())
        parent.addSubview_(label)
        return y

    def cancelClicked_(self, sender):
        """Handle cancel button"""
        if self._window:
            self._window.close()

    def saveClicked_(self, sender):
        """Handle save button"""
        try:
            # Read values from controls
            mode_index = self._controls['mode'].indexOfSelectedItem()
            self.config.mode = "always_listening" if mode_index == 1 else "push_to_talk"

            self.config.hotkeys.push_to_talk = self._controls['hotkey'].stringValue()

            self.config.transcription.model = self._controls['model'].titleOfSelectedItem()

            overlay_state = self._controls['overlay_enabled'].state()
            self.config.feedback.overlay_enabled = (overlay_state == 1)

            # Save to disk
            self.config.save()

            # Close window
            if self._window:
                self._window.close()

            # Notify callback
            if self.on_save:
                self.on_save(self.config)

            print("[Sotto] Settings saved")

        except Exception as e:
            print(f"[Sotto] Error saving settings: {e}")
            import traceback
            traceback.print_exc()


def show_settings_window(config, on_save: Optional[Callable] = None):
    """
    Show the settings window (singleton).

    Args:
        config: SottoConfig instance
        on_save: Callback when settings are saved
    """
    global _settings_window

    if _settings_window is None:
        _settings_window = SettingsWindowController(config, on_save)

    _settings_window.config = config
    _settings_window.on_save = on_save
    _settings_window.show()
