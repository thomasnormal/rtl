module spi_host_micro_arch_bind;

  bind spi_host spi_host_micro_arch_checker u_spi_host_micro_arch_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .intr_error_o(intr_error_o),
    .intr_spi_event_o(intr_spi_event_o),
    .micro_arch_if(u_spi_host_micro_arch_if)
  );

endmodule
