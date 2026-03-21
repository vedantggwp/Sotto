"""
Sotto Logging Module
Provides centralized logging configuration with file rotation and console output.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from ..config import SOTTO_DIR

# Log directory
LOG_DIR = SOTTO_DIR / "logs"


def setup_logging(debug: bool = False) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        debug: If True, set log level to DEBUG and enable verbose output.

    Returns:
        The configured root logger.
    """
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger
    logger = logging.getLogger("sotto")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Clear existing handlers
    logger.handlers.clear()

    # Formatters
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s" if debug else "%(message)s")

    # File Handler (Rotating)
    # 5MB per file, max 3 backup files
    log_file = LOG_DIR / "sotto.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.addHandler(console_handler)

    # Capture uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    logger.info(f"Logging initialized. Writing to {log_file}")
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a named logger under the sotto namespace."""
    return logging.getLogger(f"sotto.{name}")
