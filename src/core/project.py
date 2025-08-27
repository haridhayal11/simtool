"""
SimTool project configuration and management.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any


class Project:
    """Manages SimTool project configuration and file discovery."""
    
    def __init__(self, config_path: str = "simtool.cfg"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load project configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Project config not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    @property
    def build_dir(self) -> Path:
        """Get build directory path."""
        return Path(self.config.get('build_dir', 'work'))
    
    @property 
    def rtl_paths(self) -> List[Path]:
        """Get RTL source paths."""
        paths = self.config.get('rtl_paths', ['rtl'])
        return [Path(p) for p in paths]
    
    @property
    def tb_paths(self) -> List[Path]:
        """Get testbench paths.""" 
        paths = self.config.get('tb_paths', ['tb'])
        return [Path(p) for p in paths]
        
    @property
    def default_simulator(self) -> str:
        """Get default simulator."""
        return self.config.get('default_simulator', 'verilator')
        
    @property
    def default_waves(self) -> bool:
        """Get default waves setting."""
        return self.config.get('default_waves', True)
    
    def get_rtl_files(self, patterns: List[str] = None) -> List[Path]:
        """Find RTL files matching patterns."""
        if patterns is None:
            patterns = ['*.sv', '*.v', '*.vhd']
            
        files = []
        for rtl_path in self.rtl_paths:
            if rtl_path.exists():
                for pattern in patterns:
                    files.extend(rtl_path.glob(pattern))
        return files
    
    def get_tb_files(self, tb_type: str = 'auto') -> List[Path]:
        """Find testbench files."""
        files = []
        
        for tb_path in self.tb_paths:
            if not tb_path.exists():
                continue
                
            if tb_type == 'auto' or tb_type == 'cocotb':
                # Find cocotb testbenches
                for py_file in tb_path.rglob('*.py'):
                    if self._is_cocotb_testbench(py_file):
                        files.append(py_file)
            
            if tb_type == 'auto' or tb_type == 'sv':
                # Find SystemVerilog testbenches
                for sv_file in tb_path.rglob('*.sv'):
                    if self._is_sv_testbench(sv_file):
                        files.append(sv_file)
                        
                for cpp_file in tb_path.rglob('*.cpp'):
                    if self._is_cpp_testbench(cpp_file):
                        files.append(cpp_file)
                        
        return files
    
    def _is_cocotb_testbench(self, file_path: Path) -> bool:
        """Check if Python file is a cocotb testbench."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                return 'import cocotb' in content or '@cocotb.test' in content
        except:
            return False
    
    def _is_sv_testbench(self, file_path: Path) -> bool:
        """Check if SystemVerilog file is a testbench."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                return '_tb' in file_path.stem or 'module' in content and '_tb' in content
        except:
            return False
            
    def _is_cpp_testbench(self, file_path: Path) -> bool:
        """Check if C++ file is a testbench."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                return '_tb' in file_path.stem or 'main(' in content
        except:
            return False
    
    def detect_testbench_type(self, files: List[Path]) -> str:
        """Auto-detect testbench type from files."""
        if not files:
            return 'none'
            
        for file in files:
            if file.suffix == '.py' and self._is_cocotb_testbench(file):
                return 'cocotb'
            elif file.suffix in ['.sv', '.cpp'] and (self._is_sv_testbench(file) or self._is_cpp_testbench(file)):
                return 'sv'
        
        return 'unknown'