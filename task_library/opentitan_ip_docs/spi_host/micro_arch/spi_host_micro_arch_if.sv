interface spi_host_micro_arch_if;

  logic core_idle;
  logic command_active;
  logic error_pulse;
  logic event_pulse;
  logic clk_counter_nonzero;
  logic cs_active;

  modport dut (
    output core_idle,
    output command_active,
    output error_pulse,
    output event_pulse,
    output clk_counter_nonzero,
    output cs_active
  );

  modport mon (
    input core_idle,
    input command_active,
    input error_pulse,
    input event_pulse,
    input clk_counter_nonzero,
    input cs_active
  );

endinterface
