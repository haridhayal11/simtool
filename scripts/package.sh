#!/bin/bash
# SimTool Packaging Script

set -e  # Exit on error

echo "SimTool Packaging Script"
echo "========================"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Must run from project root directory"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/ simtool.egg-info/

# Create packaging environment if it doesn't exist
if [ ! -d "packaging_env" ]; then
    echo "Creating packaging environment..."
    python3 -m venv packaging_env
    source packaging_env/bin/activate
    pip install --upgrade pip build wheel twine
else
    echo "Using existing packaging environment..."
    source packaging_env/bin/activate
fi

# Run tests first
echo "Running tests..."
python -m pytest tests/ -v

# Build package
echo "Building package..."
python -m build

# Check what was built
echo "Built packages:"
ls -la dist/

# Test installation
echo "Testing package installation..."
pip install --force-reinstall dist/simtool-0.1.0-py3-none-any.whl

# Test commands
echo "Testing CLI..."
simtool --help > /dev/null && echo "CLI works"

echo "Testing GUI import..."
python -c "from src.gui.main import main; print('GUI imports successfully')"

echo ""
echo "Package built successfully!"
echo ""
echo "Distribution files:"
echo "   - $(pwd)/dist/simtool-0.1.0-py3-none-any.whl (wheel)"
echo "   - $(pwd)/dist/simtool-0.1.0.tar.gz (source)"
echo ""
echo "To install:"
echo "   pip install dist/simtool-0.1.0-py3-none-any.whl"
echo ""
echo "To distribute:"
echo "   - Share the .whl file for easy installation"  
echo "   - Share the .tar.gz for source installation"
echo "   - Upload to PyPI with: twine upload dist/*"