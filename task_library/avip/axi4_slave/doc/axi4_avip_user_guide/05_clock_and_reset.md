## 5. Clock and Reset

### 5.1 Clock (aclk)

All AXI4 signals are synchronized to the `aclk` clock signal. The AVIP operates on the positive edge of `aclk`.

### 5.2 Reset (aresetn)

The AXI4 reset signal `aresetn` is an active-low asynchronous reset. All operations are gated by the deassertion of reset (aresetn = 1).

Key behaviors:
- All valid signals must be deasserted when reset is active
- All ready signals are ignored during reset
- Upon reset deassertion, the AVIP begins normal operation

---
