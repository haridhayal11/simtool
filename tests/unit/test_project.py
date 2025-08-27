"""
Unit tests for SimTool project management.
"""

import pytest
import yaml
from pathlib import Path
from src.core.project import Project


class TestProject:
    """Test cases for Project class."""
    
    def test_project_init_with_valid_config(self, mock_project):
        """Test project initialization with valid config."""
        original_cwd = Path.cwd()
        try:
            # Change to mock project directory
            import os
            os.chdir(mock_project)
            
            project = Project()
            assert project.default_simulator == 'verilator'
            assert project.default_waves is True
            assert len(project.rtl_paths) == 1
            assert project.rtl_paths[0] == Path('rtl')
        finally:
            os.chdir(original_cwd)
    
    def test_project_init_missing_config(self, temp_dir):
        """Test project initialization with missing config."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(temp_dir)
            
            with pytest.raises(FileNotFoundError):
                Project()
        finally:
            os.chdir(original_cwd)
    
    def test_get_rtl_files(self, mock_project):
        """Test RTL file discovery."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(mock_project)
            
            project = Project()
            rtl_files = project.get_rtl_files()
            
            assert len(rtl_files) == 1
            assert rtl_files[0].name == 'counter.sv'
        finally:
            os.chdir(original_cwd)
    
    def test_get_tb_files_sv(self, mock_project):
        """Test SystemVerilog testbench discovery."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(mock_project)
            
            project = Project()
            tb_files = project.get_tb_files('sv')
            
            assert len(tb_files) == 1
            assert tb_files[0].name == 'counter_tb.sv'
        finally:
            os.chdir(original_cwd)
    
    def test_detect_testbench_type(self, mock_project):
        """Test testbench type detection."""
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(mock_project)
            
            project = Project()
            tb_files = project.get_tb_files('auto')
            tb_type = project.detect_testbench_type(tb_files)
            
            assert tb_type == 'sv'
        finally:
            os.chdir(original_cwd)
    
    def test_is_sv_testbench_detection(self, temp_dir):
        """Test SystemVerilog testbench detection logic."""
        # Create test files
        valid_tb = temp_dir / 'test_tb.sv'
        valid_tb.write_text('module test_tb; endmodule')
        
        invalid_tb = temp_dir / 'test.sv'  
        invalid_tb.write_text('module test; endmodule')
        
        project = Project.__new__(Project)  # Create without calling __init__
        
        assert project._is_sv_testbench(valid_tb) is True
        assert project._is_sv_testbench(invalid_tb) is False