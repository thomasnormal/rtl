module uart_compat_bind;

  bind uart uart_compat_checker u_uart_compat_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .cio_tx_en_o(cio_tx_en_o),
    .compat_if(u_candidate.u_uart_compat_if)
  );

endmodule
