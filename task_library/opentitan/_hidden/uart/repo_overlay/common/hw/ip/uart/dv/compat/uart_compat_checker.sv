module uart_compat_checker (
  input logic clk_i,
  input logic rst_ni,
  input logic cio_tx_en_o,
  uart_compat_if.mon compat_if
);

  uart_micro_arch_if u_uart_micro_arch_if();

  assign u_uart_micro_arch_if.rx_sync = compat_if.rx_sync;
  assign u_uart_micro_arch_if.rx_sync_q1 = compat_if.rx_sync_q1;
  assign u_uart_micro_arch_if.rx_sync_q2 = compat_if.rx_sync_q2;
  assign u_uart_micro_arch_if.rx_enable = compat_if.rx_enable;

  uart_micro_arch_checker u_uart_micro_arch_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .cio_tx_en_o(cio_tx_en_o),
    .micro_arch_if(u_uart_micro_arch_if)
  );

endmodule
