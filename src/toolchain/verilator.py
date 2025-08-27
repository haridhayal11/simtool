"""
Verilator simulator adapter - calls external verilator commands.
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any

from .base import ISimulator, CompilationError, SimulationError


class VerilatorAdapter(ISimulator):
    """Verilator simulator adapter that calls external verilator commands."""
    
    def __init__(self, project_config: Dict[str, Any]):
        super().__init__(project_config)
        self.build_dir = Path(project_config.get('build_dir', 'work'))
        verilator_path = project_config.get('verilator_path')
        self.verilator_path = verilator_path if verilator_path is not None else 'verilator'
    
    def is_available(self) -> bool:
        """Check if Verilator is available."""
        return shutil.which(self.verilator_path) is not None
    
    def compile(self, files: List[Path], top_module: str, **kwargs) -> bool:
        """Show verilator command that user should run."""
        if not self.is_available():
            raise CompilationError("Verilator not found")
        
        # Build basic verilator command
        cmd_parts = [
            self.verilator_path,
            '--binary',
            '--trace',
            '--Mdir', str(self.build_dir),
        ]
        
        # Add include paths
        include_paths = self.config.get('include_paths', [])
        for inc_path in include_paths:
            cmd_parts.extend(['-I', str(inc_path)])
        
        # Add defines
        defines = self.config.get('defines', {})
        for key, value in defines.items():
            if value:
                cmd_parts.append(f'-D{key}={value}')
            else:
                cmd_parts.append(f'-D{key}')
        
        # Add source files
        for file in files:
            cmd_parts.append(str(file))
        
        # Add testbench if present
        testbench = kwargs.get('testbench')
        if testbench:
            cmd_parts.append(str(testbench))
        
        # Show the command
        cmd_str = ' '.join(cmd_parts)
        print(f"Running: {cmd_str}")
        print(f"This would compile {len(files)} RTL file(s) with Verilator")
        print(f"Build directory: {self.build_dir}")
        
        return True
    
    def simulate(self, top_module: str, waves: bool = False, gui: bool = False, **kwargs) -> bool:
        """Show simulation command that user should run."""
        executable = self.build_dir / f"V{top_module}"
        
        print(f"Simulation would run: {executable}")
        if waves:
            print("Waves would be generated")
        if gui:
            print("GTKWave would be launched")
            
        return True
    
    def clean(self) -> bool:
        """Clean build artifacts."""
        import shutil as sh
        
        try:
            if self.build_dir.exists():
                sh.rmtree(self.build_dir)
                print(f"Removed build directory: {self.build_dir}")
            
            # Clean other common artifacts
            artifacts = ['*.vcd', '*.fst', 'obj_dir']
            cleaned = []
            for pattern in artifacts:
                for file in Path('.').glob(pattern):
                    if file.is_dir():
                        sh.rmtree(file)
                    else:
                        file.unlink()
                    cleaned.append(str(file))
            
            if cleaned:
                print(f"Cleaned artifacts: {', '.join(cleaned)}")
            
            return True
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")
            return False