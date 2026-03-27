module uart_micro_arch_bind;

  bind uart uart_micro_arch_checker u_uart_micro_arch_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .cio_tx_en_o(cio_tx_en_o),
    .micro_arch_if(u_candidate.u_uart_micro_arch_if)
  );

endmodule
