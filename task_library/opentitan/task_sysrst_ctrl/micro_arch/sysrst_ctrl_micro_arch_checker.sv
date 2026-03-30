module sysrst_ctrl_micro_arch_checker (
  input logic clk_aon_i,
  input logic rst_aon_ni,
  input logic wkup_req_o,
  input logic intr_event_detected_o,
  input logic cio_key0_out_o,
  input logic cio_key1_out_o,
  input logic cio_key2_out_o,
  input logic cio_pwrb_out_o,
  sysrst_ctrl_micro_arch_if.mon micro_arch_if
);

  property p_micro_arch_known;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      !$isunknown({
        micro_arch_if.pwrb_int,
        micro_arch_if.key0_int,
        micro_arch_if.key1_int,
        micro_arch_if.key2_int,
        micro_arch_if.ac_present_int,
        micro_arch_if.ec_rst_l_int,
        micro_arch_if.flash_wp_l_int,
        micro_arch_if.lid_open_int,
        micro_arch_if.wkup_pulse,
        micro_arch_if.combo_any_pulse
      });
  endproperty

  property p_wkup_tracks_pulse;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      wkup_req_o |-> micro_arch_if.wkup_pulse;
  endproperty

  property p_event_tracks_combo;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      intr_event_detected_o |-> (micro_arch_if.combo_any_pulse || micro_arch_if.wkup_pulse);
  endproperty

  property p_key0_pass_through;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      cio_key0_out_o == micro_arch_if.key0_int;
  endproperty

  property p_key1_pass_through;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      cio_key1_out_o == micro_arch_if.key1_int;
  endproperty

  property p_key2_pass_through;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      cio_key2_out_o == micro_arch_if.key2_int;
  endproperty

  property p_pwrb_pass_through;
    @(posedge clk_aon_i) disable iff (!rst_aon_ni)
      cio_pwrb_out_o == micro_arch_if.pwrb_int;
  endproperty

  assert property (p_micro_arch_known);
  assert property (p_wkup_tracks_pulse);
  assert property (p_event_tracks_combo);
  assert property (p_key0_pass_through);
  assert property (p_key1_pass_through);
  assert property (p_key2_pass_through);
  assert property (p_pwrb_pass_through);

endmodule
