interface adc_ctrl_micro_arch_if;

  logic cfg_fsm_rst;
  logic [15:0] np_sample_cnt;
  logic [7:0] lp_sample_cnt;
  logic [2:0] fsm_state;
  logic match_pending;
  logic oneshot_done_pulse;

  modport dut (
    output cfg_fsm_rst,
    output np_sample_cnt,
    output lp_sample_cnt,
    output fsm_state,
    output match_pending,
    output oneshot_done_pulse
  );

  modport mon (
    input cfg_fsm_rst,
    input np_sample_cnt,
    input lp_sample_cnt,
    input fsm_state,
    input match_pending,
    input oneshot_done_pulse
  );

endinterface
