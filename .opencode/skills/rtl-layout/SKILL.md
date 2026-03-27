---
name: rtl-layout
description: Understand the staged RTL task workspace and the required output locations.
---

# RTL Workspace Layout

This repo stages OpenCode episodes in a small deterministic layout:

- `task/spec/`: public spec directory (may contain `.txt`, `.md`, images, etc.)
- `task/spec/interface/`: canonical public SV interface contract when available
- `task/spec/micro_arch/`: optional public microarchitecture / deep-DV ABI
- `task/task.json`: lightweight public task metadata including the authoritative `top_module`
- `submission/`: where the generator writes RTL
- `candidate/`: where the verifier reads the candidate RTL
- `result/`: where the agent writes its machine-readable outcome
- `TASK.md`: the episode-specific objective and output contract

Rules:

- Treat `task/` as read-only input.
- Treat `task/task.json` field `top_module` and `task/spec/interface/` as the authoritative public build contract.
- Write RTL deliverables (one or more `.sv`/`.v` files) to `submission/`.
- Write the machine-readable outcome to `result/result.json`.
- Large evidence files belong under `result/evidence/`.
- Do not rely on hidden benches, hidden references, or undeclared files.
