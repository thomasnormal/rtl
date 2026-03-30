# Task Quality Rubric

This rubric defines what constitutes a good task for this repository and gives a consistent way to score tasks across datasets.

The goal is not to reward tasks for being large or ornate. The goal is to reward tasks that are:

- solvable from the public task boundary
- evaluated by a trustworthy oracle
- resistant to reward hacking and shallow shortcuts
- reproducible and cheap to maintain

## Score Shape

- Score each category on a `0-5` scale.
- Convert category ratings to a weighted total out of `100`.
- Treat the gating failures in [task_quality_rubric.json](/home/thomas-ahle/rtl/configs/task_quality_rubric.json) as hard blockers regardless of total score.

Score bands:

- `85-100`: Excellent. Prioritize for training and benchmarking.
- `70-84`: Good. Usable with minor caveats.
- `50-69`: Marginal. Use only with explicit caveats or follow-up cleanup.
- `<50`: Not ready.

## Categories

### 1. Spec Quality (`20`)
Question:
Can a strong agent infer the intended RTL behavior from the public task materials alone?

Good evidence:
- `README.md`
- `doc/`
- `data/`
- `interface/`

What high score means:
- behavior is documented, not just named
- reset/default behavior is recoverable
- corner cases are visible somewhere in the public materials
- important timing or register semantics are not hidden in trainer-only collateral

### 2. Interface Contract (`15`)
Question:
Is the DUT boundary unambiguous and machine-checkable?

Good evidence:
- `task.json`
- `interface/`
- `micro_arch/`

What high score means:
- top module is explicit
- ports, widths, and public packages are present
- if the task needs a deep-DV ABI, it is published cleanly under `micro_arch/`

### 3. Oracle Quality (`25`)
Question:
Does the oracle reliably separate correct RTL from incorrect RTL?

Good evidence:
- oracle selftest
- gold RTL validation
- `dv/`
- testbench or cocotb collateral
- formal collateral when present

What high score means:
- gold selftest passes
- oracle is stable and reproducible
- the oracle checks the behavior that matters, not only superficial compile/smoke success
- known blind spots are small or documented

### 4. Self-Containment (`15`)
Question:
Can the task be staged and solved reproducibly without undocumented external dependencies?

What high score means:
- the public task bundle is enough to stage the problem
- upstream coupling is either removed or explicitly materialized
- tool assumptions are documented and realistic

### 5. Difficulty Calibration (`10`)
Question:
Is the task at an appropriate difficulty for its tier?

What high score means:
- the task is not trivial
- the task is not impossible due to underconstraint
- the tier reflects actual task complexity and oracle cost

### 6. Anti-Shortcut Robustness (`10`)
Question:
Does the task resist shallow solutions and oracle gaming?

What high score means:
- answer leakage is minimal
- the oracle cannot be satisfied by an obviously fake implementation
- the public/private split does not accidentally publish hidden verdict logic

### 7. Maintenance Cost (`5`)
Question:
Can the task be kept healthy over time without disproportionate manual effort?

What high score means:
- the oracle is not brittle for structural reasons
- docs and figures are already in stable repo form
- the task does not repeatedly require one-off manual repairs

## Scoring Process

For each task:

1. Check gating failures first.
2. Score every category `0-5`.
3. Record concrete evidence paths for each score.
4. Compute the weighted total.
5. Record the final band and the main caveats.

Recommended scoring note format:

```json
{
  "task": "task_uart",
  "scores": {
    "spec_quality": 4,
    "interface_contract": 5,
    "oracle_quality": 4,
    "self_containment": 4,
    "difficulty_calibration": 3,
    "anti_shortcut": 4,
    "maintenance_cost": 3
  },
  "evidence": {
    "spec_quality": ["doc/theory_of_operation.md", "doc/registers.md"],
    "interface_contract": ["interface/", "micro_arch/uart_micro_arch_if.sv"],
    "oracle_quality": ["dv/README.md"]
  },
  "notes": "Strong public docs and interface contract; oracle still has some deep-DV assumptions."
}
```

## How To Use It

- Use this rubric when curating new datasets into `task_library/`.
- Use it after task repairs to decide whether a task is now promotion-worthy.
- Use it to compare tasks across datasets without overfitting to one benchmark family.

The machine-readable source of truth is [task_quality_rubric.json](/home/thomas-ahle/rtl/configs/task_quality_rubric.json). The helper used to compute weighted totals is [task_quality.py](/home/thomas-ahle/rtl/src/rtl_training/task_quality.py).
