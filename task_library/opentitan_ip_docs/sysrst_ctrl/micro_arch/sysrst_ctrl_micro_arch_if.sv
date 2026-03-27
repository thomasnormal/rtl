interface sysrst_ctrl_micro_arch_if;

  logic pwrb_int;
  logic key0_int;
  logic key1_int;
  logic key2_int;
  logic ac_present_int;
  logic ec_rst_l_int;
  logic flash_wp_l_int;
  logic lid_open_int;
  logic wkup_pulse;
  logic combo_any_pulse;

  modport dut (
    output pwrb_int,
    output key0_int,
    output key1_int,
    output key2_int,
    output ac_present_int,
    output ec_rst_l_int,
    output flash_wp_l_int,
    output lid_open_int,
    output wkup_pulse,
    output combo_any_pulse
  );

  modport mon (
    input pwrb_int,
    input key0_int,
    input key1_int,
    input key2_int,
    input ac_present_int,
    input ec_rst_l_int,
    input flash_wp_l_int,
    input lid_open_int,
    input wkup_pulse,
    input combo_any_pulse
  );

endinterface
