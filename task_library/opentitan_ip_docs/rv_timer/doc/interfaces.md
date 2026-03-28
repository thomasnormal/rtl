# Interface Summary

The canonical machine-readable interface for `rv_timer` is defined in `spec/interface/`.
Use the SystemVerilog files there as the source of truth for port directions, packed types, parameters, and modports.

## Parameters

| Name | Default |
| --- | --- |
| `AlertAsyncOn` | `1'b1` |
| `AlertSkewCycles` | `1` |
| `EnableRacl` | `1'b0` |
| `RaclErrorRsp` | `EnableRacl` |
| `RaclPolicySelVec` | `'0` |

## Ports

| Direction | Name | Type |
| --- | --- | --- |
| `input` | `clk_i` | `logic` |
| `input` | `rst_ni` | `logic` |
| `input` | `tl_i` | `rv_timer_public_types_pkg::rv_timer_tl_i_t` |
| `input` | `alert_rx_i` | `rv_timer_public_types_pkg::rv_timer_alert_rx_i_t` |
| `input` | `racl_policies_i` | `rv_timer_public_types_pkg::rv_timer_racl_policies_i_t` |
| `output` | `tl_o` | `rv_timer_public_types_pkg::rv_timer_tl_o_t` |
| `output` | `alert_tx_o` | `rv_timer_public_types_pkg::rv_timer_alert_tx_o_t` |
| `output` | `racl_error_o` | `rv_timer_public_types_pkg::rv_timer_racl_error_o_t` |
| `output` | `intr_timer_expired_hart0_timer0_o` | `logic` |

## Supporting SV Files

- `spec/interface/rv_timer_public_if.sv`
- `spec/interface/rv_timer_public_regs_pkg.sv`
- `spec/interface/rv_timer_public_tlul_pkg.sv`
- `spec/interface/rv_timer_public_types_pkg.sv`
