interface dma_micro_arch_if;

  logic transfer_active;
  logic done_pulse;
  logic chunk_done_pulse;
  logic error_pulse;
  logic host_port_busy;
  logic ctn_port_busy;
  logic sys_port_busy;

  modport dut (
    output transfer_active,
    output done_pulse,
    output chunk_done_pulse,
    output error_pulse,
    output host_port_busy,
    output ctn_port_busy,
    output sys_port_busy
  );

  modport mon (
    input transfer_active,
    input done_pulse,
    input chunk_done_pulse,
    input error_pulse,
    input host_port_busy,
    input ctn_port_busy,
    input sys_port_busy
  );

endinterface
