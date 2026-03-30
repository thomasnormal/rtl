# APLIC IDC

Source:

- Extracted from RISC-V Advanced Interrupt Architecture, Version 1.0
- Official PDF: `https://docs.riscv.org/reference/hardware/aia/_attachments/riscv-interrupts.pdf`

This task scopes the AIA material down to one direct-delivery APLIC interrupt delivery control (IDC)
block for a single hart.

The checked-in PDF is copied directly from the official public source.

The `doc/` subdirectory contains the APLIC sections needed for this task, plus a compact normalized
[register summary](./doc/registers.md) that is the intended first read.

The staged public interface under `spec/interface/` normalizes the spec into a standalone RTL task:

- `0x00`: `idelivery`
- `0x04`: `iforce`
- `0x08`: `ithreshold`
- `0x18`: `topi`
- `0x1C`: `claimi`

This is intentionally not a full APLIC domain. The task boundary is one hart-facing IDC register block
plus its `irq_o` and explicit claim handshake outputs.
