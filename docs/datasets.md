# Datasets

The task store contains **2,016 RTL generation tasks** across **22 datasets**, spanning micro-benchmarks to production processor cores.

## Summary

| Dataset | Tasks | Tier | Oracle | Interface | License |
|---|---|---|---|---|---|
| **notsotiny** | 1114 | small | iverilog + eqy | context-defined | Apache-2.0 |
| **verithoughts** | 291 | small | eqy equivalence | interface/*.sv | see-repo |
| **cvdp** | 169 | small | cocotb | in test env | Apache-2.0 |
| **realbench** | 60 | small–medium | verilator | interface/*.sv | MIT |
| **resbench** | 56 | micro–small | iverilog | interface/*.sv | see-repo |
| **chipbench** | 45 | small–medium | verilator/xrun | in spec text | see-repo |
| **verilog_pcie** | 37 | medium | cocotb+icarus | interface/*.sv | MIT |
| **scr1** | 36 | medium | gold reference | interface/*.sv | Solderpad-0.51 |
| **verilog_ethernet** | 33 | medium | cocotb+icarus | interface/*.sv | MIT |
| **rtllm_v1_1** | 27 | small | iverilog | interface/*.sv | MIT |
| **ibex** | 25 | medium | gold reference | interface/*.sv | Apache-2.0 |
| **verilog_axi** | 24 | medium | cocotb+icarus | interface/*.sv | MIT |
| **veer_el2** | 22 | medium | cocotb+verilator | interface/*.sv | Apache-2.0 |
| **verilog_axis** | 21 | medium | cocotb+icarus | interface/*.sv | MIT |
| **pulp_common_cells** | 17 | small | xrun (assert) | interface/*.sv | Solderpad-0.51 |
| **opentitan_ip_docs** | 9 | medium | xrun (dvsim) | interface/*.sv | Apache-2.0 |
| **avip** | 9 | medium | UVM | interface/*.sv | — |
| **verilog_lfsr** | 6 | small | cocotb+icarus | interface/*.sv | MIT |
| **icrtl** | 6 | medium | xrun | interface/*.sv | see-repo |
| **caliptra** | 5 | medium | xrun | spec text | Apache-2.0 |
| **riscv_hardware_specs** | 2 | large | none (spec-only) | — | CC-BY-4.0 |
| **verilog_uart** | 2 | small | cocotb+icarus | interface/*.sv | MIT |

## Oracle Types

Each task defines its oracle kind in `task.json`. The oracle validates candidate RTL against the task's behavioral contract.

| Oracle Kind | Simulator | Datasets | How It Works |
|---|---|---|---|
| `simulation` | xrun, verilator, iverilog | chipbench, realbench, resbench, rtllm, icrtl | Compile candidate + testbench + ref module, run simulation, check pass criteria |
| `makefile_cocotb` | icarus (via cocotb Makefile) | verilog_axi, verilog_ethernet, verilog_pcie, verilog_axis, verilog_uart, verilog_lfsr | Copy upstream test dir, swap DUT source, run `make` |
| `veer_cocotb` | verilator (via cocotb+pyuvm) | veer_el2 | Copy VeeR block test infrastructure, swap DUT, run `make SIM=verilator` |
| `pulp_xrun` | xrun | pulp_common_cells | Compile deps + candidate + assert-based testbench with xrun |
| `uvm` | xrun | avip | Full UVM environment with named tests |
| `cocotb` | icarus | cvdp | cocotb tests via iverilog + vvp |
| `notsotiny_equiv` | iverilog + eqy | notsotiny, verithoughts | Syntax check with iverilog, then Yosys equivalence checking against golden module |
| `opentitan_dvsim` | xrun | opentitan_ip_docs | OpenTitan dvsim flow |
| `caliptra_xrun` | xrun | caliptra | Compile via file list, run self-checking testbench |
| `gold_reference` | — | ibex, scr1 | Gold RTL stored for comparison; no automated simulation oracle yet |

## Task Structure

Every task follows this layout:

```
task_id/
  public/
    spec/                    # Specification materials
      spec.txt or *.md       # Natural language spec
      interface/             # Formal SV interface files (when available)
        <module>.sv          # Module header with ports/parameters
      doc/                   # Additional documentation
    task.json                # Public metadata (top_module, tier, deliverables)
    top_module.txt           # Authoritative top module name
  oracle/                    # Hidden validation collateral
    gold_rtl.sv              # Gold reference (simulation oracles)
    sim/testbench.sv         # Testbench (simulation oracles)
    support/                 # Dependency files
    test/                    # cocotb/Makefile test dirs (Forencich/VeeR)
    rtl/                     # Gold RTL deps (Forencich)
    golden.v                 # Golden module (equivalence oracles)
    context.v                # Project context (NotSoTiny)
  task.json                  # Full task metadata including oracle config
```

## Interface Contract

Tasks should provide a formal interface specification whenever possible. The preferred form is a standalone `.sv` file under `public/spec/interface/` containing the module declaration with all ports and parameters. This tells the generator exactly what to implement.

For tasks with complex type systems (AVIP, OpenTitan), the interface directory also includes package files with custom types.

Current coverage: interface files are present for all Forencich, VeeR, PULP, RTLLM, OpenTitan, Ibex, SCR1, RealBench, ResBench, and VeriThoughts tasks. Benchmark datasets (ChipBench, CVDP, NotSoTiny) define interfaces inline in spec text or project context.

## Quality Rubric

Tasks are scored on 7 dimensions (see `docs/task-quality-rubric.md` and `configs/task_quality_rubric.json`):

| Category | Weight | What It Measures |
|---|---|---|
| Spec Quality | 20 | Can an agent infer behavior from public materials alone? |
| Interface Contract | 15 | Is the DUT boundary unambiguous and machine-checkable? |
| Oracle Quality | 25 | Does the oracle reliably separate correct from incorrect RTL? |
| Self-Containment | 15 | Can the task run without the original upstream repo? |
| Difficulty Calibration | 10 | Is the task appropriately challenging for its tier? |
| Anti-Shortcut Robustness | 10 | Does the task resist shallow solutions? |
| Maintenance Cost | 5 | Is the task cheap to keep working? |

Current band distribution:
- **Good (70+)**: avip, opentitan_ip_docs, rtllm_v1_1 — 45 tasks
- **Marginal (50-69)**: Most Forencich, ChipBench, RealBench, VeeR, PULP, NotSoTiny — 1,903 tasks
- **Not ready (<50)**: caliptra, ibex, scr1, riscv_hardware_specs — 68 tasks

The main gap in marginal datasets is spec quality (behavioral docs beyond the module header). The main gap in not-ready datasets is oracle automation.

## Shared Resources

- **ARM AMBA AXI Protocol Spec**: `data/shared_sources/protocol_specs/amba_axi_md/axi4_core_spec.md` — chapters A1-B1 (100 pages) for AXI task context
- **Yosys + eqy**: Built at `/opt/yosys-oss/` for equivalence checking (NotSoTiny, VeriThoughts oracles)
- **iverilog v12**: Built at `/opt/iverilog-v12/` for ChipBench compatibility

## Per-Dataset Oracle Files

Each oracle type has its own module under `src/rtl_training/`:

| File | Datasets |
|---|---|
| `oracle.py` | Core types + simulation oracles (xrun, iverilog, verilator) |
| `forencich_oracle.py` | verilog_axi, verilog_ethernet, verilog_pcie, verilog_axis, verilog_uart, verilog_lfsr |
| `veer_oracle.py` | veer_el2 |
| `pulp_oracle.py` | pulp_common_cells |
| `notsotiny_oracle.py` | notsotiny |
| `verithoughts_oracle.py` | verithoughts |
| `opentitan_oracle.py` | opentitan_ip_docs |

## Adding New Datasets

1. Clone the upstream repo
2. Read its README and test infrastructure to understand the intended simulator and test flow
3. Write a `store_<name>_tasks()` function in `task_store.py` (or use `store_forencich_tasks()` for cocotb Makefile repos)
4. Write a dedicated oracle module if the test flow doesn't fit existing oracles
5. Ingest tasks to `data/task_store/<name>/`
6. Run gold selftests to verify the oracle works
7. Generate `interface/*.sv` files from gold RTL
8. Add the dataset to `configs/datasets.json`
9. Score against the quality rubric
