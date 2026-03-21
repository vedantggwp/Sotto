"""
Sotto Permissions Module
Handles macOS permission checks and requests.
"""

import subprocess

from .logging import get_logger

logger = get_logger("permissions")


def check_accessibility_permissions() -> bool:
    """
    Check if the process has accessibility permissions.
    This is required for monitoring global hotkeys.

    Returns:
        bool: True if trusted, False otherwise.
    """
    try:
        # reliable check using ApplicationServices
        from ApplicationServices import AXIsProcessTrusted

        is_trusted = AXIsProcessTrusted()

        if is_trusted:
            logger.debug("Accessibility permissions verified: Trusted")
            return True
        else:
            logger.warning("Accessibility permissions NOT trusted")
            return False

    except ImportError:
        logger.error("Could not import ApplicationServices. Are you running on macOS?")
        return False
    except Exception as e:
        logger.error(f"Error checking accessibility permissions: {e}")
        return False


def prompt_for_accessibility():
    """
    Prompt the user to enable accessibility permissions.
    Attempts to open the System Settings pane.
    """
    logger.info("Prompting user for Accessibility permissions")

    instructions = """
    \n============================================================
    ⚠️  ACCESSIBILITY PERMISSIONS REQUIRED
    ============================================================
    Sotto needs Accessibility permissions to capture global hotkeys.
    
    To enable:
    1. System Settings should open automatically.
    2. Go to Privacy & Security > Accessibility.
    3. Click the '+' button if Sotto/Terminal is not listed.
    4. Enable the toggle for your terminal app (Terminal, iTerm, VS Code) or Sotto.
    5. RESTART this application.
    ============================================================\n
    """
    print(instructions)

    # Try to open System Settings to the right page
    try:
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ],
            capture_output=True,
        )
    except Exception as e:
        logger.error(f"Failed to open System Settings: {e}")


def check_microphone_permissions() -> bool:
    """
    Check if we have microphone access.
    Note: macOS doesn't provide a simple API to check this without triggering usage,
    so we mostly rely on the fact that sounddevice will fail if we don't.
    """
    # This is a placeholder. Real verification happens when opening the stream.
    return True
