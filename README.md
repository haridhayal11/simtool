# SimTool

A modern CLI and GUI tool that bridges ModelSim workflows to open-source simulation tools like Verilator, cocotb, and GTKWave.

## Features

- **Familiar Commands**: ModelSim-style CLI (`vlog`, `sim`) with automatic testbench detection
- **Modern GUI**: Visual project management with system native theme
- **Cross-Platform**: Works on Linux, macOS, and Windows
- **Multiple Simulators**: Verilator support (more coming soon)
- **Integrated Waveforms**: Automatic GTKWave integration

## Installation

```bash
# From source (development)
git clone <repository-url>
cd simtool
pip install -e .

# Launch GUI
simtool-gui

# Or use CLI
simtool init
simtool vlog rtl/*.sv --top my_module
simtool sim my_module --waves --gui
```

## Quick Start

### CLI Workflow
```bash
mkdir my_design && cd my_design
simtool init                           # Initialize project
simtool vlog rtl/*.sv --top counter    # Compile RTL
simtool sim counter --waves --gui      # Simulate with waveforms
```

### GUI Workflow
1. Launch `simtool-gui`
2. Create new project or open existing
3. Select files to compile
4. Set top module and options
5. Click Compile → Simulate → View Waves

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `init` | Initialize project | `simtool init` |
| `vlog` | Compile RTL files | `simtool vlog *.sv --top cpu` |
| `sim` | Run simulation | `simtool sim cpu --waves` |
| `doctor` | Check installation | `simtool doctor` |
| `clean` | Clean build files | `simtool clean` |

## Project Structure

```
my_project/
├── rtl/           # RTL source files
├── tb/            # Testbenches (Python/cocotb, SystemVerilog, C++)
├── work/          # Build artifacts
└── simtool.cfg    # Configuration
```

## Configuration

Create `simtool.cfg` in your project:

```yaml
default_simulator: verilator
default_waves: true
rtl_paths: [rtl, src]
tb_paths: [tb]
build_dir: work
```

## Migrating from ModelSim

| ModelSim | SimTool |
|----------|---------|
| `vlib work` | `simtool init` |
| `vlog *.sv` | `simtool vlog *.sv` |
| `vsim -voptargs=+acc top` | `simtool sim top --waves` |

## Requirements

- Python 3.8+
- Verilator (simulator)
- GTKWave (optional, for waveforms)
- tkinter (for GUI): `brew install python-tk` or `apt install python3-tk`

## Example

Check `examples/counter/` for a complete example project.

## License

MIT License - see LICENSE file for details.