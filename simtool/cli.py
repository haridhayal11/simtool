"""
SimTool CLI interface with ModelSim-style commands.
"""

import click
import sys
import os
from pathlib import Path


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