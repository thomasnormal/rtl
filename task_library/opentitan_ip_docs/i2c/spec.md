# OpenTitan I2C

## Scope

Implement the top-level OpenTitan `i2c` peripheral.
This block combines controller-mode and target-mode I2C behavior behind a TL-UL programming interface.
The task is centered on the public top module and externally visible protocol behavior.

## Functional Requirements

- Support bidirectional `SCL` and `SDA` signaling through separate input, output, and output-enable controls.
- Support both controller mode and target mode, enabled at runtime through control registers.
- In controller mode:
  - issue START, repeated START, STOP, read, and write sequences
  - support 7-bit addressing
  - support ACK/NACK handling
  - support bus arbitration detection and clock stretching
  - halt on exceptional conditions such as unexpected NACK or lost arbitration until software clears the condition
- In target mode:
  - match configured target addresses using address/mask registers
  - acquire address, R/W bit, and received data into the ACQ path
  - source read data from the TX path
  - support target-side clock stretching when FIFOs or control state require it
  - support programmable ACK/NACK control
- Support multi-controller monitoring and bus-free detection when enabled.
- Expose controller/target FIFO watermark and exception conditions through the interrupt outputs.
- `lsio_trigger_o` should align with DMA-relevant FIFO threshold behavior.
- Respect the `InputDelayCycles` parameter as part of the internal timing model.

## Interface Contract

The implementation must use top module name `i2c` and preserve the interface recorded in `task.json`.
Important ports:

- clocks/reset: `clk_i`, `rst_ni`
- TL-UL device interface: `tl_i`, `tl_o`
- alert and policy ports: `alert_rx_i`, `alert_tx_o`, `racl_policies_i`, `racl_error_o`
- RAM configuration sideband: `ram_cfg_i`, `ram_cfg_rsp_o`
- bidirectional pin controls:
  - `cio_scl_i`, `cio_scl_o`, `cio_scl_en_o`
  - `cio_sda_i`, `cio_sda_o`, `cio_sda_en_o`
- interrupt outputs for FIFO thresholds, overflow, controller halt, interference, timeout, unexpected stop, and command completion

## Verification Expectations

A good implementation should be verifiable with:

- directed controller-mode transfers covering START, repeated START, STOP, read, and write
- target-mode sequences that check address matching, ACQ/TX FIFO behavior, and clock stretching
- arbitration and NACK handling tests
- SVA checks for bus protocol invariants, output-enable correctness, and reset behavior
- UVM scoreboarding between programmed format/data FIFOs and observed I2C transactions

## Source References

These notes were curated from the local OpenTitan checkout:

- `~/opentitan/hw/ip/i2c/README.md`
- `~/opentitan/hw/ip/i2c/doc/interfaces.md`
- `~/opentitan/hw/ip/i2c/doc/theory_of_operation.md`
- `~/opentitan/hw/ip/i2c/dv/README.md`
- `~/opentitan/hw/ip/i2c/data/i2c.hjson`
- `~/opentitan/hw/ip/i2c/rtl/i2c.sv`
