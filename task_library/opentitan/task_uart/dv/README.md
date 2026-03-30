# uart Verification Notes

This directory describes the public verification intent for the task.
It is not a build recipe for the hidden oracle and it intentionally avoids upstream repo-specific setup details.

## Public Guidance

- Implement the behavior described in `spec/README.md`, `spec/doc/`, and the canonical SV boundary in `spec/interface/` for `uart`.
- If `spec/micro_arch/` is present, instantiate the required microarchitecture interface exactly and drive its documented observation signals.
- The hidden oracle is a reference-backed simulation environment derived from a stronger verification bench.
- The hidden oracle runs under `xcelium`.
- A smoke-style hidden validation target exists for this task (`uart_smoke`).

## What This Means For A Solver

- Focus on documented reset behavior, register-visible side effects, interrupt/alert behavior, and the externally visible protocol behavior.
- Do not rely on hidden repo files or hidden package imports; the public task bundle is the intended implementation boundary.
