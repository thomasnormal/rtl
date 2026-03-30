# AON_TIMER Microarchitecture Profile

This directory defines the public microarchitecture ABI for the `aon_timer`
task.

The task remains implementable from the public top-level interface, but deeper
verification needs a small set of named AON-domain observation points that are
otherwise implicit in a deeper reference design.

## Required ABI

The generated top module `aon_timer` must instantiate:

```systemverilog
aon_timer_micro_arch_if u_aon_timer_micro_arch_if();
```

The DUT must drive these observation signals:

- `wkup_enable`
- `wdog_enable`
- `sleep_mode_sync`
- `aon_wkup_cause_we`
- `aon_wdog_count_we`
- `intr_wkup_de`
- `intr_wkup_d`
- `intr_wdog_de`
- `intr_wdog_d`

These are the minimal observability points needed to explain when the AON timer
commits wakeup / watchdog events into the synchronized interrupt state seen by
the rest of the design.

## Expected Use

Compile the candidate RTL together with:

- `micro_arch/aon_timer_micro_arch_if.sv`
- `micro_arch/aon_timer_micro_arch_checker.sv`
- `micro_arch/aon_timer_micro_arch_bind.sv`
