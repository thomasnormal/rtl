module uart_compat_checker (
  input logic clk_i,
  input logic rst_ni,
  input logic cio_tx_en_o,
  uart_compat_if.mon compat_if
);

  // Match the upstream UART TB expectation that TX output enable is tied high.
  property tx_enable_tied_high_p;
    @(posedge clk_i) disable iff (!rst_ni)
      cio_tx_en_o == 1'b1;
  endproperty

  assert property (tx_enable_tied_high_p)
    else $error("uart compatibility failure: cio_tx_en_o must stay high after reset");

  // The deep-DV observability points must be driven to known values when active.
  property compat_signals_known_when_enabled_p;
    @(posedge clk_i) disable iff (!rst_ni)
      compat_if.rx_enable |-> !$isunknown({
        compat_if.rx_sync,
        compat_if.rx_sync_q1,
        compat_if.rx_sync_q2
      });
  endproperty

  assert property (compat_signals_known_when_enabled_p)
    else $error("uart compatibility failure: compatibility observability signals are unknown");

endmodule
