"""
SimTool constants and default configurations.
"""

from pathlib import Path
from typing import List, Dict, Any


class DefaultPaths:
    """Default directory and file paths for SimTool projects."""
    
    # Default directories created during project initialization
    RTL_DIR = "rtl"
    TESTBENCH_COCOTB_DIR = "tb/cocotb"
    TESTBENCH_SV_DIR = "tb/sv"
    BUILD_DIR = "work"
    SCRIPTS_DIR = "scripts"
    
    # Default search paths
    DEFAULT_RTL_PATHS = [RTL_DIR]
    DEFAULT_TB_PATHS = [TESTBENCH_COCOTB_DIR, TESTBENCH_SV_DIR]
    
    # Configuration file
    CONFIG_FILE = "simtool.cfg"
    
    # Common file extensions
    RTL_EXTENSIONS = ["*.sv", "*.v", "*.vhd"]
    PYTHON_EXTENSION = "*.py"
    SV_EXTENSION = "*.sv"
    CPP_EXTENSION = "*.cpp"
    
    # VCD/Waveform files
    VCD_FILE = "simulation.vcd"
    FST_FILE = "simulation.fst"


class DefaultConfig:
    """Default configuration values for SimTool."""
    
    SIMULATOR = "verilator"
    WAVES_ENABLED = True
    INCLUDE_PATHS: List[str] = []
    DEFINES: Dict[str, Any] = {}
    
    # Tool paths (None means use system PATH)
    VERILATOR_PATH = None
    GTKWAVE_PATH = None
    SYSTEMC_PATH = None


class ProjectStructureMessages:
    """Messages for project structure display."""
    
    RTL_DESC = "RTL source files"
    TB_DESC = "Testbench files"
    WORK_DESC = "Build artifacts (like ModelSim work library)"
    SCRIPTS_DESC = "Utility scripts"


class SimulatorTypes:
    """Supported simulator types."""
    
    VERILATOR = "verilator"
    ICARUS = "icarus"
    QUESTA = "questa"
    XCELIUM = "xcelium"
    
    ALL_SIMULATORS = [VERILATOR, ICARUS, QUESTA, XCELIUM]


class TestbenchTypes:
    """Supported testbench types."""
    
    AUTO = "auto"
    COCOTB = "cocotb"
    SYSTEMVERILOG = "sv"
    CPP = "cpp"
    
    ALL_TYPES = [AUTO, COCOTB, SYSTEMVERILOG]


class VCDPatterns:
    """Patterns for detecting VCD dumping in testbenches."""
    
    DUMPFILE_PATTERNS = ["$dumpfile", "$dumpvars"]
    COCOTB_IMPORT = "import cocotb"
    COCOTB_TEST = "@cocotb.test"
    TB_SUFFIX = "_tb"
    MAIN_FUNCTION = "main("


class PluginPaths:
    """Plugin search paths."""
    
    USER_PLUGINS = Path.home() / '.simtool' / 'plugins'
    SYSTEM_PLUGINS = [
        Path('/usr/local/share/simtool/plugins'),
        Path('/opt/simtool/plugins')
    ]