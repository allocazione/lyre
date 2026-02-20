"""Logging configuration for Lyre.

Outputs real-time logs to both stderr (terminal) and a rotating log file
stored inside the platform-specific config directory under a `logs/`
subdirectory.

Log files are rotated daily and retained for 7 days.
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(debug: bool = False):
    """Configure loguru sinks for terminal and file output.

    Args:
        debug: If True, set log level to DEBUG. Otherwise INFO.
    """
    # Import here to avoid circular import (config imports logger at module level)
    from lyre.config import CONFIG_DIR

    logger.remove()
    level = "DEBUG" if debug else "INFO"

    # -- Terminal sink (colorized, real-time) ----------------------------------
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # -- File sink (plain text, rotated daily, kept 7 days) --------------------
    logs_dir = CONFIG_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        logs_dir / "lyre_{time:YYYY-MM-DD}.log",
        level=level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} - "
            "{message}"
        ),
        rotation="00:00",   # New file every midnight
        retention="7 days", # Keep logs for 7 days
        encoding="utf-8",
    )

    logger.info(f"Logging to: {logs_dir}")
    return logger
