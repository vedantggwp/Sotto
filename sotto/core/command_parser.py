"""
Sotto Command Parser
Intelligent classification of voice input into commands vs dictation.
"""

import re
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """Type of intent detected from voice input"""
    COMMAND = "command"      # System command to execute
    DICTATION = "dictation"  # Text to type
    CONTROL = "control"      # Sotto control (e.g., "stop listening")


@dataclass
class ParsedIntent:
    """Result of parsing voice input"""
    intent_type: IntentType
    command_name: Optional[str] = None  # e.g., "open_app"
    command_args: Dict[str, Any] = None  # e.g., {"app": "Safari"}
    text: str = ""                       # Original or processed text
    confidence: float = 1.0              # How confident we are in this classification
    
    def __post_init__(self):
        if self.command_args is None:
            self.command_args = {}


class CommandParser:
    """
    Parse voice input and determine if it's a command or dictation.
    Uses pattern matching for speed (no ML inference delay).
    """
    
    # Command patterns - checked in order
    # Format: (regex pattern, command_name, arg_extractor_function)
    COMMAND_PATTERNS = [
        # Sotto Control Commands
        (r"^(stop listening|pause listening|stop)$", "sotto_stop", None),
        (r"^(start listening|resume listening|resume)$", "sotto_start", None),
        (r"^(command mode|commands only)$", "sotto_command_mode", None),
        (r"^(dictation mode|typing mode|type only)$", "sotto_dictation_mode", None),
        
        # App Commands
        (r"^open\s+(.+)$", "open_app", lambda m: {"app": m.group(1).strip()}),
        (r"^launch\s+(.+)$", "open_app", lambda m: {"app": m.group(1).strip()}),
        (r"^close\s+(?:the\s+)?window$", "close_window", None),
        (r"^quit\s+(.+)$", "quit_app", lambda m: {"app": m.group(1).strip()}),
        (r"^close\s+(.+)$", "quit_app", lambda m: {"app": m.group(1).strip()}),
        (r"^switch\s+to\s+(.+)$", "switch_app", lambda m: {"app": m.group(1).strip()}),
        (r"^go\s+to\s+(.+)$", "switch_app", lambda m: {"app": m.group(1).strip()}),
        
        # System Commands
        (r"^volume\s+(up|down|mute|unmute)$", "volume", lambda m: {"action": m.group(1)}),
        (r"^(mute|unmute)$", "volume", lambda m: {"action": m.group(1)}),
        (r"^(?:set\s+)?volume\s+(?:to\s+)?(\d+)(?:\s*%)?$", "volume_set", lambda m: {"level": int(m.group(1))}),
        (r"^volume\s+(\d+)(?:\s*%)?$", "volume_set", lambda m: {"level": int(m.group(1))}),
        (r"^brightness\s+(up|down)$", "brightness", lambda m: {"action": m.group(1)}),
        (r"^(?:set\s+)?brightness\s+(?:to\s+)?(\d+)(?:\s*%)?$", "brightness_set", lambda m: {"level": int(m.group(1))}),
        (r"^(take\s+)?screenshot$", "screenshot", None),
        (r"^(lock\s+)?screen$", "lock_screen", None),
        (r"^lock$", "lock_screen", None),
        (r"^sleep$", "sleep", None),
        
        # Text Editing Commands
        (r"^select\s+all$", "select_all", None),
        (r"^copy(\s+that)?$", "copy", None),
        (r"^cut(\s+that)?$", "cut", None),
        (r"^paste$", "paste", None),
        (r"^undo$", "undo", None),
        (r"^redo$", "redo", None),
        (r"^(delete|scratch)\s+(that|this|last)$", "delete_last", None),
        (r"^delete\s+word$", "delete_word", None),
        (r"^delete\s+line$", "delete_line", None),
        (r"^new\s+(line|paragraph)$", "new_line", None),
        (r"^(enter|return)$", "new_line", None),
        (r"^tab$", "tab", None),
        (r"^space$", "space", None),
        (r"^backspace$", "backspace", None),
        (r"^escape$", "escape", None),
        
        # Navigation Commands
        (r"^scroll\s+(up|down)$", "scroll", lambda m: {"direction": m.group(1)}),
        (r"^page\s+(up|down)$", "page", lambda m: {"direction": m.group(1)}),
        (r"^go\s+(back|forward)$", "navigate", lambda m: {"direction": m.group(1)}),
        (r"^(back|forward)$", "navigate", lambda m: {"direction": m.group(1)}),
        
        # Tab Commands
        (r"^new\s+tab$", "new_tab", None),
        (r"^close\s+tab$", "close_tab", None),
        (r"^(next|previous)\s+tab$", "switch_tab", lambda m: {"direction": m.group(1)}),
        
        # Search Commands
        (r"^search\s+(?:for\s+)?(.+)$", "search", lambda m: {"query": m.group(1).strip()}),
        (r"^google\s+(.+)$", "search_google", lambda m: {"query": m.group(1).strip()}),
        (r"^find\s+(.+)$", "find", lambda m: {"text": m.group(1).strip()}),
        
        # Dictation Control
        (r"^(period|full\s+stop)$", "insert_punctuation", lambda m: {"char": "."}),
        (r"^comma$", "insert_punctuation", lambda m: {"char": ","}),
        (r"^question\s+mark$", "insert_punctuation", lambda m: {"char": "?"}),
        (r"^exclamation\s+(mark|point)$", "insert_punctuation", lambda m: {"char": "!"}),
        (r"^colon$", "insert_punctuation", lambda m: {"char": ":"}),
        (r"^semicolon$", "insert_punctuation", lambda m: {"char": ";"}),
        (r"^quote$", "insert_punctuation", lambda m: {"char": '"'}),
        (r"^open\s+(quote|parenthesis|bracket)$", "insert_punctuation", 
         lambda m: {"char": {"quote": '"', "parenthesis": "(", "bracket": "["}[m.group(1)]}),
        (r"^close\s+(quote|parenthesis|bracket)$", "insert_punctuation",
         lambda m: {"char": {"quote": '"', "parenthesis": ")", "bracket": "]"}[m.group(1)]}),
    ]
    
    # Words that strongly indicate a command (even without matching patterns)
    COMMAND_INDICATORS = {
        "open", "close", "quit", "launch", "switch", "go",
        "select", "copy", "cut", "paste", "undo", "redo",
        "delete", "scratch", "new", "scroll", "click",
        "volume", "mute", "brightness", "screenshot",
        "search", "google", "find"
    }
    
    def __init__(self):
        # Compile patterns for speed
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), cmd, extractor)
            for pattern, cmd, extractor in self.COMMAND_PATTERNS
        ]
    
    def parse(self, text: str) -> ParsedIntent:
        """
        Parse voice input and determine intent.
        
        Args:
            text: Transcribed voice input
            
        Returns:
            ParsedIntent with classified intent
        """
        if not text:
            return ParsedIntent(
                intent_type=IntentType.DICTATION,
                text=""
            )

        # Normalize text - strip punctuation and lowercase
        normalized = text.strip().lower()
        # Remove trailing punctuation that Whisper often adds
        normalized = normalized.rstrip('.,!?;:')
        
        # Check against command patterns
        for pattern, command_name, arg_extractor in self._compiled_patterns:
            match = pattern.match(normalized)
            if match:
                # Extract arguments if extractor provided
                args = arg_extractor(match) if arg_extractor else {}
                
                # Determine if it's a Sotto control command
                if command_name.startswith("sotto_"):
                    intent_type = IntentType.CONTROL
                else:
                    intent_type = IntentType.COMMAND
                
                return ParsedIntent(
                    intent_type=intent_type,
                    command_name=command_name,
                    command_args=args,
                    text=text,
                    confidence=1.0
                )
        
        # Check for command indicators at the start of the text
        first_word = normalized.split()[0] if normalized else ""
        if first_word in self.COMMAND_INDICATORS:
            # Might be a command we don't recognize - return as unknown command
            return ParsedIntent(
                intent_type=IntentType.COMMAND,
                command_name="unknown",
                command_args={"raw_text": text},
                text=text,
                confidence=0.5  # Lower confidence for unrecognized commands
            )
        
        # Default to dictation
        return ParsedIntent(
            intent_type=IntentType.DICTATION,
            text=text
        )
    
    def add_custom_command(
        self,
        pattern: str,
        command_name: str,
        arg_extractor=None
    ):
        """Add a custom command pattern"""
        compiled = re.compile(pattern, re.IGNORECASE)
        self._compiled_patterns.insert(0, (compiled, command_name, arg_extractor))
    
    def is_command(self, text: str) -> bool:
        """Quick check if text is likely a command"""
        intent = self.parse(text)
        return intent.intent_type in (IntentType.COMMAND, IntentType.CONTROL)
    
    def get_supported_commands(self) -> List[str]:
        """Get list of all supported commands"""
        commands = set()
        for _, cmd, _ in self.COMMAND_PATTERNS:
            if not cmd.startswith("sotto_") and cmd != "unknown":
                commands.add(cmd)
        return sorted(commands)
    
    def format_for_display(self, intent: ParsedIntent) -> str:
        """Format parsed intent for display"""
        if intent.intent_type == IntentType.DICTATION:
            return f"📝 {intent.text}"
        elif intent.intent_type == IntentType.CONTROL:
            return f"🎛️ {intent.command_name}"
        else:
            args_str = ", ".join(f"{k}={v}" for k, v in intent.command_args.items())
            if args_str:
                return f"⚡ {intent.command_name}({args_str})"
            return f"⚡ {intent.command_name}"
