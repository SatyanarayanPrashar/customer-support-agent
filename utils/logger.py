import logging
import os
from typing import Optional


def setup_logger(
    level: int = logging.INFO,
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up the logger for the application.
    """
    logger = logging.getLogger("support_system")
    logger.setLevel(level)

    # Only add handlers once
    if not logger.handlers:
        formatter = logging.Formatter(log_format)

        # Console handler
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(level)
        # console_handler.setFormatter(formatter)
        # logger.addHandler(console_handler)

        # Optional file handler
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        logger.propagate = False

    return logger


def get_logger(
    level: int = logging.INFO,
    log_file: Optional[str] = "logs/support_system.log"
) -> logging.Logger:
    """
    Get the logger, auto-initializing if it has no handlers.
    """
    logger = logging.getLogger("support_system")
    if not logger.handlers:
        setup_logger(level=level, log_file=log_file)
    return logger
