---
name: xrun
description: Run fast native SystemVerilog compile-and-sim checks with Cadence Xcelium xrun.
---

# xrun

Use `xrun` for fast compile-and-run checks in the native SystemVerilog scheduler.

Common patterns:

```bash
xrun -64bit -q -l xrun.log file1.sv file2.sv
```

```bash
xrun -64bit -q -l xrun.log -xmlibdirname xcelium.d tb.sv dut.sv
```

```bash
xrun -64bit -sv -q -l result/evidence/xrun_sva.log -xmlibdirname result/evidence/xcelium_sva.d dut.sv dut_assertions.sv tb.sv
```

```bash
xrun -64bit -uvm -sv -q -l result/evidence/xrun_uvm.log -xmlibdirname result/evidence/xcelium_uvm.d dut.sv tb_pkg.sv test_top.sv
```

Guidance:

- Keep runs quiet and log to a file with `-l`.
- Use a dedicated `-xmlibdirname` in a scratch directory if you will rerun often.
- Prefer `xrun` for compile/elaboration sanity on package-heavy SystemVerilog, interfaces, compat SV, and UVM-style collateral. That matches the commercial-tool path better than a generic parser.
- For OpenTitan-style tasks or any task with package-typed ports or compat files, `xrun` is the required compile check. A `yosys` parse is not sufficient there.
- Start with compile-only or elaborate-only sanity if the bench is incomplete.
- If you wrote SVAs, keep them in separate files or bind modules and compile them alongside the DUT.
- If the environment imports `uvm_pkg`, use `-uvm` and keep the checking logic inside native SV/UVM components.
- Do not enable wave dumps unless they are necessary; they create large files.
- If the DUT depends on generated files, create them in the workspace first.
