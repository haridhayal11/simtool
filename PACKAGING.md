# SimTool Packaging Guide

## Overview

SimTool is packaged as a Python wheel distribution for easy installation and deployment.

## Package Contents

The package includes:
- **CLI Tool**: `simtool` command with ModelSim-compatible interface
- **GUI Application**: `simtool-gui` command with modern tkinter interface  
- **Core Libraries**: Project management, simulator adapters, logging, etc.
- **Examples**: Working counter example project
- **Tests**: Complete test suite

## Installation Methods

### Method 1: Install from Wheel (Recommended)

```bash
# Install from wheel file
pip install simtool-0.1.0-py3-none-any.whl

# Or install from source distribution
pip install simtool-0.1.0.tar.gz
```

### Method 2: Install from Source

```bash
# Clone repository
git clone <repository-url>
cd simtool

# Install in development mode
pip install -e .

# Or build and install
pip install build
python -m build
pip install dist/simtool-0.1.0-py3-none-any.whl
```

### Method 3: Install from PyPI (Future)

```bash
# Once published to PyPI
pip install simtool
```

## Commands Available After Installation

- `simtool` - Main CLI tool
- `simtool-gui` - GUI interface

## Dependencies

**Required:**
- Python >=3.8
- click >=8.0.0 
- pyyaml >=6.0
- colorama >=0.4.0
- cocotb >=1.7.0

**Optional (for GUI):**
- tkinter (usually included with Python)

**External Tools:**
- Verilator (for simulation)
- GTKWave (for waveform viewing)

## Verification

After installation, verify with:

```bash
# Check CLI
simtool --help
simtool doctor

# Check GUI (requires tkinter)
simtool-gui
```

## Building from Source

### Prerequisites

```bash
# Install build tools
pip install build wheel twine
```

### Build Process

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build both wheel and source distribution
python -m build

# Verify build
ls dist/
# Should show:
# simtool-0.1.0-py3-none-any.whl
# simtool-0.1.0.tar.gz
```

### Testing the Package

```bash
# Create test environment
python -m venv test_env
source test_env/bin/activate

# Install and test
pip install dist/simtool-0.1.0-py3-none-any.whl
simtool --help
simtool-gui
```

## Distribution

### Local Distribution

Share the wheel file directly:
```bash
# Send the wheel file
scp dist/simtool-0.1.0-py3-none-any.whl user@server:/path/
```

### PyPI Publication (Future)

```bash
# Upload to PyPI (requires account)
twine upload dist/*

# Upload to Test PyPI first
twine upload --repository testpypi dist/*
```

## Platform Support

- **macOS**: Tested on macOS (ARM64)
- **Linux**: Should work (not tested)  
- **Windows**: Should work (not tested)

The package is built as `py3-none-any` which means it's compatible with all platforms that support Python 3.

## File Structure in Package

```
simtool/
├── src/
│   ├── cli.py              # CLI entry point
│   ├── gui/main.py         # GUI entry point  
│   ├── core/               # Core functionality
│   ├── toolchain/          # Simulator adapters
│   └── ui/                 # CLI utilities
├── examples/               # Example projects
├── tests/                  # Test suite
├── pyproject.toml          # Package configuration
├── MANIFEST.in             # File inclusion rules
├── README.md               # Documentation
└── LICENSE                 # MIT license
```

## Troubleshooting

### Common Issues

**Missing tkinter:**
```bash
# macOS
brew install python-tk

# Ubuntu/Debian  
sudo apt-get install python3-tk
```

**Import errors:**
- Ensure Python ≥3.8
- Check all dependencies installed
- Try reinstalling with `pip install --force-reinstall`

**Command not found:**
- Check if pip install location is in PATH
- Try with `python -m src.cli` instead of `simtool`