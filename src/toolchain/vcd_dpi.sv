// SimTool VCD DPI wrapper - connects SystemVerilog to C++ VCD functions

package simtool_vcd_pkg;
    // DPI imports for VCD functions
    import "DPI-C" function void simtool_init_vcd(chandle top_module, string filename);
    import "DPI-C" function void simtool_dump_vcd(longint unsigned time_val);
    import "DPI-C" function void simtool_close_vcd();
endpackage

// Automatic VCD dumping module
module simtool_vcd_auto;
    import simtool_vcd_pkg::*;
    
    initial begin
        // Initialize VCD tracing
        simtool_init_vcd(null, "simulation.vcd");
        
        // Start a process to dump VCD data every time step
        fork
            forever begin
                #1;  // Wait for next time step
                simtool_dump_vcd($time);
            end
        join_none
    end
    
    // Cleanup on finish
    final begin
        simtool_close_vcd();
    end
    
endmodule

// Auto-instantiate the VCD dumper
simtool_vcd_auto simtool_vcd_instance();