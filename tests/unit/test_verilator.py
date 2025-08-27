"""
Unit tests for Verilator adapter.
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from src.toolchain.verilator import VerilatorAdapter
from src.toolchain.base import CompilationError, SimulationError


class TestVerilatorAdapter:
    """Test cases for VerilatorAdapter class."""
    
    def test_init_with_config(self, sample_config):
        """Test VerilatorAdapter initialization."""
        adapter = VerilatorAdapter(sample_config)
        assert adapter.build_dir == Path('work')
        assert adapter.verilator_path == 'verilator'
    
    def test_init_with_custom_verilator_path(self, sample_config):
        """Test VerilatorAdapter with custom verilator path."""
        sample_config['verilator_path'] = '/opt/verilator/bin/verilator'
        adapter = VerilatorAdapter(sample_config)
        assert adapter.verilator_path == '/opt/verilator/bin/verilator'
    
    def test_is_available_true(self, sample_config, mock_verilator_available):
        """Test is_available when Verilator is available."""
        adapter = VerilatorAdapter(sample_config)
        assert adapter.is_available() is True
    
    def test_is_available_false(self, sample_config, mock_verilator_unavailable):
        """Test is_available when Verilator is not available."""
        adapter = VerilatorAdapter(sample_config)
        assert adapter.is_available() is False
    
    def test_compile_verilator_not_found(self, sample_config, mock_verilator_unavailable):
        """Test compile when Verilator is not available."""
        adapter = VerilatorAdapter(sample_config)
        
        with pytest.raises(CompilationError, match="Verilator not found"):
            adapter.compile([Path('test.sv')], 'test_top')
    
    @patch('subprocess.run')
    def test_compile_success(self, mock_run, sample_config, mock_verilator_available, temp_dir):
        """Test successful compilation."""
        # Mock successful subprocess call
        mock_run.return_value = Mock(returncode=0, stderr='', stdout='')
        
        # Set up adapter with temp directory
        sample_config['build_dir'] = str(temp_dir / 'work')
        adapter = VerilatorAdapter(sample_config)
        
        files = [Path('test.sv')]
        result = adapter.compile(files, 'test_top', waves=False)
        
        assert result is True
        assert mock_run.called
    
    @patch('subprocess.run')
    def test_compile_failure(self, mock_run, sample_config, mock_verilator_available, temp_dir):
        """Test compilation failure."""
        # Mock failed subprocess call
        mock_run.return_value = Mock(returncode=1, stderr='Compilation error', stdout='')
        
        sample_config['build_dir'] = str(temp_dir / 'work')
        adapter = VerilatorAdapter(sample_config)
        
        with pytest.raises(CompilationError, match="Verilator compilation failed"):
            adapter.compile([Path('test.sv')], 'test_top', waves=False)
    
    def test_generate_main_cpp(self, sample_config, temp_dir):
        """Test C++ main file generation."""
        sample_config['build_dir'] = str(temp_dir / 'work')
        adapter = VerilatorAdapter(sample_config)
        
        # Ensure build directory exists
        adapter.build_dir.mkdir(parents=True, exist_ok=True)
        
        main_file = adapter._generate_main_cpp('test_top', True, 5000)
        
        assert main_file is not None
        assert main_file.exists()
        
        # Check content
        content = main_file.read_text()
        assert 'Vtest_top' in content
        assert 'const vluint64_t sim_time = 5000;' in content
        assert 'simulation.vcd' in content
    
    def test_generate_main_cpp_default_time(self, sample_config, temp_dir):
        """Test C++ main file generation with default time."""
        sample_config['build_dir'] = str(temp_dir / 'work')
        adapter = VerilatorAdapter(sample_config)
        
        adapter.build_dir.mkdir(parents=True, exist_ok=True)
        
        main_file = adapter._generate_main_cpp('test_top', True)
        
        content = main_file.read_text()
        assert 'const vluint64_t sim_time = 1000000000;' in content
    
    def test_simulate_executable_not_found(self, sample_config):
        """Test simulate when executable doesn't exist."""
        adapter = VerilatorAdapter(sample_config)
        
        with pytest.raises(SimulationError, match="Executable not found"):
            adapter.simulate('nonexistent_module')
    
    @patch('subprocess.run')
    def test_clean_success(self, mock_run, sample_config, temp_dir):
        """Test successful cleanup."""
        sample_config['build_dir'] = str(temp_dir / 'work')
        adapter = VerilatorAdapter(sample_config)
        
        # Create build directory with some files
        adapter.build_dir.mkdir(parents=True, exist_ok=True)
        (adapter.build_dir / 'test_file').write_text('test')
        
        result = adapter.clean()
        assert result is True
        assert not adapter.build_dir.exists()