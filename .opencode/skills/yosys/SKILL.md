---
name: yosys
description: Use Yosys for cheap RTL parsing, hierarchy, and structural sanity checks.
---

# Yosys

Use `yosys` for syntax, hierarchy, and structural sanity checks before expensive simulation or formal runs.

Common patterns:

```bash
yosys -p 'read_verilog -sv dut.sv; hierarchy -check -top TopModule; proc; check'
```

```bash
yosys -p 'read_verilog -sv *.sv; hierarchy -auto-top; proc; check'
```

Guidance:

- Start with `read_verilog -sv`, `hierarchy -check`, `proc`, and `check`.
- Use the public task metadata to pick the expected top module when known.
- Yosys is often the cheapest way to catch missing ports, undeclared nets, and width issues.
- Treat Yosys as a fallback for small standalone RTL. For OpenTitan-style tasks, package-heavy SystemVerilog, interfaces, compat SV, or UVM-style collateral, do not use Yosys as the required compile check; use `xrun`/Xcelium instead.
- Keep the script explicit in the command line so the run is reproducible.
