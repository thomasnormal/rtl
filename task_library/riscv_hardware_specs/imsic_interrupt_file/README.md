# IMSIC Interrupt File

Source:

- Extracted from RISC-V Advanced Interrupt Architecture, Version 1.0
- Official PDF: `https://docs.riscv.org/reference/hardware/aia/_attachments/riscv-interrupts.pdf`

This task scopes the AIA material down to a single IMSIC interrupt file with a concrete pin-level
public interface.

The checked-in PDF is copied directly from the official public source.

The `doc/` subdirectory contains only the IMSIC-relevant markdown chunks from the checked-in manual
transcription of the public PDF, plus a compact normalized [register summary](./doc/registers.md)
that is the intended first read for this task.

The staged public interface under `spec/interface/` normalizes the spec into a standalone RTL task:

- `0x000`: `seteipnum_le`
- `0x004`: `seteipnum_be`
- `0x070`: `eidelivery`
- `0x072`: `eithreshold`
- `0x080-0x0BF`: `eip[0:63]`
- `0x0C0-0x0FF`: `eie[0:63]`
- `0x140`: normalized `topei` read/claim register derived from `mtopei`/`stopei` semantics

This is intentionally not a full hart CSR subsystem. The task boundary is one interrupt file plus its
hart-facing interrupt output.
