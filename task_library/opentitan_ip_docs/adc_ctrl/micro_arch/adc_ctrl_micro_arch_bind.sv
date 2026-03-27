module adc_ctrl_micro_arch_bind;

  bind adc_ctrl adc_ctrl_micro_arch_checker u_adc_ctrl_micro_arch_checker (
    .clk_aon_i(clk_aon_i),
    .rst_aon_ni(rst_aon_ni),
    .intr_match_pending_o(intr_match_pending_o),
    .micro_arch_if(u_adc_ctrl_micro_arch_if)
  );

endmodule
