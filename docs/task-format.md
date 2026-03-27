# Task Format

This repo uses a public task format that is intentionally independent of any
particular upstream codebase.

The goal is:

- a generator or verifier can solve the task from the staged workspace alone
- the hidden oracle can still adapt a stronger repo-native DV flow behind that
  public boundary

## Public Task Surface

Agents only see:

```text
task/
  top_module.txt
  task.json
  spec/
    README.md
    doc/
    data/
    dv/
    interface/
    micro_arch/   # optional
```

That staged `task/` directory is intended to be complete. A solver should not
need access to hidden repo code or upstream implementation files.

### `task/top_module.txt`

This is the authoritative public DUT top-module name.

It is intentionally a standalone file so the public contract does not bury
the most important build target inside JSON bookkeeping.

### `task/task.json`

This is lightweight public machine-readable metadata:

- dataset and task identity
- deliverable locations

The canonical external interface no longer lives here. It lives in
`task/spec/interface/`.

### `task/spec/interface/`

This is the canonical public DUT boundary in SystemVerilog.

It should be sufficient to compile and elaborate a correct standalone
implementation without importing any hidden or upstream packages.

For OpenTitan-derived tasks this may include:

- a generated `<top>_public_if.sv`
- a generated `<top>_public_types_pkg.sv`
- a generated `<top>_public_tlul_pkg.sv`
- a generated `<top>_public_regs_pkg.sv`

The public interface package should preserve all semantically relevant boundary
fields, not just the minimum needed for a smoke test.

### `task/spec/micro_arch/`

This is the optional public microarchitecture / verification ABI.

It exists for tasks where deep verification needs more than the top-level port
contract, but we still want the task to remain solvable in isolation.

The microarchitecture contract must itself be self-contained SV.

## Microarchitecture Contract Rules

If `task/spec/micro_arch/` exists:

- it must contain `README.md`
- it must contain exactly one `*_micro_arch_if.sv`
- that interface must define a `dut` modport
- that interface must define at least one consumer modport such as `tb` or `mon`

Recommended layout:

```text
task/spec/micro_arch/
  README.md
  <top>_micro_arch_if.sv
  <top>_micro_arch_checker.sv
  <top>_micro_arch_bind.sv
```

Recommended semantics:

- `interface`: named observation and optional fault-injection points
- `checker`: local ABI sanity rules
- `bind`: top-level bind path used by adapted DV/oracle flows

## Design Intent

`interface/` and `micro_arch/` serve different purposes:

- `interface/` is the public hardware boundary
- `micro_arch/` is the explicit deep-DV ABI

The hidden oracle may adapt a repo-native bench to use those files, but the
task itself must remain implementable without access to the upstream repo.

That means:

- no public references to hidden repo paths
- no requirement to import hidden packages
- no hidden hierarchy assumptions smuggled into the task

If a deep oracle needs extra structure, it should be spelled out in
`micro_arch/`, not inferred from a specific upstream implementation.

## Hidden Oracle Validation Modes

The public task format does not require a hidden reference RTL.

Oracle validation depends on what hidden assets exist for that task family:

- `reference_backed`
  - The hidden oracle has a trusted reference implementation.
  - Validation should include:
    - reference/gold selftest
    - mutant or bug-bank discrimination
    - candidate validation against the hidden oracle
  - OpenTitan belongs in this bucket.

- `reference_free`
  - The hidden oracle has no trusted reference RTL, only a self-checking bench,
    assertions, formal properties, or another executable validator.
  - Validation should include:
    - oracle harness selfcheck where possible
    - mutant or bug-bank discrimination against the executable oracle
    - candidate validation against that oracle
  - In this mode there is no universal "gold-pass" requirement because there is
    no hidden gold RTL to pass.

- `public_only`
  - There is no hidden oracle yet, only a public task bundle.
  - The task may still be useful for supervised pretraining, document
    conversion, or later oracle construction, but it is not yet an oracle-backed
    training/eval task.

So the invariant is not "every oracle must have a gold-pass."
The invariant is:

- every oracle-backed task must have a reproducible validation story
- and that story must match the hidden assets actually available for that task
