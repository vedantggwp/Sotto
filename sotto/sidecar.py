"""
Sotto Sidecar Entry Point
Communicates with Tauri v2 UI via stdin/stdout JSON.

Usage (Tauri spawns this as a sidecar):
    python -m sotto.sidecar

The process:
  1. Preloads the Whisper model.
  2. Reads JSON command lines from stdin.
  3. Dispatches to AudioEngine / Transcriber / CommandParser / CommandExecutor.
  4. Streams AudioLevelMsg at ~20 Hz while recording.
  5. On stop_recording: transcribes, parses intent, executes, reports result.
"""

import atexit
import math
import signal
import sys
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

from sotto.core.audio import AudioEngine
from sotto.core.command_parser import CommandParser, IntentType
from sotto.core.executor import CommandExecutor
from sotto.core.transcriber import Transcriber
from sotto.protocol import (
    AudioLevelMsg,
    CommandMsg,
    ErrorMsg,
    StateChangeMsg,
    TranscriptionMsg,
    decode_command,
    send,
)

# Minimum recorded duration (seconds) to attempt transcription.
# Audio shorter than this is almost certainly noise or an accidental tap.
MIN_AUDIO_DURATION_S = 0.1

# Audio sample rate — must match AudioEngine.SAMPLE_RATE
SAMPLE_RATE = 16_000

# Flag set by signal handlers to request clean shutdown from the main loop.
# Signal handlers must NOT call cleanup directly — deadlock risk with audio lock.
_shutdown_requested = threading.Event()


# ---------------------------------------------------------------------------
# Engine composition
# ---------------------------------------------------------------------------

@dataclass
class SidecarEngine:
    """Thin container that owns all sub-systems used by the sidecar."""
    audio: AudioEngine
    transcriber: Transcriber
    parser: CommandParser
    executor: CommandExecutor


def _build_engine() -> SidecarEngine:
    """Instantiate and return a fully wired SidecarEngine (no hotkeys, no UI)."""
    return SidecarEngine(
        audio=AudioEngine(),
        transcriber=Transcriber(),
        parser=CommandParser(),
        executor=CommandExecutor(),
    )


def _compute_rms(chunk: np.ndarray) -> float:
    """Return RMS amplitude of *chunk* clamped to [0.0, 1.0]."""
    rms = math.sqrt(float(np.mean(chunk ** 2)))
    return min(1.0, rms)


def _make_audio_callback():
    """
    Return a closure to pass to AudioEngine.start_recording(on_audio=...).

    The closure is called on the audio capture thread at ~31 ms intervals
    (512 samples / 16 kHz). It sends an AudioLevelMsg per call.
    Stdout writes for short lines are atomic on Unix, so no extra lock needed.
    """
    def _on_audio(chunk: np.ndarray) -> None:
        level = _compute_rms(chunk)
        send(AudioLevelMsg(level=level))

    return _on_audio


# ---------------------------------------------------------------------------
# Command dispatch
# ---------------------------------------------------------------------------

def handle_command(cmd: CommandMsg, engine: SidecarEngine) -> str:
    """
    Dispatch *cmd* to the appropriate sub-system.

    Returns a short status string describing the outcome:
        "recording"  – start_recording succeeded
        "done"       – stop_recording: audio transcribed & executed
        "idle"       – stop_recording: audio too short, nothing done
        "config_set" – set_config applied
        "quit"       – caller should exit the read loop
        "unknown"    – unrecognised command (non-fatal)
    """
    command = cmd.command

    if command == "start_recording":
        send(StateChangeMsg(state="listening"))
        engine.audio.start_recording(on_audio=_make_audio_callback())
        return "recording"

    if command == "stop_recording":
        audio = engine.audio.stop_recording()
        duration_s = len(audio) / SAMPLE_RATE

        if duration_s < MIN_AUDIO_DURATION_S:
            send(StateChangeMsg(state="idle"))
            return "idle"

        send(StateChangeMsg(state="transcribing"))

        text, _confidence = engine.transcriber.transcribe(audio)

        if text:
            intent = engine.parser.parse(text)
            if intent.intent_type == IntentType.DICTATION:
                engine.executor.type_text(intent.text)
            elif intent.intent_type in (IntentType.COMMAND, IntentType.CONTROL):
                engine.executor.execute(
                    intent.command_name or "",
                    intent.command_args or {},
                )

        send(TranscriptionMsg(text=text))
        send(StateChangeMsg(state="done"))
        return "done"

    if command == "set_config":
        # key/value are both Optional[str]; ignore if either is absent
        if cmd.key and cmd.value is not None:
            _apply_config(cmd.key, cmd.value, engine)
        return "config_set"

    if command == "quit":
        send(StateChangeMsg(state="idle"))
        return "quit"

    # Unrecognised — log via protocol so Tauri can surface it
    send(ErrorMsg(error=f"Unknown command: {command!r}"))
    return "unknown"


def _apply_config(key: str, value: str, engine: SidecarEngine) -> None:
    """Apply a runtime configuration change."""
    leaf_key = key.split(".")[-1] if "." in key else key
    if leaf_key == "model":
        # Hot-swap the Whisper model; unload first to free RAM
        engine.transcriber.unload_model()
        engine.transcriber.model_name = value
        # Lazy-load on next transcription
    # Additional config keys can be handled here in future


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def _cleanup(engine_ref: list) -> None:
    """
    Release audio streams and Whisper model. Called from the main thread
    after the stdin loop exits — never from a signal handler (deadlock risk).
    Safe to call multiple times.
    """
    if not engine_ref:
        return
    eng = engine_ref[0]
    try:
        eng.audio.shutdown()
    except Exception:
        pass
    try:
        eng.transcriber.unload_model()
    except Exception:
        pass


def _signal_handler(signum, frame):
    """Set the shutdown flag. Cleanup runs from the main thread, not here."""
    _shutdown_requested.set()


# ---------------------------------------------------------------------------
# Main read loop
# ---------------------------------------------------------------------------

def run(engine: Optional[SidecarEngine] = None) -> None:
    """
    Block on stdin, reading one JSON command per line.
    Exits when 'quit' is received, stdin is closed (Tauri died), or SIGTERM.
    """
    if engine is None:
        engine = _build_engine()

    engine_ref = [engine]
    atexit.register(_cleanup, engine_ref)

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    send(StateChangeMsg(state="idle"))

    # Preload Whisper so first recording feels instant
    engine.transcriber.load_model()

    for raw_line in sys.stdin:
        # Check if a signal requested shutdown
        if _shutdown_requested.is_set():
            break

        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            cmd = decode_command(raw_line)
        except (ValueError, KeyError) as exc:
            send(ErrorMsg(error=str(exc)))
            continue

        try:
            result = handle_command(cmd, engine)
        except Exception as exc:  # noqa: BLE001 — surface all engine errors
            send(ErrorMsg(error=f"Engine error handling {cmd.command!r}: {exc}"))
            continue

        if result == "quit":
            break

    # stdin closed (Tauri died) or quit/signal received — clean up from main thread
    _cleanup(engine_ref)


if __name__ == "__main__":
    run()
