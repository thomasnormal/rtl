# UART Specification

This task is presented as a standalone hardware-design problem. Use `spec/interface/` as the canonical boundary for `uart`, and use `spec/micro_arch/` only when deeper verification compatibility is required.

# Overview

This document specifies UART hardware IP functionality.

## Features

- 2-pin full duplex external interface
- 8-bit data word, optional even or odd parity bit per byte
- 1 stop bit
- 64 x 8b RX buffer
- 32 x 8b TX buffer
- Programmable baud rate
- Interrupt for transmit empty, receive overflow, frame error, parity error, break error, receive
  timeout

## Description

The UART module is a serial-to-parallel receive (RX) and parallel-to-serial
(TX) full duplex design intended to communicate to an outside device, typically
for basic terminal-style communication. It is programmed to run at a particular
baud rate and contains only a transmit and receive signal to the outside world,
i.e. no synchronizing clock. The programmable baud rate guarantees to be met up
to 1Mbps.
