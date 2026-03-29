# RISC-V Hardware Specs

This task library is the first checked-in `spec-only` public corpus.

It contains authoritative PDFs copied from official RISC-V International documentation so the
task-store can materialize public-only tasks without any hidden oracle assets. Each task directory also
includes a checked-in `doc/` tree with a manual markdown transcription of the public PDF. Narrower
tasks can also carry compact normalized summaries such as `doc/registers.md` when the raw spec prose is
broader than the intended RTL boundary.

Current bundle:

- `imsic_interrupt_file/`: single-interrupt-file IMSIC task carved from RISC-V Advanced Interrupt Architecture v1.0
- `aplic_idc/`: single-hart APLIC IDC task carved from RISC-V Advanced Interrupt Architecture v1.0

Raw source material retained for future task carving:

- `external_debug/`: full checked-in External Debug PDF plus the full manual markdown transcription
- `advanced_interrupt_architecture/`: full checked-in AIA PDF plus the full manual markdown transcription
