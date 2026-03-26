# OpenTitan DMA

## Scope

Implement the top-level `dma` peripheral.
This is a single-channel DMA controller that can move data across multiple address spaces, optionally in hardware-handshake mode and optionally with inline hashing.

## Functional Requirements

- Accept configuration and control over a TL-UL device interface.
- Act as a bus master on the OpenTitan internal TL-UL host port, the control-network TL-UL host port, and the system-bus interface.
- Support one transfer at a time.
- Support transfer directions:
  - memory to memory
  - memory to peripheral
  - peripheral to memory
- Support source and destination addressing modes:
  - incrementing
  - fixed
  - wrapping/chunked
- Support 1-byte, 2-byte, and 4-byte transfer granularities.
- Support chunked transfer completion and full-transfer completion interrupts.
- Support hardware-handshake mode using `lsio_trigger_i` for low-speed peripherals such as UART, I2C, SPI host, and SPI device.
- Perform the documented access checks and isolation behavior around DMA-enabled OpenTitan memory.
- Support optional inline hashing modes flowing data through SHA2 logic while the transfer proceeds.
- Report completion and error status via `intr_dma_done_o`, `intr_dma_chunk_done_o`, and `intr_dma_error_o`.

## Interface Contract

The implementation must use top module name `dma` and preserve the interface recorded in `task.json`.
Important ports:

- clock/reset: `clk_i`, `rst_ni`
- scan / trigger sidebands: `scanmode_i`, `lsio_trigger_i`
- alert and policy ports: `alert_rx_i`, `alert_tx_o`, `racl_policies_i`, `racl_error_o`
- configuration TL-UL device interface: `tl_d_i`, `tl_d_o`
- OpenTitan/control-network/system master-side interfaces:
  - `ctn_tl_h2d_o`, `ctn_tl_d2h_i`
  - `host_tl_h_o`, `host_tl_h_i`
  - `sys_o`, `sys_i`
- interrupts: `intr_dma_done_o`, `intr_dma_chunk_done_o`, `intr_dma_error_o`

## Verification Expectations

A good implementation should be verifiable with:

- memory-transfer tests covering incrementing, fixed, and wrapping source/destination modes
- handshake-mode tests that emulate low-speed FIFO service
- checks for correct chunk accounting, final completion, and error reporting
- scoreboarding of read and write traffic on every master port
- SVA checks for TL-UL protocol compliance, reset-known outputs, and legal state-machine progression
- optional end-to-end checks on inline hashing results

## Source References

These notes were curated from the local OpenTitan checkout:

- `~/opentitan/hw/ip/dma/README.md`
- `~/opentitan/hw/ip/dma/doc/interfaces.md`
- `~/opentitan/hw/ip/dma/doc/theory_of_operation.md`
- `~/opentitan/hw/ip/dma/dv/README.md`
- `~/opentitan/hw/ip/dma/data/dma.hjson`
- `~/opentitan/hw/ip/dma/rtl/dma.sv`
