module pattgen_micro_arch_bind;

  bind pattgen pattgen_micro_arch_checker u_pattgen_micro_arch_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .intr_done_ch0_o(intr_done_ch0_o),
    .intr_done_ch1_o(intr_done_ch1_o),
    .micro_arch_if(u_pattgen_micro_arch_if)
  );

endmodule
