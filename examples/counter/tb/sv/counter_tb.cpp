#include "Vcounter.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    
    Vcounter* top = new Vcounter;
    
    VerilatedVcdC* tfp = nullptr;
    if (Verilated::gotFinish() == false) {
        Verilated::traceEverOn(true);
        tfp = new VerilatedVcdC;
        top->trace(tfp, 99);
        tfp->open("counter.vcd");
    }
    
    // Simple test
    top->rst_n = 0;
    top->enable = 0;
    top->clk = 0;
    
    for (int cycle = 0; cycle < 100; cycle++) {
        // Reset for first few cycles
        if (cycle < 5) {
            top->rst_n = 0;
        } else {
            top->rst_n = 1;
            top->enable = 1;
        }
        
        // Clock edge
        top->clk = 0;
        top->eval();
        if (tfp) tfp->dump(cycle*2);
        
        top->clk = 1;
        top->eval();
        if (tfp) tfp->dump(cycle*2+1);
        
        printf("Cycle %d: count = %d\n", cycle, top->count);
    }
    
    if (tfp) {
        tfp->close();
        delete tfp;
    }
    
    delete top;
    return 0;
}