"""Logging configuration for Chronos agent."""

import sys
from pathlib import Path
from loguru import logger
from src.chronos.config import config


def setup_logger(log_file: str = "chronos.log") -> None:
    """
    Configure logging for the application.
    
    Args:
        log_file: Name of the log file
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with color
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=config.log_level,
        colorize=True,
    )
    
    # File handler
    log_path = config.logs_dir / log_file
    logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=config.log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )
    
    logger.info(f"Logger initialized. Log file: {log_path}")


def get_logger(name: str):
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name)


# Initialize logger on import
setup_logger()

