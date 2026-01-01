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
from .core.audio import AudioEngine, VoiceActivityDetector
from .core.transcriber import Transcriber
from .core.command_parser import CommandParser, IntentType
from .core.executor import CommandExecutor
from .ui.overlay import create_overlay


class Sotto:
    """
    Main Sotto application.
    Coordinates all components for voice control.
    """
    
    def __init__(self):
        """Initialize Sotto"""
        print("🎙️ Initializing Sotto...")
        
        # Ensure directories exist
        ensure_directories()
        
        # Load configuration
        self.config = get_config()
        
        # Initialize components
        self.audio = AudioEngine()
        self.transcriber = Transcriber(
            model_name=self.config.transcription.model,
            device=self.config.transcription.device,
            compute_type=self.config.transcription.compute_type
        )
        self.parser = CommandParser()
        self.executor = CommandExecutor(on_status=self._on_executor_status)
        self.overlay = create_overlay(
            duration=self.config.feedback.overlay_duration,
            position=self.config.feedback.overlay_position
        )
        
        # State
        self._is_listening = False
        self._is_recording = False
        self._running = True
        self._hotkey_listener = None
        self._push_to_talk_pressed = False
        
        # Parse hotkeys
        self._setup_hotkeys()
        
        print("✅ Sotto initialized")
    
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
        if self.config.feedback.overlay_enabled:
            self.overlay.show(message, "⚡")
    
    def _on_key_press(self, key):
        """Handle key press events"""
        self._current_keys.add(key)
        
        # Check for push-to-talk
        if self._push_to_talk_keys.issubset(self._current_keys):
            if not self._push_to_talk_pressed and self.config.mode == "push_to_talk":
                self._push_to_talk_pressed = True
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
        self.overlay.show_listening()
        self.audio.start_recording()
        print("🎤 Recording started")
    
    def _stop_recording(self):
        """Stop recording and process audio"""
        if not self._is_recording:
            return
        
        self._is_recording = False
        audio_data = self.audio.stop_recording()
        print(f"⏹️ Recording stopped ({len(audio_data)} samples)")
        
        # Process in background
        if len(audio_data) > 0:
            threading.Thread(target=self._process_audio, args=(audio_data,), daemon=True).start()
    
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
        try:
            # Transcribe
            self.overlay.show("Processing...", "⏳")
            text, confidence = self.transcriber.transcribe(
                audio_data,
                language=self.config.transcription.language
            )
            
            if not text or confidence < 0.3:
                self.overlay.show("Could not understand", "❓")
                return
            
            print(f"📝 Transcribed: '{text}' (confidence: {confidence:.2f})")
            
            # Parse intent
            intent = self.parser.parse(text)
            display = self.parser.format_for_display(intent)
            
            if self.config.feedback.overlay_enabled:
                self.overlay.show(display)
            
            # Execute action
            if intent.intent_type == IntentType.COMMAND:
                if intent.command_name == "unknown":
                    self.overlay.show(f"Unknown command: {text}", "❓")
                else:
                    self.executor.execute(intent.command_name, intent.command_args)
            
            elif intent.intent_type == IntentType.CONTROL:
                self._handle_control_command(intent.command_name)
            
            elif intent.intent_type == IntentType.DICTATION:
                # Type the text
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
        from .ui.menubar import SottoMenubar
        
        def on_toggle():
            if self.config.mode == "push_to_talk":
                # In push-to-talk mode, toggle doesn't make sense from menu
                pass
            else:
                if self._is_listening:
                    self._stop_listening()
                else:
                    self._start_listening()
        
        def on_mode_change(mode):
            self.config.mode = mode
            if mode == "always_listening" and not self._is_listening:
                self._start_listening()
            elif mode == "push_to_talk":
                self._stop_listening()
        
        def on_quit():
            self._running = False
            self._is_listening = False
        
        # Load model
        print("📦 Loading Whisper model...")
        self.transcriber.load_model()
        
        # Setup hotkey listener
        self._hotkey_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._hotkey_listener.start()
        
        # Create and run menubar app
        self.menubar = SottoMenubar(
            on_toggle_listening=on_toggle,
            on_mode_change=on_mode_change,
            on_quit=on_quit
        )
        
        self.overlay.show_success("Sotto is ready!")
        self.menubar.run()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sotto - Voice Control for macOS")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode (no menubar)")
    parser.add_argument("--model", default="base.en", help="Whisper model to use")
    args = parser.parse_args()
    
    # Update config if model specified
    config = get_config()
    if args.model:
        config.transcription.model = args.model
    
    # Create and run app
    app = Sotto()
    
    if args.cli:
        app.run()
    else:
        app.run_with_menubar()


if __name__ == "__main__":
    main()
