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
- `configs/opentitan_ip_docs_tasks.json`: curated manual OpenTitan medium-tier task manifest.
- `configs/verifier_smoke.json`: a first-pass verifier-training config.
- `src/rtl_training/`: task-store, OpenCode runtime, hidden-oracle validation, and RL helpers.
- `task_library/opentitan_ip_docs/`: manually ingested OpenTitan spec bundles for `uart`, `i2c`, `spi_host`, `dma`, and `sysrst_ctrl`, copied from the local checkout with their original doc layout.
- `opencode.json` and `.opencode/`: checked-in OpenCode prompts and hardware-tool skills.
- `tests/`: regression tests for public/oracle separation, OpenCode workspaces, and reward/config logic.
- `docs/`: project plan, dataset notes, and an engineering log.

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

`rtllm_v1_1` uses the checked-in manual interface manifest in `configs/rtllm_v1_1_interfaces.json` instead of inferred port extraction from the prose spec. When a task has public interface metadata, the task store also materializes `public/spec/interface/<top>_public_if.sv`, a generated SV interface with canonical `dut` and `tb` modports.

Materialize the first curated OpenTitan medium-tier pack:

```bash
python - <<'PY'
from rtl_training.task_store import store_opentitan_ip_docs_tasks

store_opentitan_ip_docs_tasks(
    "data/task_store",
    source_root="~/opentitan",
)
PY
```

For the OpenTitan pack, the public task contains the copied upstream docs, while the task metadata points at a shared hidden source bundle under `data/shared_sources/registry.json` for upstream `rtl/` and `dv/` paths. Those private assets are not staged into agent workspaces.

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
3. `scale_corpus`: RTL-Repo for broader repository-level RTL exposure, but not as your main reward source.

The project plan in `docs/project-plan.md` assumes you will upgrade a small subset of the seed tasks into truly trusted formal anchors before running serious RL.

## Immediate Next Steps

1. Download RTLLM and VerilogEval locally and materialize them into the split public/oracle task store.
2. Pick 10-20 small synchronous designs and turn them into formal anchor tasks with SBY/EQY.
3. Train the generator and verifier in staged OpenCode workspaces with the hardware skills checked into `.opencode/skills/`.
4. Plug the OpenCode episode runtime and hidden-oracle evaluator into a Tinker environment.
