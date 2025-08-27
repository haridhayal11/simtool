// SimTool automatic VCD dumping support
// This module will be automatically instantiated by Verilator

module simtool_vcd_auto();
    initial begin
        // Automatic VCD dumping for SimTool
        $dumpfile("simulation.vcd");
        $dumpvars(0);  // Dump all variables at all levels
        
        // Add some helpful information  
        $display("[SimTool] VCD dumping enabled: simulation.vcd");
    end
endmodule