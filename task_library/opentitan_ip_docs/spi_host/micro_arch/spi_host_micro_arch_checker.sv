module spi_host_micro_arch_checker (
  input logic clk_i,
  input logic rst_ni,
  input logic intr_error_o,
  input logic intr_spi_event_o,
  spi_host_micro_arch_if.mon micro_arch_if
);

  property p_micro_arch_known;
    @(posedge clk_i) disable iff (!rst_ni)
      !$isunknown({
        micro_arch_if.core_idle,
        micro_arch_if.command_active,
        micro_arch_if.error_pulse,
        micro_arch_if.event_pulse,
        micro_arch_if.clk_counter_nonzero,
        micro_arch_if.cs_active
      });
  endproperty

  property p_error_tracks_irq;
    @(posedge clk_i) disable iff (!rst_ni)
      intr_error_o == micro_arch_if.error_pulse;
  endproperty

  property p_event_tracks_irq;
    @(posedge clk_i) disable iff (!rst_ni)
      intr_spi_event_o == micro_arch_if.event_pulse;
  endproperty

  property p_command_active_implies_not_idle;
    @(posedge clk_i) disable iff (!rst_ni)
      micro_arch_if.command_active |-> !micro_arch_if.core_idle;
  endproperty

  assert property (p_micro_arch_known);
  assert property (p_error_tracks_irq);
  assert property (p_event_tracks_irq);
  assert property (p_command_active_implies_not_idle);

endmodule
