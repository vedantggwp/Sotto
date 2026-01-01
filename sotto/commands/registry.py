"""
Sotto Command Registry
Central registry for all voice commands.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum


class CommandCategory(Enum):
    """Categories of commands"""
    SYSTEM = "system"
    APP = "app"
    TEXT = "text"
    NAVIGATION = "navigation"
    SEARCH = "search"
    CONTROL = "control"
    CUSTOM = "custom"


@dataclass
class Command:
    """Definition of a voice command"""
    name: str
    description: str
    patterns: List[str]  # Voice patterns that trigger this command
    category: CommandCategory
    examples: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    enabled: bool = True


class CommandRegistry:
    """
    Central registry for all voice commands.
    Provides command lookup and documentation.
    """
    
    # Built-in commands
    BUILTIN_COMMANDS = [
        # System Commands
        Command(
            name="volume",
            description="Control system volume",
            patterns=["volume up", "volume down", "mute", "unmute"],
            category=CommandCategory.SYSTEM,
            examples=["volume up", "mute"]
        ),
        Command(
            name="brightness",
            description="Control screen brightness",
            patterns=["brightness up", "brightness down"],
            category=CommandCategory.SYSTEM,
            examples=["brightness down"]
        ),
        Command(
            name="screenshot",
            description="Take a screenshot",
            patterns=["screenshot", "take screenshot"],
            category=CommandCategory.SYSTEM,
            examples=["screenshot"]
        ),
        Command(
            name="lock_screen",
            description="Lock the screen",
            patterns=["lock", "lock screen"],
            category=CommandCategory.SYSTEM,
            examples=["lock screen"]
        ),
        Command(
            name="sleep",
            description="Put Mac to sleep",
            patterns=["sleep"],
            category=CommandCategory.SYSTEM,
            requires_confirmation=True,
            examples=["sleep"]
        ),
        
        # App Commands
        Command(
            name="open_app",
            description="Open an application",
            patterns=["open <app>", "launch <app>"],
            category=CommandCategory.APP,
            examples=["open Safari", "launch Finder"]
        ),
        Command(
            name="quit_app",
            description="Quit an application",
            patterns=["quit <app>", "close <app>"],
            category=CommandCategory.APP,
            requires_confirmation=True,
            examples=["quit Safari"]
        ),
        Command(
            name="switch_app",
            description="Switch to an application",
            patterns=["switch to <app>", "go to <app>"],
            category=CommandCategory.APP,
            examples=["switch to Notes"]
        ),
        Command(
            name="close_window",
            description="Close current window",
            patterns=["close window", "close the window"],
            category=CommandCategory.APP,
            examples=["close window"]
        ),
        
        # Text Editing Commands
        Command(
            name="select_all",
            description="Select all text",
            patterns=["select all"],
            category=CommandCategory.TEXT,
            examples=["select all"]
        ),
        Command(
            name="copy",
            description="Copy selection",
            patterns=["copy", "copy that"],
            category=CommandCategory.TEXT,
            examples=["copy"]
        ),
        Command(
            name="cut",
            description="Cut selection",
            patterns=["cut", "cut that"],
            category=CommandCategory.TEXT,
            examples=["cut"]
        ),
        Command(
            name="paste",
            description="Paste from clipboard",
            patterns=["paste"],
            category=CommandCategory.TEXT,
            examples=["paste"]
        ),
        Command(
            name="undo",
            description="Undo last action",
            patterns=["undo"],
            category=CommandCategory.TEXT,
            examples=["undo"]
        ),
        Command(
            name="redo",
            description="Redo last undone action",
            patterns=["redo"],
            category=CommandCategory.TEXT,
            examples=["redo"]
        ),
        Command(
            name="delete_last",
            description="Delete last dictation",
            patterns=["delete that", "scratch that", "delete this", "delete last"],
            category=CommandCategory.TEXT,
            examples=["delete that"]
        ),
        Command(
            name="new_line",
            description="Insert new line",
            patterns=["new line", "new paragraph", "enter", "return"],
            category=CommandCategory.TEXT,
            examples=["new line"]
        ),
        
        # Navigation Commands
        Command(
            name="scroll",
            description="Scroll the page",
            patterns=["scroll up", "scroll down"],
            category=CommandCategory.NAVIGATION,
            examples=["scroll down"]
        ),
        Command(
            name="navigate",
            description="Browser back/forward",
            patterns=["back", "forward", "go back", "go forward"],
            category=CommandCategory.NAVIGATION,
            examples=["go back"]
        ),
        Command(
            name="new_tab",
            description="Open new tab",
            patterns=["new tab"],
            category=CommandCategory.NAVIGATION,
            examples=["new tab"]
        ),
        Command(
            name="close_tab",
            description="Close current tab",
            patterns=["close tab"],
            category=CommandCategory.NAVIGATION,
            examples=["close tab"]
        ),
        
        # Search Commands
        Command(
            name="search",
            description="Search using Spotlight",
            patterns=["search <query>", "search for <query>"],
            category=CommandCategory.SEARCH,
            examples=["search for weather"]
        ),
        Command(
            name="search_google",
            description="Search on Google",
            patterns=["google <query>"],
            category=CommandCategory.SEARCH,
            examples=["google python tutorials"]
        ),
        Command(
            name="find",
            description="Find text in current app",
            patterns=["find <text>"],
            category=CommandCategory.SEARCH,
            examples=["find hello"]
        ),
        
        # Sotto Control
        Command(
            name="sotto_stop",
            description="Stop listening",
            patterns=["stop listening", "pause listening", "stop"],
            category=CommandCategory.CONTROL,
            examples=["stop listening"]
        ),
        Command(
            name="sotto_start",
            description="Start listening",
            patterns=["start listening", "resume listening", "resume"],
            category=CommandCategory.CONTROL,
            examples=["start listening"]
        ),
        Command(
            name="sotto_command_mode",
            description="Switch to command-only mode",
            patterns=["command mode", "commands only"],
            category=CommandCategory.CONTROL,
            examples=["command mode"]
        ),
        Command(
            name="sotto_dictation_mode",
            description="Switch to dictation-only mode",
            patterns=["dictation mode", "typing mode", "type only"],
            category=CommandCategory.CONTROL,
            examples=["dictation mode"]
        ),
    ]
    
    def __init__(self):
        self._commands: Dict[str, Command] = {}
        self._custom_commands: Dict[str, Command] = {}
        
        # Register built-in commands
        for cmd in self.BUILTIN_COMMANDS:
            self._commands[cmd.name] = cmd
    
    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name"""
        return self._commands.get(name) or self._custom_commands.get(name)
    
    def get_all_commands(self) -> List[Command]:
        """Get all registered commands"""
        return list(self._commands.values()) + list(self._custom_commands.values())
    
    def get_commands_by_category(self, category: CommandCategory) -> List[Command]:
        """Get commands in a specific category"""
        return [cmd for cmd in self.get_all_commands() if cmd.category == category]
    
    def add_custom_command(self, command: Command):
        """Add a custom command"""
        command.category = CommandCategory.CUSTOM
        self._custom_commands[command.name] = command
    
    def remove_custom_command(self, name: str) -> bool:
        """Remove a custom command"""
        if name in self._custom_commands:
            del self._custom_commands[name]
            return True
        return False
    
    def enable_command(self, name: str) -> bool:
        """Enable a command"""
        cmd = self.get_command(name)
        if cmd:
            cmd.enabled = True
            return True
        return False
    
    def disable_command(self, name: str) -> bool:
        """Disable a command"""
        cmd = self.get_command(name)
        if cmd:
            cmd.enabled = False
            return True
        return False
    
    def get_help_text(self) -> str:
        """Generate help text for all commands"""
        lines = ["# Sotto Voice Commands\n"]
        
        for category in CommandCategory:
            commands = self.get_commands_by_category(category)
            if commands:
                lines.append(f"\n## {category.value.title()} Commands\n")
                for cmd in commands:
                    status = "✓" if cmd.enabled else "✗"
                    lines.append(f"- **{cmd.name}** {status}")
                    lines.append(f"  - {cmd.description}")
                    lines.append(f"  - Say: {', '.join(cmd.examples[:3])}")
        
        return "\n".join(lines)
