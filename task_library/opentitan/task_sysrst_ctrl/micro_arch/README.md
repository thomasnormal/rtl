# SYSRST_CTRL Microarchitecture Profile

This directory defines the public microarchitecture ABI for the `sysrst_ctrl`
task.

The public top-level interface describes the externally visible pins and reset /
wakeup outputs. The microarchitecture ABI here adds the synchronized internal
pin view and event pulses used by deeper verification.

## Required ABI

The generated top module `sysrst_ctrl` must instantiate:

```systemverilog
sysrst_ctrl_micro_arch_if u_sysrst_ctrl_micro_arch_if();
```

The DUT must drive these signals:

- `pwrb_int`
- `key0_int`
- `key1_int`
- `key2_int`
- `ac_present_int`
- `ec_rst_l_int`
- `flash_wp_l_int`
- `lid_open_int`
- `wkup_pulse`
- `combo_any_pulse`

These signals expose the synchronized input view and the main wakeup / combo
event pulses without forcing the candidate to preserve any specific original
submodule hierarchy.
