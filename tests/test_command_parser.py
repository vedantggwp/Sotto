"""
Tests for Command Parser
"""

import pytest

from sotto.core.command_parser import CommandParser, IntentType


@pytest.fixture
def parser():
    return CommandParser()


def test_dictation(parser):
    """Test that regular speech defaults to dictation"""
    intent = parser.parse("Hello world")
    assert intent.intent_type == IntentType.DICTATION
    assert intent.text == "Hello world"


def test_basic_command(parser):
    """Test a basic command like 'open Safari'"""
    intent = parser.parse("Open Safari")
    assert intent.intent_type == IntentType.COMMAND
    assert intent.command_name == "open_app"
    assert intent.command_args == {"app": "safari"}


def test_control_command(parser):
    """Test a control command like 'stop listening'"""
    intent = parser.parse("Stop listening")
    assert intent.intent_type == IntentType.CONTROL
    assert intent.command_name == "sotto_stop"


def test_formatting(parser):
    """Test punctuation formatting"""
    # Note: parser handles lowercasing, but keeping original text for display?
    # Actually parser stores original text in 'text' field.
    intent = parser.parse("This is a test.")
    assert intent.text == "This is a test."

    # Test built-in punctuation commands
    intent = parser.parse("period")
    assert intent.command_name == "insert_punctuation"
    assert intent.command_args == {"char": "."}
