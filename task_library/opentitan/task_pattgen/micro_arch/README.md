# PATTGEN Microarchitecture Profile

This directory defines the public microarchitecture ABI for the `pattgen`
task.

The public top-level interface is enough to describe the generated waveforms.
The microarchitecture ABI here captures the per-channel enable and counter
state that a deeper reference verification environment uses for coverage and
completion reasoning.

## Required ABI

The generated top module `pattgen` must instantiate:

```systemverilog
pattgen_micro_arch_if u_pattgen_micro_arch_if();
```

The DUT must drive these observation signals:

- `ch0_active`
- `ch1_active`
- `ch0_rep_cnt_en`
- `ch1_rep_cnt_en`
- `ch0_clk_cnt`
- `ch1_clk_cnt`
- `ch0_rep_cnt`
- `ch1_rep_cnt`
