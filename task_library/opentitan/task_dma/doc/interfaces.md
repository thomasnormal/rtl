# Interface Summary

The canonical machine-readable interface for `dma` is defined in `spec/interface/`.
Use the SystemVerilog files there as the source of truth for port directions, packed types, parameters, and modports.

## Parameters

| Name | Default |
| --- | --- |
| `AlertAsyncOn` | `1'b1` |
| `AlertSkewCycles` | `1` |
| `EnableDataIntgGen` | `1'b1` |
| `EnableRspDataIntgCheck` | `1'b1` |
| `TlUserRsvd` | `'0` |
| `SysRaclRole` | `'0` |
| `OtAgentId` | `0` |
| `EnableRacl` | `1'b0` |
| `RaclErrorRsp` | `EnableRacl` |
| `RaclPolicySelVec` | `'0` |

## Ports

| Direction | Name | Type |
| --- | --- | --- |
| `input` | `clk_i` | `logic` |
| `input` | `rst_ni` | `logic` |
| `input` | `scanmode_i` | `dma_public_types_pkg::dma_scanmode_i_t` |
| `input` | `lsio_trigger_i` | `dma_public_types_pkg::dma_lsio_trigger_i_t` |
| `input` | `alert_rx_i` | `dma_public_types_pkg::dma_alert_rx_i_t` |
| `input` | `racl_policies_i` | `dma_public_types_pkg::dma_racl_policies_i_t` |
| `input` | `tl_d_i` | `dma_public_types_pkg::dma_tl_d_i_t` |
| `input` | `ctn_tl_d2h_i` | `dma_public_types_pkg::dma_ctn_tl_d2h_i_t` |
| `input` | `host_tl_h_i` | `dma_public_types_pkg::dma_host_tl_h_i_t` |
| `input` | `sys_i` | `dma_public_types_pkg::dma_sys_i_t` |
| `output` | `intr_dma_done_o` | `logic` |
| `output` | `intr_dma_chunk_done_o` | `logic` |
| `output` | `intr_dma_error_o` | `logic` |
| `output` | `alert_tx_o` | `dma_public_types_pkg::dma_alert_tx_o_t` |
| `output` | `racl_error_o` | `dma_public_types_pkg::dma_racl_error_o_t` |
| `output` | `tl_d_o` | `dma_public_types_pkg::dma_tl_d_o_t` |
| `output` | `ctn_tl_h2d_o` | `dma_public_types_pkg::dma_ctn_tl_h2d_o_t` |
| `output` | `host_tl_h_o` | `dma_public_types_pkg::dma_host_tl_h_o_t` |
| `output` | `sys_o` | `dma_public_types_pkg::dma_sys_o_t` |

## Supporting SV Files

- `spec/interface/dma_public_if.sv`
- `spec/interface/dma_public_regs_pkg.sv`
- `spec/interface/dma_public_tlul_pkg.sv`
- `spec/interface/dma_public_types_pkg.sv`
