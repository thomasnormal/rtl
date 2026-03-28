# Interface Summary

The canonical machine-readable interface for `sysrst_ctrl` is defined in `spec/interface/`.
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
| `input` | `tl_i` | `sysrst_ctrl_public_types_pkg::sysrst_ctrl_tl_i_t` |
| `input` | `alert_rx_i` | `sysrst_ctrl_public_types_pkg::sysrst_ctrl_alert_rx_i_t` |
| `input` | `cio_ac_present_i` | `logic` |
| `input` | `cio_ec_rst_l_i` | `logic` |
| `input` | `cio_key0_in_i` | `logic` |
| `input` | `cio_key1_in_i` | `logic` |
| `input` | `cio_key2_in_i` | `logic` |
| `input` | `cio_pwrb_in_i` | `logic` |
| `input` | `cio_lid_open_i` | `logic` |
| `input` | `cio_flash_wp_l_i` | `logic` |
| `output` | `tl_o` | `sysrst_ctrl_public_types_pkg::sysrst_ctrl_tl_o_t` |
| `output` | `alert_tx_o` | `sysrst_ctrl_public_types_pkg::sysrst_ctrl_alert_tx_o_t` |
| `output` | `wkup_req_o` | `logic` |
| `output` | `rst_req_o` | `logic` |
| `output` | `intr_event_detected_o` | `logic` |
| `output` | `cio_bat_disable_o` | `logic` |
| `output` | `cio_flash_wp_l_o` | `logic` |
| `output` | `cio_ec_rst_l_o` | `logic` |
| `output` | `cio_key0_out_o` | `logic` |
| `output` | `cio_key1_out_o` | `logic` |
| `output` | `cio_key2_out_o` | `logic` |
| `output` | `cio_pwrb_out_o` | `logic` |
| `output` | `cio_z3_wakeup_o` | `logic` |
| `output` | `cio_bat_disable_en_o` | `logic` |
| `output` | `cio_flash_wp_l_en_o` | `logic` |
| `output` | `cio_ec_rst_l_en_o` | `logic` |
| `output` | `cio_key0_out_en_o` | `logic` |
| `output` | `cio_key1_out_en_o` | `logic` |
| `output` | `cio_key2_out_en_o` | `logic` |
| `output` | `cio_pwrb_out_en_o` | `logic` |
| `output` | `cio_z3_wakeup_en_o` | `logic` |

## Supporting SV Files

- `spec/interface/sysrst_ctrl_public_if.sv`
- `spec/interface/sysrst_ctrl_public_regs_pkg.sv`
- `spec/interface/sysrst_ctrl_public_tlul_pkg.sv`
- `spec/interface/sysrst_ctrl_public_types_pkg.sv`
