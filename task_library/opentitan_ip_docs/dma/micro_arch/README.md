# DMA Microarchitecture Profile

This directory defines the public microarchitecture ABI for the OpenTitan
`dma` task.

The top-level interface captures the externally visible DMA behavior. The
microarchitecture ABI here adds the minimal event-level observability needed to
reuse deeper DMA verification without assuming the original OpenTitan internal
register-hardware structs.

## Required ABI

The generated top module `dma` must instantiate:

```systemverilog
dma_micro_arch_if u_dma_micro_arch_if();
```

The DUT must drive these observation signals:

- `transfer_active`
- `done_pulse`
- `chunk_done_pulse`
- `error_pulse`
- `host_port_busy`
- `ctn_port_busy`
- `sys_port_busy`

These signals summarize the DMA engine activity and interrupt-generating
micro-events without forcing the candidate to reproduce the original `reg2hw`
representation.
