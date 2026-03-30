# Interface Summary

The canonical machine-readable interface for `aon_timer` is defined in `spec/interface/`.
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
| `input` | `clk_aon_i` | `logic` |
| `input` | `rst_ni` | `logic` |
| `input` | `rst_aon_ni` | `logic` |
| `input` | `tl_i` | `aon_timer_public_types_pkg::aon_timer_tl_i_t` |
| `input` | `alert_rx_i` | `aon_timer_public_types_pkg::aon_timer_alert_rx_i_t` |
| `input` | `racl_policies_i` | `aon_timer_public_types_pkg::aon_timer_racl_policies_i_t` |
| `input` | `lc_escalate_en_i` | `aon_timer_public_types_pkg::aon_timer_lc_escalate_en_i_t` |
| `input` | `sleep_mode_i` | `logic` |
| `output` | `tl_o` | `aon_timer_public_types_pkg::aon_timer_tl_o_t` |
| `output` | `alert_tx_o` | `aon_timer_public_types_pkg::aon_timer_alert_tx_o_t` |
| `output` | `racl_error_o` | `aon_timer_public_types_pkg::aon_timer_racl_error_o_t` |
| `output` | `intr_wkup_timer_expired_o` | `logic` |
| `output` | `intr_wdog_timer_bark_o` | `logic` |
| `output` | `nmi_wdog_timer_bark_o` | `logic` |
| `output` | `wkup_req_o` | `logic` |
| `output` | `aon_timer_rst_req_o` | `logic` |

## Supporting SV Files

- `spec/interface/aon_timer_public_if.sv`
- `spec/interface/aon_timer_public_regs_pkg.sv`
- `spec/interface/aon_timer_public_tlul_pkg.sv`
- `spec/interface/aon_timer_public_types_pkg.sv`
