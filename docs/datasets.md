# Dataset Notes

## Recommended Acquisition Order

### 1. RTLLM v1.1 / v2.0

Use RTLLM first because each task already has the three artifacts you need for anchor seeding:

- natural-language spec
- hidden simulation testbench
- verified RTL reference

This is the cleanest starting point for a split public/oracle task store.

In practice, fetch both public branches:

- `v1.1` for the 29-task branch named in the original RTLLM release
- `main` for the current 50-task RTLLM-2.0 style tree

### 2. VerilogEval V2

Use VerilogEval second because it gives you a stronger public benchmark and a maintained harness with failure analysis. Treat it as another anchor-seed source, then manually upgrade a subset into formal anchors.

### 3. AssertEval

Use AssertEval to train the verifier on assertion writing and formal task selection. It is not large enough to be the whole project, but it is directly aligned with evidence generation.

### 4. OpenTitan / Ibex

Use these later, after the small-task pipeline is stable. They are valuable because they look like real DV repositories:

- testplans
- DV docs
- scoreboards
- SVAs
- UVM benches
- reference models

They are not good phase-0 data because setup cost is too high.

The first OpenTitan medium-tier pack is now checked in as curated task bundles for:

- `uart`
- `i2c`
- `spi_host`
- `dma`
- `sysrst_ctrl`

These are manually ingested spec bundles copied from the local `~/opentitan` checkout, not rewritten summaries and not an automated ingest pipeline. The public task metadata is curated, the spec content itself is the upstream OpenTitan documentation with its original directory structure preserved, and the materialized task store references a shared hidden source bundle for upstream `rtl/` and `dv/` paths needed by future oracle work.

### 5. RTL-Repo

Use RTL-Repo for scale and repository context, not as the main RL reward source. It broadens code exposure and can help later with generator pretraining or repository-conditioned tasks.

## Tiering Strategy

Use four user-facing tiers, and keep them separate in both ingest and evaluation.

### Small

Use this for the current anchor path:

- RTLLM v1.1 / v2.0
- VerilogEval
- AssertEval

Properties:

- short natural-language specs or small prompt-style tasks
- direct hidden simulation or formal collateral
- good for oracle calibration, verifier pretraining, and regression testing

### Medium

Target roughly 10-30 page PDFs or rendered PDFs.

Best sources:

- individual OpenTitan IP datasheets plus DV docs, starting with the checked-in `uart`, `i2c`, `spi_host`, `dma`, and `sysrst_ctrl` task pack
- focused OpenHW core manuals or manual chapters
- open protocol specs such as Wishbone B4, paired with public implementations and trainer-built oracles

Properties:

- one IP or protocol at a time
- enough prose/tables/timing to require retrieval and requirement extraction
- still bounded enough that one verifier episode can plausibly cover the whole spec

Important:

- do not wait for “perfect native PDFs”; authoritative HTML/markdown docs are fine, and for the first OpenTitan pack we manually copied the upstream documentation bundle directly into the task library

### Large

Target roughly 30-300 page manuals.

Best public sources:

- OpenTitan top-level datasheets and integration docs
- CVA6 user manual
- CORE-V-MCU user manual
- NVDLA integration and hardware docs
- ONFI protocol specs as an open memory/protocol family

Properties:

- subsystem, controller, or SoC-level integration concerns
- multiple interfaces, registers, modes, and timing stories
- retrieval/chunking becomes mandatory

### Industrial

Reserve this for standards and SoC architecture packages that need legal review or private ingest.

Examples:

- JEDEC DDR3 / DDR6
- large internal SoC specs
- other consortium or vendor standards with redistribution limits

Properties:

- often multi-document and hundreds of pages
- usually not safe to mix into the public pipeline
- require a separate private artifact store, private chunk index, and explicit license tracking

## Recommended Next Datasets

If the goal is “more data soon” without getting blocked on licensing, the next best sequence is:

1. OpenTitan IP docs as the first medium tier
2. OpenHW single-core manuals as the second medium tier
3. OpenTitan top-level docs, CVA6, CORE-V-MCU, and NVDLA as the first large tier
4. ONFI as the first open memory/protocol large tier
5. JEDEC DDR3 / DDR6 only after the private/licensed pipeline exists

## Task Store Record

Every stored task should become:

```text
task_id/
  public/
    spec.txt
    task.json
  oracle/
    gold_rtl.v
    sim/
    formal/
  task.json
```

Candidate RTLs should live outside the task store, for example in `runs/<episode_id>/submission/candidate.sv`.

## Avoid These Mistakes

- Do not treat simulation pass/fail alone as a gold oracle on every task.
- Do not mix noisy scale corpora into the reward path.
- Do not start with OpenTitan-scale benches before the small-task environment works.
- Do not let the generator or verifier see the hidden oracle artifacts during training episodes.
