---
name: sv-verification
description: Write executable SystemVerilog verification collateral, especially SVAs and self-checking benches, when judging RTL against a public spec.
---

# SV Verification

Use this skill when you need evidence, not just a code review.

## Workflow

1. Extract a numbered checklist from the spec.
2. For each requirement, choose the cheapest strong check:
   - concurrent SVA for invariants, timing, and handshake rules
   - self-checking directed or randomized SystemVerilog testbench for functional behavior
   - small reference-model scoreboard when outputs can be computed directly
   - UVM-style driver/monitor/scoreboard only when the interface or sequencing is too complex for a small bench
3. Save generated verification files under `result/evidence/`.
4. Run the checks with `xrun` or `sby`.
5. Map the evidence back to the checklist and call out any unresolved gaps explicitly.

## Guidance

- Prefer plain SystemVerilog plus SVAs over full UVM for small single-module tasks.
- Use actual UVM-style structure when you need reusable transactions, sequencing, monitoring, or scoreboarding across multiple channels.
- Run UVM in the native SV scheduler with `xrun -uvm`; do not move the stimulus or checking logic into ad hoc host-language code if SV/UVM can express it directly.
- Make assertions specific and named.
- Keep assertions in separate files or bind modules so the DUT stays unchanged.
- Check reset behavior explicitly.
- For combinational blocks, exhaust small state spaces when practical.
- For sequential logic, test timing, enables, hold behavior, and corner cases, not just end-state values.
- Keep benches self-checking; do not rely on manual waveform inspection for the final verdict.
- Keep logs and generated files under `result/evidence/` so the final verdict can cite them.

## SVA Patterns

- Use concurrent assertions for:
  - reset postconditions
  - ready/valid or request/ack timing
  - pulse and edge-detection timing
  - latency windows such as `req |-> ##[1:4] rsp`
  - stability rules such as "hold data while valid and not ready"
  - exclusivity and one-hot constraints
- Prefer `bind` when the DUT should remain untouched.
- If a property can be checked in both a scoreboard and an assertion, use both when the cost is small: assertions catch temporal bugs early, scoreboards catch end-to-end functional mismatches.

## UVM Patterns

- Escalate to UVM when a plain SV bench is becoming awkward because you need:
  - reusable transactions
  - randomized sequences with constraints
  - monitors and a scoreboard across multiple interfaces
  - protocol backpressure or out-of-order checking
- Keep the UVM environment minimal:
  - interface
  - sequence item
  - sequencer and driver
  - monitor
  - scoreboard or reference model
  - environment
  - one or two focused tests
- Prefer a deterministic smoke test first, then randomized tests.
- Finish with a clear pass/fail summary in the log, not only UVM info messages.
