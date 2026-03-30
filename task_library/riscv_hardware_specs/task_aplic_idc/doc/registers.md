# APLIC IDC Normalized Register Summary

This file is the compact task-facing summary for the normalized `riscv_aplic_idc` public interface.
It is intentionally narrower and more concrete than the full AIA prose in the page-chunk markdown.

## Scope

- The task models one APLIC interrupt delivery control (IDC) block for one hart.
- The task uses the AIA direct-delivery register semantics for `idelivery`, `iforce`, `ithreshold`,
  `topi`, and `claimi`.
- The task is not a full APLIC domain. The wider APLIC source tables are normalized into public input
  buses that provide the current per-source pending, enable, and priority view for this hart.
- The normalized task supports 32 sources, numbered `1..31`.
- Source `0` is reserved, ignored as an input source, and never wins selection.

## Reset State

After reset, the normalized public state is:

- `idelivery = 0`
- `iforce = 0`
- `ithreshold = 0`
- `irq_o = 0`
- `claim_pulse_o = 0`
- `claim_id_o = 0`

## Address Map

| Address | Name | Behavior |
| --- | --- | --- |
| `0x00` | `idelivery` | WARL delivery-enable register. Supported values are `0` and `1`. Other writes are ignored. |
| `0x04` | `iforce` | WARL force register. Supported values are `0` and `1`. Other writes are ignored. |
| `0x08` | `ithreshold` | WLRL 8-bit threshold register. Priority values greater than or equal to a nonzero threshold do not contribute to delivery. |
| `0x18` | `topi` | Read-only top interrupt register. Writes are ignored. |
| `0x1C` | `claimi` | Same read value as `topi`. A nonzero read requests a claim through `claim_pulse_o` / `claim_id_o`. Writes are ignored. |

All other addresses are reserved: reads return zero and writes have no effect.

## Source Inputs

- `src_pending_i[31:0]`: pending bits for sources `0..31`
- `src_enable_i[31:0]`: enable bits for sources `0..31`
- `src_prio_i[255:0]`: flattened `32 x 8-bit` priority table

Source `i` uses byte `src_prio_i[i*8 +: 8]`.

Normalized priority rules:

- priority `0` is treated as inactive / unsupported and must not win selection
- smaller nonzero priority numbers mean higher priority
- if priorities tie, the smaller source number wins

## `topi` / `claimi` Encoding

- If no source qualifies, reads from `topi` and `claimi` return zero.
- Otherwise the winning source is encoded as:
  - bits `25:16`: source identity
  - bits `7:0`: source priority
  - all other bits zero
- `topi` is not affected by `domain_ie_i` or by `idelivery`.

## Delivery Rules

- A source qualifies for `topi` when:
  - its source number is in `1..31`
  - its pending bit is `1`
  - its enable bit is `1`
  - its priority is nonzero
  - and either `ithreshold == 0` or its priority is strictly less than `ithreshold`
- `irq_o` is asserted iff:
  - `domain_ie_i == 1`
  - `idelivery == 1`
  - and either `iforce == 1` or `topi != 0`

## Claim Semantics

- Reading `claimi` returns the same value as `topi`.
- If that value is nonzero, assert `claim_pulse_o` for one cycle and drive `claim_id_o` with the
  winning source number.
- Since pending bits are public inputs in this normalized task, the environment clears the claimed
  source after observing `claim_pulse_o`.
- If a read of `claimi` returns zero, `iforce` is cleared to zero.
