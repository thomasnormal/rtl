# Debug Abstract Command Frontend Summary

This file is the compact task-facing summary for the normalized `riscv_debug_abstract_cmd` public
interface. It is intentionally narrower and more concrete than the full External Debug prose in the
page-chunk markdown.

## Scope

- The task models only the abstract-command front end for one hart.
- The task owns only `data0`, `abstractcs`, `command`, and `abstractauto`.
- The task is not a full debug module. It does not implement `dmcontrol`, `dmstatus`, hart run
  control, Program Buffer storage, or System Bus Access.
- Actual command execution is delegated to an external executor through `cmd_start_o` and the
  `cmd_done_i` / `cmd_cmderr_i` / `cmd_data0_i` completion handshake.

## Request / Response Timing

- Requests are sampled on the rising edge when `req_valid_i` is high.
- `rsp_valid_o` pulses high for one cycle on the next cycle for every accepted read or write.
- Reads return register contents in `rsp_rdata_o`.
- Writes return `rsp_rdata_o = 0`.

## Reset State

After reset, the normalized public state is:

- `data0 = 0`
- `command_latched = 0`
- `abstractauto = 0`
- `abstractcs.busy = 0`
- `abstractcs.cmderr = 0`
- `abstractcs.datacount = 1`
- `abstractcs.progbufsize = 0`
- `cmd_start_o = 0`

Equivalently, reads of `abstractcs` after reset must return `0x0000_0001`.

## Address Map

| Address | Name | Behavior |
| --- | --- | --- |
| `0x04` | `data0` | Read/write abstract data register 0. |
| `0x16` | `abstractcs` | Read the packed status word. Writing ones to bits `9:7` clears the corresponding `cmderr` bits when the frontend is idle. |
| `0x17` | `command` | Write-only command register. Accepted writes latch the command word and start execution. Reads return zero. |
| `0x18` | `abstractauto` | Read/write autoexec register. Only `autoexecdata[0]` is implemented; all other bits read as zero and ignore writes. |

All other addresses are reserved: reads return zero and writes have no effect.

## `abstractcs` Packing

- `abstractcs[28:24] = progbufsize = 0`
- `abstractcs[12] = busy`
- `abstractcs[9:7] = cmderr`
- `abstractcs[3:0] = datacount = 1`
- All other bits are zero.

## Busy / Error Rules

- Writing `command` when `busy = 0` and `cmderr = 0`:
  - latches `req_wdata_i` as the current command,
  - pulses `cmd_start_o`,
  - drives `cmd_word_o` with the launched command in the same cycle as `cmd_start_o`,
  - drives `cmd_data0_o` with the launched `data0` argument in the same cycle as `cmd_start_o`,
  - sets `busy = 1`.
- If `cmderr != 0`, writes to `command` are ignored and do not start a new command.
- While `busy = 1`, any write to `command`, `abstractcs`, or `abstractauto` sets `cmderr = 1`
  if `cmderr` was `0`.
- While `busy = 1`, any read or write of `data0` sets `cmderr = 1` if `cmderr` was `0`.
- The busy error does not overwrite an existing nonzero `cmderr`.

## Completion Rules

- When `cmd_done_i` pulses:
  - `busy` clears to `0`,
  - `data0` is updated from `cmd_data0_i`,
  - if `cmd_cmderr_i != 0` and `cmderr` is still `0`, `cmderr` becomes `cmd_cmderr_i`.

## `abstractauto` Rules

- Only bit `0` (`autoexecdata[0]`) is implemented.
- When `autoexecdata[0] = 1` and the frontend is idle:
  - a write to `data0` updates `data0`, then retriggers the current latched command,
  - a read of `data0` returns the current `data0`, then retriggers the current latched command.
- The retriggered execution follows the same `cmd_start_o` / `cmd_word_o` / `cmd_data0_o` behavior
  as a direct write to `command`.

## Required Launch-Time Examples

These examples are normative for the normalized task.

### Example 1: direct `command` write

Initial state:

- `data0 = 0x1111_0001`
- `command_latched = 0x0000_0000`
- `busy = 0`
- `cmderr = 0`

If software writes `0xCAFE_BABE` to `command`:

- `cmd_start_o` pulses once,
- `cmd_word_o = 0xCAFE_BABE` in that same pulse cycle,
- `cmd_data0_o = 0x1111_0001` in that same pulse cycle,
- `command_latched` becomes `0xCAFE_BABE`,
- `busy` becomes `1`.

### Example 2: autoexec write to `data0`

Initial state:

- `data0 = 0x1111_0001`
- `command_latched = 0xCAFE_BABE`
- `abstractauto[0] = 1`
- `busy = 0`
- `cmderr = 0`

If software writes `0x2222_0002` to `data0`:

- `data0` becomes `0x2222_0002`,
- `cmd_start_o` pulses once,
- `cmd_word_o = 0xCAFE_BABE` in that same pulse cycle,
- `cmd_data0_o = 0x2222_0002` in that same pulse cycle,
- `busy` becomes `1`.

### Example 3: autoexec read of `data0`

Initial state:

- `data0 = 0x3333_0003`
- `command_latched = 0xCAFE_BABE`
- `abstractauto[0] = 1`
- `busy = 0`
- `cmderr = 0`

If software reads `data0`:

- the read returns `0x3333_0003`,
- `cmd_start_o` pulses once,
- `cmd_word_o = 0xCAFE_BABE` in that same pulse cycle,
- `cmd_data0_o = 0x3333_0003` in that same pulse cycle,
- `busy` becomes `1`.
