---
name: eqy
description: Run equivalence checks between two explicit RTL implementations with EQY.
---

# EQY

Use `eqy` for equivalence checking when you have two RTL implementations that should be semantically identical.

Typical flow:

1. Prepare an `.eqy` file naming the gold and gate/candidate designs.
2. Run:

```bash
eqy check.eqy
```

Guidance:

- EQY is most useful for optimizer tasks or for comparing two explicit implementations.
- It is not a substitute for a task-level testbench when the reference behavior is only described in prose.
- Keep the compared tops explicit and make reset/clock assumptions clear.
