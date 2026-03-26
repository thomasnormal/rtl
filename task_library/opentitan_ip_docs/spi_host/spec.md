# OpenTitan SPI Host

## Scope

Implement the top-level `spi_host` peripheral.
This is a programmable SPI master oriented toward NOR flash and similar external devices, with segmented command execution and automatic chip-select control.

## Functional Requirements

- Drive SPI transactions over `SCK`, `CSB`, and `SD[3:0]`.
- Support the four standard CPOL/CPHA combinations and configurable chip-select timing.
- Support segmented commands where each segment has its own:
  - direction (`Tx`, `Rx`, `Bidir`, or dummy/none)
  - width/speed mode (`Std`, `Dual`, `Quad`)
  - byte length
  - chip-select hold behavior (`CSAAT`)
- Permit multi-segment transactions by keeping chip select asserted across intermediate segments.
- Support both TX and RX FIFOs and expose watermark / readiness / error behavior through interrupts and status.
- Support pass-through coordination with the SPI device path through `passthrough_i` / `passthrough_o`.
- `lsio_trigger_o` should reflect DMA-relevant RX/TX FIFO threshold status.
- The public parameter `NumCS` controls the width of the chip-select outputs.

## Interface Contract

The implementation must use top module name `spi_host` and preserve the interface recorded in `task.json`.
Important ports:

- clocks/reset: `clk_i`, `rst_ni`
- TL-UL device interface: `tl_i`, `tl_o`
- alert and policy ports: `alert_rx_i`, `alert_tx_o`, `racl_policies_i`, `racl_error_o`
- SPI pins:
  - `cio_sck_o`, `cio_sck_en_o`
  - `cio_csb_o`, `cio_csb_en_o`
  - `cio_sd_i`, `cio_sd_o`, `cio_sd_en_o`
- pass-through interface: `passthrough_i`, `passthrough_o`
- interrupts: `intr_error_o`, `intr_spi_event_o`

## Verification Expectations

A good implementation should be verifiable with:

- directed segment sequences for Standard, Dual, and Quad modes
- checks for chip-select lead/trail/idle timing and `CSAAT` behavior
- scoreboarding between programmed segments and observed SPI waveforms
- FIFO underflow / overflow / invalid-command tests
- SVA checks for TL-UL compliance, reset-known outputs, and valid IO direction switching between TX and RX phases
- optional UVM agent-based decoding of SPI transactions

## Source References

These notes were curated from the local OpenTitan checkout:

- `~/opentitan/hw/ip/spi_host/README.md`
- `~/opentitan/hw/ip/spi_host/doc/interfaces.md`
- `~/opentitan/hw/ip/spi_host/doc/theory_of_operation.md`
- `~/opentitan/hw/ip/spi_host/dv/README.md`
- `~/opentitan/hw/ip/spi_host/data/spi_host.hjson`
- `~/opentitan/hw/ip/spi_host/rtl/spi_host.sv`
