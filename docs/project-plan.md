# Project Plan

## Thesis

Train a verifier agent that takes `(spec, candidate_rtl)`, chooses verification actions, and learns to match a hidden oracle on anchor tasks. Then use that verifier to score larger-scale generator outputs.

## Milestones

### M0. Public/Oracle Task Store

Materialize every anchor task into a split layout:

- `spec.txt`
- `public/task.json`
- `oracle/` for hidden benches or formal collateral
- `task.json`

The public subtree is what OpenCode agents see. The oracle subtree stays trainer-only.

Exit criterion: RTLLM and VerilogEval ingest into the same hidden-oracle task store.

### M1. Trusted Formal Anchors

Pick 10-20 small designs and upgrade them to trusted anchors:

- miter against `gold_rtl.v` where possible
- SBY proofs for safety/liveness where practical
- small directed regressions for simulator sanity

Exit criterion: every anchor task has a reproducible oracle verdict.

### M2. OpenCode Trace Collection

Collect boring but sane traces through OpenCode workspaces:

1. inspect spec and IO
2. parse/compile/lint
3. run short sim
4. emit one or two assertions
5. run formal if still uncertain
6. return verdict plus evidence bundle

Exit criterion: a trace dataset with action logs, staged workspaces, costs, and oracle labels.

### M3. Tinker RL

Wrap the verifier as a Tinker environment:

- `initial_observation`: spec, RTL, and budget
- `step`: tool action -> observation delta
- reward: oracle match + evidence utility - tool cost - false alarms

Exit criterion: the verifier beats a passive classifier baseline on held-out anchors.

### M4. Generator Loop

Use the verifier to score generated RTL:

1. sample spec
2. stage K public workspaces
3. run OpenCode generator episodes
4. validate with hidden oracles and verifier-backed rewards
5. replay anchor tasks to detect drift

Exit criterion: generator quality improves on held-out anchor families without reward hacking.
