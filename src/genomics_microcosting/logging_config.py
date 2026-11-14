# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Logging configuration for the microcosting application."""

import logging
import sys
from pathlib import Path


def setup_logging(
    log_level: int = logging.INFO,
    log_file: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """Set up logging for the application.

    Args:
        log_level: Logging level (default: INFO)
        log_file: Optional file to write logs to
        format_string: Optional format string for log messages

    Returns:
        Configured logger instance

    """
    # Create logger
    logger = logging.getLogger("microcosting")
    logger.setLevel(log_level)

    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # Set up format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        # Ensure directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "microcosting") -> logging.Logger:
    """Get a logger instance with the specified name.

    Args:
        name: Name for the logger (default: "microcosting")

    Returns:
        Logger instance

    """
    return logging.getLogger(name)


# Example usage
if __name__ == "__main__":
    # Set up logging
    logger = setup_logging(logging.DEBUG, "logs/microcosting.log")

    # Test logging
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
