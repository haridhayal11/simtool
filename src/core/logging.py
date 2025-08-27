"""
Centralized logging configuration for SimTool.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from ..ui.colors import Colors


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for different log levels."""
    
    COLORS = {
        logging.DEBUG: Colors.DIM,
        logging.INFO: Colors.INFO,
        logging.WARNING: Colors.WARNING,  
        logging.ERROR: Colors.ERROR,
        logging.CRITICAL: Colors.ERROR + Colors.BRIGHT,
    }
    
    SYMBOLS = {
        logging.DEBUG: '·',
        logging.INFO: 'ℹ',
        logging.WARNING: '⚠',
        logging.ERROR: '✗',
        logging.CRITICAL: '💥',
    }
    
    def format(self, record):
        # Get color and symbol for log level
        color = self.COLORS.get(record.levelno, '')
        symbol = self.SYMBOLS.get(record.levelno, '')
        
        # Format the message
        if hasattr(record, 'no_symbol') and record.no_symbol:
            # Skip symbol for certain messages (like command output)
            formatted = f"{color}{record.getMessage()}{Colors.RESET}"
        else:
            formatted = f"{color}{symbol} {record.getMessage()}{Colors.RESET}"
        
        return formatted


class SimToolLogger:
    """Centralized logger for SimTool with consistent formatting."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.logger = logging.getLogger('simtool')
            self.setup_logging()
            self._initialized = True
    
    def setup_logging(self, level: int = logging.INFO, log_file: Optional[Path] = None):
        """Setup logging configuration."""
        self.logger.setLevel(level)
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(ColoredFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)  # File gets all messages
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def set_level(self, level: int):
        """Set logging level."""
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message (info level with success formatting)."""
        # Custom success logging
        colored_msg = f"{Colors.SUCCESS}✓ {message}{Colors.RESET}"
        self.logger.info(colored_msg, extra={'no_symbol': True, **kwargs})
    
    def progress(self, message: str, **kwargs):
        """Log progress message."""
        colored_msg = f"{Colors.CYAN}→ {message}{Colors.RESET}"
        self.logger.info(colored_msg, extra={'no_symbol': True, **kwargs})
    
    def command(self, message: str, **kwargs):
        """Log command execution."""
        colored_msg = f"{Colors.COMMAND}{message}{Colors.RESET}"
        self.logger.info(colored_msg, extra={'no_symbol': True, **kwargs})
    
    def header(self, message: str, **kwargs):
        """Log header message."""
        colored_msg = f"{Colors.BRIGHT}{Colors.BLUE}{message}{Colors.RESET}"
        self.logger.info(colored_msg, extra={'no_symbol': True, **kwargs})


# Global logger instance
logger = SimToolLogger()

# Convenience functions for backward compatibility
def setup_logging(verbose: bool = False, quiet: bool = False, log_file: Optional[Path] = None):
    """Setup logging based on CLI flags."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logger.setup_logging(level, log_file)

def get_logger() -> SimToolLogger:
    """Get the global logger instance."""
    return logger