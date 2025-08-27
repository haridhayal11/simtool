"""
Base simulator interface and common functionality.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import subprocess


class ISimulator(ABC):
    """Interface for simulator adapters."""
    
    def __init__(self, project_config: Dict[str, Any]):
        self.config = project_config
    
    @abstractmethod
    def compile(self, files: List[Path], top_module: str, **kwargs) -> bool:
        """Compile RTL files."""
        pass
    
    @abstractmethod 
    def simulate(self, top_module: str, waves: bool = False, gui: bool = False, **kwargs) -> bool:
        """Run simulation."""
        pass
    
    @abstractmethod
    def clean(self) -> bool:
        """Clean build artifacts."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if simulator is available on system."""
        pass


class SimulatorError(Exception):
    """Base exception for simulator errors."""
    pass


class CompilationError(SimulatorError):
    """Exception raised during compilation."""
    pass


class SimulationError(SimulatorError):
    """Exception raised during simulation."""
    pass