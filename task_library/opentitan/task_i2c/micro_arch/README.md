# I2C Microarchitecture Profile

This directory defines the public microarchitecture ABI for the `i2c` task.

The top-level interface already captures the externally visible bus behavior.
The microarchitecture ABI here adds the specific bus-monitor and state-machine
observation points that a deeper I2C verification environment relies on.

## Required ABI

The generated top module `i2c` must instantiate:

```systemverilog
i2c_micro_arch_if u_i2c_micro_arch_if();
```

The DUT must drive these signals:

- `start_detect`
- `stop_detect`
- `host_idle`
- `target_idle`
- `scl_drive_low`
- `sda_drive_low`
- `fsm_state`

These signals make the protocol monitor state explicit without requiring the
candidate to preserve the original `i2c_core` hierarchy.
