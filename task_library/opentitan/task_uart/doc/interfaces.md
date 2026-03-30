# Interface Summary

The canonical machine-readable interface for `uart` is defined in `spec/interface/`.
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
| `input` | `tl_i` | `uart_public_types_pkg::uart_tl_i_t` |
| `input` | `alert_rx_i` | `uart_public_types_pkg::uart_alert_rx_i_t` |
| `input` | `racl_policies_i` | `uart_public_types_pkg::uart_racl_policies_i_t` |
| `input` | `cio_rx_i` | `logic` |
| `output` | `tl_o` | `uart_public_types_pkg::uart_tl_o_t` |
| `output` | `alert_tx_o` | `uart_public_types_pkg::uart_alert_tx_o_t` |
| `output` | `racl_error_o` | `uart_public_types_pkg::uart_racl_error_o_t` |
| `output` | `lsio_trigger_o` | `logic` |
| `output` | `cio_tx_o` | `logic` |
| `output` | `cio_tx_en_o` | `logic` |
| `output` | `intr_tx_watermark_o` | `logic` |
| `output` | `intr_tx_empty_o` | `logic` |
| `output` | `intr_rx_watermark_o` | `logic` |
| `output` | `intr_tx_done_o` | `logic` |
| `output` | `intr_rx_overflow_o` | `logic` |
| `output` | `intr_rx_frame_err_o` | `logic` |
| `output` | `intr_rx_break_err_o` | `logic` |
| `output` | `intr_rx_timeout_o` | `logic` |
| `output` | `intr_rx_parity_err_o` | `logic` |

## Supporting SV Files

- `spec/interface/uart_public_if.sv`
- `spec/interface/uart_public_regs_pkg.sv`
- `spec/interface/uart_public_tlul_pkg.sv`
- `spec/interface/uart_public_types_pkg.sv`
