interface aon_timer_micro_arch_if;

  logic wkup_enable;
  logic wdog_enable;
  logic sleep_mode_sync;
  logic aon_wkup_cause_we;
  logic aon_wdog_count_we;
  logic intr_wkup_de;
  logic intr_wkup_d;
  logic intr_wdog_de;
  logic intr_wdog_d;

  modport dut (
    output wkup_enable,
    output wdog_enable,
    output sleep_mode_sync,
    output aon_wkup_cause_we,
    output aon_wdog_count_we,
    output intr_wkup_de,
    output intr_wkup_d,
    output intr_wdog_de,
    output intr_wdog_d
  );

  modport mon (
    input wkup_enable,
    input wdog_enable,
    input sleep_mode_sync,
    input aon_wkup_cause_we,
    input aon_wdog_count_we,
    input intr_wkup_de,
    input intr_wkup_d,
    input intr_wdog_de,
    input intr_wdog_d
  );

endinterface
