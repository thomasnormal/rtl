# SPI_HOST Microarchitecture Profile

This directory defines the public microarchitecture ABI for the OpenTitan
`spi_host` task.

The public top-level interface already describes the observable SPI behavior.
The microarchitecture ABI here makes the command-engine state explicit enough to
support adapted deeper verification without exposing the original `u_spi_core`
hierarchy.

## Required ABI

The generated top module `spi_host` must instantiate:

```systemverilog
spi_host_micro_arch_if u_spi_host_micro_arch_if();
```

The DUT must drive these observation signals:

- `core_idle`
- `command_active`
- `error_pulse`
- `event_pulse`
- `clk_counter_nonzero`
- `cs_active`
