module dma_micro_arch_bind;

  bind dma dma_micro_arch_checker u_dma_micro_arch_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .intr_dma_done_o(intr_dma_done_o),
    .intr_dma_chunk_done_o(intr_dma_chunk_done_o),
    .intr_dma_error_o(intr_dma_error_o),
    .micro_arch_if(u_dma_micro_arch_if)
  );

endmodule
