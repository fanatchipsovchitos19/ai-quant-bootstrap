"""
AI Quant Bootstrap — Logging Module
Unified logger with colored console output and file logging.
"""

import sys
import io
import logging
from pathlib import Path
from datetime import datetime

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


# Global logger cache
_loggers: dict[str, logging.Logger] = {}


def setup_logger(
    name: str = "AIQuantBootstrap",
    level: str = "INFO",
    log_dir: str = "data/logs"
) -> logging.Logger:
    """
    Creates and returns a configured logger.
    
    Args:
        name: Logger name (usually bot name like "ArbitrageScanner").
        level: Log level: DEBUG, INFO, WARNING, ERROR.
        log_dir: Directory for log files.
    
    Returns:
        Configured logger instance.
    """
    
    # Return cached logger if already configured
    if name in _loggers:
        return _loggers[name]
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Prevent duplicate handlers on repeated calls
    if logger.handlers:
        _loggers[name] = logger
        return logger
    
    # --- Console Handler (colored if available) ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    if HAS_COLORLOG:
        console_format = colorlog.ColoredFormatter(
            fmt=(
                "%(asctime)s "
                "%(log_color)s%(levelname)-8s%(reset)s "
                "| %(name)-20s "
                "| %(message_log_color)s%(message)s%(reset)s"
            ),
            datefmt="%H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={
                'message': {
                    'DEBUG': 'white',
                    'INFO': 'white',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red',
                }
            }
        )
    else:
        console_format = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s | %(name)-20s | %(message)s",
            datefmt="%H:%M:%S"
        )
    
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # --- File Handler (all logs to file) ---
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    file_name = f"{name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(
        log_path / file_name,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    _loggers[name] = logger
    return logger


def get_logger(name: str = "AIQuantBootstrap") -> logging.Logger:
    """
    Returns an existing logger or creates a default one.
    """
    if name in _loggers:
        return _loggers[name]
    return setup_logger(name)


# Quick test
if __name__ == "__main__":
    log = setup_logger("TestLogger", "DEBUG")
    log.debug("Debug message — детали для отладки.")
    log.info("Info message — бот запущен.")
    log.warning("Warning message — что-то подозрительное.")
    log.error("Error message — ошибка, но бот работает.")