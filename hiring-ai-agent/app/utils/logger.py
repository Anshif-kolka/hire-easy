"""
Logger - Centralized logging configuration.
"""
import logging
import sys
from typing import Optional


# Store configured loggers
_loggers = {}

# Default format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LEVEL = logging.INFO


def setup_logger(
    name: str = "hiring_agent",
    level: int = DEFAULT_LEVEL,
    format_string: str = DEFAULT_FORMAT,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up and configure a logger.
    
    Args:
        name: Logger name
        level: Logging level
        format_string: Log message format
        log_file: Optional file path for file logging
        
    Returns:
        Configured logger
    """
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    _loggers[name] = logger
    return logger


def get_logger(name: str = "hiring_agent") -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__ of the calling module)
        
    Returns:
        Logger instance
    """
    # Create child logger under main app logger
    if name.startswith("app."):
        # Module logger
        parent_name = "hiring_agent"
        if parent_name not in _loggers:
            setup_logger(parent_name)
        
        full_name = f"{parent_name}.{name}"
        return logging.getLogger(full_name)
    
    # Root or custom logger
    if name not in _loggers:
        return setup_logger(name)
    
    return _loggers[name]


def set_log_level(level: int, name: str = "hiring_agent") -> None:
    """
    Change log level for a logger.
    
    Args:
        level: New logging level
        name: Logger name
    """
    logger = get_logger(name)
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


# Convenience functions for quick logging
def debug(msg: str, *args, **kwargs):
    get_logger().debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    get_logger().info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    get_logger().warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    get_logger().error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    get_logger().critical(msg, *args, **kwargs)
