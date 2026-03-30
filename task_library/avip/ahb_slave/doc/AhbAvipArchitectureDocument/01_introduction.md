# Chapter 1 - Introduction

The Advanced High-Performance Bus (AHB) is part of ARM's Advanced Microcontroller Bus
Architecture (AMBA) family. It defines a high-performance bus interface for efficient,
high-speed communication between system components such as CPUs, memory controllers, and
DMA engines.

## 1.1 Key Features

- Supports 32-bit and 64-bit address buses.
- Uses a pipelined structure for high-performance data transfers.
- Supports burst transfers for efficient block movement.
- Allows programmable wait states for slower slaves.
- Reports errors through the `HRESP` signal.
- Separates address and data phases for improved bus efficiency.
- Supports larger data widths, including 32-bit and 64-bit transfers.
- Fits high-bandwidth peripherals such as GPUs, memory subsystems, and accelerators.
