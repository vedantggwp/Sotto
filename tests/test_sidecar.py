"""
Tests for sotto.sidecar — handle_command dispatch with mocked sub-systems.

All heavy dependencies (AudioEngine, Transcriber, CommandParser,
CommandExecutor) are replaced by lightweight fakes so the tests run
without microphone access, GPU, or Whisper model files.
"""

from dataclasses import dataclass, field
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sotto.core.command_parser import IntentType, ParsedIntent
from sotto.protocol import CommandMsg, StateChangeMsg, TranscriptionMsg
from sotto.sidecar import (
    MIN_AUDIO_DURATION_S,
    SAMPLE_RATE,
    SidecarEngine,
    handle_command,
)


# ---------------------------------------------------------------------------
# Fake / stub helpers
# ---------------------------------------------------------------------------

def _make_audio(duration_s: float) -> np.ndarray:
    """Return a silent float32 array of the given duration at SAMPLE_RATE."""
    n_samples = int(duration_s * SAMPLE_RATE)
    return np.zeros(n_samples, dtype=np.float32)


def _make_engine(
    *,
    audio_return: Optional[np.ndarray] = None,
    transcribe_return: tuple = ("hello world", 0.9),
    parse_return: Optional[ParsedIntent] = None,
) -> SidecarEngine:
    """
    Build a SidecarEngine with all sub-systems replaced by MagicMocks.

    Args:
        audio_return:      what AudioEngine.stop_recording() returns
        transcribe_return: what Transcriber.transcribe() returns
        parse_return:      what CommandParser.parse() returns
    """
    audio = MagicMock()
    audio.start_recording = MagicMock()
    audio.stop_recording = MagicMock(
        return_value=audio_return if audio_return is not None else _make_audio(1.0)
    )

    transcriber = MagicMock()
    transcriber.transcribe = MagicMock(return_value=transcribe_return)

    parser = MagicMock()
    parser.parse = MagicMock(
        return_value=parse_return
        if parse_return is not None
        else ParsedIntent(
            intent_type=IntentType.DICTATION,
            text=transcribe_return[0],
        )
    )

    executor = MagicMock()
    executor.type_text = MagicMock()
    executor.execute = MagicMock()

    return SidecarEngine(
        audio=audio,
        transcriber=transcriber,
        parser=parser,
        executor=executor,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_start_recording_calls_audio_start(capsys):
    engine = _make_engine()
    cmd = CommandMsg(command="start_recording")

    result = handle_command(cmd, engine)

    assert result == "recording"
    engine.audio.start_recording.assert_called_once()
    # Verify an on_audio callback was passed
    call_kwargs = engine.audio.start_recording.call_args
    on_audio = (
        call_kwargs.kwargs.get("on_audio")
        or (call_kwargs.args[0] if call_kwargs.args else None)
    )
    assert callable(on_audio), "on_audio callback should be passed to start_recording"


def test_start_recording_sends_listening_state(capsys):
    engine = _make_engine()
    cmd = CommandMsg(command="start_recording")

    handle_command(cmd, engine)

    captured = capsys.readouterr()
    import json
    lines = [json.loads(l) for l in captured.out.strip().splitlines() if l.strip()]
    state_msgs = [l for l in lines if l.get("type") == "state_change"]
    assert any(m["state"] == "listening" for m in state_msgs)


def test_stop_recording_transcribes_and_returns_done(capsys):
    audio_data = _make_audio(1.0)  # 1 s — well above MIN_AUDIO_DURATION_S
    engine = _make_engine(
        audio_return=audio_data,
        transcribe_return=("open Safari", 0.95),
        parse_return=ParsedIntent(
            intent_type=IntentType.COMMAND,
            command_name="open_app",
            command_args={"app": "safari"},
            text="open Safari",
        ),
    )
    cmd = CommandMsg(command="stop_recording")

    result = handle_command(cmd, engine)

    assert result == "done"
    engine.audio.stop_recording.assert_called_once()
    engine.transcriber.transcribe.assert_called_once_with(audio_data)
    engine.executor.execute.assert_called_once_with("open_app", {"app": "safari"})


def test_stop_recording_sends_transcription_message(capsys):
    engine = _make_engine(
        audio_return=_make_audio(1.0),
        transcribe_return=("hello world", 0.9),
    )
    cmd = CommandMsg(command="stop_recording")

    handle_command(cmd, engine)

    import json
    lines = [json.loads(l) for l in capsys.readouterr().out.strip().splitlines() if l.strip()]
    tx_msgs = [l for l in lines if l.get("type") == "transcription"]
    assert len(tx_msgs) == 1
    assert tx_msgs[0]["text"] == "hello world"


def test_short_audio_ignored_returns_idle(capsys):
    """Audio shorter than MIN_AUDIO_DURATION_S must not trigger transcription."""
    short_duration = MIN_AUDIO_DURATION_S * 0.5
    engine = _make_engine(audio_return=_make_audio(short_duration))
    cmd = CommandMsg(command="stop_recording")

    result = handle_command(cmd, engine)

    assert result == "idle"
    engine.transcriber.transcribe.assert_not_called()
    engine.executor.execute.assert_not_called()
    engine.executor.type_text.assert_not_called()


def test_quit_returns_quit(capsys):
    engine = _make_engine()
    cmd = CommandMsg(command="quit")

    result = handle_command(cmd, engine)

    assert result == "quit"


def test_quit_sends_idle_state(capsys):
    engine = _make_engine()
    cmd = CommandMsg(command="quit")

    handle_command(cmd, engine)

    import json
    lines = [json.loads(l) for l in capsys.readouterr().out.strip().splitlines() if l.strip()]
    state_msgs = [l for l in lines if l.get("type") == "state_change"]
    assert any(m["state"] == "idle" for m in state_msgs)


def test_set_config_applies_model(capsys):
    engine = _make_engine()
    engine.transcriber.unload_model = MagicMock()
    cmd = CommandMsg(command="set_config", key="model", value="small.en")

    result = handle_command(cmd, engine)

    assert result == "config_set"
    engine.transcriber.unload_model.assert_called_once()
    assert engine.transcriber.model_name == "small.en"


def test_set_config_applies_dotted_model_key(capsys):
    """Settings may send dotted keys like 'transcription.model'; leaf key is used."""
    engine = _make_engine()
    engine.transcriber.unload_model = MagicMock()
    cmd = CommandMsg(command="set_config", key="transcription.model", value="tiny.en")

    result = handle_command(cmd, engine)

    assert result == "config_set"
    engine.transcriber.unload_model.assert_called_once()
    assert engine.transcriber.model_name == "tiny.en"


def test_unknown_command_returns_unknown_and_sends_error(capsys):
    engine = _make_engine()
    cmd = CommandMsg(command="do_the_magic")

    result = handle_command(cmd, engine)

    assert result == "unknown"
    import json
    lines = [json.loads(l) for l in capsys.readouterr().out.strip().splitlines() if l.strip()]
    error_msgs = [l for l in lines if l.get("type") == "error"]
    assert len(error_msgs) == 1
    assert "do_the_magic" in error_msgs[0]["error"]


def test_stop_recording_dictation_types_text(capsys):
    """Dictation intent should call executor.type_text, not executor.execute."""
    engine = _make_engine(
        audio_return=_make_audio(1.0),
        transcribe_return=("meeting at noon", 0.8),
        parse_return=ParsedIntent(
            intent_type=IntentType.DICTATION,
            text="meeting at noon",
        ),
    )
    cmd = CommandMsg(command="stop_recording")

    handle_command(cmd, engine)

    engine.executor.type_text.assert_called_once_with("meeting at noon")
    engine.executor.execute.assert_not_called()


def test_stop_recording_sends_transcribing_then_done_states(capsys):
    """Verify the exact state sequence: transcribing -> transcription -> done."""
    import json

    engine = _make_engine(
        audio_return=_make_audio(1.0),
        transcribe_return=("hello", 0.95),
        parse_return=ParsedIntent(
            intent_type=IntentType.DICTATION,
            text="hello",
        ),
    )
    cmd = CommandMsg(command="stop_recording")

    handle_command(cmd, engine)

    captured = capsys.readouterr().out
    lines = [json.loads(line) for line in captured.strip().split("\n") if line.strip()]
    states = [msg["state"] for msg in lines if msg.get("type") == "state_change"]
    assert states == ["transcribing", "done"], f"Expected [transcribing, done], got {states}"
