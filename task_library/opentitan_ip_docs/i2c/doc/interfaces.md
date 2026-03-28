# Interface Summary

The canonical machine-readable interface for `i2c` is defined in `spec/interface/`.
Use the SystemVerilog files there as the source of truth for port directions, packed types, parameters, and modports.

## Parameters

| Name | Default |
| --- | --- |
| `AlertAsyncOn` | `1'b1` |
| `AlertSkewCycles` | `1` |
| `InputDelayCycles` | `0` |
| `EnableRacl` | `1'b0` |
| `RaclErrorRsp` | `EnableRacl` |
| `RaclPolicySelVec` | `'0` |

## Ports

| Direction | Name | Type |
| --- | --- | --- |
| `input` | `clk_i` | `logic` |
| `input` | `rst_ni` | `logic` |
| `input` | `ram_cfg_i` | `i2c_public_types_pkg::i2c_ram_cfg_i_t` |
| `input` | `tl_i` | `i2c_public_types_pkg::i2c_tl_i_t` |
| `input` | `alert_rx_i` | `i2c_public_types_pkg::i2c_alert_rx_i_t` |
| `input` | `racl_policies_i` | `i2c_public_types_pkg::i2c_racl_policies_i_t` |
| `input` | `cio_scl_i` | `logic` |
| `input` | `cio_sda_i` | `logic` |
| `output` | `ram_cfg_rsp_o` | `i2c_public_types_pkg::i2c_ram_cfg_rsp_o_t` |
| `output` | `tl_o` | `i2c_public_types_pkg::i2c_tl_o_t` |
| `output` | `alert_tx_o` | `i2c_public_types_pkg::i2c_alert_tx_o_t` |
| `output` | `racl_error_o` | `i2c_public_types_pkg::i2c_racl_error_o_t` |
| `output` | `cio_scl_o` | `logic` |
| `output` | `cio_scl_en_o` | `logic` |
| `output` | `cio_sda_o` | `logic` |
| `output` | `cio_sda_en_o` | `logic` |
| `output` | `lsio_trigger_o` | `logic` |
| `output` | `intr_fmt_threshold_o` | `logic` |
| `output` | `intr_rx_threshold_o` | `logic` |
| `output` | `intr_acq_threshold_o` | `logic` |
| `output` | `intr_rx_overflow_o` | `logic` |
| `output` | `intr_controller_halt_o` | `logic` |
| `output` | `intr_scl_interference_o` | `logic` |
| `output` | `intr_sda_interference_o` | `logic` |
| `output` | `intr_stretch_timeout_o` | `logic` |
| `output` | `intr_sda_unstable_o` | `logic` |
| `output` | `intr_cmd_complete_o` | `logic` |
| `output` | `intr_tx_stretch_o` | `logic` |
| `output` | `intr_tx_threshold_o` | `logic` |
| `output` | `intr_acq_stretch_o` | `logic` |
| `output` | `intr_unexp_stop_o` | `logic` |
| `output` | `intr_host_timeout_o` | `logic` |

## Supporting SV Files

- `spec/interface/i2c_public_if.sv`
- `spec/interface/i2c_public_regs_pkg.sv`
- `spec/interface/i2c_public_tlul_pkg.sv`
- `spec/interface/i2c_public_types_pkg.sv`
