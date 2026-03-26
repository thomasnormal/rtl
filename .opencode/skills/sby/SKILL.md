---
name: sby
description: Run lightweight SymbiYosys formal checks when assertions or bounded proofs are helpful.
---

# SymbiYosys

Use `sby` when the task is small enough for lightweight formal checking or when you can express the key property clearly.

Typical flow:

1. Write a small `.sby` file.
2. Include the DUT and any assertion wrapper.
3. Run:

```bash
sby -f check.sby
```

Guidance:

- Prefer bounded safety checks first.
- Keep assumptions explicit and minimal.
- Save generated assertion wrappers and `.sby` files under `result/evidence/` if they matter to the verdict.
- If the state space is clearly too large, stop early and switch back to simulation or linting.
