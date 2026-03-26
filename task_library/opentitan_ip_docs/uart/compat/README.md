# UART Compatibility Profile

This directory defines the first deep-DV compatibility profile for the OpenTitan `uart` task.

The functional task is still the public top-level `uart` interface from `task.json`.
However, if you want the generated RTL to be compatible with deeper OpenTitan-style verification,
it must also satisfy the SV compatibility ABI in this directory.

## Required ABI

The generated top module `uart` must instantiate a compatibility interface with the exact instance name:

```systemverilog
uart_compat_if u_uart_compat_if();
```

The DUT must drive the following signals on that interface:

- `rx_sync`
- `rx_sync_q1`
- `rx_sync_q2`
- `rx_enable`

These are observability points used by deeper UART verification.
They do not change the public top-level interface, but they provide a stable contract for adapted OpenTitan tests.

## Expected Use

When checking compatibility, compile the candidate RTL together with:

- `compat/uart_compat_if.sv`
- `compat/uart_compat_checker.sv`
- `compat/uart_compat_bind.sv`

If the DUT does not instantiate `u_uart_compat_if`, the bind/checker path should fail to elaborate.

## Example Pattern

```systemverilog
uart_compat_if u_uart_compat_if();

assign u_uart_compat_if.rx_sync    = rx_sync;
assign u_uart_compat_if.rx_sync_q1 = rx_sync_q1;
assign u_uart_compat_if.rx_sync_q2 = rx_sync_q2;
assign u_uart_compat_if.rx_enable  = rx_enable;
```

The exact internal implementation is still up to the generator.
This compatibility profile only requires that those observation points are exported through the named interface instance.
