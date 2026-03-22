"""
Tests for sotto.protocol — JSON IPC encode/decode.
"""

import json

import pytest

from sotto.protocol import (
    AudioLevelMsg,
    CommandMsg,
    ErrorMsg,
    StateChangeMsg,
    TranscriptionMsg,
    decode_command,
    encode_message,
)


# ---------------------------------------------------------------------------
# Encoding tests (Engine -> Tauri)
# ---------------------------------------------------------------------------

def test_state_change_encodes():
    msg = StateChangeMsg(state="listening")
    line = encode_message(msg)
    data = json.loads(line)
    assert data == {"type": "state_change", "state": "listening"}


def test_state_change_idle_encodes():
    msg = StateChangeMsg(state="idle")
    line = encode_message(msg)
    data = json.loads(line)
    assert data["type"] == "state_change"
    assert data["state"] == "idle"


def test_audio_level_encodes():
    msg = AudioLevelMsg(level=0.42)
    line = encode_message(msg)
    data = json.loads(line)
    assert data == {"type": "audio_level", "level": 0.42}


def test_audio_level_boundary_values_encode():
    for level in (0.0, 1.0):
        msg = AudioLevelMsg(level=level)
        data = json.loads(encode_message(msg))
        assert data["level"] == level


def test_transcription_encodes():
    msg = TranscriptionMsg(text="hello world")
    line = encode_message(msg)
    data = json.loads(line)
    assert data == {"type": "transcription", "text": "hello world"}


def test_transcription_empty_text_encodes():
    msg = TranscriptionMsg(text="")
    data = json.loads(encode_message(msg))
    assert data["type"] == "transcription"
    assert data["text"] == ""


def test_error_encodes():
    msg = ErrorMsg(error="mic denied")
    line = encode_message(msg)
    data = json.loads(line)
    assert data == {"type": "error", "error": "mic denied"}


def test_encode_produces_single_line():
    """Encoded messages must not contain embedded newlines."""
    for msg in (
        StateChangeMsg(state="idle"),
        AudioLevelMsg(level=0.5),
        TranscriptionMsg(text="test"),
        ErrorMsg(error="boom"),
    ):
        line = encode_message(msg)
        assert "\n" not in line


# ---------------------------------------------------------------------------
# Decoding tests (Tauri -> Engine)
# ---------------------------------------------------------------------------

def test_decode_start_command():
    raw = '{"command":"start_recording"}'
    cmd = decode_command(raw)
    assert isinstance(cmd, CommandMsg)
    assert cmd.command == "start_recording"
    assert cmd.key is None
    assert cmd.value is None


def test_decode_stop_command():
    raw = '{"command":"stop_recording"}'
    cmd = decode_command(raw)
    assert cmd.command == "stop_recording"


def test_decode_set_config_command():
    raw = '{"command":"set_config","key":"model","value":"small.en"}'
    cmd = decode_command(raw)
    assert cmd.command == "set_config"
    assert cmd.key == "model"
    assert cmd.value == "small.en"


def test_decode_quit_command():
    raw = '{"command":"quit"}'
    cmd = decode_command(raw)
    assert cmd.command == "quit"


def test_decode_invalid_json_raises_value_error():
    with pytest.raises(ValueError, match="Invalid JSON"):
        decode_command("not json at all")


def test_decode_missing_command_key_raises_key_error():
    with pytest.raises(KeyError):
        decode_command('{"action":"start"}')


def test_decode_strips_whitespace():
    raw = '  {"command":"quit"}  \n'
    cmd = decode_command(raw)
    assert cmd.command == "quit"
