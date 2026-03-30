interface pattgen_micro_arch_if;

  logic ch0_active;
  logic ch1_active;
  logic ch0_rep_cnt_en;
  logic ch1_rep_cnt_en;
  logic [31:0] ch0_clk_cnt;
  logic [31:0] ch1_clk_cnt;
  logic [9:0] ch0_rep_cnt;
  logic [9:0] ch1_rep_cnt;

  modport dut (
    output ch0_active,
    output ch1_active,
    output ch0_rep_cnt_en,
    output ch1_rep_cnt_en,
    output ch0_clk_cnt,
    output ch1_clk_cnt,
    output ch0_rep_cnt,
    output ch1_rep_cnt
  );

  modport mon (
    input ch0_active,
    input ch1_active,
    input ch0_rep_cnt_en,
    input ch1_rep_cnt_en,
    input ch0_clk_cnt,
    input ch1_clk_cnt,
    input ch0_rep_cnt,
    input ch1_rep_cnt
  );

endinterface
