# Debug Abstract Command Frontend

Source:

- Extracted from RISC-V External Debug Support, Version 0.13.2
- Official PDF: `https://docs.riscv.org/reference/debug-trace-ras/debug/v0.13.2/_attachments/riscv-debug.pdf`

This task scopes the External Debug material down to a single abstract-command front end with a
concrete pin-level public interface.

The checked-in PDF is copied directly from the official public source.

The `doc/` subdirectory contains only the abstract-command-relevant markdown chunks from the
checked-in manual transcription of the public PDF, plus a compact normalized
[register summary](./doc/registers.md) that is the intended first read for this task.

The staged public interface under `spec/interface/` normalizes the spec into a standalone RTL task:

- `0x04`: `data0`
- `0x16`: `abstractcs`
- `0x17`: `command`
- `0x18`: `abstractauto`

This is intentionally not a full debug module. The task boundary is one single-hart abstract-command
frontend plus the command-start / completion handshake to an external executor.
