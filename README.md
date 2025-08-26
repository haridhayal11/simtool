# SimTool

A CLI tool that bridges ModelSim workflows to open-source simulation tools like Verilator, cocotb, and GTKWave.

## Features

- **Familiar Commands**: Use ModelSim-style commands (`vlog`, `vcom`, `sim`) 
- **Auto-Detection**: Automatically detects testbench types (cocotb vs SystemVerilog)
- **Multiple Simulators**: Support for Verilator (more coming)
- **Waveform Integration**: Automatic GTKWave integration
- **SystemC Support**: Co-simulation with SystemC models
- **Cross-Platform**: Works on Linux and macOS

## Installation

```bash
# Clone and setup
git clone <repository-url>
cd simtool

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install SimTool
pip install -e .
```

## Quick Start

1. **Initialize a new project**:
```bash
mkdir my_design
cd my_design
simtool init
```

2. **Compile your RTL**:
```bash
simtool vlog rtl/*.sv --top my_module
```

3. **Run simulation**:
```bash
simtool sim my_module --waves
```

## Commands

### `simtool init`
Initialize a new SimTool project (similar to ModelSim's `vlib`).

```bash
simtool init [--simulator verilator] [--force]
```

Creates project structure:
```
project/
├── rtl/           # RTL source files
├── tb/
│   ├── cocotb/    # Python testbenches  
│   └── sv/        # SystemVerilog testbenches
├── work/          # Build artifacts (like ModelSim work library)
├── scripts/       # Utility scripts
└── simtool.cfg    # Project configuration
```

### `simtool vlog`
Compile Verilog/SystemVerilog files (similar to ModelSim's `vlog`).

```bash
simtool vlog [FILES...] [OPTIONS]
```

Options:
- `--top MODULE`: Top-level module
- `--standard STD`: Language standard (sv-2017, sv-2012, etc.)
- `--include DIR`: Include directories
- `--define NAME[=VALUE]`: Preprocessor defines
- `--library LIB`: Target library (default: work)
- `--coverage`: Enable coverage

### `simtool sim`
Run simulation (similar to ModelSim's `vsim`).

```bash
simtool sim TOP_MODULE [OPTIONS]
```

Options:
- `--waves`: Generate waveforms
- `--gui`: Open GTKWave after simulation
- `--systemc`: Enable SystemC co-simulation
- `--tb-type TYPE`: Force testbench type (auto/cocotb/sv)
- `--timeout SEC`: Simulation timeout
- `--plusarg ARG`: Pass plusargs to simulation

### `simtool doctor`
Check tool installations and environment.

```bash
simtool doctor
```

### `simtool clean`
Clean build artifacts.

```bash
simtool clean
```

## Testbench Auto-Detection

SimTool automatically detects testbench types:

- **Cocotb**: Looks for `@cocotb.test` or `import cocotb` in `.py` files
- **SystemVerilog**: Looks for `module *_tb` or testbench patterns in `.sv` files

## Example Usage

See the `examples/counter/` directory for a complete example:

```bash
cd examples/counter
simtool doctor                           # Check installation
simtool vlog rtl/counter.sv --top counter  # Compile
simtool sim counter --waves --gui         # Simulate with waveforms
```

## Configuration

Projects can be configured via `simtool.cfg` (YAML format):

```yaml
default_simulator: verilator
default_waves: true
rtl_paths: 
  - rtl
  - src
tb_paths:
  - tb/cocotb
  - tb/sv
build_dir: work
include_paths:
  - include
defines:
  DEBUG: 1
  WIDTH: 32
```

## SystemC Co-Simulation

Enable SystemC support with the `--systemc` flag:

```bash
simtool sim my_module --systemc --waves
```

This automatically:
- Configures Verilator for SystemC generation
- Links against SystemC libraries  
- Handles build complexity

## Requirements

- Python 3.8+
- One or more simulators:
  - Verilator (recommended)
  - More simulators coming soon
- GTKWave (optional, for waveform viewing)
- SystemC (optional, for co-simulation)

## Migrating from ModelSim

| ModelSim | SimTool |
|----------|---------|
| `vlib work` | `simtool init` |
| `vlog *.sv` | `simtool vlog *.sv` |
| `vsim -voptargs=+acc top` | `simtool sim top --waves` |
| ModelSim GUI | `simtool sim top --gui` (uses GTKWave) |

**Key Improvements:**
- Creates familiar `work/` directory like ModelSim work library
- Automatic testbench type detection (cocotb vs SystemVerilog)
- Integrated GTKWave waveform viewing
- Cross-platform support (Linux & macOS)

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Lint code
flake8 simtool/
black simtool/
```

## License

MIT License - see LICENSE file for details.