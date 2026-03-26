# OpenTitan System Reset Controller

## Scope

Implement the top-level `sysrst_ctrl` peripheral.
This is an always-on control block that watches trusted IO pins, applies debounce and combo-detection rules, controls reset-related outputs, and generates wakeup / reset requests.

## Functional Requirements

- Operate across the main clock/reset and always-on clock/reset domains.
- Pass through the keyboard/button inputs to their corresponding outputs during normal operation, with optional inversion.
- Support programmable combo detection on button/key combinations held active for programmable durations.
- Support optional combo preconditions and per-combo actions.
- Supported actions include:
  - interrupt generation
  - wakeup request
  - reset request
  - EC reset pulse generation/stretching
  - battery disable output
- Support edge-based key/input interrupt detection on trusted inputs such as power button, keys, AC present, EC reset, and flash write protect.
- Support ultra-low-power wakeup behavior on selected input transitions.
- Keep `ec_rst_l` and `flash_wp_l` asserted low through reset until software explicitly releases them.
- Support lockable configuration and output override behavior.

## Interface Contract

The implementation must use top module name `sysrst_ctrl` and preserve the interface recorded in `task.json`.
Important ports:

- clocks/resets: `clk_i`, `clk_aon_i`, `rst_ni`, `rst_aon_ni`
- TL-UL device interface: `tl_i`, `tl_o`
- alert interface: `alert_rx_i`, `alert_tx_o`
- trusted inputs:
  - `cio_ac_present_i`
  - `cio_ec_rst_l_i`
  - `cio_key0_in_i`, `cio_key1_in_i`, `cio_key2_in_i`
  - `cio_pwrb_in_i`
  - `cio_lid_open_i`
  - `cio_flash_wp_l_i`
- outputs and enables:
  - `cio_bat_disable_o`
  - `cio_flash_wp_l_o`, `cio_flash_wp_l_en_o`
  - `cio_ec_rst_l_o`, `cio_ec_rst_l_en_o`
  - `cio_key0_out_o`, `cio_key0_out_en_o`
  - `cio_key1_out_o`, `cio_key1_out_en_o`
  - `cio_key2_out_o`, `cio_key2_out_en_o`
  - `cio_pwrb_out_o`, `cio_pwrb_out_en_o`
  - `cio_z3_wakeup_o`, `cio_z3_wakeup_en_o`
- wakeup/reset/interrupt outputs: `wkup_req_o`, `rst_req_o`, `intr_event_detected_o`

## Verification Expectations

A good implementation should be verifiable with:

- combo-detection tests with programmable debounce and hold times
- checks for wakeup and reset signaling side effects
- assertions that reset-default outputs such as `ec_rst_l` and `flash_wp_l` remain asserted until software release
- pin override and inversion tests
- edge-detect interrupt tests on the trusted inputs
- SVA checks for reset behavior, known-value outputs, and TL-UL protocol compliance

## Source References

These notes were curated from the local OpenTitan checkout:

- `~/opentitan/hw/ip/sysrst_ctrl/README.md`
- `~/opentitan/hw/ip/sysrst_ctrl/doc/interfaces.md`
- `~/opentitan/hw/ip/sysrst_ctrl/doc/theory_of_operation.md`
- `~/opentitan/hw/ip/sysrst_ctrl/dv/README.md`
- `~/opentitan/hw/ip/sysrst_ctrl/data/sysrst_ctrl.hjson`
- `~/opentitan/hw/ip/sysrst_ctrl/rtl/sysrst_ctrl.sv`
