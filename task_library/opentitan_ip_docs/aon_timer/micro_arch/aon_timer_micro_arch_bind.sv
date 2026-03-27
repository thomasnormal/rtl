module aon_timer_micro_arch_bind;

  bind aon_timer aon_timer_micro_arch_checker u_aon_timer_micro_arch_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .intr_wkup_timer_expired_o(intr_wkup_timer_expired_o),
    .intr_wdog_timer_bark_o(intr_wdog_timer_bark_o),
    .nmi_wdog_timer_bark_o(nmi_wdog_timer_bark_o),
    .micro_arch_if(u_aon_timer_micro_arch_if)
  );

endmodule
