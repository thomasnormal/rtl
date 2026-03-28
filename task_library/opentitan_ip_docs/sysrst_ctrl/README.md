# System Reset Control Technical Specification

This task is presented as a standalone hardware-design problem. Use `spec/interface/` as the canonical boundary for `sysrst_ctrl`, and use `spec/micro_arch/` only when deeper verification compatibility is required.

# Overview

This document specifies the functionality of the System Reset Controller (`sysrst_ctrl`) that provides programmable hardware-level responses to trusted IOs and basic board-level reset sequencing capabilities.
These capabilities include keyboard and button combination-triggered actions, reset stretching for system-level reset signals, and internal reset / wakeup requests that go to the system reset and power-management logic.

## Features

The IP block implements the following features:

- Always-on: uses the always-on power and clock domain
- EC reset pulse duration control and stretching
- Keyboard and button combination (combo) triggered action
- AC_present can trigger interrupt
- Configuration registers can be set and locked until the next chip reset
- Pin output override

## Description

The `sysrst_ctrl` logic is very simple.
It looks up the configuration registers to decide how long the EC reset pulse duration and how long the key presses should be.
Also what actions to take (e.g. Interrupt, EC reset, target device reset request, disconnect the battery from the power tree).

The configuration programming interface is not based on any existing interface.
