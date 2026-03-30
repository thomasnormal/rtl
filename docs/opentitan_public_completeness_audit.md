# OpenTitan Public Completeness Audit

Date: 2026-03-27

This audit covers the 9 curated OpenTitan-derived IP tasks in
`data/task_store/opentitan`.

The question is not just whether the tasks are syntactically present, but
whether an external solver has a realistic chance to implement a candidate
accepted by the hidden oracle **using only the public task bundle**.

## Audit Rule

For each task, the public bundle should include:

- top-level overview in `spec/README.md`
- interface description in `spec/doc/interfaces.md`
- register description in `spec/doc/registers.md`
- behavior description in `spec/doc/theory_of_operation.md`
- programmer guide when upstream provides one
- compact machine-readable task data when it helps implementation
- public DV notes and diagrams in `spec/dv/`
- self-contained HDL boundary in `spec/interface/*.sv`
- explicit deep-DV ABI in `spec/micro_arch/*.sv`

The public task should be implementable without access to hidden reference RTL
or hidden oracle files. The public docs should also be task-facing: they should
not drown the solver in repo paths, project badges, build commands, or other
upstream-specific noise that is irrelevant to implementing the design.

## Result Summary

All 9 curated tasks now have a curated public spec layer derived from the
upstream docs and checked in directly under the task library.

The public bundles intentionally do **not** mirror every upstream file. Instead
they keep the solver-facing material and remove or rewrite upstream-specific
content such as:

- repo-relative build instructions
- dashboard badges and project-status boilerplate
- raw DV sim config files
- raw testplan HJSON files
- direct references to upstream package paths

The only real content gap remains `sysrst_ctrl`, which does not publish a
separate `doc/programmers_guide.md` upstream.

## Per-Task Assessment

| Task | Public Spec Coverage | Public ABI Coverage | Confidence | Main Caveat |
| --- | --- | --- | --- | --- |
| `adc_ctrl` | Curated README, interfaces, registers, theory, programmer guide, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | High | Mixed always-on / main clock domains add implementation complexity |
| `aon_timer` | Curated README, interfaces, registers, theory, programmer guide, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | High | Cross-domain interrupt timing remains subtle |
| `dma` | Curated README, interfaces, registers, theory, programmer guide, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | Medium | Most complex boundary in the pack; multiple bus/response channels |
| `i2c` | Curated README, interfaces, registers, theory, programmer guide, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | Medium | Protocol behavior is dense and timing-sensitive |
| `pattgen` | Curated README, interfaces, registers, theory, programmer guide, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | High | Dual-channel counter semantics still need careful reading |
| `rv_timer` | Curated README, interfaces, registers, theory, programmer guide, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | High | Public control-bus and alert semantics must be implemented precisely |
| `spi_host` | Curated README, interfaces, registers, theory, programmer guide, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | Medium | Command engine and FSM behavior are relatively complex |
| `sysrst_ctrl` | Curated README, interfaces, registers, theory, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | Medium | No separate upstream programmer guide; behavior is spread across README/theory/registers |
| `uart` | Curated README, interfaces, registers, theory, programmer guide, DV notes, interface SV, micro-arch SV | Full `interface/` and `micro_arch/` | High | Interrupt and FIFO corner cases still require careful implementation |

## Conclusions

- The OpenTitan-derived public bundles are now **document-complete** for the
  task-facing surface we want generators and verifiers to read.
- The bundles are now intentionally more general than the upstream repo docs:
  they preserve relevant behavior and ABI, but strip or rewrite unrelated
  OpenTitan-specific material.
- The remaining risk is no longer "missing docs", but task difficulty:
  protocol complexity, cross-domain behavior, and register-visible side effects.
- `dma` remains the least friendly public task because its boundary is the most
  complex, not because documentation is missing.
- `sysrst_ctrl` is acceptable as-is, but it inherits an upstream documentation
  gap: there is no standalone programmer guide to mirror.

## Next Confidence Step

The next way to validate completeness is empirical:

1. choose one of the easier audited tasks, such as `aon_timer` or `pattgen`
2. run a strong generator model against the public bundle only
3. see whether the hidden oracle can accept the result

That would test not just that the docs exist, but that the public task is
actually solvable in practice.
