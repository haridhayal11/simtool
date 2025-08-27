"""
Integration tests for CLI workflows.
"""

import pytest
import os
from click.testing import CliRunner
from pathlib import Path
from src.cli import main


class TestCLIWorkflow:
    """Integration tests for CLI commands."""
    
    def test_init_command(self, temp_dir):
        """Test project initialization command."""
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)
            runner = CliRunner()
            
            result = runner.invoke(main, ['init'])
            
            assert result.exit_code == 0
            assert 'Initialized SimTool project' in result.output
            assert (temp_dir / 'rtl').exists()
            assert (temp_dir / 'tb').exists()
            assert (temp_dir / 'work').exists()
            assert (temp_dir / 'simtool.cfg').exists()
        finally:
            os.chdir(original_cwd)
    
    def test_init_command_force(self, temp_dir):
        """Test project initialization with force flag."""
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)
            runner = CliRunner()
            
            # Create existing directory
            (temp_dir / 'rtl').mkdir()
            
            result = runner.invoke(main, ['init', '--force'])
            
            assert result.exit_code == 0
            assert 'Initialized SimTool project' in result.output
        finally:
            os.chdir(original_cwd)
    
    def test_doctor_command(self):
        """Test doctor command."""
        runner = CliRunner()
        result = runner.invoke(main, ['doctor'])
        
        assert result.exit_code == 0
        assert 'Checking simulator installations' in result.output
    
    def test_vlog_without_config(self, temp_dir):
        """Test vlog command without project config."""
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)
            runner = CliRunner()
            
            result = runner.invoke(main, ['vlog', '--top', 'test'])
            
            assert result.exit_code == 1
            assert 'Project config not found' in result.output
        finally:
            os.chdir(original_cwd)
    
    def test_clean_without_config(self, temp_dir):
        """Test clean command without project config."""
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)
            runner = CliRunner()
            
            result = runner.invoke(main, ['clean'])
            
            assert result.exit_code == 1
            assert 'Project config not found' in result.output
        finally:
            os.chdir(original_cwd)