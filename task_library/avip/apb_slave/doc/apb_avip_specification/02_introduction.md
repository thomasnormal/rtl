# Chapter 1 Introduction

This chapter provides an overview of the APB protocol. It contains the following sections:

- *About the APB protocol* on page 1-2
- *APB revisions* on page 1-3.

## 1.1 About the APB protocol

The *Advanced Peripheral Bus* (APB) is part of the *Advanced Microcontroller Bus Architecture* (AMBA) protocol family. It defines a low-cost interface that is optimized for minimal power consumption and reduced interface complexity.

The APB protocol is not pipelined, use it to connect to low-bandwidth peripherals that do not require the high performance of the AXI protocol.

The APB protocol relates a signal transition to the rising edge of the clock, to simplify the integration of APB peripherals into any design flow. Every transfer takes at least two cycles.

The APB can interface with:

- AMBA *Advanced High-performance Bus* (AHB)
- AMBA *Advanced High-performance Bus Lite* (AHB-Lite)
- AMBA *Advanced Extensible Interface* (AXI)
- AMBA *Advanced Extensible Interface Lite* (AXI4-Lite)

You can use it to access the programmable control registers of peripheral devices.

## 1.2 APB revisions

The *APB Specification Rev E*, released in 1998, is now obsolete and is superseded by the following three revisions:

- AMBA 2 APB Specification
- AMBA 3 APB Protocol Specification v1.0
- AMBA APB Protocol Specification v2.0.

### 1.2.1 AMBA 2 APB Specification

The AMBA 2 APB Specification is detailed in *AMBA Specification Rev 2* (ARM IHI 0011A).

This specification defines the interface signals, the basic read and write transfers, and the two APB components the APB bridge and the APB slave.

This version of the specification is referred to as APB2.

### 1.2.2 AMBA 3 APB Protocol Specification v1.0

The *AMBA 3 APB Protocol Specification v1.0* defines the following additional functionality:

- Wait states. See Chapter 3 *Transfers*.
- Error reporting. See *Error response* on page 3-6.

The following interface signals support this functionality:

- **PREADY** — A ready signal to indicate completion of an APB transfer.
- **PSLVERR** — An error signal to indicate the failure of a transfer.

This version of the specification is referred to as APB3.

### 1.2.3 AMBA APB Protocol Specification v2.0

The *AMBA APB Protocol Specification v2.0* defines the following additional functionality:

- Transaction protection. See *Protection unit support* on page 3-8.
- Sparse data transfer. See *Write strobes* on page 3-4.

The following interface signals support this functionality:

- **PPROT** — A protection signal to support both non-secure and secure transactions on APB.
- **PSTRB** — A write strobe signal to enable sparse data transfer on the write data bus.

This version of the specification is referred to as APB4.
