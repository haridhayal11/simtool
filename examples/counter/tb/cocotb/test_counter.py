"""
Cocotb testbench for counter module.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge
from cocotb.regression import TestFactory


@cocotb.test()
async def test_counter_basic(dut):
    """Basic counter functionality test"""
    
    # Create clock
    clock = Clock(dut.clk, 10, units="ns")  # 100MHz clock
    cocotb.start_soon(clock.start())
    
    # Reset
    dut.rst_n.value = 0
    dut.enable.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    
    # Check reset state
    assert dut.count.value == 0, f"Counter should be 0 after reset, got {dut.count.value}"
    
    # Release reset
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    
    # Enable counting
    dut.enable.value = 1
    
    # Check counting
    for expected in range(1, 10):
        await RisingEdge(dut.clk)
        assert dut.count.value == expected, f"Expected {expected}, got {dut.count.value}"
    
    # Disable counting
    dut.enable.value = 0
    current_count = dut.count.value
    
    # Wait a few cycles and check count doesn't change
    for _ in range(5):
        await RisingEdge(dut.clk)
        assert dut.count.value == current_count, "Counter should not increment when disabled"


@cocotb.test()
async def test_counter_overflow(dut):
    """Test counter overflow behavior"""
    
    # Create clock
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    
    # Reset
    dut.rst_n.value = 0
    dut.enable.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    
    # Release reset and enable
    dut.rst_n.value = 1
    dut.enable.value = 1
    await RisingEdge(dut.clk)
    
    # Count to overflow (assuming 8-bit counter)
    max_count = 2**8 - 1  # 255 for 8-bit
    
    # Fast-forward to near overflow
    for _ in range(max_count - 5):
        await RisingEdge(dut.clk)
    
    # Check the last few counts and overflow
    for expected in range(max_count - 4, max_count + 5):  # Go past overflow
        await RisingEdge(dut.clk)
        expected_wrapped = expected % (2**8)
        assert dut.count.value == expected_wrapped, f"Expected {expected_wrapped}, got {dut.count.value}"


# Test different counter widths if parameterized
if hasattr(cocotb.top, 'WIDTH'):
    # This would need simulator support for parameters
    pass