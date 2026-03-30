# Chapter 6 - Verification Plan

![Figure 5.1: Verification plan template](figures/figure-042.png)

*Figure 5.1: Verification plan template*

## 6.1 Verification Plan

The verification plan defines what must be verified in the design under test and how the
verification strategy will demonstrate that the DUT features have been exercised. In practice,
the plan maps design features into measurable coverage goals and directed test scenarios.

## 6.2 Template of Verification Plan

The document states that the verification-plan template itself is maintained in an Excel sheet and
is referenced as `Ahb Verification Plan`.

## 6.3 Sections for Different Test Scenarios

### 6.3.1 Directed Tests

The directed tests provide explicit stimulus, run the design in simulation, and check the
behavior against expected outcomes. The test matrix in this chapter focuses on transaction types
and burst-transfer behavior.

| Sl. No. | Test Name | Description |
| ---: | --- | --- |
| 1 | `AhbWriteTest` | Verifies AHB write operation for burst types `WRAP4`, `INCR4`, `WRAP8`, `INCR8`, `WRAP16`, and `INCR16`. |
| 2 | `AhbReadTest` | Verifies AHB read operation for burst types `WRAP4`, `INCR4`, `WRAP8`, `INCR8`, `WRAP16`, and `INCR16`. |
| 3 | `AhbSingleWriteTest` | Verifies AHB write operation for `SINGLE` burst transfers. |
| 4 | `AhbSingleReadTest` | Verifies AHB read operation for `SINGLE` burst transfers. |
| 5 | `AhbWriteWithBusyTest` | Verifies AHB write operation with a `BUSY` transaction. |
| 6 | `AhbReadWithBusyTest` | Verifies AHB read operation with a `BUSY` transaction. |
| 7 | `AhbSingleWriteWithWaitStateTest` | Verifies AHB single-write transfers with wait states. |
| 8 | `AhbSingleReadWithWaitStateTest` | Verifies AHB single-read transfers with wait states. |
| 9 | `AhbWriteWithWaitStateTest` | Verifies burst-write operation with wait states. |
| 10 | `AhbReadWithWaitStateTest` | Verifies burst-read operation with wait states. |
