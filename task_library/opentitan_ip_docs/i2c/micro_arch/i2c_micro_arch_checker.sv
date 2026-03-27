module i2c_micro_arch_checker (
  input logic clk_i,
  input logic rst_ni,
  input logic cio_scl_en_o,
  input logic cio_sda_en_o,
  i2c_micro_arch_if.mon micro_arch_if
);

  property p_micro_arch_known;
    @(posedge clk_i) disable iff (!rst_ni)
      !$isunknown({
        micro_arch_if.start_detect,
        micro_arch_if.stop_detect,
        micro_arch_if.host_idle,
        micro_arch_if.target_idle,
        micro_arch_if.scl_drive_low,
        micro_arch_if.sda_drive_low,
        micro_arch_if.fsm_state
      });
  endproperty

  property p_scl_enable_matches_drive;
    @(posedge clk_i) disable iff (!rst_ni)
      cio_scl_en_o |-> micro_arch_if.scl_drive_low;
  endproperty

  property p_sda_enable_matches_drive;
    @(posedge clk_i) disable iff (!rst_ni)
      cio_sda_en_o |-> micro_arch_if.sda_drive_low;
  endproperty

  assert property (p_micro_arch_known);
  assert property (p_scl_enable_matches_drive);
  assert property (p_sda_enable_matches_drive);

endmodule
