"""
Plugin system for SimTool simulator extensibility.
"""

import importlib
import importlib.util
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Type, Optional, Any
from dataclasses import dataclass

from .logging import get_logger
from ..toolchain.base import ISimulator


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    name: str
    version: str
    description: str
    author: str
    supported_formats: List[str]
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ISimulatorPlugin(ABC):
    """Interface for simulator plugins."""
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        pass
    
    @abstractmethod
    def create_adapter(self, config: Dict[str, Any]) -> ISimulator:
        """Create simulator adapter instance."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if simulator is available on the system."""
        pass


class PluginRegistry:
    """Registry for simulator plugins."""
    
    def __init__(self):
        self.logger = get_logger()
        self._plugins: Dict[str, ISimulatorPlugin] = {}
        self._builtin_simulators = {
            'verilator': 'src.toolchain.verilator:VerilatorPlugin'
        }
    
    def register_plugin(self, plugin: ISimulatorPlugin) -> None:
        """
        Register a simulator plugin.
        
        Args:
            plugin: Plugin instance to register
        """
        name = plugin.metadata.name.lower()
        
        if name in self._plugins:
            self.logger.warning(f"Plugin '{name}' already registered, replacing")
        
        self._plugins[name] = plugin
        self.logger.debug(f"Registered plugin: {name}")
    
    def get_plugin(self, name: str) -> Optional[ISimulatorPlugin]:
        """
        Get plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(name.lower())
    
    def list_plugins(self) -> List[str]:
        """Get list of registered plugin names."""
        return list(self._plugins.keys())
    
    def list_available_plugins(self) -> List[str]:
        """Get list of available (installed) plugin names."""
        available = []
        for name, plugin in self._plugins.items():
            try:
                if plugin.is_available():
                    available.append(name)
            except Exception as e:
                self.logger.debug(f"Error checking availability of plugin '{name}': {e}")
        return available
    
    def create_simulator(self, name: str, config: Dict[str, Any]) -> ISimulator:
        """
        Create simulator instance from plugin.
        
        Args:
            name: Simulator name
            config: Configuration dictionary
            
        Returns:
            Simulator adapter instance
            
        Raises:
            ValueError: If plugin not found or simulator not available
        """
        plugin = self.get_plugin(name)
        if plugin is None:
            raise ValueError(f"Simulator plugin '{name}' not found")
        
        if not plugin.is_available():
            raise ValueError(f"Simulator '{name}' is not available on this system")
        
        return plugin.create_adapter(config)
    
    def load_builtin_plugins(self) -> None:
        """Load built-in simulator plugins."""
        for name, module_path in self._builtin_simulators.items():
            try:
                self._load_plugin_from_path(module_path)
                self.logger.debug(f"Loaded built-in plugin: {name}")
            except Exception as e:
                self.logger.error(f"Failed to load built-in plugin '{name}': {e}")
    
    def load_plugins_from_directory(self, plugin_dir: Path) -> None:
        """
        Load plugins from directory.
        
        Args:
            plugin_dir: Directory containing plugin files
        """
        if not plugin_dir.exists() or not plugin_dir.is_dir():
            self.logger.debug(f"Plugin directory not found: {plugin_dir}")
            return
        
        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue  # Skip private files
                
            try:
                self._load_plugin_from_file(plugin_file)
                self.logger.debug(f"Loaded plugin from: {plugin_file}")
            except Exception as e:
                self.logger.error(f"Failed to load plugin from '{plugin_file}': {e}")
    
    def _load_plugin_from_path(self, module_path: str) -> None:
        """Load plugin from module path (module:class format)."""
        if ':' not in module_path:
            raise ValueError(f"Invalid module path format: {module_path}")
        
        module_name, class_name = module_path.split(':', 1)
        
        try:
            module = importlib.import_module(module_name)
            plugin_class = getattr(module, class_name)
            
            if not issubclass(plugin_class, ISimulatorPlugin):
                raise TypeError(f"Class '{class_name}' is not a simulator plugin")
            
            plugin_instance = plugin_class()
            self.register_plugin(plugin_instance)
            
        except ImportError as e:
            raise ImportError(f"Failed to import module '{module_name}': {e}")
        except AttributeError:
            raise AttributeError(f"Class '{class_name}' not found in module '{module_name}'")
    
    def _load_plugin_from_file(self, plugin_file: Path) -> None:
        """Load plugin from Python file."""
        spec = importlib.util.spec_from_file_location(plugin_file.stem, plugin_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {plugin_file}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find plugin classes in module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, ISimulatorPlugin) and 
                obj is not ISimulatorPlugin and 
                obj.__module__ == module.__name__):
                
                plugin_instance = obj()
                self.register_plugin(plugin_instance)
                break
        else:
            raise ValueError(f"No simulator plugin class found in {plugin_file}")


# Global plugin registry
_registry = None

def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
        _registry.load_builtin_plugins()
        
        # Load plugins from standard locations
        plugin_dirs = [
            Path.home() / '.simtool' / 'plugins',
            Path('/usr/local/share/simtool/plugins'),
            Path('/opt/simtool/plugins')
        ]
        
        for plugin_dir in plugin_dirs:
            _registry.load_plugins_from_directory(plugin_dir)
    
    return _registry