"""Structured logging setup for Code Sergeant."""
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir: str = "logs") -> logging.Logger:
    """
    Set up structured logging to both file and console.

    Args:
        log_dir: Directory to store log files

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Create log file with timestamp
    log_file = (
        log_path / f"code_sergeant_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    # Configure root logger
    logger = logging.getLogger("code_sergeant")
    logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler with detailed formatting
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Console handler with simpler formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")

    return logger
