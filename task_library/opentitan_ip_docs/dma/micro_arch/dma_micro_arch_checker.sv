module dma_micro_arch_checker (
  input logic clk_i,
  input logic rst_ni,
  input logic intr_dma_done_o,
  input logic intr_dma_chunk_done_o,
  input logic intr_dma_error_o,
  dma_micro_arch_if.mon micro_arch_if
);

  property p_micro_arch_known;
    @(posedge clk_i) disable iff (!rst_ni)
      !$isunknown({
        micro_arch_if.transfer_active,
        micro_arch_if.done_pulse,
        micro_arch_if.chunk_done_pulse,
        micro_arch_if.error_pulse,
        micro_arch_if.host_port_busy,
        micro_arch_if.ctn_port_busy,
        micro_arch_if.sys_port_busy
      });
  endproperty

  property p_done_tracks_irq;
    @(posedge clk_i) disable iff (!rst_ni)
      intr_dma_done_o == micro_arch_if.done_pulse;
  endproperty

  property p_chunk_done_tracks_irq;
    @(posedge clk_i) disable iff (!rst_ni)
      intr_dma_chunk_done_o == micro_arch_if.chunk_done_pulse;
  endproperty

  property p_error_tracks_irq;
    @(posedge clk_i) disable iff (!rst_ni)
      intr_dma_error_o == micro_arch_if.error_pulse;
  endproperty

  assert property (p_micro_arch_known);
  assert property (p_done_tracks_irq);
  assert property (p_chunk_done_tracks_irq);
  assert property (p_error_tracks_irq);

endmodule
