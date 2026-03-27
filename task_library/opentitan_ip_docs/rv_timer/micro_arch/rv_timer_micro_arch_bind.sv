module rv_timer_micro_arch_bind;

  bind rv_timer rv_timer_micro_arch_checker u_rv_timer_micro_arch_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .intr_timer_expired_hart0_timer0_o(intr_timer_expired_hart0_timer0_o),
    .alert_tx_o(alert_tx_o),
    .micro_arch_if(u_rv_timer_micro_arch_if)
  );

endmodule
