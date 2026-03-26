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

### 5. RTL-Repo

Use RTL-Repo for scale and repository context, not as the main RL reward source. It broadens code exposure and can help later with generator pretraining or repository-conditioned tasks.

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
