module counter_tb;
    
    logic clk;
    logic rst_n;
    logic enable;
    logic [7:0] count;
    
    counter #(.WIDTH(8)) dut (
        .clk(clk),
        .rst_n(rst_n), 
        .enable(enable),
        .count(count)
    );
    
    // Clock generation
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end
    
    // Test sequence  
    initial begin
        $dumpfile("counter.vcd");
        $dumpvars;
        
        // Initialize
        rst_n = 0;
        enable = 0;
        
        // Wait and release reset
        repeat(10) @(posedge clk);
        rst_n = 1;
        
        // Enable counter
        repeat(5) @(posedge clk);
        enable = 1;
        
        // Let it count
        repeat(100) @(posedge clk);
        
        $finish;
    end

endmodule