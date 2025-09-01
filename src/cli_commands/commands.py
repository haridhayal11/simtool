"""
CLI command handlers with separated concerns.
"""

import subprocess
import shutil
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..core.project import Project
from ..core.logging import get_logger
from ..core.plugin_system import get_plugin_registry
from ..core.constants import DefaultPaths, DefaultConfig, ProjectStructureMessages
from ..core.exceptions import (
    ProjectConfigError, SimulatorNotFoundError, CompilationFailedError,
    SimulationFailedError, ToolNotFoundError, format_exception_with_context
)
from ..toolchain.base import SimulatorError, CompilationError, SimulationError
from ..ui.colors import success, error, progress, info, warning, header


class ProjectInitializer:
    """Handles project initialization."""
    
    def __init__(self):
        self.logger = get_logger()
    
    def initialize_project(self, simulator: str = DefaultConfig.SIMULATOR, force: bool = False) -> bool:
        """Initialize a new SimTool project."""
        try:
            # Create directory structure
            directories = [
                DefaultPaths.RTL_DIR,
                DefaultPaths.TESTBENCH_DIR,
                DefaultPaths.BUILD_DIR,
                DefaultPaths.SCRIPTS_DIR
            ]
            
            for dir_name in directories:
                dir_path = Path(dir_name)
                if dir_path.exists() and not force:
                    pass  # Directory already exists
                else:
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.logger.success(f"Created directory: {dir_path}")
            
            # Create configuration file
            self._create_config_file(simulator, force)
            
            # Log success
            self.logger.success(f"Initialized SimTool project with {simulator} as default simulator")
            self._show_project_structure()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize project: {e}")
            return False
    
    def _create_config_file(self, simulator: str, force: bool):
        """Create the simtool.cfg configuration file."""
        config_file = Path(DefaultPaths.CONFIG_FILE)
        
        if config_file.exists() and not force:
            return  # Config file already exists
        
        config_content = f"""default_simulator: {simulator}
default_waves: {str(DefaultConfig.WAVES_ENABLED).lower()}
rtl_paths: 
  - {DefaultPaths.RTL_DIR}
tb_paths:
  - {DefaultPaths.TESTBENCH_DIR}
build_dir: {DefaultPaths.BUILD_DIR}
include_paths: []
defines: {{}}
systemc_path: null
gtkwave_path: null
verilator_path: null"""
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        self.logger.success(f"Created config file: {config_file}")
    
    def _show_project_structure(self):
        """Display the created project structure."""
        self.logger.header("Project structure:")
        self.logger.info(f"  {DefaultPaths.RTL_DIR}/       - {ProjectStructureMessages.RTL_DESC}", no_symbol=True)
        self.logger.info(f"  tb/        - {ProjectStructureMessages.TB_DESC}", no_symbol=True)
        self.logger.info(f"  {DefaultPaths.BUILD_DIR}/      - {ProjectStructureMessages.WORK_DESC}", no_symbol=True)
        self.logger.info(f"  {DefaultPaths.SCRIPTS_DIR}/   - {ProjectStructureMessages.SCRIPTS_DESC}", no_symbol=True)


class CompileHandler:
    """Handles RTL compilation."""
    
    def __init__(self):
        self.logger = get_logger()
    
    def compile_rtl(self, files: List[Path], top_module: str, simulator: Optional[str] = None,
                   tb_type: str = 'auto', waves: Optional[bool] = None, verbose: bool = False) -> bool:
        """Compile RTL files with the specified simulator."""
        try:
            # Load project configuration
            project = Project()
            
            # Get source files
            if files:
                # User specified files - separate RTL from testbench files
                rtl_files = []
                tb_files = []
                
                for file in files:
                    if file.suffix.lower() in ['.sv', '.v', '.vhd']:
                        # Check if this looks like a testbench based on content or name
                        if project._is_sv_testbench(file) or 'tb' in file.stem or 'test' in file.stem:
                            tb_files.append(file)
                        else:
                            rtl_files.append(file)
                    elif file.suffix.lower() == '.py':
                        if project._is_cocotb_testbench(file):
                            tb_files.append(file)
                    elif file.suffix.lower() in ['.cpp', '.c']:
                        if project._is_cpp_testbench(file):
                            tb_files.append(file)
                
                detected_tb_type = project.detect_testbench_type(tb_files) if tb_files else 'none'
                
                if not rtl_files:
                    self.logger.error("No RTL files found in specified files")
                    return False
            else:
                # No files specified - discover from project
                rtl_files = project.get_rtl_files()
                if not rtl_files:
                    self.logger.error("No RTL files found")
                    return False
                
                # Get testbench files only when auto-discovering
                tb_files = project.get_tb_files(tb_type)
                detected_tb_type = project.detect_testbench_type(tb_files)
            
            if verbose:
                self.logger.info(f"RTL files: {[str(f) for f in rtl_files]}")
                self.logger.info(f"Testbench files: {[str(f) for f in tb_files]}")
                self.logger.info(f"Detected testbench type: {detected_tb_type}")
            
            # Create simulator adapter
            sim_name = simulator or project.default_simulator
            sim = self._create_simulator(sim_name, project)
            
            # Determine waves setting
            enable_waves = waves if waves is not None else project.default_waves
            
            # Compile
            self.logger.info(f"Compiling with {sim_name}...")
            if enable_waves:
                self.logger.info("Transparent VCD waveform generation enabled")
            
            testbench = tb_files[0] if tb_files else None
            success = sim.compile(rtl_files, top_module, testbench=testbench, waves=enable_waves)
            
            if success:
                self.logger.success("Compilation successful")
            else:
                self.logger.error("Compilation failed")
            
            return success
            
        except FileNotFoundError as e:
            exc = ProjectConfigError(
                str(e),
                suggestions=[
                    "Run 'simtool init' to initialize a project",
                    f"Ensure you're in the correct directory with {DefaultPaths.CONFIG_FILE}",
                    "Check that the configuration file exists and is readable"
                ]
            )
            self.logger.error(exc.get_detailed_message())
            return False
            
        except (CompilationError, SimulatorError) as e:
            exc = CompilationFailedError(
                str(e),
                simulator=sim_name if 'sim_name' in locals() else 'unknown',
                files=rtl_files if 'rtl_files' in locals() else [],
                context={
                    'command': 'compile',
                    'top_module': top_module,
                    'waves_enabled': enable_waves if 'enable_waves' in locals() else None,
                    'testbench_type': detected_tb_type if 'detected_tb_type' in locals() else 'none'
                }
            )
            self.logger.error(exc.get_detailed_message())
            return False
    
    def _create_simulator(self, sim_name: str, project: Project):
        """Create simulator adapter using plugin system."""
        try:
            registry = get_plugin_registry()
            return registry.create_simulator(sim_name, project.config)
        except ValueError as e:
            available = registry.list_available_plugins()
            raise SimulatorNotFoundError(
                sim_name,
                available_simulators=available,
                context={'requested_from': 'compile_handler'}
            )


class SimulationHandler:
    """Handles simulation execution."""
    
    def __init__(self):
        self.logger = get_logger()
    
    def run_simulation(self, module: str, gui: bool = False,
                      time: Optional[str] = None, simulator: Optional[str] = None,
                      verbose: bool = False) -> bool:
        """Run simulation of the specified module."""
        try:
            # Load project configuration
            project = Project()
            
            # Create simulator adapter
            sim_name = simulator or project.default_simulator
            sim = self._create_simulator(sim_name, project)
            
            # Auto-detect if waves were enabled during compilation
            waves = self._detect_tracing_enabled(project)
            
            # Parse and validate time parameter if provided
            parsed_time = self._parse_time_parameter(time) if time else None
            
            if verbose:
                self.logger.info(f"Simulator: {sim_name}")
                self.logger.info(f"Module: {module}")
                self.logger.info(f"Waves: {waves}")
                self.logger.info(f"GUI: {gui}")
                if parsed_time:
                    self.logger.info(f"Time: {parsed_time}")
            
            # Run simulation
            self.logger.info(f"Running simulation of {module}...")
            success = sim.simulate(module, waves=waves, gui=gui, time=parsed_time)
            
            if success:
                self.logger.success("Simulation completed")
                if waves:
                    vcd_file = Path(f"{module}.vcd")
                    if vcd_file.exists():
                        self.logger.info(f"Waveform saved to: {vcd_file}")
            else:
                self.logger.error("Simulation failed")
            
            return success
            
        except FileNotFoundError as e:
            self.logger.error(str(e))
            self.logger.info("Run 'simtool init' to initialize a project and 'simtool vlog' to compile")
            return False
            
        except (SimulationError, SimulatorError) as e:
            exc = SimulationFailedError(
                str(e),
                module=module,
                context={
                    'command': 'simulate',
                    'simulator': sim_name if 'sim_name' in locals() else 'unknown',
                    'waves_enabled': waves,
                    'gui_requested': gui
                }
            )
            self.logger.error(exc.get_detailed_message())
            return False
    
    def _create_simulator(self, sim_name: str, project: Project):
        """Create simulator adapter using plugin system."""
        try:
            registry = get_plugin_registry()
            return registry.create_simulator(sim_name, project.config)
        except ValueError as e:
            available = registry.list_available_plugins()
            raise SimulatorNotFoundError(
                sim_name,
                available_simulators=available,
                context={'requested_from': 'simulation_handler'}
            )
    
    def _detect_tracing_enabled(self, project) -> bool:
        """Auto-detect if tracing was enabled during compilation."""
        try:
            # Method 1: Check project configuration for default waves setting
            if hasattr(project, 'default_waves') and project.default_waves:
                return True
            
            # Method 2: Look for build artifacts that indicate tracing was enabled
            build_dir = Path(project.project_path) / 'work'
            if build_dir.exists():
                # Check for Verilator trace-related files
                trace_files = list(build_dir.glob('*trace*')) + list(build_dir.glob('*vcd*'))
                if trace_files:
                    return True
                
                # Check makefiles for trace flags
                makefiles = list(build_dir.glob('*.mk'))
                for makefile in makefiles:
                    try:
                        content = makefile.read_text()
                        if '--trace' in content or 'verilated_vcd' in content:
                            return True
                    except:
                        pass
            
            # Method 3: Check for existing waveform files in project directory
            project_path = Path(project.project_path)
            wave_files = (list(project_path.glob('*.vcd')) + 
                         list(project_path.glob('*.fst')) +
                         list(project_path.glob('*.ghw')))
            if wave_files:
                self.logger.info("Found existing waveform files - assuming tracing was enabled")
                return True
            
            # Method 4: Default fallback - assume tracing is available
            # This is safer than assuming it's not available
            self.logger.debug("Could not determine tracing status, assuming enabled")
            return True
            
        except Exception as e:
            self.logger.debug(f"Error detecting tracing: {e}, assuming enabled")
            return True
    
    def _parse_time_parameter(self, time_str: str) -> str:
        """Parse time parameter with units and return in simulator-compatible format."""
        if not time_str:
            return None
        
        # Regular expression to match number and optional unit
        time_pattern = r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]*)$'
        match = re.match(time_pattern, time_str.strip())
        
        if not match:
            self.logger.warning(f"Invalid time format: {time_str}, expected format: <number><unit> (e.g., 1000ns, 10us, 1ms)")
            return time_str  # Return as-is and let simulator handle it
        
        value, unit = match.groups()
        unit = unit.lower() if unit else ''
        
        # Validate and normalize time units
        valid_units = {
            '': 'ns',      # Default to nanoseconds if no unit specified
            'ps': 'ps',    # picoseconds
            'ns': 'ns',    # nanoseconds  
            'us': 'us',    # microseconds
            'ms': 'ms',    # milliseconds
            's': 's',      # seconds
        }
        
        if unit not in valid_units:
            self.logger.warning(f"Unknown time unit '{unit}', supported units: {list(valid_units.keys())}")
            return time_str  # Return as-is and let simulator handle it
        
        # Return formatted time string
        normalized_unit = valid_units[unit]
        result = f"{value}{normalized_unit}"
        self.logger.debug(f"Parsed time parameter: {time_str} -> {result}")
        return result


class CleanupHandler:
    """Handles build artifact cleanup."""
    
    def __init__(self):
        self.logger = get_logger()
    
    def clean_artifacts(self, verbose: bool = False) -> bool:
        """Clean build artifacts."""
        try:
            # Load project configuration
            project = Project()
            
            # Create simulator adapter for cleanup
            sim_name = project.default_simulator
            sim = self._create_simulator(sim_name, project)
            
            if verbose:
                self.logger.info(f"Cleaning {sim_name} artifacts...")
            
            # Clean
            success = sim.clean()
            
            if success:
                self.logger.success("Clean completed")
            else:
                self.logger.error("Clean failed")
            
            return success
            
        except FileNotFoundError as e:
            self.logger.error(str(e))
            self.logger.info("Run 'simtool init' to initialize a project")
            return False
            
        except Exception as e:
            self.logger.error(str(e))
            return False
    
    def _create_simulator(self, sim_name: str, project: Project):
        """Create simulator adapter using plugin system."""
        try:
            registry = get_plugin_registry()
            return registry.create_simulator(sim_name, project.config)
        except ValueError as e:
            available = registry.list_available_plugins()
            raise SimulatorNotFoundError(
                sim_name,
                available_simulators=available,
                context={'requested_from': 'cleanup_handler'}
            )


class DoctorHandler:
    """Handles system diagnostic checks."""
    
    def __init__(self):
        self.logger = get_logger()
    
    def check_system(self) -> bool:
        """Check tool installation and environment."""
        self.logger.header("Checking simulator installations:")
        
        # Check Verilator
        self._check_verilator()
        
        # Check other tools
        self.logger.header("\nChecking other tools:")
        other_tools = ['gtkwave', 'make', 'cmake']
        
        for tool in other_tools:
            if shutil.which(tool):
                self.logger.success(f"{tool}: Found")
            else:
                self.logger.warning(f"{tool}: Not found (optional)")
        
        return True
    
    def _check_verilator(self):
        """Check Verilator installation and version."""
        verilator_path = shutil.which('verilator')
        if verilator_path:
            try:
                result = subprocess.run(['verilator', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    version_line = result.stdout.strip().split('\n')[0]
                    self.logger.success(f"Verilator: {version_line}")
                else:
                    self.logger.error("Verilator: Found but error getting version")
            except Exception:
                self.logger.error("Verilator: Found but error getting version")
        else:
            self.logger.error("Verilator: Not found")