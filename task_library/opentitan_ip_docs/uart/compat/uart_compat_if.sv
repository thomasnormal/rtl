interface uart_compat_if;
  logic rx_sync;
  logic rx_sync_q1;
  logic rx_sync_q2;
  logic rx_enable;

  modport dut (
    output rx_sync,
    output rx_sync_q1,
    output rx_sync_q2,
    output rx_enable
  );

  modport mon (
    input rx_sync,
    input rx_sync_q1,
    input rx_sync_q2,
    input rx_enable
  );
endinterface
