interface i2c_micro_arch_if;

  logic start_detect;
  logic stop_detect;
  logic host_idle;
  logic target_idle;
  logic scl_drive_low;
  logic sda_drive_low;
  logic [7:0] fsm_state;

  modport dut (
    output start_detect,
    output stop_detect,
    output host_idle,
    output target_idle,
    output scl_drive_low,
    output sda_drive_low,
    output fsm_state
  );

  modport mon (
    input start_detect,
    input stop_detect,
    input host_idle,
    input target_idle,
    input scl_drive_low,
    input sda_drive_low,
    input fsm_state
  );

endinterface
