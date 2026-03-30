# Interface Summary

The canonical machine-readable interface for `pattgen` is defined in `spec/interface/`.
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
| `input` | `rst_ni` | `logic` |
| `input` | `tl_i` | `pattgen_public_types_pkg::pattgen_tl_i_t` |
| `input` | `alert_rx_i` | `pattgen_public_types_pkg::pattgen_alert_rx_i_t` |
| `output` | `tl_o` | `pattgen_public_types_pkg::pattgen_tl_o_t` |
| `output` | `alert_tx_o` | `pattgen_public_types_pkg::pattgen_alert_tx_o_t` |
| `output` | `cio_pda0_tx_o` | `logic` |
| `output` | `cio_pcl0_tx_o` | `logic` |
| `output` | `cio_pda1_tx_o` | `logic` |
| `output` | `cio_pcl1_tx_o` | `logic` |
| `output` | `cio_pda0_tx_en_o` | `logic` |
| `output` | `cio_pcl0_tx_en_o` | `logic` |
| `output` | `cio_pda1_tx_en_o` | `logic` |
| `output` | `cio_pcl1_tx_en_o` | `logic` |
| `output` | `intr_done_ch0_o` | `logic` |
| `output` | `intr_done_ch1_o` | `logic` |

## Supporting SV Files

- `spec/interface/pattgen_public_if.sv`
- `spec/interface/pattgen_public_regs_pkg.sv`
- `spec/interface/pattgen_public_tlul_pkg.sv`
- `spec/interface/pattgen_public_types_pkg.sv`
