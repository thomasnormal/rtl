module aon_timer_micro_arch_checker (
  input logic clk_i,
  input logic rst_ni,
  input logic intr_wkup_timer_expired_o,
  input logic intr_wdog_timer_bark_o,
  input logic nmi_wdog_timer_bark_o,
  aon_timer_micro_arch_if.mon micro_arch_if
);

  property p_micro_arch_known;
    @(posedge clk_i) disable iff (!rst_ni)
      !$isunknown({
        micro_arch_if.wkup_enable,
        micro_arch_if.wdog_enable,
        micro_arch_if.sleep_mode_sync,
        micro_arch_if.aon_wkup_cause_we,
        micro_arch_if.aon_wdog_count_we,
        micro_arch_if.intr_wkup_de,
        micro_arch_if.intr_wkup_d,
        micro_arch_if.intr_wdog_de,
        micro_arch_if.intr_wdog_d
      });
  endproperty

  property p_wkup_commit_reaches_irq;
    @(posedge clk_i) disable iff (!rst_ni)
      (micro_arch_if.intr_wkup_de && micro_arch_if.intr_wkup_d) |-> ##[0:2] intr_wkup_timer_expired_o;
  endproperty

  property p_wdog_commit_reaches_irq;
    @(posedge clk_i) disable iff (!rst_ni)
      (micro_arch_if.intr_wdog_de && micro_arch_if.intr_wdog_d) |-> ##[0:2] intr_wdog_timer_bark_o;
  endproperty

  property p_nmi_matches_bark;
    @(posedge clk_i) disable iff (!rst_ni)
      nmi_wdog_timer_bark_o == intr_wdog_timer_bark_o;
  endproperty

  assert property (p_micro_arch_known);
  assert property (p_wkup_commit_reaches_irq);
  assert property (p_wdog_commit_reaches_irq);
  assert property (p_nmi_matches_bark);

endmodule
