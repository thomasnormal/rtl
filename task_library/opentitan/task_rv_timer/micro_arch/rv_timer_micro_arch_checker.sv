module rv_timer_micro_arch_checker (
  input logic clk_i,
  input logic rst_ni,
  input logic intr_timer_expired_hart0_timer0_o,
  input logic [1:0] alert_tx_o,
  rv_timer_micro_arch_if.mon micro_arch_if
);

  default clocking cb @(posedge clk_i); endclocking

  property p_timer_state_known;
    disable iff (!rst_ni)
      !$isunknown({
        micro_arch_if.ctrl_active_0,
        micro_arch_if.intr_state_0,
        micro_arch_if.timer_val_0,
        micro_arch_if.compare_val_0_0
      });
  endproperty

  property p_intr_pin_matches_intr_state;
    disable iff (!rst_ni)
      intr_timer_expired_hart0_timer0_o == micro_arch_if.intr_state_0;
  endproperty

  property p_fatal_alert_pulse_matches_output;
    disable iff (!rst_ni)
      micro_arch_if.fatal_alert_pulse |-> (alert_tx_o != '0);
  endproperty

  property p_error_pulse_drives_alert;
    disable iff (!rst_ni)
      micro_arch_if.tl_intg_error_pulse |-> ##[0:2] micro_arch_if.fatal_alert_pulse;
  endproperty

  assert property (p_timer_state_known)
    else $error("rv_timer microarchitecture failure: state observability contains unknowns");

  assert property (p_intr_pin_matches_intr_state)
    else $error("rv_timer microarchitecture failure: intr pin does not match exported intr_state");

  assert property (p_fatal_alert_pulse_matches_output)
    else $error("rv_timer microarchitecture failure: fatal alert pulse not reflected on alert_tx_o");

  assert property (p_error_pulse_drives_alert)
    else $error("rv_timer microarchitecture failure: tl_intg_error_pulse did not lead to alert");
endmodule
