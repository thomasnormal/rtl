module sysrst_ctrl_micro_arch_bind;

  bind sysrst_ctrl sysrst_ctrl_micro_arch_checker u_sysrst_ctrl_micro_arch_checker (
    .clk_aon_i(clk_aon_i),
    .rst_aon_ni(rst_aon_ni),
    .wkup_req_o(wkup_req_o),
    .intr_event_detected_o(intr_event_detected_o),
    .cio_key0_out_o(cio_key0_out_o),
    .cio_key1_out_o(cio_key1_out_o),
    .cio_key2_out_o(cio_key2_out_o),
    .cio_pwrb_out_o(cio_pwrb_out_o),
    .micro_arch_if(u_sysrst_ctrl_micro_arch_if)
  );

endmodule
