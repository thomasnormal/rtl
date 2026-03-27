# ADC_CTRL Microarchitecture Profile

This directory defines the public microarchitecture ABI for the OpenTitan
`adc_ctrl` task.

The public functional boundary is still the top-level DUT interface in
`task/spec/interface/`. The files here describe additional named observation
points that a standalone implementation should expose if it wants to be
compatible with deeper OpenTitan-style checking.

## Required ABI

The generated top module `adc_ctrl` must instantiate:

```systemverilog
adc_ctrl_micro_arch_if u_adc_ctrl_micro_arch_if();
```

The DUT must drive these observation signals:

- `cfg_fsm_rst`
- `np_sample_cnt`
- `lp_sample_cnt`
- `fsm_state`
- `match_pending`
- `oneshot_done_pulse`

These signals mirror the AON-domain ADC control state that the OpenTitan DV
environment reasons about when checking oneshot capture and FSM reset behavior.

## Expected Use

Compile the candidate RTL together with:

- `micro_arch/adc_ctrl_micro_arch_if.sv`
- `micro_arch/adc_ctrl_micro_arch_checker.sv`
- `micro_arch/adc_ctrl_micro_arch_bind.sv`

If the DUT does not instantiate `u_adc_ctrl_micro_arch_if`, deep-DV
compatibility checks should fail to elaborate.
