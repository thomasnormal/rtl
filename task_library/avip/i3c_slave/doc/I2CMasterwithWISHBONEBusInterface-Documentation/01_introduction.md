## Introduction

The I2C (Inter-IC Communication) bus has become an industrial de-facto standard for short-distance communication among ICs since its introduction in the early 1980s. The I2C bus uses two bidirectional open-drain wires with pull-up resistors. There is no strict baud rate requirement as with other communication standards. The true multi-master bus allows protection of data corruption if multiple masters initiate data transfer at the same time. These, and many other features of the I2C bus, provide efficient and flexible means for control functions that do not require high speed data transfer, and for applications that require a small amount of data exchanges.

Implementing the I2C bus master in an FPGA adds the popular communication interface to components that do not have I2C interface integrated on chip. At the same time, the FPGA frees up the on-board microcontroller for heavier tasks in the system.

The WISHBONE Bus interface is a free, open-source standard that is gaining popularity in digital systems that require usage of IP cores. This bus interface encourages IP reuse by defining a common interface among IP cores. That in turn provides portability for the system, speeds up time to market, and reduces cost for the end products.

This document and the design are based on the OpenCores I2C master core, which was used as a peripheral component for the LatticeMico32™ IP core (see the I2C-Master Core Specification from OpenCores for further information). The design provides a bridge between the I2C bus and the WISHBONE bus. A typical application of this design includes the interface between a WISHBONE compliant on-board microcontroller and multiple I2C peripheral components. The I2C master core generates the clock and is responsible for the initiation and termination of each data transfer.

Both Verilog and VHDL versions of the reference design are available. Lattice design tools are used for synthesis, place and route and simulation. The design can be targeted to multiple Lattice device families.
