# IMSIC Normalized Register Summary

This file is the compact task-facing summary for the normalized `riscv_imsic` public interface.
It is intentionally narrower and more concrete than the full AIA prose in the page-chunk markdown.

## Scope

- The task models one interrupt file plus its `irq_o` output.
- The normalized task implements interrupt identities `1..2047`.
- Identity `0` is unsupported and behaves as hardwired zero / ignored.
- The task is not a full hart CSR subsystem. `0x140` is a normalized stand-in for `mtopei` /
  `stopei` read-and-claim behavior.

## Reset State

After reset, the normalized public state is:

- `eidelivery = 0x4000_0000`
- `eithreshold = 0`
- all `eip[*] = 0`
- all `eie[*] = 0`
- `irq_o = 0`

## Address Map

| Address | Name | Behavior |
| --- | --- | --- |
| `0x000` | `seteipnum_le` | Write-only set-pending-by-identity port. Valid writes set the pending bit for identity `i`. Reads return zero. |
| `0x004` | `seteipnum_be` | Same functional behavior as `seteipnum_le` for this normalized task. Reads return zero. |
| `0x070` | `eidelivery` | WARL delivery-control register. Supported values are `0`, `1`, and `0x4000_0000`. Other writes are ignored. |
| `0x072` | `eithreshold` | WLRL threshold register over the implemented identity range `0..2047`. Values above `2047` are ignored. |
| `0x080..0x0BF` | `eip[0:63]` | Pending-bit array, 64 words x 32 bits. Bit `i[4:0]` of word `i>>5` is the pending bit for identity `i`. |
| `0x0C0..0x0FF` | `eie[0:63]` | Enable-bit array, same packing as `eip`. |
| `0x140` | normalized `topei` | Read returns the current top pending-and-enabled interrupt in `*topei` format. Write ignores `wdata` and claims that interrupt by clearing its pending bit. |

All other addresses are reserved: reads return zero and writes have no effect.

## Bit-Level Notes

- `eip[0][0]` and `eie[0][0]` correspond to unsupported identity `0` and must remain zero.
- All other bits in `eip[*]` and `eie[*]` are implemented for identities `1..2047`.

## Delivery and Priority Rules

- An interrupt is eligible when its pending bit is set in `eip`, its enable bit is set in `eie`,
  and it is below the current threshold if `eithreshold != 0`.
- Lower interrupt identity means higher priority.
- `irq_o` is asserted iff:
  - `eidelivery == 1`, and
  - at least one interrupt is eligible.
- `eidelivery = 0x4000_0000` is the supported alternate-controller value from the base spec; in this
  normalized task it suppresses `irq_o` exactly like disabled delivery.

## Normalized `topei` Encoding

- If no interrupt is eligible, reads from `0x140` return zero.
- Otherwise, reading `0x140` returns the winning identity `i` in both bits `26:16` and `10:0`,
  matching the repeated-ID shape of AIA `*topei`.
- Writing `0x140` claims the currently reported interrupt by clearing its pending bit.
- The write data is ignored.
