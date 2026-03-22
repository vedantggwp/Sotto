"""
Sotto - Main Application
Integrates all components for voice control.
"""

import argparse
import os
import signal
import sys
import threading
import time

from .config import ensure_directories, get_config
from .core.audio import AudioEngine, VoiceActivityDetector
from .core.command_parser import CommandParser, IntentType
from .core.executor import CommandExecutor
from .core.hotkeys import HotkeyManager
from .core.transcriber import Transcriber
from .utils.logging import get_logger, setup_logging
from .utils.permissions import check_accessibility_permissions, prompt_for_accessibility

# Global logger
logger = get_logger("main")


class _NoOpOverlay:
    """Stub overlay that logs messages instead of showing native UI.
    The real overlay now lives in the Tauri frontend."""

    def show(self, message: str, icon: str = "") -> None:
        logger.debug(f"[overlay] {icon} {message}")

    def show_success(self, message: str) -> None:
        logger.debug(f"[overlay] {message}")

    def show_error(self, message: str) -> None:
        logger.warning(f"[overlay] {message}")

    def show_transcription(self, text: str) -> None:
        logger.debug(f"[overlay] transcription: {text}")


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
        logger.info("🎙️ Initializing Sotto...")

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
            compute_type=self.config.transcription.compute_type,
        )
        self.parser = CommandParser()
        self.executor = CommandExecutor(on_status=self._on_executor_status)

        # Overlay is created lazily (after rumps starts in GUI mode)
        self._overlay = None

        # State
        self._is_listening = False
        self._running = True
        self._state_lock = threading.Lock()
        self._process_lock = threading.Lock()
        self.menubar = None

        # Hotkeys
        self.hotkey_manager = HotkeyManager(
            ptt_hotkey=self.config.hotkeys.push_to_talk,
            toggle_hotkey=self.config.hotkeys.toggle_listening,
            on_ptt_start=self._on_ptt_start,
            on_ptt_end=self._on_ptt_end,
            on_toggle=self._toggle_always_listening,
        )

        logger.info("✅ Sotto initialized")

    @property
    def overlay(self):
        """Lazy overlay creation - returns a no-op stub (real UI is now Tauri)"""
        if self._overlay is None:
            self._overlay = _NoOpOverlay()
        return self._overlay

    def _on_executor_status(self, message: str):
        """Handle executor status messages"""
        logger.info(f"[Executor] {message}")

        # Show in overlay with appropriate icon
        if self.config.feedback.overlay_enabled:
            if message.startswith("✅"):
                self.overlay.show_success(message)
            elif message.startswith("❌") or message.startswith("❓"):
                self.overlay.show_error(message)
            else:
                self.overlay.show(message, "⚡")

    def _on_ptt_start(self):
        """Callback: Push-to-Talk started"""
        if self.config.mode == "push_to_talk":
            logger.info("🎤 Push-to-Talk: Recording...")
            self._start_recording()

    def _on_ptt_end(self):
        """Callback: Push-to-Talk ended"""
        if self.config.mode == "push_to_talk":
            logger.info("🎤 Push-to-Talk: Stopped")
            self._stop_recording()

    def _toggle_always_listening(self):
        """Callback: Toggle always listening mode"""
        if self.config.mode == "always_listening":
            with self._state_lock:
                listening = self._is_listening
            if listening:
                self._stop_listening()
            else:
                self._start_listening()
        else:
            logger.info("Ignored toggle: Not in always_listening mode")

    def _start_recording(self):
        """Start recording audio"""
        if self.audio.is_recording():
            return

        self.audio.start_recording()

        # Show recording indicator
        if self.config.feedback.overlay_enabled:
            self.overlay.show("🎤 Listening...", "")

    def _stop_recording(self):
        """Stop recording and process audio"""
        if not self.audio.is_recording():
            return

        audio_data = self.audio.stop_recording()
        duration = len(audio_data) / 16000  # 16kHz sample rate

        # Process in background
        if len(audio_data) > 0 and duration > 0.3:  # At least 0.3 seconds
            logger.info(f"Processing {duration:.1f}s of audio...")
            if self.config.feedback.overlay_enabled:
                self.overlay.show("Processing...", "⏳")
            threading.Thread(target=self._process_audio, args=(audio_data,), daemon=True).start()
        else:
            logger.debug("Recording too short, ignoring")
            if self.config.feedback.overlay_enabled:
                self.overlay.show("Too short", "❓")

    def _start_listening(self):
        """Start always-listening mode"""
        with self._state_lock:
            if self._is_listening:
                return
            self._is_listening = True
        logger.info("Always-listening mode ON")
        self.overlay.show("Always listening mode ON", "🎤")

        # Start continuous listening thread
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _stop_listening(self):
        """Stop always-listening mode"""
        with self._state_lock:
            self._is_listening = False
        logger.info("Always-listening mode OFF")
        self.overlay.show("Listening stopped", "⏹️")

    def _listen_loop(self):
        """Continuous listening loop for always-listening mode"""
        vad = VoiceActivityDetector(energy_threshold=0.01, silence_duration=1.0)

        logger.debug("Starting VAD loop")
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
            self.audio.stop_recording()

            # Process if we detected speech
            if speech_detected and len(audio_buffer) > 0:
                import numpy as np

                audio = np.concatenate(audio_buffer)
                if len(audio) > 8000:  # At least 0.5 seconds
                    self._process_audio(audio)

            vad.reset()
            time.sleep(0.1)

    def _process_audio(self, audio_data):
        """Process recorded audio (serialized to prevent interleaved execution)"""
        with self._process_lock:
            self._process_audio_inner(audio_data)

    def _process_audio_inner(self, audio_data):
        """Inner audio processing logic"""
        try:
            # Transcribe
            text, confidence = self.transcriber.transcribe(
                audio_data, language=self.config.transcription.language
            )

            if not text:
                self.overlay.show("Could not understand", "❓")
                logger.debug("No speech detected (empty transcription)")
                return

            # Parse intent
            intent = self.parser.parse(text)
            display = self.parser.format_for_display(intent)

            logger.info(f"Heard: '{text}' | Action: {display}")

            if self.config.feedback.overlay_enabled:
                self.overlay.show(display)

            # Execute action
            if intent.intent_type == IntentType.COMMAND:
                if intent.command_name == "unknown":
                    logger.warning(f"Unknown command: {text}")
                    self.overlay.show(f"Unknown command: {text}", "❓")
                else:
                    logger.info(f"Executing: {intent.command_name}")
                    self.executor.execute(intent.command_name, intent.command_args)

            elif intent.intent_type == IntentType.CONTROL:
                logger.info(f"Control: {intent.command_name}")
                self._handle_control_command(intent.command_name)

            elif intent.intent_type == IntentType.DICTATION:
                logger.info(f"Typing: {text}")
                self.executor.type_text(text + " ")
                self.overlay.show_transcription(text)

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
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

    def start(self):
        """Start Sotto (non-blocking)"""
        # Load model in background
        logger.info("Loading Whisper model...")
        threading.Thread(target=self.transcriber.load_model, daemon=True).start()

        # Start hotkey listener
        self.hotkey_manager.start()

        # Start always listening if configured
        if self.config.mode == "always_listening":
            self._start_listening()

        self.overlay.show_success("Sotto is ready!")

    def stop(self):
        """Stop Sotto"""
        logger.info("Stopping Sotto...")
        self._running = False
        self._is_listening = False
        self.hotkey_manager.stop()

    def run(self):
        """Run Sotto in CLI mode (Blocking)"""
        if not check_accessibility_permissions():
            prompt_for_accessibility()

        print("\n" + "=" * 50)
        print("🎙️ Sotto is running (CLI Mode)")
        print(f"   Logs: {self.config.feedback.overlay_enabled}")
        print("=" * 50 + "\n")

        self.start()

        # Handle signals
        self._running = True
        try:
            while self._running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n👋 Stopping...")
        finally:
            self.stop()
            sys.exit(0)

    def run_with_menubar(self):
        """Run with menubar UI (for GUI mode)"""
        import rumps

        from .ui.menubar import SottoMenubar

        sotto_app = self

        # Check permissions early
        if not check_accessibility_permissions():
            prompt_for_accessibility()

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
            # Same logic as before
            sotto_app.config.transcription.model = model
            logger.info(f"Switching model: {model}")
            sotto_app.transcriber = Transcriber(
                model_name=model,
                device=sotto_app.config.transcription.device,
                compute_type=sotto_app.config.transcription.compute_type,
            )
            threading.Thread(target=sotto_app.transcriber.load_model, daemon=True).start()
            sotto_app.overlay.show_success(f"Model: {model}")

        def on_quit():
            sotto_app.stop()

        self.menubar = SottoMenubar(
            on_toggle_listening=on_toggle,
            on_mode_change=on_mode_change,
            on_model_change=on_model_change,
            on_quit=on_quit,
        )

        @rumps.timer(0.5)
        def initialize_components(timer):
            timer.stop()
            sotto_app.start()

        logger.info("Starting menubar...")
        self.menubar.run()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Sotto - Voice Control for macOS")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--model", help="Whisper model to use")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    # Setup Logging
    setup_logging(debug=args.debug)
    if args.debug:
        os.environ["SOTTO_DEBUG"] = "1"

    # Load config
    config = get_config()
    if args.model:
        config.transcription.model = args.model

    if args.cli:
        app = Sotto(gui_mode=False)
        app.run()
    else:
        app = Sotto(gui_mode=True)
        app.run_with_menubar()


if __name__ == "__main__":
    main()
