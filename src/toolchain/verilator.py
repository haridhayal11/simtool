"""
Verilator simulator adapter - calls external verilator commands.
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from .base import ISimulator, CompilationError, SimulationError
from ..core.logging import get_logger
from ..core.plugin_system import ISimulatorPlugin, PluginMetadata


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
        """Actually run verilator compilation."""
        if not self.is_available():
            raise CompilationError("Verilator not found")
        
        # Create build directory
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        # Store waves setting for simulation  
        waves_enabled = kwargs.get('waves', True)
        self._waves_enabled = waves_enabled
        
        # Generate main.cpp file if waves are enabled
        main_cpp_file = None
        if waves_enabled:
            main_cpp_file = self._generate_main_cpp(top_module, waves_enabled)
        
        # Build basic verilator command
        if waves_enabled and main_cpp_file:
            cmd_parts = [
                self.verilator_path,
                '--cc',
                '--exe',
                '--trace',
                '--timing',
                '--Mdir', str(self.build_dir),
                '--top-module', top_module,
            ]
        else:
            cmd_parts = [
                self.verilator_path,
                '--binary',
                '--trace',
                '--Mdir', str(self.build_dir),
                '--top-module', top_module,
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
        
        # Add generated main.cpp file if using --exe mode
        if waves_enabled and main_cpp_file:
            cmd_parts.append(str(main_cpp_file))
        
        # Store waves setting for simulation phase
        self._compile_waves_enabled = waves_enabled
        
        # Show and run the command
        cmd_str = ' '.join(cmd_parts)
        logger = get_logger()
        logger.command(f"Running: {cmd_str}")
        
        try:
            result = subprocess.run(cmd_parts, capture_output=True, text=True, cwd='.')
            if result.returncode != 0:
                raise CompilationError(f"Verilator compilation failed:\n{result.stderr}")
            
            # If using --exe mode, we need to run make to build the executable
            if waves_enabled and main_cpp_file:
                logger.info("Building executable with make...")
                make_cmd = ['make', '-C', str(self.build_dir), '-f', f'V{top_module}.mk', f'V{top_module}']
                make_result = subprocess.run(make_cmd, capture_output=True, text=True, cwd='.')
                if make_result.returncode != 0:
                    raise CompilationError(f"Make build failed:\n{make_result.stderr}")
                logger.success("Executable built successfully")
            
            logger.success(f"Compiled {len(files)} RTL file(s) with Verilator")
            return True
            
        except subprocess.TimeoutExpired:
            raise CompilationError("Verilator compilation timed out")
        except Exception as e:
            raise CompilationError(f"Verilator compilation error: {e}")
    
    def simulate(self, top_module: str, waves: bool = False, gui: bool = False, **kwargs) -> bool:
        """Actually run the simulation."""
        # Check if we need to regenerate main.cpp with different time limit
        sim_time = kwargs.get('time')
        logger = get_logger()
        if sim_time and waves:
            # Regenerate main.cpp with new time limit
            main_cpp_file = self._generate_main_cpp(top_module, waves, sim_time)
            if main_cpp_file:
                # Rebuild the executable with new time limit
                logger.info(f"Rebuilding with simulation time limit: {sim_time}")
                make_cmd = ['make', '-C', str(self.build_dir), '-f', f'V{top_module}.mk', f'V{top_module}']
                make_result = subprocess.run(make_cmd, capture_output=True, text=True, cwd='.')
                if make_result.returncode != 0:
                    raise SimulationError(f"Make rebuild failed:\n{make_result.stderr}")
        
        executable = self.build_dir / f"V{top_module}"
        
        if not executable.exists():
            raise SimulationError(f"Executable not found: {executable}. Run 'simtool vlog' first.")
        
        logger.info(f"Running simulation: {executable}")
        
        # Run the executable (VCD dumping must be in the testbench)
        sim_cmd = [str(executable)]
        
        try:
            result = subprocess.run(sim_cmd, capture_output=True, text=True, cwd='.')
            
            # Check if VCD was generated and provide helpful guidance
            vcd_generated = Path('simulation.vcd').exists()
            if waves and vcd_generated:
                logger.info("VCD file generated: simulation.vcd")
            elif waves and not vcd_generated:
                logger.warning("VCD file not generated")
                logger.info("SimTool uses transparent VCD generation - no testbench modification needed.")
                logger.info("If VCD generation fails, check that your testbench runs properly.")
            
            if result.returncode != 0:
                raise SimulationError(f"Simulation failed:\n{result.stderr}")
            
            if result.stdout:
                logger.info("Simulation output:\n" + result.stdout)
            
            logger.success("Simulation completed")
            
            # Check for waveform files (FST or VCD) and launch GTKWave if requested
            if gui and waves:
                # Look for FST file first (Verilator's preferred format), then VCD
                wave_file = Path('simulation.fst')
                if not wave_file.exists():
                    wave_file = Path('simulation.vcd')
                if not wave_file.exists():
                    wave_files = list(Path('.').glob('*.fst')) + list(Path('.').glob('*.vcd'))
                    wave_file = wave_files[0] if wave_files else None
                
                if wave_file and wave_file.exists():
                    self._launch_gtkwave(wave_file)
                else:
                    logger.warning("No waveform file found for GUI display")
            elif waves:
                # Look for FST file first, then VCD
                wave_file = Path('simulation.fst')
                if not wave_file.exists():
                    wave_file = Path('simulation.vcd')
                if not wave_file.exists():
                    wave_files = list(Path('.').glob('*.fst')) + list(Path('.').glob('*.vcd'))
                    wave_file = wave_files[0] if wave_files else None
                
                if wave_file and wave_file.exists():
                    logger.info(f"Waveform saved to: {wave_file}")
            
            return True
            
        except subprocess.TimeoutExpired:
            raise SimulationError("Simulation timed out")
        except Exception as e:
            raise SimulationError(f"Simulation error: {e}")
    
    def _create_vcd_wrapper_executable(self, original_exe: Path, top_module: str) -> Optional[Path]:
        """Create a wrapper executable that enables VCD dumping."""
        try:
            # For now, just create a shell script wrapper that sets VCD environment
            wrapper_script = self.build_dir / f"{original_exe.name}_vcd_wrapper.sh"
            
            script_content = f"""#!/bin/bash
# SimTool VCD wrapper script
echo "[SimTool] Running simulation with automatic VCD generation"

# Set environment variables for VCD dumping (if supported)
export VERILATOR_VCD=1
export VCD_OUTPUT=simulation.vcd

# Check if testbench has VCD dumping
if grep -q "\\$dumpfile\\|\\$dumpvars" tb/*.sv tb/*.cpp 2>/dev/null; then
    echo "[SimTool] VCD dumping detected in testbench"
else
    echo "[SimTool] Warning: No VCD dumping found in testbench files"
    echo "[SimTool] Add \\$dumpfile(\\"simulation.vcd\\"); \\$dumpvars(0); to your testbench"
fi

# Run the original executable
exec "{original_exe.absolute()}" "$@"
"""
            
            wrapper_script.write_text(script_content)
            wrapper_script.chmod(0o755)  # Make executable
            
            return wrapper_script
            
        except Exception as e:
            logger = get_logger()
            logger.warning(f"Could not create VCD wrapper: {e}")
            return None
    
    def _create_tracing_main(self, top_module: str) -> Optional[Path]:
        """Create a C++ main file that enables VCD tracing automatically."""
        try:
            main_file = self.build_dir / 'simtool_main.cpp'
            
            cpp_content = f'''#include "V{top_module}.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

int main(int argc, char** argv) {{
    // Initialize Verilator
    Verilated::commandArgs(argc, argv);
    
    // Create instance of our module
    V{top_module}* top = new V{top_module};
    
    // Initialize VCD tracing
    Verilated::traceEverOn(true);
    VerilatedVcdC* tfp = new VerilatedVcdC;
    top->trace(tfp, 99);
    tfp->open("simulation.vcd");
    
    printf("[SimTool] VCD tracing enabled: simulation.vcd\\n");
    
    // Simple clock generation for a basic run
    // Note: Real testbench logic should be in SystemVerilog
    for (int time = 0; time < 1000; time++) {{
        top->eval();
        tfp->dump(time);
    }}
    
    // Cleanup
    tfp->close();
    delete tfp;
    delete top;
    
    printf("[SimTool] Simulation completed\\n");
    return 0;
}}'''
            
            main_file.write_text(cpp_content)
            return main_file
            
        except Exception as e:
            logger = get_logger()
            logger.warning(f"Could not create tracing main: {e}")
            return None
    
    def _create_vcd_wrapper(self, top_module: str, files: List[Path]) -> str:
        """Create a SystemVerilog wrapper that enables automatic VCD dumping."""
        wrapper_content = f"""
// SimTool automatic VCD wrapper
// This creates a standalone initial block for VCD tracing

`ifdef VERILATOR
// For Verilator, we need to bind the VCD dumping to the top module
bind {top_module} initial begin
    $dumpfile("simulation.vcd");
    $dumpvars(0);
    $display("[SimTool] Automatic VCD tracing enabled: simulation.vcd");
end
`else
// For other simulators, use a standalone initial block
initial begin
    $dumpfile("simulation.vcd");
    $dumpvars(0);
    $display("[SimTool] Automatic VCD tracing enabled: simulation.vcd");
end
`endif
"""
        return wrapper_content
    
    def _launch_gtkwave(self, vcd_file: Path):
        """Launch GTKWave with VCD file."""
        gtkwave_path = self.config.get('gtkwave_path')
        gtkwave_path = gtkwave_path if gtkwave_path is not None else 'gtkwave'
        
        logger = get_logger()
        if shutil.which(gtkwave_path):
            try:
                subprocess.Popen([gtkwave_path, str(vcd_file)])
                logger.success(f"Launched GTKWave with {vcd_file}")
            except Exception as e:
                logger.warning(f"Could not launch GTKWave: {e}")
        else:
            logger.warning("GTKWave not found, cannot display waveforms")
    
    def _generate_main_cpp(self, top_module: str, waves_enabled: bool, sim_time: Optional[int] = None) -> Optional[Path]:
        """Generate a C++ main file for transparent VCD tracing."""
        try:
            # Load template
            template_path = Path(__file__).parent / 'verilator_main_template.cpp'
            logger = get_logger()
            if not template_path.exists():
                logger.warning(f"Template not found: {template_path}")
                return None
                
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            # Replace placeholders
            # Use a large but reasonable default time to let $finish control when no custom time is specified
            max_sim_time = str(sim_time) if sim_time else "1000000000"  # 1 billion time units
            main_content = template_content.replace('{TOP_MODULE}', top_module)
            main_content = main_content.replace('{TRACE_FILE}', "simulation")
            main_content = main_content.replace('{MAX_SIM_TIME}', max_sim_time)
            
            # Write generated main.cpp
            main_cpp_path = self.build_dir / 'simtool_main.cpp'
            with open(main_cpp_path, 'w') as f:
                f.write(main_content)
                
            logger.info(f"Generated transparent tracing main: {main_cpp_path}")
            return main_cpp_path
            
        except Exception as e:
            logger = get_logger()
            logger.warning(f"Could not generate main.cpp: {e}")
            return None
    
    def clean(self) -> bool:
        """Clean build artifacts."""
        import shutil as sh
        
        logger = get_logger()
        try:
            if self.build_dir.exists():
                sh.rmtree(self.build_dir)
                logger.success(f"Removed build directory: {self.build_dir}")
            
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
                logger.info(f"Cleaned artifacts: {', '.join(cleaned)}")
            
            return True
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
            return False


class VerilatorPlugin(ISimulatorPlugin):
    """Verilator simulator plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        """Plugin metadata."""
        return PluginMetadata(
            name="verilator",
            version="1.0.0",
            description="Verilator open-source SystemVerilog simulator",
            author="SimTool Team",
            supported_formats=["sv", "v"],
            dependencies=["verilator"]
        )
    
    def create_adapter(self, config: Dict[str, Any]) -> ISimulator:
        """Create Verilator adapter instance."""
        return VerilatorAdapter(config)
    
    def is_available(self) -> bool:
        """Check if Verilator is available."""
        verilator_path = shutil.which('verilator')
        return verilator_path is not None