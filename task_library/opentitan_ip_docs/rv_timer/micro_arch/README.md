# RV_TIMER Microarchitecture Profile

This directory defines the public microarchitecture ABI for the `rv_timer`
task.

The functional task is still the public top-level `rv_timer` boundary from
`task/task.json` and `task/spec/interface/`. The files here define additional
named observation points that a generated implementation must expose if it
wants to be compatible with deeper reference-derived verification.

## Required ABI

The generated top module `rv_timer` must instantiate the exact interface:

```systemverilog
rv_timer_micro_arch_if u_rv_timer_micro_arch_if();
```

The DUT must drive these observation signals:

- `ctrl_active_0`
- `intr_state_0`
- `timer_val_0`
- `compare_val_0_0`
- `tl_intg_error_pulse`
- `fatal_alert_pulse`

These are not extra public IOs. They are explicit observability points for
adapted deep-DV checks.

## Intent

- `ctrl_active_0`, `intr_state_0`, `timer_val_0`, and `compare_val_0_0`
  expose the key timer-state observables that the scoreboard reasons about.
- `tl_intg_error_pulse` is the microarchitecture-level indication that the
  design has detected a TL integrity fault.
- `fatal_alert_pulse` is the microarchitecture-level indication that such a
  fatal fault produced an alert event.

The task remains implementable in isolation because every required signal is
spelled out here in SV. No hidden package imports or hidden hierarchy names are
needed by the generator.

## Expected Use

When checking microarchitecture compatibility, compile the candidate RTL with:

- `micro_arch/rv_timer_micro_arch_if.sv`
- `micro_arch/rv_timer_micro_arch_checker.sv`
- `micro_arch/rv_timer_micro_arch_bind.sv`

If the DUT does not instantiate `u_rv_timer_micro_arch_if`, the bind path
should fail to elaborate.
