"""
Sotto Configuration Management
Handles all settings, hotkeys, and user preferences.
"""

import os
import yaml
from pathlib import Path
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# Paths
SOTTO_DIR = Path.home() / ".sotto"
CONFIG_FILE = SOTTO_DIR / "config.yaml"
MODELS_DIR = SOTTO_DIR / "models"


class HotkeyConfig(BaseModel):
    """Hotkey configuration"""
    push_to_talk: str = Field(default="<cmd>+<shift>+<space>", description="Hold to speak")
    toggle_listening: str = Field(default="<cmd>+<shift>+l", description="Toggle always-listening mode")
    cancel: str = Field(default="<escape>", description="Cancel current operation")


class TranscriptionConfig(BaseModel):
    """Whisper transcription settings"""
    model: str = Field(default="base.en", description="Whisper model size")
    language: str = Field(default="en", description="Language code")
    device: str = Field(default="auto", description="Device: auto, cpu, cuda, mps")
    compute_type: str = Field(default="int8", description="Compute type for faster inference")


class FeedbackConfig(BaseModel):
    """User feedback settings"""
    audio_enabled: bool = Field(default=True, description="Play sounds for feedback")
    overlay_enabled: bool = Field(default=True, description="Show floating overlay")
    overlay_duration: float = Field(default=2.0, description="How long overlay stays visible")
    overlay_position: str = Field(default="top-center", description="Overlay position on screen")


class CommandConfig(BaseModel):
    """Command behavior settings"""
    confirmation_required: List[str] = Field(
        default=["quit", "shutdown", "restart", "delete"],
        description="Commands requiring confirmation"
    )
    custom_commands: dict = Field(default_factory=dict, description="User-defined commands")


class SottoConfig(BaseModel):
    """Main Sotto configuration"""
    mode: Literal["push_to_talk", "always_listening"] = Field(
        default="push_to_talk",
        description="Voice input mode"
    )
    hotkeys: HotkeyConfig = Field(default_factory=HotkeyConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    feedback: FeedbackConfig = Field(default_factory=FeedbackConfig)
    commands: CommandConfig = Field(default_factory=CommandConfig)
    
    # Runtime state (not persisted)
    is_listening: bool = Field(default=False, exclude=True)
    
    @classmethod
    def load(cls) -> "SottoConfig":
        """Load configuration from file or create default"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()
    
    def save(self) -> None:
        """Save configuration to file"""
        SOTTO_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(self.model_dump(exclude={'is_listening'}), f, default_flow_style=False)
    
    def get_model_path(self) -> Path:
        """Get path to the Whisper model"""
        return MODELS_DIR / self.transcription.model


def ensure_directories():
    """Create necessary directories"""
    SOTTO_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


# Singleton config instance
_config: Optional[SottoConfig] = None


def get_config() -> SottoConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = SottoConfig.load()
    return _config


def reload_config() -> SottoConfig:
    """Reload configuration from file"""
    global _config
    _config = SottoConfig.load()
    return _config
