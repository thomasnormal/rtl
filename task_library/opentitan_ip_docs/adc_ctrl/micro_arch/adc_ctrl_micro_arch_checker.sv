module adc_ctrl_micro_arch_checker (
  input logic clk_aon_i,
  input logic rst_aon_ni,
  input logic intr_match_pending_o,
  adc_ctrl_micro_arch_if.mon micro_arch_if
);

  property p_micro_arch_known;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      !$isunknown({
        micro_arch_if.cfg_fsm_rst,
        micro_arch_if.np_sample_cnt,
        micro_arch_if.lp_sample_cnt,
        micro_arch_if.fsm_state,
        micro_arch_if.match_pending,
        micro_arch_if.oneshot_done_pulse
      });
  endproperty

  property p_match_pending_tracks_irq;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      intr_match_pending_o == micro_arch_if.match_pending;
  endproperty

  assert property (p_micro_arch_known);
  assert property (p_match_pending_tracks_irq);

endmodule
