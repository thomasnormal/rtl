# OpenTitan Public Completeness Audit

Date: 2026-03-27

This audit covers the 9 curated OpenTitan IP tasks in
`data/task_store/opentitan_ip_docs`.

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
- machine-readable register/spec data in `spec/data/*.hjson`
- public DV collateral in `spec/dv/`
- self-contained HDL boundary in `spec/interface/*.sv`
- explicit deep-DV ABI in `spec/micro_arch/*.sv`

The public task should be implementable without access to hidden OpenTitan RTL
or hidden oracle files. It is acceptable for copied upstream docs to mention
OpenTitan names in prose; it is not acceptable for the public HDL contract to
require hidden packages or hidden paths.

## Result Summary

All 9 curated OpenTitan tasks now mirror the relevant public upstream files
under `README.md`, `doc/`, `data/`, and `dv/`, in addition to the generated
`interface/` and `micro_arch/` contracts.

The only upstream gap is `sysrst_ctrl`, which does not publish a separate
`doc/programmers_guide.md`. That is an upstream limitation, not a task-pack
loss.

## Per-Task Assessment

| Task | Public Spec Coverage | Public ABI Coverage | Confidence | Main Caveat |
| --- | --- | --- | --- | --- |
| `adc_ctrl` | README, interfaces, registers, theory, programmer guide, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | High | Mixed always-on / main clock domains add implementation complexity |
| `aon_timer` | README, interfaces, registers, theory, programmer guide, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | High | Cross-domain interrupt timing remains subtle |
| `dma` | README, interfaces, registers, theory, programmer guide, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | Medium | Most complex boundary in the pack; multiple bus/response channels |
| `i2c` | README, interfaces, registers, theory, programmer guide, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | Medium | Protocol behavior is dense and timing-sensitive |
| `pattgen` | README, interfaces, registers, theory, programmer guide, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | High | Dual-channel counter semantics still need careful reading |
| `rv_timer` | README, interfaces, registers, theory, programmer guide, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | High | Public TL and alert semantics must be implemented precisely |
| `spi_host` | README, interfaces, registers, theory, programmer guide, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | Medium | Command engine and FSM behavior are relatively complex |
| `sysrst_ctrl` | README, interfaces, registers, theory, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | Medium | No separate upstream programmer guide; behavior is spread across README/theory/registers |
| `uart` | README, interfaces, registers, theory, programmer guide, HJSON, DV docs/config | Full `interface/` and `micro_arch/` | High | Interrupt and FIFO corner cases still require careful implementation |

## Conclusions

- The OpenTitan public bundles are now **document-complete** relative to the
  relevant public upstream collateral we chose to mirror.
- The remaining risk is no longer "missing docs", but task difficulty:
  protocol complexity, cross-domain behavior, and TL/register side effects.
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
