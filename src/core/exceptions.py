"""
SimTool custom exceptions with better error context.
"""

import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any


class SimToolError(Exception):
    """Base exception class for SimTool with enhanced error context."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, 
                 suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.context = context or {}
        self.suggestions = suggestions or []
    
    def get_detailed_message(self) -> str:
        """Get detailed error message with context and suggestions."""
        lines = [str(self)]
        
        if self.context:
            lines.append("\nError Context:")
            for key, value in self.context.items():
                lines.append(f"  {key}: {value}")
        
        if self.suggestions:
            lines.append("\nSuggestions:")
            for i, suggestion in enumerate(self.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
        
        return "\n".join(lines)


class ProjectConfigError(SimToolError):
    """Raised when project configuration is invalid or missing."""
    
    def __init__(self, message: str, config_path: Optional[Path] = None, 
                 field: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if config_path:
            context['config_file'] = str(config_path)
        if field:
            context['invalid_field'] = field
        
        suggestions = kwargs.get('suggestions', [])
        if not suggestions and not config_path:
            suggestions.append("Run 'simtool init' to create a new project")
        elif field:
            suggestions.append(f"Check the '{field}' field in your configuration file")
            suggestions.append("Refer to simtool documentation for valid configuration options")
        
        super().__init__(message, context, suggestions)


class SimulatorNotFoundError(SimToolError):
    """Raised when a requested simulator is not available."""
    
    def __init__(self, simulator_name: str, available_simulators: Optional[List[str]] = None, **kwargs):
        message = f"Simulator '{simulator_name}' is not available"
        
        context = kwargs.get('context', {})
        context['requested_simulator'] = simulator_name
        if available_simulators:
            context['available_simulators'] = available_simulators
        
        suggestions = kwargs.get('suggestions', [])
        if not suggestions:
            suggestions.append("Run 'simtool doctor' to check simulator installations")
            if available_simulators:
                suggestions.append(f"Use one of the available simulators: {', '.join(available_simulators)}")
            else:
                suggestions.append("Install the required simulator (e.g., 'apt install verilator' on Ubuntu)")
        
        super().__init__(message, context, suggestions)


class CompilationFailedError(SimToolError):
    """Raised when RTL compilation fails."""
    
    def __init__(self, message: str, simulator: Optional[str] = None, 
                 files: Optional[List[Path]] = None, stderr: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if simulator:
            context['simulator'] = simulator
        if files:
            context['source_files'] = [str(f) for f in files]
        if stderr:
            context['compiler_output'] = stderr
        
        suggestions = kwargs.get('suggestions', [])
        if not suggestions:
            suggestions.append("Check syntax errors in your RTL files")
            suggestions.append("Verify include paths and file dependencies")
            suggestions.append("Run with --verbose for more detailed output")
        
        super().__init__(message, context, suggestions)


class SimulationFailedError(SimToolError):
    """Raised when simulation execution fails."""
    
    def __init__(self, message: str, module: Optional[str] = None, 
                 executable: Optional[Path] = None, stderr: Optional[str] = None, **kwargs):
        context = kwargs.get('context', {})
        if module:
            context['top_module'] = module
        if executable:
            context['executable'] = str(executable)
        if stderr:
            context['simulation_output'] = stderr
        
        suggestions = kwargs.get('suggestions', [])
        if not suggestions:
            suggestions.append("Run 'simtool vlog' first to compile your design")
            suggestions.append("Check testbench logic and simulation time limits")
            if not executable or not executable.exists():
                suggestions.append("Verify the executable was generated during compilation")
        
        super().__init__(message, context, suggestions)


class FileDiscoveryError(SimToolError):
    """Raised when required files cannot be found."""
    
    def __init__(self, message: str, search_paths: Optional[List[Path]] = None, 
                 patterns: Optional[List[str]] = None, **kwargs):
        context = kwargs.get('context', {})
        if search_paths:
            context['search_paths'] = [str(p) for p in search_paths]
        if patterns:
            context['file_patterns'] = patterns
        
        suggestions = kwargs.get('suggestions', [])
        if not suggestions:
            suggestions.append("Check that your files exist in the expected directories")
            suggestions.append("Verify rtl_paths and tb_paths in your simtool.cfg")
            suggestions.append("Use absolute paths or run from project root directory")
        
        super().__init__(message, context, suggestions)


class ToolNotFoundError(SimToolError):
    """Raised when required external tools are not found."""
    
    def __init__(self, tool_name: str, install_command: Optional[str] = None, **kwargs):
        message = f"Required tool '{tool_name}' not found in PATH"
        
        context = kwargs.get('context', {})
        context['missing_tool'] = tool_name
        
        suggestions = kwargs.get('suggestions', [])
        if not suggestions:
            suggestions.append("Run 'simtool doctor' to check all tool installations")
            if install_command:
                suggestions.append(f"Install with: {install_command}")
            suggestions.append(f"Ensure {tool_name} is in your system PATH")
        
        super().__init__(message, context, suggestions)


class PluginError(SimToolError):
    """Raised when plugin loading or execution fails."""
    
    def __init__(self, message: str, plugin_name: Optional[str] = None, 
                 plugin_path: Optional[Path] = None, **kwargs):
        context = kwargs.get('context', {})
        if plugin_name:
            context['plugin_name'] = plugin_name
        if plugin_path:
            context['plugin_path'] = str(plugin_path)
        
        suggestions = kwargs.get('suggestions', [])
        if not suggestions:
            suggestions.append("Check plugin compatibility with SimTool version")
            suggestions.append("Verify plugin dependencies are installed")
            suggestions.append("Check plugin file permissions and syntax")
        
        super().__init__(message, context, suggestions)


def format_exception_with_context(exc: Exception, additional_context: Optional[Dict[str, Any]] = None) -> str:
    """Format any exception with additional context information."""
    if isinstance(exc, SimToolError):
        # Already has context, just add any additional context
        if additional_context:
            exc.context.update(additional_context)
        return exc.get_detailed_message()
    
    # For non-SimTool exceptions, create a formatted message
    lines = [f"Error: {exc}"]
    
    if additional_context:
        lines.append("\nContext:")
        for key, value in additional_context.items():
            lines.append(f"  {key}: {value}")
    
    # Add traceback for debugging
    lines.append(f"\nException Type: {type(exc).__name__}")
    
    return "\n".join(lines)


def get_exception_suggestions(exc: Exception) -> List[str]:
    """Get suggestions for common exception types."""
    exc_type = type(exc).__name__
    message = str(exc).lower()
    
    suggestions = []
    
    if "filenotfound" in exc_type.lower() or "no such file" in message:
        suggestions.extend([
            "Check that the file path is correct",
            "Verify you're running from the correct directory",
            "Ensure the file exists and has proper permissions"
        ])
    
    elif "permission" in message:
        suggestions.extend([
            "Check file permissions",
            "Try running with appropriate privileges",
            "Ensure the file is not locked by another process"
        ])
    
    elif "timeout" in message:
        suggestions.extend([
            "Check if the process is hanging",
            "Try increasing timeout values",
            "Verify system resources are available"
        ])
    
    elif "import" in message or "module" in message:
        suggestions.extend([
            "Check that required Python packages are installed",
            "Verify your Python environment and PATH",
            "Try reinstalling the missing package"
        ])
    
    return suggestions