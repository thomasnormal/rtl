# UART Microarchitecture Profile

This directory defines the first deep-DV microarchitecture profile for the OpenTitan `uart` task.

The functional task is still the public top-level `uart` interface from `task.json`.
However, if you want the generated RTL to be compatible with deeper OpenTitan-style verification,
it must also satisfy the SV microarchitecture ABI in this directory.

## Required ABI

The generated top module `uart` must instantiate a microarchitecture interface with the exact instance name:

```systemverilog
uart_micro_arch_if u_uart_micro_arch_if();
```

The DUT must drive the following signals on that interface:

- `rx_sync`
- `rx_sync_q1`
- `rx_sync_q2`
- `rx_enable`

These are observability points used by deeper UART verification.
They do not change the public top-level interface, but they provide a stable contract for adapted OpenTitan tests.

## Expected Use

When checking microarchitecture compatibility, compile the candidate RTL together with:

- `micro_arch/uart_micro_arch_if.sv`
- `micro_arch/uart_micro_arch_checker.sv`
- `micro_arch/uart_micro_arch_bind.sv`

If the DUT does not instantiate `u_uart_micro_arch_if`, the bind/checker path should fail to elaborate.

## Example Pattern

```systemverilog
uart_micro_arch_if u_uart_micro_arch_if();

assign u_uart_micro_arch_if.rx_sync    = rx_sync;
assign u_uart_micro_arch_if.rx_sync_q1 = rx_sync_q1;
assign u_uart_micro_arch_if.rx_sync_q2 = rx_sync_q2;
assign u_uart_micro_arch_if.rx_enable  = rx_enable;
```

The exact internal implementation is still up to the generator.
This microarchitecture profile only requires that those observation points are exported through the named interface instance.
