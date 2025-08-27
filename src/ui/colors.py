"""
Colored output utilities for SimTool CLI.
"""

import colorama
from colorama import Fore, Back, Style

# Initialize colorama
colorama.init(autoreset=True)


class Colors:
    """Color constants and utilities."""
    
    # Basic colors
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE
    
    # Styles
    BRIGHT = Style.BRIGHT
    DIM = Style.DIM
    RESET = Style.RESET_ALL
    
    # Semantic colors
    SUCCESS = GREEN
    ERROR = RED
    WARNING = YELLOW
    INFO = BLUE
    COMMAND = CYAN
    HIGHLIGHT = MAGENTA


def success(text: str) -> str:
    """Format success message."""
    return f"{Colors.SUCCESS}✓ {text}{Colors.RESET}"


def error(text: str) -> str:
    """Format error message."""
    return f"{Colors.ERROR}✗ {text}{Colors.RESET}"


def warning(text: str) -> str:
    """Format warning message."""
    return f"{Colors.WARNING}⚠ {text}{Colors.RESET}"


def info(text: str) -> str:
    """Format info message."""
    return f"{Colors.INFO}ℹ {text}{Colors.RESET}"


def command(text: str) -> str:
    """Format command text."""
    return f"{Colors.COMMAND}{text}{Colors.RESET}"


def highlight(text: str) -> str:
    """Format highlighted text."""
    return f"{Colors.HIGHLIGHT}{text}{Colors.RESET}"


def bold(text: str) -> str:
    """Format bold text."""
    return f"{Colors.BRIGHT}{text}{Colors.RESET}"


def dim(text: str) -> str:
    """Format dimmed text."""
    return f"{Colors.DIM}{text}{Colors.RESET}"


def header(text: str) -> str:
    """Format header text."""
    return f"{Colors.BRIGHT}{Colors.BLUE}{text}{Colors.RESET}"


def progress(text: str) -> str:
    """Format progress text."""
    return f"{Colors.CYAN}→ {text}{Colors.RESET}"