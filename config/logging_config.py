"""
Logging configuration for the Stock Analysis Application.
"""
import os
import sys
import time
from pathlib import Path

from loguru import logger

from config.settings import LOG_DIR, LOG_LEVEL, LOG_RETENTION, LOG_ROTATION


def setup_logging():
    """
    Configure the application logging system.

    Sets up loguru logger with:
    - Console output with appropriate formatting
    - File output with rotation and retention policies
    - Custom log levels and formats
    """
    # Remove default logger
    logger.remove()

    # Add console logger with appropriate format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True,
    )

    # Add file logger with rotation
    log_file = os.path.join(LOG_DIR, f"stock_analysis_{time.strftime('%Y%m%d')}.log")
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
    )

    # Add specific loggers for different components

    # Market data logger
    market_log_file = os.path.join(LOG_DIR, "market_data.log")
    logger.add(
        market_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=LOG_LEVEL,
        filter=lambda record: "market_data" in record["name"],
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
    )

    # Authentication logger
    auth_log_file = os.path.join(LOG_DIR, "authentication.log")
    logger.add(
        auth_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=LOG_LEVEL,
        filter=lambda record: "auth" in record["name"],
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
    )

    # Analysis logger
    analysis_log_file = os.path.join(LOG_DIR, "analysis.log")
    logger.add(
        analysis_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=LOG_LEVEL,
        filter=lambda record: "analysis" in record["name"],
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
    )

    # API logger
    api_log_file = os.path.join(LOG_DIR, "api.log")
    logger.add(
        api_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=LOG_LEVEL,
        filter=lambda record: "api" in record["name"],
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
    )

    # Error logger - separate file for errors and above
    error_log_file = os.path.join(LOG_DIR, "errors.log")
    logger.add(
        error_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        backtrace=True,
        diagnose=True,
    )

    logger.info(f"Logging initialized with level: {LOG_LEVEL}")
    logger.info(f"Log files directory: {LOG_DIR}")

    return logger