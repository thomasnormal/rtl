# Chapter 7 - Assertion Plan

## 7.1 Assertion Plan Overview

The assertion plan describes how the environment uses SystemVerilog assertions to validate the
behavior of the design continuously during verification.

### 7.1.1 What Are Assertions?

- Assertions specify required behavior of the system.
- They are verification constructs that monitor an implementation for compliance with the
  specification.
- They can be used to prove, assume, or count properties in formal tools.
- They help detect functional bugs early in the design cycle.
- They can be used in simulation, formal verification, and emulation.

### 7.1.2 Why Use Assertions?

- To validate design behavior automatically.
- To detect bugs early and localize their source faster.
- To contribute functional-coverage evidence.
- To flag invalid input stimulus that violates assumptions.
- To enable automated property checking in formal flows.

### 7.1.3 Benefits of Assertions

- Improved design observability
- Improved debug speed
- Improved documentation of intended behavior

## 7.2 Template of Assertion Plan

![Figure 7.1: checkHaddrAlignment Assertion](figures/figure-045.png)

*Figure 7.1: checkHaddrAlignment Assertion*

The document says the assertion-plan template itself is kept in an Excel sheet and referenced as
`AHB Assertion Plan`.

## 7.3 Master Assertion Condition

### 7.3.1 `checkHaddrAlignment`

The `checkHaddrAlignment` property is evaluated on `posedge hclk` and is disabled while
`hresetn` is low. When `hready` is high, `htrans` is not `IDLE`, `hburst` is not `SINGLE`, and
`hsize` is not `BYTE`, the property checks that `HADDR` is aligned to the transfer size:

- `HALFWORD`: `haddr[0]` must be `0`
- `WORD`: `haddr[1:0]` must be `00`

If the alignment requirement is not met, the assertion raises an error.

![Figure 7.2: checkStrobe Assertion](figures/figure-046.png)

*Figure 7.2: checkStrobe Assertion*

### 7.3.2 `checkStrobe`

The `checkStrobe` property also evaluates on `posedge hclk` and is disabled during reset.
Whenever `htrans` is not `IDLE`, it checks `hwstrb` against `hsize`:

- `BYTE`: exactly 1 strobe bit set
- `HALFWORD`: exactly 2 strobe bits set
- `WORD`: exactly 4 strobe bits set

If the strobe pattern does not match the transfer size, the assertion fails.

## 7.4 Slave Assertion Condition

![Figure 7.3: checkHrespOKayForValid Assertion](figures/figure-047-1.png)

*Figure 7.3: checkHrespOKayForValid Assertion*

### 7.4.1 `checkHrespOKayForValid`

This property evaluates on `posedge hclk` and is disabled during reset. When `hreadyout` is
high and `htrans` is not `IDLE`, it checks that `hresp` is `0`, corresponding to an `OKAY`
response. A nonzero response causes the assertion to fail.

![Figure 7.4: checkSlaveHrdataValid Assertion](figures/figure-047-2.png)

*Figure 7.4: checkSlaveHrdataValid Assertion*

### 7.4.2 `checkSlaveHrdataValid`

When `hwrite` is low for a read transfer, `hreadyout` is high, `htrans` is not `IDLE`, and
`hselx` is asserted, the next clock cycle checks that `hreadyout` remains stable and that
`hrdata` is not unknown. If `hrdata` is invalid, the assertion fails.
