"""
Sotto IPC Protocol
JSON message definitions for Tauri <-> Python sidecar communication.

Engine -> Tauri (stdout): one JSON line per message
Tauri -> Engine (stdin):  one JSON line per command
"""

import json
import sys
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Engine -> Tauri messages (stdout)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StateChangeMsg:
    """Notify Tauri that the engine state has changed."""
    state: str  # "idle" | "listening" | "processing"

    def to_dict(self) -> dict:
        return {"type": "state_change", "state": self.state}


@dataclass(frozen=True)
class AudioLevelMsg:
    """Streaming audio RMS level during recording (0.0 – 1.0)."""
    level: float

    def to_dict(self) -> dict:
        return {"type": "audio_level", "level": self.level}


@dataclass(frozen=True)
class TranscriptionMsg:
    """Transcribed text result after stop_recording."""
    text: str

    def to_dict(self) -> dict:
        return {"type": "transcription", "text": self.text}


@dataclass(frozen=True)
class ErrorMsg:
    """Report an engine error to Tauri."""
    error: str

    def to_dict(self) -> dict:
        return {"type": "error", "error": self.error}


# Union type for type hints
EngineMsg = StateChangeMsg | AudioLevelMsg | TranscriptionMsg | ErrorMsg


# ---------------------------------------------------------------------------
# Tauri -> Engine commands (stdin)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CommandMsg:
    """
    A command sent from Tauri to the Python engine.

    Fields:
        command: one of "start_recording" | "stop_recording" | "set_config" | "quit"
        key:     present for "set_config"
        value:   present for "set_config"
    """
    command: str
    key: str | None = None
    value: str | None = None


# ---------------------------------------------------------------------------
# Codec helpers
# ---------------------------------------------------------------------------

def encode_message(msg: EngineMsg) -> str:
    """Serialise an engine message to a single JSON line (no trailing newline)."""
    return json.dumps(msg.to_dict(), separators=(",", ":"))


def decode_command(line: str) -> CommandMsg:
    """
    Deserialise a raw JSON line from stdin into a CommandMsg.

    Raises:
        ValueError: if the line is not valid JSON or is missing 'command'.
        KeyError: if 'command' key is absent.
    """
    try:
        data = json.loads(line.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON command: {line!r}") from exc

    if "command" not in data:
        raise KeyError(f"Missing 'command' key in: {data!r}")

    return CommandMsg(
        command=data["command"],
        key=data.get("key"),
        value=data.get("value"),
    )


def send(msg: EngineMsg) -> None:
    """
    Write an engine message to stdout, flushed immediately.

    stdout writes for short lines are atomic on Unix, so this is safe
    to call from the audio callback thread without an extra lock.
    """
    sys.stdout.write(encode_message(msg) + "\n")
    sys.stdout.flush()
