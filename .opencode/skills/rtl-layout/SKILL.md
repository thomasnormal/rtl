---
name: rtl-layout
description: Understand the staged RTL task workspace and the required output locations.
---

# RTL Workspace Layout

This repo stages OpenCode episodes in a small deterministic layout:

- `task/spec.txt`: public natural-language task description
- `task/task.json`: public task metadata, including the candidate top-module hint
- `submission/`: where the generator writes RTL
- `candidate/`: where the verifier reads the candidate RTL
- `result/`: where the agent writes its machine-readable outcome
- `TASK.md`: the episode-specific objective and output contract

Rules:

- Treat `task/` as read-only input.
- Write the main RTL deliverable to `submission/candidate.sv` unless `TASK.md` says otherwise.
- Write the machine-readable outcome to `result/result.json`.
- Large evidence files belong under `result/evidence/`.
- Do not rely on hidden benches, hidden references, or undeclared files.
