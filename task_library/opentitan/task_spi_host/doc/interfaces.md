# Interface Summary

The canonical machine-readable interface for `spi_host` is defined in `spec/interface/`.
Use the SystemVerilog files there as the source of truth for port directions, packed types, parameters, and modports.

## Parameters

| Name | Default |
| --- | --- |
| `AlertAsyncOn` | `1'b1` |
| `AlertSkewCycles` | `1` |
| `NumCS` | `1` |
| `EnableRacl` | `1'b0` |
| `RaclErrorRsp` | `EnableRacl` |
| `RaclPolicySelVec` | `'0` |
| `RaclPolicySelWinRXDATA` | `0` |
| `RaclPolicySelWinTXDATA` | `0` |

## Ports

| Direction | Name | Type |
| --- | --- | --- |
| `input` | `clk_i` | `logic` |
| `input` | `rst_ni` | `logic` |
| `input` | `tl_i` | `spi_host_public_types_pkg::spi_host_tl_i_t` |
| `input` | `alert_rx_i` | `spi_host_public_types_pkg::spi_host_alert_rx_i_t` |
| `input` | `racl_policies_i` | `spi_host_public_types_pkg::spi_host_racl_policies_i_t` |
| `input` | `passthrough_i` | `spi_host_public_types_pkg::spi_host_passthrough_i_t` |
| `input` | `cio_sd_i` | `logic [3:0]` |
| `output` | `tl_o` | `spi_host_public_types_pkg::spi_host_tl_o_t` |
| `output` | `alert_tx_o` | `spi_host_public_types_pkg::spi_host_alert_tx_o_t` |
| `output` | `racl_error_o` | `spi_host_public_types_pkg::spi_host_racl_error_o_t` |
| `output` | `cio_sck_o` | `logic` |
| `output` | `cio_sck_en_o` | `logic` |
| `output` | `cio_csb_o` | `logic [NumCS-1:0]` |
| `output` | `cio_csb_en_o` | `logic [NumCS-1:0]` |
| `output` | `cio_sd_o` | `logic [3:0]` |
| `output` | `cio_sd_en_o` | `logic [3:0]` |
| `output` | `passthrough_o` | `spi_host_public_types_pkg::spi_host_passthrough_o_t` |
| `output` | `lsio_trigger_o` | `logic` |
| `output` | `intr_error_o` | `logic` |
| `output` | `intr_spi_event_o` | `logic` |

## Supporting SV Files

- `spec/interface/spi_host_public_if.sv`
- `spec/interface/spi_host_public_regs_pkg.sv`
- `spec/interface/spi_host_public_tlul_pkg.sv`
- `spec/interface/spi_host_public_types_pkg.sv`
