"""
Pytest configuration and fixtures for SimTool tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config():
    """Sample project configuration for tests."""
    return {
        'default_simulator': 'verilator',
        'default_waves': True,
        'rtl_paths': ['rtl'],
        'tb_paths': ['tb/cocotb', 'tb/sv'],
        'build_dir': 'work',
        'include_paths': [],
        'defines': {},
        'systemc_path': None,
        'gtkwave_path': None,
        'verilator_path': None
    }


@pytest.fixture
def mock_project(temp_dir, sample_config):
    """Create a mock SimTool project structure."""
    # Create directories
    (temp_dir / 'rtl').mkdir()
    (temp_dir / 'tb' / 'sv').mkdir(parents=True)
    (temp_dir / 'tb' / 'cocotb').mkdir()
    (temp_dir / 'work').mkdir()
    
    # Create sample RTL file
    rtl_file = temp_dir / 'rtl' / 'counter.sv'
    rtl_file.write_text("""
module counter #(
    parameter WIDTH = 4
) (
    input wire clk,
    input wire rst_n,
    output reg [WIDTH-1:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 0;
        else
            count <= count + 1;
    end
endmodule
""")
    
    # Create sample testbench
    tb_file = temp_dir / 'tb' / 'sv' / 'counter_tb.sv'
    tb_file.write_text("""
module counter_tb;
    reg clk, rst_n;
    wire [3:0] count;
    
    counter dut (.clk(clk), .rst_n(rst_n), .count(count));
    
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end
    
    initial begin
        rst_n = 0;
        #20 rst_n = 1;
        #100;
        $finish;
    end
endmodule
""")
    
    # Create config file
    import yaml
    config_file = temp_dir / 'simtool.cfg'
    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f)
    
    return temp_dir


@pytest.fixture
def mock_verilator_available(monkeypatch):
    """Mock Verilator as available."""
    import shutil
    monkeypatch.setattr(shutil, 'which', lambda x: '/usr/bin/verilator' if x == 'verilator' else None)


@pytest.fixture
def mock_verilator_unavailable(monkeypatch):
    """Mock Verilator as unavailable."""
    import shutil
    monkeypatch.setattr(shutil, 'which', lambda x: None)