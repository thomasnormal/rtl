module pattgen_micro_arch_checker (
  input logic clk_i,
  input logic rst_ni,
  input logic intr_done_ch0_o,
  input logic intr_done_ch1_o,
  pattgen_micro_arch_if.mon micro_arch_if
);

  property p_micro_arch_known;
    @(posedge clk_i) disable iff (!rst_ni)
      !$isunknown({
        micro_arch_if.ch0_active,
        micro_arch_if.ch1_active,
        micro_arch_if.ch0_rep_cnt_en,
        micro_arch_if.ch1_rep_cnt_en,
        micro_arch_if.ch0_clk_cnt,
        micro_arch_if.ch1_clk_cnt,
        micro_arch_if.ch0_rep_cnt,
        micro_arch_if.ch1_rep_cnt
      });
  endproperty

  property p_done_ch0_requires_terminal_progress;
    @(posedge clk_i) disable iff (!rst_ni)
      intr_done_ch0_o |-> (!micro_arch_if.ch0_active || (micro_arch_if.ch0_rep_cnt == '0));
  endproperty

  property p_done_ch1_requires_terminal_progress;
    @(posedge clk_i) disable iff (!rst_ni)
      intr_done_ch1_o |-> (!micro_arch_if.ch1_active || (micro_arch_if.ch1_rep_cnt == '0));
  endproperty

  assert property (p_micro_arch_known);
  assert property (p_done_ch0_requires_terminal_progress);
  assert property (p_done_ch1_requires_terminal_progress);

endmodule
