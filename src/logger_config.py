"""
Logging configuration for the fishery system.
All system logs are written to logs/fishery_system.log
User interface uses Rich library for beautiful terminal output.
"""
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(log_dir="logs", log_file="fishery_system.log", level=logging.INFO):
    """
    Setup logging configuration for the fishery system.
    
    Args:
        log_dir: Directory to store log files
        log_file: Name of the log file
        level: Logging level (default: INFO)
    
    Returns:
        logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    log_file_path = log_path / log_file
    
    # Create logger
    logger = logging.getLogger("fishery_system")
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation (max 10MB, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.propagate = False
    
    return logger


def get_logger(name=None):
    """
    Get a logger instance for a specific agent or component.
    
    Args:
        name: Name of the logger (usually agent class name)
    
    Returns:
        logger: Logger instance
    """
    if name:
        return logging.getLogger(f"fishery_system.{name}")
    return logging.getLogger("fishery_system")

