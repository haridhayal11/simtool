// Pure combinational adder module
module adder #(
    parameter WIDTH = 8
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    input  wire             carry_in,
    output wire [WIDTH-1:0] sum,
    output wire             carry_out
);

    assign {carry_out, sum} = a + b + {{(WIDTH-1){1'b0}}, carry_in};

endmodule