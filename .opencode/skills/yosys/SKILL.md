---
name: yosys
description: Legacy Yosys notes. This repo uses xrun/Xcelium instead.
---

# Yosys

Do not use `yosys` in this repo's generator or verifier flows. Use `xrun`/Xcelium for syntax, compile, elaboration, and smoke checks instead.

If you are debugging outside the main training flows and need a quick open-source parser locally, these are the old patterns:

```bash
yosys -p 'read_verilog -sv dut.sv; hierarchy -check -top TopModule; proc; check'
```

```bash
yosys -p 'read_verilog -sv *.sv; hierarchy -auto-top; proc; check'
```

Guidance:

- Prefer `xrun` in this repository, even for small standalone RTL.
- If you use these commands for local debugging, keep the script explicit in the command line so the run is reproducible.
