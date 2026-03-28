# Timer Specification

This task is presented as a standalone hardware-design problem. Use `spec/interface/` as the canonical boundary for `rv_timer`, and use `spec/micro_arch/` only when deeper verification compatibility is required.

# Overview

This document specifies RISC-V Timer hardware IP functionality.
system.

## Features

- 64-bit timer with 12-bit prescaler and 8-bit step register
- Compliant with RISC-V privileged specification v1.11
- Configurable number of timers per hart and number of harts

Note: Although the number of timers is indeed configurable, the implementation currently only connects up one timer for one hart.
## Description

The timer module provides a configurable number of 64-bit counters where each
counter increments by a step value whenever the prescaler times out. Each timer
generates an interrupt if the counter reaches (or is above) a programmed
value. The timer is intended to be used by the processors to check the current
time relative to the reset or the system power-on.

In this version, the timer doesn't consider low-power modes and
assumes the clock is neither turned off nor changed during runtime.

The timer IP provides memory-mapped registers equivalent to `mtime` and `mtimecmp` which can
be used as the machine-mode timer registers defined in the RISC-V privileged
timers and harts have been added.
