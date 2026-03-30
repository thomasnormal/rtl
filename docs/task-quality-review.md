# Task Quality Review

Date: 2026-03-30

This review applies the rubric in [task-quality-rubric.md](/home/thomas-ahle/rtl/docs/task-quality-rubric.md)
to all materialized datasets in `data/task_store/`.

Important:

- The scores below are a curation review, not automatic ground truth.
- Totals are computed from the current rubric weights.
- Gating failures matter more than the numeric total.
- Datasets scored at the dataset level unless per-task detail already existed (opentitan, avip, riscv_hardware_specs).

## Executive Summary

- Materialized datasets reviewed: `25`
- `excellent`: `0`
- `good`: `16`
- `marginal`: `6`
- `not_ready`: `3`

Gating failures found in 3 datasets:
- `ibex`, `scr1`: no real oracle (gold_reference = diff against gold, no behavioral testing)
- `caliptra`: oracle depends on upstream repo checkout at `/tmp/caliptra-rtl`

## Dataset Summary

| Dataset | Tasks | Score | Band | Gating Failure | Main Issue |
| --- | ---: | ---: | --- | --- | --- |
| `rtllm_v1_1` | 27 | 83 | good | -- | -- |
| `rtllm_v2_0` | 48 | 83 | good | -- | -- |
| `verilogeval_v2_spec_to_rtl` | 156 | 72 | good | -- | Minimal specs, no interface files |
| `chipbench` | 45 | 77 | good | -- | No interface files |
| `resbench` | 56 | 76 | good | -- | Gold RTL are stubs (testbench is oracle) |
| `realbench` | 60 | 78 | good | -- | -- |
| `icrtl` | 6 | 66 | marginal | -- | 2/6 gold selftests fail, no interface files |
| `opentitan` | 9 | 79 | good | -- | Maintenance cost, oracle complexity |
| `cvdp` | 169 | 54 | marginal | -- | Minimal specs, no gold RTL, no interface files |
| `verilog_axi` | 24 | 77 | good | -- | -- |
| `verilog_ethernet` | 33 | 77 | good | -- | -- |
| `verilog_pcie` | 37 | 77 | good | -- | -- |
| `verilog_axis` | 21 | 77 | good | -- | -- |
| `verilog_uart` | 2 | 75 | good | -- | Only 2 tasks |
| `verilog_lfsr` | 6 | 77 | good | -- | -- |
| `pulp_common_cells` | 17 | 63 | marginal | -- | Minimal spec (module header only) |
| `veer_el2` | 22 | 51 | marginal | -- | Minimal spec (219 bytes), large oracle dep tree |
| `notsotiny` | 1114 | 69 | marginal | -- | No prose spec (context = Verilog with hole) |
| `verithoughts` | 291 | 77 | good | -- | -- |
| `protocolllm` | 9 | 51 | marginal | -- | Lint-only oracle, no behavioral testing |
| `ibex` | 25 | 43 | not_ready | yes | No oracle (gold_reference only), minimal spec |
| `scr1` | 36 | 43 | not_ready | yes | No oracle (gold_reference only), minimal spec |
| `caliptra` | 5 | 35 | not_ready | yes | Oracle depends on /tmp/caliptra-rtl |
| `avip` | 9 | 77 | good | -- | No gold RTL selftest yet |
| `riscv_hardware_specs` | 2 | 58 | marginal | yes | No oracle at all |

## Per-Dataset Scores

Scale: category scores are `0-5`, total is weighted to `0-100`.

Category abbreviations:

- `Spec`: spec quality (15)
- `Doc`: documentation quality (10)
- `Ifc`: interface contract (15)
- `Ora`: oracle quality (25)
- `Self`: self-containment (15)
- `Diff`: difficulty calibration (5)
- `AS`: anti-shortcut robustness (10)
- `Maint`: maintenance cost (5)

### RTLLM Family

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `rtllm_v1_1` | 4 | 3 | 5 | 4 | 5 | 4 | 3 | 5 | 83 | good |
| `rtllm_v2_0` | 4 | 3 | 5 | 4 | 5 | 4 | 3 | 5 | 83 | good |

Evidence:
- **Spec**: Detailed spec.txt per task with port descriptions and behavioral requirements. Missing some edge cases.
- **Doc**: Plain text specs, not markdown chapters. No figures. Readable but unstructured.
- **Ifc**: SystemVerilog interface files with dut/tb modports for every task. Interface README.md included.
- **Ora**: Gold selftest 27/27 (v1.1). Simulation testbenches with reference RTL comparison. Stable.
- **Self**: Fully self-contained. No upstream dependency.
- **AS**: Reference RTL comparison is solid, but small tasks may have recognizable patterns.
- **Maint**: Simple structure, no external dependencies, no moving parts.

### VerilogEval

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `verilogeval_v2_spec_to_rtl` | 3 | 2 | 3 | 4 | 5 | 4 | 3 | 5 | 72 | good |

Evidence:
- **Spec**: Brief natural language specs ("implement a module that..."). Main behavior present, some tasks underspecified.
- **Doc**: Plain text, minimal structure. No figures or tables.
- **Ifc**: No separate interface files. Interface embedded in spec text.
- **Ora**: Mismatch-counting testbenches with reference RTL. 156 tasks, consistent schema.
- **Self**: Fully self-contained.
- **Diff**: Micro tier. Avg 21 lines gold RTL. Appropriate for baseline training.

### ChipBench / ResBench / RealBench / ICRTL

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `chipbench` | 4 | 3 | 3 | 4 | 5 | 4 | 3 | 5 | 77 | good |
| `resbench` | 3 | 2 | 4 | 4 | 5 | 3 | 4 | 5 | 76 | good |
| `realbench` | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 78 | good |
| `icrtl` | 4 | 3 | 2 | 3 | 4 | 4 | 4 | 3 | 66 | marginal |

Evidence:
- **chipbench**: Detailed specs, verilator preferred, 3 categories (cpu/nsc/sc). Gold 44/45. No interface files.
- **resbench**: Brief specs but 55/56 have separate interface stubs. Testbench-as-oracle (no reference RTL). Gold 56/56. 12 domain categories.
- **realbench**: Markdown specs with block diagrams, interface stubs, verification infrastructure. Gold 56/60. Medium complexity.
- **icrtl**: Detailed human.md specs (7.4KB), test data in oracle. But only 6 tasks, gold 4/6 (2 oracle failures), no interface files.

### CVDP

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `cvdp` | 2 | 1 | 2 | 3 | 4 | 3 | 3 | 4 | 54 | marginal |

Evidence:
- **Spec**: spec.txt only (~4-5KB plain text). Brief behavioral descriptions.
- **Doc**: Minimal. No markdown, no figures, no tables.
- **Ifc**: No interface files. Top module in task.json but no port details.
- **Ora**: Python cocotb testbenches (169 tasks). No gold RTL. No selftest data yet. Cocotb harness with test_runner.py.
- **Self**: Self-contained Python test harness. All test infrastructure local.
- **AS**: Behavioral cocotb testing, but no reference RTL to compare against.

### Forencich Family (verilog_*)

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `verilog_axi` | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 3 | 77 | good |
| `verilog_ethernet` | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 3 | 77 | good |
| `verilog_pcie` | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 3 | 77 | good |
| `verilog_axis` | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 3 | 77 | good |
| `verilog_uart` | 4 | 3 | 4 | 4 | 4 | 3 | 4 | 3 | 75 | good |
| `verilog_lfsr` | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 3 | 77 | good |

Evidence:
- **Spec**: Comprehensive spec.txt with parameters, interface signals, behavioral requirements. Real protocol documentation.
- **Doc**: Text specs, not markdown chapters. Detailed but unstructured.
- **Ifc**: Interface .sv stubs extracted per task.
- **Ora**: Upstream Makefile + cocotb tests with protocol-level testing (AxiStreamBus, scapy for Ethernet, backpressure/idle insertion). Gold RTL included.
- **Self**: Tests and gold RTL included in oracle/. Makefile dependency means the test runner invokes upstream infrastructure, but it's all local.
- **AS**: Protocol-level behavioral testing with parameter sweeps, stress scenarios.
- **Maint**: Upstream Makefile coupling adds some fragility.
- **verilog_uart**: Only 2 tasks — difficulty_calibration slightly lower due to lack of variety.

### PULP, VeeR

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `pulp_common_cells` | 2 | 2 | 4 | 3 | 4 | 4 | 3 | 4 | 63 | marginal |
| `veer_el2` | 1 | 1 | 3 | 3 | 3 | 4 | 3 | 3 | 51 | marginal |

Evidence:
- **pulp**: spec.txt is module header with parameter/port definitions only — no prose, no behavioral description. Interface stubs provided. xrun assertion testbenches with deps/ and include/ directories.
- **veer**: spec.txt is 219 bytes, essentially empty. Full VeeR EL2 design hierarchy in oracle/design/ (64KB+ files). CocoTB + Verilator tests. Large dependency tree needed to run tests.

### Equivalence-Based (notsotiny, verithoughts)

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `notsotiny` | 3 | 2 | 3 | 3 | 5 | 4 | 4 | 5 | 69 | marginal |
| `verithoughts` | 4 | 3 | 4 | 3 | 5 | 4 | 4 | 5 | 77 | good |

Evidence:
- **notsotiny**: Spec is full project Verilog (1732 lines) with target module blanked out. No prose description — model must infer behavior from surrounding code. Oracle = iverilog compilation + Yosys eqy equivalence check against golden.v. 1114 tasks from real Tiny Tapeout designs. Hard to game (equivalence checking). No selftest data yet.
- **verithoughts**: Detailed natural language spec (2068 lines) + interface .sv stubs. `verified_by_authors` flag. Same eqy oracle. 291 tasks from NYU. Better spec surface than notsotiny.

### ProtocolLLM

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `protocolllm` | 3 | 3 | 3 | 1 | 4 | 3 | 1 | 5 | 51 | marginal |

Evidence:
- **Spec**: Module specs with signal documentation, protocol PDFs (AXI, I2C, SPI, UART) in oracle.
- **Ifc**: Interface helper/driver .sv files.
- **Ora**: **Lint-only** — `verilator --lint-only`. No simulation, no behavioral check. Any compilable module passes. This is barely an oracle.
- **AS**: Lint-only means trivial stubs can pass. Anti-shortcut robustness is essentially zero.

### Gold-Reference Only (ibex, scr1)

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `ibex` | 1 | 1 | 4 | 1 | 4 | 3 | 1 | 4 | 43 | not_ready |
| `scr1` | 1 | 1 | 4 | 1 | 4 | 3 | 1 | 4 | 43 | not_ready |

Evidence:
- **Spec**: spec.txt is module header only (signal list). No behavioral description at all.
- **Doc**: No prose, no figures, no documentation surface.
- **Ifc**: Interface .sv stubs provided — this is the one strong point.
- **Ora**: `gold_reference` kind = diff/compare against gold RTL. **No testbench, no simulation, no behavioral validation.** This is effectively testing memorization, not understanding. **GATING FAILURE**: oracle does not reliably separate correct from incorrect RTL.
- **AS**: If oracle is gold-match, the task rewards copying the answer, not implementing the design.

### Caliptra

| Dataset | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `caliptra` | 1 | 1 | 2 | 2 | 1 | 4 | 3 | 1 | 35 | not_ready |

Evidence:
- **Spec**: spec.txt is 527 bytes — module header only.
- **Ifc**: No interface files in public/.
- **Ora**: xrun testbenches exist in files.f, but every path references `/tmp/caliptra-rtl` (121 external file references). **GATING FAILURE**: task depends on upstream repository layout.
- **Self**: Completely non-self-contained. Cannot stage without the upstream checkout.
- **Maint**: Brittle — any upstream repo change breaks everything.

### AVIP (per-task detail)

| Task | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `ahb_slave` | 4.0 | 4.5 | 4.5 | 3.5 | 4.5 | 3.0 | 3.5 | 3.0 | 78.5 | good |
| `apb_slave` | 4.5 | 4.5 | 4.5 | 3.5 | 4.5 | 3.0 | 3.5 | 3.0 | 80.0 | good |
| `axi4_slave` | 3.5 | 3.5 | 4.5 | 3.5 | 4.5 | 3.0 | 3.5 | 2.5 | 74.5 | good |
| `i3c_slave` | 4.0 | 3.5 | 4.0 | 4.0 | 4.5 | 3.0 | 3.0 | 2.5 | 76.0 | good |
| `uart_slave` | 4.0 | 4.0 | 4.0 | 3.5 | 4.5 | 2.5 | 3.0 | 3.0 | 74.5 | good |

Evidence: UVM testbenches with 11+ named test cases per task. Comprehensive PDFs (4MB+), SystemVerilog interface files, assertion/coverage plans. No gold RTL (testbench is the oracle). Requires Cadence/Questa simulators.

### OpenTitan (per-task detail)

| Task | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_adc_ctrl` | 4.5 | 4.5 | 4.0 | 4.0 | 4.0 | 3.5 | 4.0 | 3.5 | 81.5 | good |
| `task_aon_timer` | 4.5 | 4.5 | 4.0 | 4.0 | 4.0 | 3.0 | 4.0 | 4.0 | 81.5 | good |
| `task_dma` | 4.5 | 4.5 | 3.5 | 3.0 | 3.0 | 4.0 | 4.0 | 2.5 | 71.5 | good |
| `task_i2c` | 4.5 | 4.5 | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | 3.5 | 82.0 | good |
| `task_pattgen` | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | 3.0 | 4.0 | 4.0 | 79.0 | good |
| `task_rv_timer` | 4.5 | 4.5 | 4.5 | 3.5 | 4.0 | 3.5 | 4.0 | 3.0 | 80.0 | good |
| `task_spi_host` | 4.5 | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | 3.5 | 81.0 | good |
| `task_sysrst_ctrl` | 4.0 | 3.5 | 4.0 | 3.0 | 3.5 | 3.5 | 4.0 | 2.5 | 70.5 | good |
| `task_uart` | 4.5 | 4.5 | 4.5 | 4.0 | 4.0 | 3.5 | 4.0 | 3.5 | 83.0 | good |

Evidence: Comprehensive docs (README, theory_of_operation, interfaces, programmers_guide), SVG figures, hjson data, micro-architecture ABI. Full dvsim/xcelium oracle. Gold selftest 9/9.

### RISC-V Hardware Specs (per-task detail)

| Task | Spec | Doc | Ifc | Ora | Self | Diff | AS | Maint | Total | Band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `task_aplic_idc` | 4.5 | 4.0 | 4.5 | 0.0 | 4.5 | 3.0 | 2.0 | 3.0 | 58.5 | marginal |
| `task_imsic_interrupt_file` | 4.5 | 3.5 | 4.5 | 0.0 | 4.5 | 3.0 | 2.0 | 3.0 | 57.5 | marginal |

Evidence: Official RISC-V AIA docs, explicit top modules, interface/ contracts, solver-facing README. **No oracle** — the blocking issue.

## Gating Failures

These datasets have hard blockers that must be resolved before they can be used for training:

| Dataset | Gating Failure | Resolution Path |
| --- | --- | --- |
| `ibex` | No real oracle. `gold_reference` = diff against gold RTL, no behavioral validation. | Add simulation testbenches (Ibex upstream DV exists, needs ingestion). |
| `scr1` | Same as ibex. | Add simulation testbenches from upstream SCR1 DV. |
| `caliptra` | Oracle files.f references `/tmp/caliptra-rtl` — 121 external paths. | Bundle required RTL into oracle/ or rewrite file list to use relative paths. |
| `riscv_hardware_specs` | No oracle at all. Spec-only tasks. | Build formal or simulation oracle from RISC-V AIA spec. |

## Recommended Actions

### Immediate (fix not_ready datasets or drop them)

1. **caliptra**: Bundle the required RTL files into oracle/ with relative paths. The test infrastructure exists, it just needs to be self-contained. Estimated effort: low.
2. **ibex/scr1**: Either add testbenches from upstream DV (medium effort) or move to a "raw materials" category until oracles exist.

### Short-term (improve marginal datasets)

3. **cvdp**: Add interface files and improve spec surface. 169 tasks with cocotb oracles — high value if specs are better.
4. **veer_el2**: Write meaningful spec.txt content describing each block's behavior. The oracle infrastructure is there, the spec surface is not.
5. **pulp_common_cells**: Same — specs need prose beyond module headers.
6. **notsotiny**: Consider adding brief natural-language descriptions of what each module does. The equivalence oracle is strong.
7. **protocolllm**: Replace lint-only oracle with simulation testbenches. Lint is not a meaningful reward signal.
8. **icrtl**: Fix the 2 failing gold selftests.

### Already good — run generator evals

9. The 16 `good`-band datasets (2,025 tasks total) are ready for generator evaluation. Priority order by information value:
   - `chipbench` (45), `resbench` (56) — small, different oracle styles
   - `verilog_axi` (24), `verilog_ethernet` (33) — medium, protocol-level testing
   - `verithoughts` (291) — large task count, equivalence oracle
   - `realbench` (60) — real IP cores
