# OpenTitan UART

## Scope

Implement the top-level OpenTitan UART peripheral `uart`.
This is a TL-UL controlled UART with one receive pin and one transmit pin.
The task is not to rebuild the entire OpenTitan repository structure around it; the target is the RTL for the public top module and its externally visible behavior.

## Functional Requirements

- Provide a full-duplex UART with one RX input and one TX output.
- Transmit frames start from idle-high, emit a start bit (`0`), then 8 data bits least-significant-bit first, an optional parity bit, and one stop bit (`1`).
- The transmit path accepts bytes through the register interface and drains a TX FIFO.
- The receive path oversamples the RX line, detects the start bit, samples data near the center of each bit period, and pushes valid bytes into an RX FIFO.
- Support programmable baud-rate generation via the control register NCO.
- Support optional parity checking on receive and parity generation on transmit.
- Detect and report receive errors:
  - frame error
  - break error
  - parity error
  - RX timeout
  - RX overflow
- Expose FIFO and transfer progress through the status and interrupt outputs:
  - `intr_tx_watermark_o`
  - `intr_tx_empty_o`
  - `intr_rx_watermark_o`
  - `intr_tx_done_o`
  - error-related receive interrupts
- `tx_watermark`, `tx_empty`, and `rx_watermark` are level-style status interrupts, while events such as `tx_done` and error conditions are edge/event style.
- `lsio_trigger_o` should reflect DMA-relevant FIFO watermark status.

## Interface Contract

The implementation must use top module name `uart` and preserve the public OpenTitan-style interface documented in `task.json`.
Important ports:

- clocks/resets: `clk_i`, `rst_ni`
- bus device interface: `tl_i`, `tl_o`
- alert interface: `alert_rx_i`, `alert_tx_o`
- policy/logging interface: `racl_policies_i`, `racl_error_o`
- serial pins: `cio_rx_i`, `cio_tx_o`, `cio_tx_en_o`
- DMA/status output: `lsio_trigger_o`
- interrupt outputs for TX/RX watermarks, TX completion, RX overflow, RX frame/break/timeout/parity errors

## Verification Expectations

A good implementation should be verifiable with:

- CSR/TL-UL traffic that configures baud rate, parity, and FIFO thresholds
- directed or random serial stimulus on `cio_rx_i`
- checks for start/data/parity/stop framing on `cio_tx_o`
- FIFO watermark and empty interrupt checks
- SVA checks for known-value outputs after reset and TL-UL protocol correctness
- optional UVM scoreboarding of register traffic against UART line activity

## Source References

These notes were curated from the local OpenTitan checkout:

- `~/opentitan/hw/ip/uart/README.md`
- `~/opentitan/hw/ip/uart/doc/interfaces.md`
- `~/opentitan/hw/ip/uart/doc/theory_of_operation.md`
- `~/opentitan/hw/ip/uart/dv/README.md`
- `~/opentitan/hw/ip/uart/data/uart.hjson`
- `~/opentitan/hw/ip/uart/rtl/uart.sv`
