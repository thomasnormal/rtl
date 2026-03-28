# Interface Summary

The canonical machine-readable interface for `adc_ctrl` is defined in `spec/interface/`.
Use the SystemVerilog files there as the source of truth for port directions, packed types, parameters, and modports.

## Parameters

| Name | Default |
| --- | --- |
| `AlertAsyncOn` | `1'b1` |
| `AlertSkewCycles` | `1` |

## Ports

| Direction | Name | Type |
| --- | --- | --- |
| `input` | `clk_i` | `logic` |
| `input` | `clk_aon_i` | `logic` |
| `input` | `rst_ni` | `logic` |
| `input` | `rst_aon_ni` | `logic` |
| `input` | `tl_i` | `adc_ctrl_public_types_pkg::adc_ctrl_tl_i_t` |
| `input` | `alert_rx_i` | `adc_ctrl_public_types_pkg::adc_ctrl_alert_rx_i_t` |
| `input` | `adc_i` | `adc_ctrl_public_types_pkg::adc_ctrl_adc_i_t` |
| `output` | `tl_o` | `adc_ctrl_public_types_pkg::adc_ctrl_tl_o_t` |
| `output` | `alert_tx_o` | `adc_ctrl_public_types_pkg::adc_ctrl_alert_tx_o_t` |
| `output` | `adc_o` | `adc_ctrl_public_types_pkg::adc_ctrl_adc_o_t` |
| `output` | `intr_match_pending_o` | `logic` |
| `output` | `wkup_req_o` | `logic` |

## Supporting SV Files

- `spec/interface/adc_ctrl_public_if.sv`
- `spec/interface/adc_ctrl_public_regs_pkg.sv`
- `spec/interface/adc_ctrl_public_tlul_pkg.sv`
- `spec/interface/adc_ctrl_public_types_pkg.sv`
