// Shift register module with different signal names
module shift_register #(
    parameter WIDTH = 8
) (
    input  wire       clock,    // Different clock name
    input  wire       reset,    // Active high reset
    input  wire       shift_en, // Different enable name
    input  wire       serial_in,
    output wire [WIDTH-1:0] parallel_out
);

    reg [WIDTH-1:0] shift_reg;
    
    always @(posedge clock or posedge reset) begin
        if (reset) begin
            shift_reg <= {WIDTH{1'b0}};
        end else if (shift_en) begin
            shift_reg <= {shift_reg[WIDTH-2:0], serial_in};
        end
    end
    
    assign parallel_out = shift_reg;

endmodule