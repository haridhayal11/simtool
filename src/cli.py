"""
SimTool CLI interface with ModelSim-style commands.
"""

import click
import sys
import os
from pathlib import Path

from .core.project import Project
from .core.logging import get_logger, setup_logging
from .core.plugin_system import get_plugin_registry
from .core.constants import DefaultPaths, DefaultConfig, ProjectStructureMessages, TestbenchTypes
from .core.exceptions import (
    ProjectConfigError, SimulatorNotFoundError, CompilationFailedError, 
    SimulationFailedError, format_exception_with_context
)
from .toolchain.base import SimulatorError, CompilationError, SimulationError
from .ui.colors import success, error, progress, info, warning, header


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
@click.option('--log-file', type=click.Path(), help='Log file path')
@click.pass_context
def main(ctx, verbose, quiet, log_file):
    """SimTool: Bridge ModelSim workflows to open-source simulation tools."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    ctx.obj['log_file'] = Path(log_file) if log_file else None
    
    # Setup logging
    setup_logging(verbose, quiet, ctx.obj['log_file'])


@main.command()
@click.option('--simulator', default=DefaultConfig.SIMULATOR, 
              help='Default simulator (verilator, icarus, etc.)')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing project')
@click.pass_context
def init(ctx, simulator, force):
    """Initialize a new SimTool project (similar to vlib work)."""
    from .cli_commands.commands import ProjectInitializer
    
    initializer = ProjectInitializer()
    success = initializer.initialize_project(simulator, force)
    if not success:
        sys.exit(1)


@main.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.option('--top', required=True, help='Top-level module name')
@click.option('--simulator', help='Override default simulator')
@click.option('--tb-type', default=TestbenchTypes.AUTO, type=click.Choice(TestbenchTypes.ALL_TYPES), help='Testbench type')
@click.option('--waves/--no-waves', default=None, help='Enable/disable VCD waveform generation')
@click.pass_context
def vlog(ctx, files, top, simulator, tb_type, waves):
    """Compile RTL files (similar to ModelSim vlog)."""
    from .cli_commands.commands import CompileHandler
    
    verbose = ctx.obj['verbose']
    file_paths = [Path(f) for f in files] if files else []
    
    handler = CompileHandler()
    success = handler.compile_rtl(file_paths, top, simulator, tb_type, waves, verbose)
    if not success:
        sys.exit(1)


@main.command()
@click.argument('module', required=True)
@click.option('--gui', is_flag=True, help='Launch GTKWave GUI')
@click.option('--time', type=str, help='Maximum simulation time with units (e.g., 1000ns, 10us, 1ms, default: let testbench control)')
@click.option('--simulator', help='Override default simulator')
@click.pass_context
def sim(ctx, module, gui, time, simulator):
    """Run simulation (similar to ModelSim vsim)."""
    from .cli_commands.commands import SimulationHandler
    
    verbose = ctx.obj['verbose']
    
    handler = SimulationHandler()
    success = handler.run_simulation(module, gui, time, simulator, verbose)
    if not success:
        sys.exit(1)


@main.command()
@click.pass_context
def clean(ctx):
    """Clean build artifacts."""
    from .cli_commands.commands import CleanupHandler
    
    verbose = ctx.obj['verbose']
    
    handler = CleanupHandler()
    success = handler.clean_artifacts(verbose)
    if not success:
        sys.exit(1)





@main.command()
@click.pass_context
def doctor(ctx):
    """Check tool installation and environment."""
    from .cli_commands.commands import DoctorHandler
    
    handler = DoctorHandler()
    handler.check_system()


if __name__ == '__main__':
    main()