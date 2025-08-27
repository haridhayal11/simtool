"""
SimTool CLI interface with ModelSim-style commands.
"""

import click
import sys
import os
from pathlib import Path

from .core.project import Project
from .toolchain.verilator import VerilatorAdapter
from .toolchain.base import SimulatorError, CompilationError, SimulationError


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
@click.pass_context
def main(ctx, verbose, quiet):
    """SimTool: Bridge ModelSim workflows to open-source simulation tools."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet


@main.command()
@click.option('--simulator', default='verilator', 
              help='Default simulator (verilator, icarus, etc.)')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing project')
@click.pass_context
def init(ctx, simulator, force):
    """Initialize a new SimTool project (similar to vlib work)."""
    verbose = ctx.obj['verbose']
    
    # Create directory structure with 'work' directory like ModelSim
    directories = ['rtl', 'tb/cocotb', 'tb/sv', 'work', 'scripts']
    for dir_name in directories:
        dir_path = Path(dir_name)
        if dir_path.exists() and not force:
            if verbose:
                print(f"Directory already exists: {dir_path}")
        else:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"Created directory: {dir_path}")
    
    # Create simtool.cfg
    config_file = Path("simtool.cfg")
    if config_file.exists() and not force:
        if verbose:
            print(f"Config file already exists: {config_file}")
    else:
        config_content = f"""default_simulator: {simulator}
default_waves: true
rtl_paths: 
  - rtl
tb_paths:
  - tb/cocotb
  - tb/sv
build_dir: work
include_paths: []
defines: {{}}
systemc_path: null
gtkwave_path: null
verilator_path: null"""
        
        with open(config_file, 'w') as f:
            f.write(config_content)
        print(f"Created config file: {config_file}")
    
    print(f"Initialized SimTool project with {simulator} as default simulator")
    print("Project structure:")
    print("  rtl/       - RTL source files")
    print("  tb/        - Testbench files")
    print("  work/      - Build artifacts (like ModelSim work library)")
    print("  scripts/   - Utility scripts")


@main.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.option('--top', required=True, help='Top-level module name')
@click.option('--simulator', help='Override default simulator')
@click.option('--tb-type', default='auto', type=click.Choice(['auto', 'cocotb', 'sv']), help='Testbench type')
@click.pass_context
def vlog(ctx, files, top, simulator, tb_type):
    """Compile RTL files (similar to ModelSim vlog)."""
    verbose = ctx.obj['verbose']
    
    try:
        # Load project configuration
        project = Project()
        
        # Get RTL files
        rtl_files = [Path(f) for f in files] if files else project.get_rtl_files()
        if not rtl_files:
            click.echo("Error: No RTL files found", err=True)
            sys.exit(1)
            
        # Get testbench files
        tb_files = project.get_tb_files(tb_type)
        detected_tb_type = project.detect_testbench_type(tb_files)
        
        if verbose:
            click.echo(f"RTL files: {[str(f) for f in rtl_files]}")
            click.echo(f"Testbench files: {[str(f) for f in tb_files]}")
            click.echo(f"Detected testbench type: {detected_tb_type}")
        
        # Use specified simulator or default
        sim_name = simulator or project.default_simulator
        
        # Create simulator adapter
        if sim_name == 'verilator':
            sim = VerilatorAdapter(project.config)
        else:
            click.echo(f"Error: Unsupported simulator: {sim_name}", err=True)
            sys.exit(1)
            
        # Compile
        click.echo(f"Compiling with {sim_name}...")
        testbench = tb_files[0] if tb_files else None
        success = sim.compile(rtl_files, top, testbench=testbench)
        
        if success:
            click.echo(f"✓ Compilation successful")
        else:
            click.echo("✗ Compilation failed", err=True)
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Run 'simtool init' to initialize a project", err=True)
        sys.exit(1)
    except (CompilationError, SimulatorError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('module', required=True)
@click.option('--waves', is_flag=True, help='Enable waveform generation')
@click.option('--gui', is_flag=True, help='Launch GTKWave GUI')
@click.option('--simulator', help='Override default simulator')
@click.pass_context
def sim(ctx, module, waves, gui, simulator):
    """Run simulation (similar to ModelSim vsim)."""
    verbose = ctx.obj['verbose']
    
    try:
        # Load project configuration
        project = Project()
        
        # Use specified simulator or default
        sim_name = simulator or project.default_simulator
        
        # Create simulator adapter
        if sim_name == 'verilator':
            sim = VerilatorAdapter(project.config)
        else:
            click.echo(f"Error: Unsupported simulator: {sim_name}", err=True)
            sys.exit(1)
            
        # Use project default for waves if not specified
        if not waves and project.default_waves:
            waves = True
            
        if verbose:
            click.echo(f"Simulator: {sim_name}")
            click.echo(f"Module: {module}")
            click.echo(f"Waves: {waves}")
            click.echo(f"GUI: {gui}")
        
        # Run simulation
        click.echo(f"Running simulation of {module}...")
        success = sim.simulate(module, waves=waves, gui=gui)
        
        if success:
            click.echo(f"✓ Simulation completed")
            if waves:
                vcd_file = Path(f"{module}.vcd")
                if vcd_file.exists():
                    click.echo(f"Waveform saved to: {vcd_file}")
        else:
            click.echo("✗ Simulation failed", err=True)
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Run 'simtool init' to initialize a project and 'simtool vlog' to compile", err=True)
        sys.exit(1)
    except (SimulationError, SimulatorError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def clean(ctx):
    """Clean build artifacts."""
    verbose = ctx.obj['verbose']
    
    try:
        # Load project configuration
        project = Project()
        
        # Use default simulator for cleanup
        sim_name = project.default_simulator
        
        # Create simulator adapter
        if sim_name == 'verilator':
            sim = VerilatorAdapter(project.config)
        else:
            click.echo(f"Error: Unsupported simulator: {sim_name}", err=True)
            sys.exit(1)
            
        if verbose:
            click.echo(f"Cleaning {sim_name} artifacts...")
        
        # Clean
        success = sim.clean()
        
        if success:
            click.echo("✓ Clean completed")
        else:
            click.echo("✗ Clean failed", err=True)
            sys.exit(1)
            
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Run 'simtool init' to initialize a project", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def doctor(ctx):
    """Check tool installation and environment."""
    import subprocess
    import shutil
    
    print("Checking simulator installations:")
    
    # Check Verilator
    verilator_path = shutil.which('verilator')
    if verilator_path:
        try:
            result = subprocess.run(['verilator', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.strip().split('\n')[0]
                print(f"  ✓ Verilator: {version_line}")
            else:
                print(f"  ✗ Verilator: Found but error getting version")
        except:
            print(f"  ✗ Verilator: Found but error getting version")
    else:
        print(f"  ✗ Verilator: Not found")
    
    # Check other tools
    print("\nChecking other tools:")
    other_tools = ['gtkwave', 'make', 'cmake']
    
    for tool in other_tools:
        if shutil.which(tool):
            print(f"  ✓ {tool}: Found")
        else:
            print(f"  ? {tool}: Not found (optional)")


if __name__ == '__main__':
    main()