"""
Sotto - Main Application
Integrates all components for voice control.
"""

import sys
import threading
import time
import signal
from typing import Optional

from pynput import keyboard

from .config import get_config, ensure_directories, SottoConfig


def check_accessibility_permissions() -> bool:
    """Check if we have accessibility permissions for global hotkeys."""
    try:
        # Use ApplicationServices to check accessibility trust
        from ApplicationServices import AXIsProcessTrusted
        return AXIsProcessTrusted()
    except ImportError:
        # Fallback: assume we need to warn if we get the pynput error
        return True  # Can't check, assume OK
    except Exception:
        return True


def print_accessibility_instructions():
    """Print instructions for granting accessibility permissions."""
    print("\n" + "=" * 60)
    print("⚠️  ACCESSIBILITY PERMISSIONS REQUIRED")
    print("=" * 60)
    print("""
Sotto needs Accessibility permissions to capture hotkeys.

To enable:
1. Open System Settings > Privacy & Security > Accessibility
2. Click the '+' button
3. Add your terminal app (Terminal, iTerm2, etc.) or the Sotto app
4. Toggle the switch to enable it
5. Restart Sotto

Without this permission, push-to-talk hotkeys won't work.
You can still use 'always_listening' mode via the menubar.
""")
    print("=" * 60 + "\n")


from .core.audio import AudioEngine, VoiceActivityDetector
from .core.transcriber import Transcriber
from .core.command_parser import CommandParser, IntentType
from .core.executor import CommandExecutor

# Global debug flag
DEBUG = False


def debug_print(*args, **kwargs):
    """Print only if debug mode is enabled"""
    if DEBUG:
        print(*args, **kwargs)


class Sotto:
    """
    Main Sotto application.
    Coordinates all components for voice control.
    """

    def __init__(self, gui_mode: bool = False):
        """
        Initialize Sotto.

        Args:
            gui_mode: If True, delay overlay creation until after rumps starts
        """
        print("🎙️ Initializing Sotto...")

        # Ensure directories exist
        ensure_directories()

        # Load configuration
        self.config = get_config()
        self._gui_mode = gui_mode

        # Initialize core components (no UI yet)
        self.audio = AudioEngine()
        self.transcriber = Transcriber(
            model_name=self.config.transcription.model,
            device=self.config.transcription.device,
            compute_type=self.config.transcription.compute_type
        )
        self.parser = CommandParser()
        self.executor = CommandExecutor(on_status=self._on_executor_status)

        # Overlay is created lazily (after rumps starts in GUI mode)
        self._overlay = None

        # State
        self._is_listening = False
        self._is_recording = False
        self._running = True
        self._hotkey_listener = None
        self._push_to_talk_pressed = False
        self.menubar = None

        # Parse hotkeys
        self._setup_hotkeys()

        print("✅ Sotto initialized")

    @property
    def overlay(self):
        """Lazy overlay creation - ensures it's created after NSApplication exists"""
        if self._overlay is None:
            from .ui.overlay import create_overlay
            self._overlay = create_overlay(
                duration=self.config.feedback.overlay_duration,
                position=self.config.feedback.overlay_position
            )
        return self._overlay
    
    def _setup_hotkeys(self):
        """Setup global hotkeys"""
        # Convert config hotkeys to pynput format
        def parse_hotkey(hotkey_str: str):
            """Parse hotkey string to pynput keys"""
            parts = hotkey_str.replace('<', '').replace('>', '').split('+')
            keys = set()
            for part in parts:
                part = part.strip().lower()
                if part == 'cmd':
                    keys.add(keyboard.Key.cmd)
                elif part == 'ctrl':
                    keys.add(keyboard.Key.ctrl)
                elif part == 'shift':
                    keys.add(keyboard.Key.shift)
                elif part == 'alt':
                    keys.add(keyboard.Key.alt)
                elif part == 'space':
                    keys.add(keyboard.Key.space)
                elif len(part) == 1:
                    keys.add(keyboard.KeyCode.from_char(part))
            return keys
        
        self._push_to_talk_keys = parse_hotkey(self.config.hotkeys.push_to_talk)
        self._toggle_keys = parse_hotkey(self.config.hotkeys.toggle_listening)
        self._current_keys = set()
    
    def _on_executor_status(self, message: str):
        """Handle executor status messages"""
        # Always print to terminal
        print(f"[Sotto] {message}")

        # Show in overlay with appropriate icon
        if self.config.feedback.overlay_enabled:
            if message.startswith("✅"):
                self.overlay.show_success(message)
            elif message.startswith("❌") or message.startswith("❓"):
                self.overlay.show_error(message)
            else:
                self.overlay.show(message, "⚡")
    
    def _on_key_press(self, key):
        """Handle key press events"""
        self._current_keys.add(key)

        # Check for push-to-talk
        if self._push_to_talk_keys.issubset(self._current_keys):
            if not self._push_to_talk_pressed and self.config.mode == "push_to_talk":
                self._push_to_talk_pressed = True
                print("[Sotto] 🎤 Recording... (release hotkey to stop)")
                self._start_recording()
        
        # Check for toggle listening
        if self._toggle_keys.issubset(self._current_keys):
            self._toggle_always_listening()
    
    def _on_key_release(self, key):
        """Handle key release events"""
        try:
            self._current_keys.discard(key)
        except:
            pass
        
        # Check if push-to-talk was released
        if self._push_to_talk_pressed:
            if not self._push_to_talk_keys.issubset(self._current_keys):
                self._push_to_talk_pressed = False
                if self.config.mode == "push_to_talk" and self._is_recording:
                    self._stop_recording()
    
    def _toggle_always_listening(self):
        """Toggle always listening mode"""
        if self.config.mode == "always_listening":
            if self._is_listening:
                self._stop_listening()
            else:
                self._start_listening()
    
    def _start_recording(self):
        """Start recording audio"""
        if self._is_recording:
            return

        self._is_recording = True
        self.audio.start_recording()

        # Show recording indicator
        if self.config.feedback.overlay_enabled:
            self.overlay.show("🎤 Listening...", "")
    
    def _stop_recording(self):
        """Stop recording and process audio"""
        if not self._is_recording:
            return

        self._is_recording = False
        audio_data = self.audio.stop_recording()
        duration = len(audio_data) / 16000  # 16kHz sample rate

        # Process in background
        if len(audio_data) > 0 and duration > 0.3:  # At least 0.3 seconds
            print(f"[Sotto] ⏳ Processing {duration:.1f}s of audio...")
            if self.config.feedback.overlay_enabled:
                self.overlay.show("Processing...", "⏳")
            threading.Thread(target=self._process_audio, args=(audio_data,), daemon=True).start()
        else:
            print("[Sotto] Recording too short, ignoring")
            if self.config.feedback.overlay_enabled:
                self.overlay.show("Too short", "❓")
    
    def _start_listening(self):
        """Start always-listening mode"""
        if self._is_listening:
            return
        
        self._is_listening = True
        self.overlay.show("Always listening mode ON", "🎤")
        
        # Start continuous listening thread
        threading.Thread(target=self._listen_loop, daemon=True).start()
    
    def _stop_listening(self):
        """Stop always-listening mode"""
        self._is_listening = False
        self.overlay.show("Listening stopped", "⏹️")
    
    def _listen_loop(self):
        """Continuous listening loop for always-listening mode"""
        vad = VoiceActivityDetector(energy_threshold=0.01, silence_duration=1.0)
        
        while self._is_listening and self._running:
            # Start recording
            self.audio.start_recording()
            audio_buffer = []
            speech_detected = False
            
            # Listen until silence
            while self._is_listening and self._running:
                chunk = self.audio.get_audio_chunk(timeout=0.1)
                if chunk is not None:
                    audio_buffer.append(chunk)
                    
                    if vad.is_speech(chunk):
                        speech_detected = True
                    
                    if speech_detected and vad.check_silence_timeout(chunk):
                        break
            
            # Stop recording
            audio_data = self.audio.stop_recording()
            
            # Process if we detected speech
            if speech_detected and len(audio_buffer) > 0:
                import numpy as np
                audio = np.concatenate(audio_buffer)
                if len(audio) > 8000:  # At least 0.5 seconds
                    self._process_audio(audio)
            
            vad.reset()
            time.sleep(0.1)
    
    def _process_audio(self, audio_data):
        """Process recorded audio"""
        debug_print(f"[Process] Starting transcription of {len(audio_data)} samples...")
        try:
            # Transcribe
            text, confidence = self.transcriber.transcribe(
                audio_data,
                language=self.config.transcription.language
            )

            if not text:
                self.overlay.show("Could not understand", "❓")
                print("[Sotto] No speech detected")
                return

            # Parse intent
            intent = self.parser.parse(text)
            display = self.parser.format_for_display(intent)

            # Always show what was heard and what we're doing
            print(f"[Sotto] Heard: '{text}'")
            print(f"[Sotto] Action: {display}")

            if self.config.feedback.overlay_enabled:
                self.overlay.show(display)

            # Execute action
            if intent.intent_type == IntentType.COMMAND:
                if intent.command_name == "unknown":
                    print(f"[Sotto] ❓ Unknown command")
                    self.overlay.show(f"Unknown command: {text}", "❓")
                else:
                    print(f"[Sotto] ⚡ Executing: {intent.command_name}")
                    self.executor.execute(intent.command_name, intent.command_args)

            elif intent.intent_type == IntentType.CONTROL:
                print(f"[Sotto] 🎛️ Control: {intent.command_name}")
                self._handle_control_command(intent.command_name)

            elif intent.intent_type == IntentType.DICTATION:
                # Type the text
                print(f"[Sotto] 📝 Typing: {text}")
                self.executor.type_text(text + " ")
                self.overlay.show_transcription(text)
            
        except Exception as e:
            print(f"Error processing audio: {e}")
            self.overlay.show_error(str(e))
    
    def _handle_control_command(self, command: str):
        """Handle Sotto control commands"""
        if command == "sotto_stop":
            self._stop_listening()
        elif command == "sotto_start":
            self._start_listening()
        elif command == "sotto_command_mode":
            self.config.mode = "push_to_talk"
            self.overlay.show("Command mode (push to talk)", "🎛️")
        elif command == "sotto_dictation_mode":
            self.config.mode = "always_listening"
            self._start_listening()
            self.overlay.show("Dictation mode (always listening)", "🎛️")
    
    def run(self):
        """Run the Sotto application"""
        # Check accessibility permissions
        if not check_accessibility_permissions():
            print_accessibility_instructions()

        print("\n" + "=" * 50)
        print("🎙️ Sotto is running!")
        print("=" * 50)
        print(f"\n📋 Mode: {self.config.mode}")
        print(f"🎹 Push to Talk: {self.config.hotkeys.push_to_talk}")
        print(f"🔄 Toggle Listening: {self.config.hotkeys.toggle_listening}")
        print("\n💡 Tips:")
        print("  • Hold the hotkey and speak")
        print("  • Say commands like 'open Safari' or 'volume up'")
        print("  • Just speak to dictate text")
        print("  • Press Ctrl+C to quit")
        print("\n" + "=" * 50 + "\n")
        
        # Load model in background
        print("📦 Loading Whisper model (this may take a moment)...")
        self.transcriber.load_model()
        
        # Setup hotkey listener
        self._hotkey_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._hotkey_listener.start()
        
        # Handle shutdown
        def signal_handler(sig, frame):
            print("\n👋 Shutting down Sotto...")
            self._running = False
            self._is_listening = False
            if self._hotkey_listener:
                self._hotkey_listener.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start in always listening mode if configured
        if self.config.mode == "always_listening":
            self._start_listening()
        
        # Keep running
        self.overlay.show_success("Sotto is ready!")
        
        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            signal_handler(None, None)
    
    def run_with_menubar(self):
        """Run with menubar UI (for GUI mode)"""
        import rumps
        from .ui.menubar import SottoMenubar

        sotto_app = self  # Reference for callbacks

        def on_toggle():
            if sotto_app.config.mode == "push_to_talk":
                pass
            else:
                if sotto_app._is_listening:
                    sotto_app._stop_listening()
                else:
                    sotto_app._start_listening()

        def on_mode_change(mode):
            sotto_app.config.mode = mode
            if mode == "always_listening" and not sotto_app._is_listening:
                sotto_app._start_listening()
            elif mode == "push_to_talk":
                sotto_app._stop_listening()

        def on_model_change(model):
            sotto_app.config.transcription.model = model
            print(f"🔄 Switching to model: {model}")
            sotto_app.transcriber = Transcriber(
                model_name=model,
                device=sotto_app.config.transcription.device,
                compute_type=sotto_app.config.transcription.compute_type
            )
            sotto_app.transcriber.load_model()
            sotto_app.overlay.show_success(f"Model: {model}")

        def on_quit():
            sotto_app._running = False
            sotto_app._is_listening = False
            if sotto_app._hotkey_listener:
                sotto_app._hotkey_listener.stop()

        # Create menubar app FIRST (this sets up NSApplication)
        self.menubar = SottoMenubar(
            on_toggle_listening=on_toggle,
            on_mode_change=on_mode_change,
            on_model_change=on_model_change,
            on_quit=on_quit
        )

        # Use rumps timer to initialize after runloop starts
        @rumps.timer(0.5)  # Run once after 0.5 seconds
        def initialize_components(timer):
            timer.stop()  # Only run once

            print("📦 Loading Whisper model...")
            sotto_app.transcriber.load_model()
            print("✅ Model loaded")

            # Start hotkey listener
            sotto_app._hotkey_listener = keyboard.Listener(
                on_press=sotto_app._on_key_press,
                on_release=sotto_app._on_key_release
            )
            sotto_app._hotkey_listener.start()
            print("✅ Hotkey listener started")

            # NOW create and show overlay (NSApplication exists)
            sotto_app.overlay.show_success("Sotto is ready!")
            print("✅ Sotto is ready!")

        # Start the menubar app (this blocks and runs the NSRunLoop)
        print("Starting menubar...")
        self.menubar.run()


def main():
    """Main entry point"""
    global DEBUG
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Sotto - Voice Control for macOS")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (no menubar)")
    parser.add_argument("--model", help="Whisper model to use (overrides config)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Set debug mode
    DEBUG = args.debug
    if args.debug:
        os.environ['SOTTO_DEBUG'] = '1'

    # Load config
    config = get_config()

    # Override model if specified on command line
    if args.model:
        config.transcription.model = args.model

    print("=" * 50)
    print("🎙️ Sotto - Voice Control for macOS")
    print("=" * 50)

    if args.cli:
        # CLI mode - terminal only, create overlay immediately
        print("Running in CLI mode (no menubar)")
        app = Sotto(gui_mode=False)
        app.run()
    else:
        # GUI mode - menubar app, delay overlay until rumps starts
        print("Running with menubar UI")
        print(f"Hotkey: {config.hotkeys.push_to_talk}")
        print(f"Model: {config.transcription.model}")
        print("=" * 50)
        app = Sotto(gui_mode=True)
        app.run_with_menubar()


if __name__ == "__main__":
    main()
