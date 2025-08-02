import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """
    Creates a logger with the given name that logs to both the console and a rotating file.
    """

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(name)

    if logger.handlers:
        # Avoid adding handlers again if logger is reused
        return logger

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s-%(lineno)d: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)  # Console only shows INFO+
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Ensure logs directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Rotating File Handler
    file_handler = RotatingFileHandler(
        filename=log_dir / "application.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,  # keep last 3 log files
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # File keeps DEBUG+ logs
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
