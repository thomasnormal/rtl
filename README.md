# RTL Training Runtime

OpenCode-centered runtime for RTL generator and verifier agents, with deterministic hidden-oracle validation owned by the trainer.

## Goal

The core boundary is:

- OpenCode agents work in staged public workspaces with strong local tools.
- The trainer owns the hidden oracle validators and runs them after the agent finishes.

That keeps deterministic validation available to the training framework without leaking it to the generator or verifier agents.

## What is in this repo

- `configs/datasets.json`: dataset manifest and acquisition order.
- `configs/rtllm_v1_1_interfaces.json`: curated manual interface contract for all RTLLM v1.1 tasks.
- `configs/opentitan_tasks.json`: curated manual OpenTitan medium-tier task manifest.
- `configs/riscv_hardware_specs_tasks.json`: curated manual spec-only RISC-V hardware-spec task manifest.
- `configs/verifier_smoke.json`: a first-pass verifier-training config.
- `src/rtl_training/`: task-store, OpenCode runtime, hidden-oracle validation, and RL helpers.
- `task_library/opentitan/`: manually ingested OpenTitan spec bundles for `adc_ctrl`, `aon_timer`, `uart`, `i2c`, `spi_host`, `pattgen`, `dma`, `rv_timer`, and `sysrst_ctrl`, copied from the local checkout with their original doc layout. Oracle code lives in `task_library/opentitan/helper.py`.
- `task_library/riscv_hardware_specs/`: the first checked-in spec-only public corpus, currently with bounded IMSIC and APLIC IDC tasks plus raw checked-in External Debug and AIA source transcriptions for future carving.
- `opencode.json` and `.opencode/`: checked-in OpenCode prompts and hardware-tool skills.
- `tests/`: regression tests for public/oracle separation, OpenCode workspaces, and reward/config logic.
- `docs/`: project plan, dataset notes, and an engineering log.

## Datasets

### Materialized datasets

| Dataset | Tasks | Tier | Oracle | Gold | Gen pass | Description |
|---|---|---|---|---|---|---|
| `rtllm_v1_1` | 27 | small | simulation | 27/27 | 57% pass@5 | Hand-written designs with testbenches and verified RTL references |
| `chipbench` | 45 | small | simulation | 44/45 | -- | VerilogEval-style harness; 30 self-contained + 6 non-self-contained + 9 CPU IP |
| `resbench` | 56 | small | simulation | 56/56 | -- | FPGA resource-aware problems; self-checking testbenches, no gold RTL |
| `realbench` | 60 | medium | simulation | 56/60 | -- | Real IP cores (AES, SD card, E203 RISC-V) with markdown specs |
| `icrtl` | 6 | medium | simulation | 4/6 | -- | Industry contest challenges (LBP, GEMM, convolution, Huffman, etc.) |
| `opentitan` | 9 | medium | dvsim | 9/9 | 0/3 | Curated OpenTitan IPs: uart, i2c, spi_host, adc_ctrl, aon_timer, pattgen, dma, rv_timer, sysrst_ctrl |
| `cvdp` | 169 | small | cocotb | -- | -- | CVDP benchmark; cocotb testbenches with iverilog |
| `verilog_axi` | 24 | medium | makefile cocotb | -- | -- | AXI4 bus components (adapters, crossbars, DMA, FIFOs) |
| `verilog_ethernet` | 33 | medium | makefile cocotb | -- | -- | Ethernet MAC/PHY/UDP/IP stack (1G/10G/25G) |
| `verilog_pcie` | 37 | medium | makefile cocotb | -- | -- | PCIe DMA, TLP, MSI-X, configuration space |
| `verilog_axis` | 21 | medium | makefile cocotb | -- | -- | AXI-Stream infrastructure (FIFOs, muxes, switches, COBS codec) |
| `verilog_uart` | 2 | small | makefile cocotb | -- | -- | UART RX/TX modules |
| `verilog_lfsr` | 6 | small | makefile cocotb | -- | -- | LFSR, CRC, PRBS, scramble/descramble |
| `pulp_common_cells` | 17 | small | xrun assert | -- | -- | PULP building blocks: CDC, FIFOs, arbiters, ECC, crossbars |
| `veer_el2` | 22 | medium | cocotb+verilator | -- | -- | VeeR EL2 RISC-V blocks: PIC, DMA, ALU, decoder, PMP, IFU, LSU |
| `notsotiny` | 1114 | small | iverilog+eqy | -- | -- | Real Tiny Tapeout designs; module completion + equivalence checking |
| `verithoughts` | 291 | small | iverilog+eqy | -- | -- | Formally verified Verilog generation tasks from NYU |
| `hwfixbench` | 500 | medium | diff | -- | -- | Real bug-fix PRs from Ibex, OpenTitan, CVA6, CORE-V Wally (SWE-Bench for hardware) |
| `ibex` | 25 | medium | gold reference | -- | -- | Ibex RISC-V core modules with gold reference RTL |
| `scr1` | 36 | medium | gold reference | -- | -- | SCR1 RISC-V core modules from Syntacore; silicon-proven RV32IMC |
| `caliptra` | 5 | medium | xrun | -- | -- | Caliptra RoT crypto: SHA-256/512, HMAC, ECC, DOE with self-checking TBs |
| `avip` | 9 | medium | uvm | -- | -- | AVIP verification IP: AHB, APB, AXI4, I2C, I3C, SPI, UART, JTAG, USB slaves |
| `riscv_hardware_specs` | 2 | large | none | -- | -- | Spec-only: IMSIC interrupt file, APLIC IDC (from RISC-V AIA PDF) |

**Gold** = gold selftest pass count (oracle validates its own reference RTL).
**Gen pass** = generator agent oracle pass rate. `rtllm_v1_1` uses `openai/gpt-5-mini`; opentitan used `openai/gpt-5.4`. `--` = not yet evaluated.

### Not yet materialized

These are defined in `configs/datasets.json` but not yet ingested into the task store:

`rtllm_v2_0` (50), `verilogeval_v2_spec_to_rtl` (156), `asserteval` (20), `rtl_repo` (4000, pretraining only — no oracle).

### Oracle types

Each task group owns its oracle code in `task_library/<group>/helper.py`:

| Oracle | Simulator | Used by |
|---|---|---|
| `simulation` | iverilog / xrun / verilator | rtllm, chipbench, realbench, resbench, icrtl |
| `cocotb` | iverilog + cocotb | cvdp |
| `makefile_cocotb` | upstream Makefile + icarus | verilog_axi, verilog_ethernet, verilog_pcie, verilog_axis, verilog_uart, verilog_lfsr |
| `cocotb+verilator` | verilator + cocotb + pyuvm | veer_el2 |
| `xrun` | xrun assertion / self-checking | pulp_common_cells, caliptra |
| `uvm` | xrun -uvm | avip |
| `gold_reference` | xrun / iverilog | ibex, scr1 |
| `iverilog+eqy` | iverilog + Yosys eqy | notsotiny, verithoughts |
| `hwfixbench_diff` | diff against gold fix | hwfixbench |
| `opentitan_dvsim` | xcelium via dvsim | opentitan |
| `none` | -- | riscv_hardware_specs |

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
./scripts/fetch_seed_datasets.sh
```

Materialize a hidden-oracle task store:

```bash
python - <<'PY'
from rtl_training.task_store import store_rtllm_tasks, store_verilog_eval_tasks

store_rtllm_tasks("third_party/RTLLM-v1.1", "data/task_store", dataset_name="rtllm_v1_1")
store_rtllm_tasks("third_party/RTLLM-v2.0", "data/task_store", dataset_name="rtllm_v2_0")
store_verilog_eval_tasks(
    "third_party/verilog-eval",
    "data/task_store",
    dataset_name="verilogeval_v2_spec_to_rtl",
)
PY
```

`rtllm_v1_1` uses the checked-in manual interface manifest in `configs/rtllm_v1_1_interfaces.json` instead of inferred port extraction from the prose spec. When a task has a public interface contract, the task store materializes `public/task.json` with a `top_module` field plus `public/spec/interface/<top>_public_if.sv`, a generated SV interface with canonical `dut` and `tb` modports.

Materialize the first curated OpenTitan medium-tier pack:

```bash
python - <<'PY'
from rtl_training.task_store import store_opentitan_tasks

store_opentitan_tasks(
    "data/task_store",
    source_root="~/opentitan",
)
PY
```

For the OpenTitan pack, the public task contains the copied upstream docs, but the public solver-facing contract is still self-contained: `public/task.json` carries the DUT `top_module`, and `public/spec/interface/` contains task-local package-free SV artifacts such as `uart_public_if.sv` and `uart_public_types_pkg.sv`. When a task needs deeper verification hooks, it can also expose a self-contained public microarchitecture ABI under `public/spec/micro_arch/`. The hidden task metadata retains the repo-native port types so the oracle can generate wrappers/adapters without forcing the generator to import upstream OpenTitan packages. See `docs/task-format.md` for the intended public task shape.

Materialize the first spec-only public pack:

```bash
python - <<'PY'
from rtl_training.task_store import store_riscv_hardware_specs_tasks

store_riscv_hardware_specs_tasks("data/task_store")
PY
```

This pack carries public PDFs only. There is no hidden oracle or private source bundle; it exists to validate the public-only ingest path before adding larger spec corpora. The checked-in `doc/` trees are manual `gpt-5.4-mini` conversions of those public PDFs and materialize alongside the source documents.

The task metadata also points at a shared hidden source bundle under `data/shared_sources/registry.json` for upstream `rtl/` and `dv/` paths. Those private assets are not staged into agent workspaces.

The UART task also carries a hidden copied golden RTL reference under `oracle/golden_rtl/`, plus a repo-native `dvsim` smoke oracle description in the task metadata. Gold selftests stage micro-arch stubs so the upstream DV flow stays runnable, while candidate validation can stage the real public micro-arch ABI and a hidden wrapper overlay.

Run the OpenTitan UART gold selftest:

```bash
python - <<'PY'
from task_library.opentitan.helper import validate_opentitan_gold_reference
from rtl_training.task_store import load_stored_task

task = load_stored_task("data/task_store/opentitan/uart")
result = validate_opentitan_gold_reference(
    task,
    work_root="runs/oracle_eval",
)
print("PASS" if result.passed else "FAIL", result.plan.log_path)
PY
```

Stage a generator workspace for OpenCode:

```bash
python - <<'PY'
from rtl_training.runtime import prepare_generator_episode

episode = prepare_generator_episode(
    "data/task_store/rtllm_v2_0/adder_8bit",
    "/tmp/rtl-episodes/episode_0001",
)
print(episode.workspace.root)
print(episode.workspace.submission_dir)
PY
```

Run the generator with OpenCode from the staged workspace:

```bash
cd /tmp/rtl-episodes/episode_0001
opencode run --agent generator --format json "Read TASK.md and complete the generator task."
```

Validate the result with the hidden oracle after the agent run:

```bash
python - <<'PY'
from rtl_training.oracle import validate_candidate
from rtl_training.task_store import load_stored_task

task = load_stored_task("data/task_store/rtllm_v2_0/adder_8bit")
result = validate_candidate(
    task,
    "runs/episode_0001/submission",
    work_root="runs/oracle_eval",
)
print("PASS" if result.passed else "FAIL", result.simulator, result.plan.log_path)
PY
```

Benchmark the verifier agent on labeled generator outputs:

```bash
set -a && source .env && set +a
python -m rtl_training.verifier_benchmark \
  runs/repeat_benchmark/rtllm_v1_1_gpt_5_mini_5x_20260325T175035Z \
  data/task_store/rtllm_v1_1 \
  runs/verifier_benchmark/rtllm_v1_1_run01 \
  --template-root . \
  --model openai/gpt-5-mini \
  --run-id run_01 \
  --resume
```

The verifier benchmark treats `candidate/` as immutable input. If the agent edits the staged RTL, the episode is marked incorrect even if it later emits a verdict.

## Oracle Policy

Not every task family has a hidden gold RTL.

Use three oracle modes:

- `reference_backed`: hidden reference RTL exists, so require reference/gold selftest plus mutant discrimination. OpenTitan is in this bucket.
- `reference_free`: no hidden gold RTL, but a self-checking bench / assertions / formal oracle exists. Require oracle-harness validation plus mutant or bug-bank discrimination.
- `public_only`: no hidden oracle yet. These tasks are not oracle-backed training/eval tasks yet.

So "gold-pass" is not a universal requirement. It only applies to reference-backed oracle families.

## Isolation Boundary

The generator and verifier can have full bash inside the staged workspace, but the hidden oracle stays outside that workspace. In practice the checked-in `opencode.json` leaves `bash` enabled while denying `external_directory`, so the agent can use the local hardware toolchain without seeing the trainer-owned oracle assets. Batch and verifier runs now stage episodes under `/tmp/rtl-episodes` by default, then move the finished workspace back under `runs/...` for inspection. Override that with `RTL_EPISODE_STAGING_ROOT=/path/to/staging`, and stale temporary workspaces older than 24 hours are cleaned automatically before new episodes start.

## Tinker Setup

Keep Tinker optional at the repo level so the unit tests stay runnable without credentials. When you are ready to train:

```bash
pip install tinker
git clone https://github.com/thinking-machines-lab/tinker-cookbook.git
pip install -e ./tinker-cookbook
export TINKER_API_KEY=...
```

The RL-side helpers stay in Python, but the policy runtime is OpenCode. The intended split is:

- Tinker owns sampling, grouping, and policy updates.
- OpenCode owns the generator/verifier agent loop inside each staged workspace.
- The trainer runtime owns hidden-oracle evaluation outside the workspace.

## First Dataset Plan

Use the datasets in three layers instead of trying to find one magical corpus:

1. `anchor_seed`: RTLLM and VerilogEval for spec + hidden simulation oracle.
2. `verification_side`: AssertEval for assertion/formal evidence generation.
3. `spec_only_corpus`: official public specs without hidden oracles, starting with the checked-in RISC-V hardware-spec pack.
4. `scale_corpus`: RTL-Repo for broader repository-level RTL exposure, but not as your main reward source.

The project plan in `docs/project-plan.md` assumes you will upgrade a small subset of the seed tasks into truly trusted formal anchors before running serious RL.

## Immediate Next Steps

1. Download RTLLM and VerilogEval locally and materialize them into the split public/oracle task store.
2. Pick 10-20 small synchronous designs and turn them into formal anchor tasks with SBY/EQY.
3. Train the generator and verifier in staged OpenCode workspaces with the hardware skills checked into `.opencode/skills/`.
4. Plug the OpenCode episode runtime and hidden-oracle evaluator into a Tinker environment.
