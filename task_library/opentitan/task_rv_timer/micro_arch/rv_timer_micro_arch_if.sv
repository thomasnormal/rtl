interface rv_timer_micro_arch_if;
  logic        ctrl_active_0;
  logic        intr_state_0;
  logic [63:0] timer_val_0;
  logic [63:0] compare_val_0_0;
  logic        tl_intg_error_pulse;
  logic        fatal_alert_pulse;

  modport dut (
    output ctrl_active_0,
    output intr_state_0,
    output timer_val_0,
    output compare_val_0_0,
    output tl_intg_error_pulse,
    output fatal_alert_pulse
  );

  modport tb (
    input ctrl_active_0,
    input intr_state_0,
    input timer_val_0,
    input compare_val_0_0,
    input tl_intg_error_pulse,
    input fatal_alert_pulse
  );

  modport mon (
    input ctrl_active_0,
    input intr_state_0,
    input timer_val_0,
    input compare_val_0_0,
    input tl_intg_error_pulse,
    input fatal_alert_pulse
  );
endinterface
