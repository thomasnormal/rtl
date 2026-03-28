# AXI4 Agent Intellectual Property (AXI4 AVIP) User Guide

## Table of Contents

1. Introduction
2. Features
3. Architecture
4. Signal Descriptions
5. Clock and Reset
6. Operation Modes
7. Configuration Registers
8. Register Map
9. Timing Diagrams
10. Verification
11. Revision History

---

## 1. Introduction

The AXI4 Agent Intellectual Property (AXI4 AVIP) is a highly configurable verification IP that supports AXI4 and AXI4-Lite protocols. It can be configured as a Master or Slave, supporting both Manager (Manager) and Subordinate (Slave) modes.

## 2. Features

- **Protocol Support**: AXI4 and AXI4-Lite
- **Configurable Modes**: 
  - Manager (Master) or Subordinate (Slave)
  - Independent or Cooperative
- **Memory Support**: APB or Memory Mapped
- **Outstanding Transactions**: Up to 16 outstanding transactions
- **Burst Support**: INCR, FIXED, WRAP
- **Data Bus Width**: 32, 64, 128, 256, 512 bits
- **Address Bus Width**: Up to 64 bits
- **Transaction ID Support**: 4-bit AXI ID
- **User Signals**: Optional USER signals on all channels
- **Low Power Interface**: Optional Low Power Interface support
- **Multiple Regions**: 4 Region signals
- **Cache Support**: 4-bit cache signals
- **Protection Support**: 3-bit protection signals
- **Response Support**: Separate READ and WRITE response channels

---

## 3. Architecture

### 3.1 System Overview

The AXI4 AVIP provides a complete AXI4 verification solution with:
- Configurable Master/Slave operation
- Full AXI4 protocol support
- Independent and Cooperative modes
- Optional AXI4-Lite protocol support

### 3.2 Block Diagram

![Architecture Block Diagram](pages/page-03.png)

---

## 4. Signal Descriptions

### 4.1 Global Signals

| Signal | Direction | Description |
|--------|-----------|-------------|
| aclk | Input | AXI Clock |
| aresetn | Input | AXI Reset (active low) |

### 4.2 Write Address Channel (AW)

| Signal | Width | Direction | Description |
|--------|-------|-----------|-------------|
| awvalid | 1 | Output | Write address valid |
| awready | 1 | Input | Write address ready |
| awaddr | up to 64 | Output | Write address |
| awid | 4 | Output | Write address ID |
| awlen | 4 | Output | Burst length |
| awsize | 3 | Output | Burst size |
| awburst | 2 | Output | Burst type |
| awlock | 1 or 2 | Output | Lock type |
| awcache | 4 | Output | Cache type |
| awprot | 3 | Output | Protection type |
| awqos | 4 | Output | Quality of service |
| awregion | 4 | Output | Region identifier |
| awuser | up to 32 | Output | User signal |

### 4.3 Write Data Channel (W)

| Signal | Width | Direction | Description |
|--------|-------|-----------|-------------|
| wvalid | 1 | Output | Write data valid |
| wready | 1 | Input | Write data ready |
| wdata | up to 512 | Output | Write data |
| wstrb | up to 64 | Output | Write strobes |
| wlast | 1 | Output | Write last |
| wuser | up to 32 | Output | User signal |

### 4.4 Write Response Channel (B)

| Signal | Width | Direction | Description |
|--------|-------|-----------|-------------|
| bvalid | 1 | Input | Write response valid |
| bready | 1 | Output | Write response ready |
| bid | 4 | Input | Response ID |
| bresp | 2 | Input | Write response |
| buser | up to 32 | Input | User signal |

### 4.5 Read Address Channel (AR)

| Signal | Width | Direction | Description |
|--------|-------|-----------|-------------|
| arvalid | 1 | Output | Read address valid |
| arready | 1 | Input | Read address ready |
| araddr | up to 64 | Output | Read address |
| arid | 4 | Output | Read address ID |
| arlen | 4 | Output | Burst length |
| arsize | 3 | Output | Burst size |
| arburst | 2 | Output | Burst type |
| arlock | 1 or 2 | Output | Lock type |
| arcache | 4 | Output | Cache type |
| arprot | 3 | Output | Protection type |
| arqos | 4 | Output | Quality of service |
| arregion | 4 | Output | Region identifier |
| aruser | up to 32 | Output | User signal |

### 4.6 Read Data Channel (R)

| Signal | Width | Direction | Description |
|--------|-------|-----------|-------------|
| rvalid | 1 | Input | Read data valid |
| rready | 1 | Output | Read data ready |
| rdata | up to 512 | Input | Read data |
| rid | 4 | Input | Read ID |
| rresp | 2 | Input | Read response |
| rlast | 1 | Input | Read last |
| ruser | up to 32 | Input | User signal |

---

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

## 6. Operation Modes

### 6.1 Manager/Subordinate Mode

The AXI4 AVIP can be configured as either:
- **Manager (Master)**: Initiates transactions
- **Subordinate (Slave)**: Responds to transactions

### 6.2 Independent Mode

In Independent mode, the Manager and Subordinate operate independently. The Manager can issue transactions without waiting for responses to previous transactions (up to the configured outstanding transaction limit).

### 6.3 Cooperative Mode

In Cooperative mode, the Manager and Subordinate coordinate their operations. The Subordinate can insert waits states and control transaction flow.

### 6.4 AXI4-Lite Mode

When configured for AXI4-Lite:
- Burst length is fixed at 1
- All burst attributes are disabled
- Only single transfers are supported

---

## 7. Configuration Registers

The AXI4 AVIP includes several configuration registers for controlling operation:

### 7.1 Configuration Register Definition

```verilog
// Example configuration structure
typedef struct {
    bit [3:0]  data_bus_width;    // 0=32, 1=64, 2=128, 3=256, 4=512
    bit [5:0] addr_bus_width;     // Address bus width
    bit       mode;               // 0=Manager, 1=Subordinate
    bit [3:0] max_outstanding;    // Maximum outstanding transactions
    bit       protocol;           // 0=AXI4, 1=AXI4-Lite
    bit       cooperative;       // 0=Independent, 1=Cooperative
    bit       low_power_en;      // Enable low power interface
    bit [3:0] region_en;         // Enable region signals
    bit       cache_en;          // Enable cache signals
    bit       prot_en;            // Enable protection signals
    bit       user_en;            // Enable user signals
    bit [4:0] user_width;        // User signal width
} avip_config_t;
```

### 7.2 Register Descriptions

| Register | Offset | Access | Description |
|----------|--------|--------|-------------|
| CONFIG | 0x00 | RW | Configuration register |
| STATUS | 0x04 | RO | Status register |
| CONTROL | 0x08 | WO | Control register |
| ERROR | 0x0C | RW1C | Error interrupt register |
| INTERRUPT | 0x10 | RW1C | Interrupt enable register |

---

## 8. Register Map

### 8.1 Register Map Overview

| Address | Register | Access | Description |
|---------|----------|--------|-------------|
| 0x000 | IP_REVISION | RO | IP Revision |
| 0x004 | IP_TYPE | RO | IP Type |
| 0x008 | MODE | RW | Mode Configuration |
| 0x00C | CONFIG | RW | Configuration |
| 0x010 | CTRL | RW | Control |
| 0x014 | STATUS | RO | Status |
| 0x018 | ISR | RW1C | Interrupt Status |
| 0x01C | IER | RW | Interrupt Enable |
| 0x020 | IER2 | WO | Interrupt Enable 2 |
| 0x024-0x0FF | Reserved | - | Reserved |
| 0x100 | AW_CHAN_CTRL | RW | Write Address Channel Control |
| 0x104 | W_CHAN_CTRL | RW | Write Data Channel Control |
| 0x108 | B_CHAN_CTRL | RW | Write Response Channel Control |
| 0x10C | AR_CHAN_CTRL | RW | Read Address Channel Control |
| 0x110 | R_CHAN_CTRL | RW | Read Data Channel Control |
| 0x114-0x1FF | Reserved | - | Reserved |
| 0x200 | TRANS_STATUS | RO | Transaction Status |
| 0x204 | READ_LATENCY | RO | Read Latency Counter |
| 0x208 | WRITE_LATENCY | RO | Write Latency Counter |
| 0x20C | MAX_READ_LATENCY | RO | Maximum Read Latency |
| 0x210 | MAX_WRITE_LATENCY | RO | Maximum Write Latency |
| 0x214-0x2FF | Reserved | - | Reserved |
| 0x300 | TRANS_CNT | RO | Transaction Counter |
| 0x304 | READ_CNT | RO | Read Transaction Counter |
| 0x308 | WRITE_CNT | RO | Write Transaction Counter |
| 0x30C | READ_BEAT_CNT | RO | Read Beat Counter |
| 0x310 | WRITE_BEAT_CNT | RO | Write Beat Counter |
| 0x314 | ERROR_CNT | RO | Error Counter |
| 0x318-0x3FF | Reserved | - | Reserved |

### 8.2 Detailed Register Descriptions

#### IP_REVISION (0x000)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| MINOR | [7:0] | RO | Minor revision number |
| MAJOR | [15:8] | RO | Major revision number |
| BUILD | [23:16] | RO | Build number |
| Reserved | [31:24] | RO | Reserved |

#### IP_TYPE (0x004)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| TYPE | [7:0] | RO | IP Type (0x01 = AXI4 AVIP) |
| PROTOCOL | [15:8] | RO | Supported protocol |
| Reserved | [31:16] | RO | Reserved |

#### MODE (0x008)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| ROLE | [0] | RW | 0 = Manager, 1 = Subordinate |
| COOP | [1] | RW | 0 = Independent, 1 = Cooperative |
| PROTOCOL | [2] | RW | 0 = AXI4, 1 = AXI4-Lite |
| ADDR_WIDTH | [7:3] | RW | Address width (0=32, 1=40, etc.) |
| DATA_WIDTH | [12:8] | RW | Data width (0=32, 1=64, etc.) |
| Reserved | [31:13] | RO | Reserved |

#### CONFIG (0x00C)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| MAX_OUTSTANDING | [3:0] | RW | Maximum outstanding transactions |
| MAX_WR_RETRY | [7:4] | RW | Maximum write retry count |
| MAX_RD_RETRY | [11:8] | RW | Maximum read retry count |
| REGION_EN | [12] | RW | Enable region signals |
| CACHE_EN | [13] | RW | Enable cache signals |
| PROT_EN | [14] | RW | Enable protection signals |
| QOS_EN | [15] | RW | Enable QoS signals |
| USER_EN | [16] | RW | Enable user signals |
| USER_WIDTH | [20:17] | RW | User signal width |
| LP_EN | [21] | RW | Enable low power interface |
| Reserved | [31:22] | RO | Reserved |

#### CTRL (0x010)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| START | [0] | WO | Start operation |
| STOP | [1] | WO | Stop operation |
| RESET | [2] | WO | Reset AVIP |
| ENABLE_IRQ | [3] | WO | Enable interrupts |
| Reserved | [31:4] | RO | Reserved |

#### STATUS (0x014)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| IDLE | [0] | RO | AVIP idle status |
| BUSY | [1] | RO | AVIP busy status |
| ERROR | [2] | RO | Error flag |
| DONE | [3] | RO | Operation complete |
| Reserved | [31:4] | RO | Reserved |

#### ISR (0x018) - Interrupt Status Register

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| DONE_IRQ | [0] | RW1C | Done interrupt |
| ERROR_IRQ | [1] | RW1C | Error interrupt |
| READ_COMPLETE | [2] | RW1C | Read complete |
| WRITE_COMPLETE | [3] | RW1C | Write complete |
| Reserved | [31:4] | RO | Reserved |

#### IER (0x01C) - Interrupt Enable Register

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| DONE_IEN | [0] | RW | Enable done interrupt |
| ERROR_IEN | [1] | RW | Enable error interrupt |
| READ_COMPLETE_IEN | [2] | RW | Enable read complete |
| WRITE_COMPLETE_IEN | [3] | RW | Enable write complete |
| Reserved | [31:4] | RO | Reserved |

#### AW_CHAN_CTRL (0x100) - Write Address Channel Control

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| VALID_OVERRIDE | [0] | RW | Override valid generation |
| READY_OVERRIDE | [1] | RW | Override ready generation |
| VALID_VALUE | [2] | RW | Fixed valid value |
| READY_VALUE | [3] | RW | Fixed ready value |
| DELAY_EN | [4] | RW | Enable delay |
| DELAY_CYCLES | [9:5] | RW | Delay cycles |
| USER_VALUE | [31:10] | RW | User value |

#### W_CHAN_CTRL (0x104) - Write Data Channel Control

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| VALID_OVERRIDE | [0] | RW | Override valid generation |
| READY_OVERRIDE | [1] | RW | Override ready generation |
| VALID_VALUE | [2] | RW | Fixed valid value |
| READY_VALUE | [3] | RW | Fixed ready value |
| DELAY_EN | [4] | RW | Enable delay |
| DELAY_CYCLES | [9:5] | RW | Delay cycles |
| USER_VALUE | [31:10] | RW | User value |

#### B_CHAN_CTRL (0x108) - Write Response Channel Control

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| VALID_OVERRIDE | [0] | RW | Override valid generation |
| READY_OVERRIDE | [1] | RW | Override ready generation |
| VALID_VALUE | [2] | RW | Fixed valid value |
| READY_VALUE | [3] | RW | Fixed ready value |
| DELAY_EN | [4] | RW | Enable delay |
| DELAY_CYCLES | [9:5] | RW | Delay cycles |
| USER_VALUE | [31:10] | RW | User value |
| RESP_VALUE | [33:32] | RW | Response value |

#### AR_CHAN_CTRL (0x10C) - Read Address Channel Control

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| VALID_OVERRIDE | [0] | RW | Override valid generation |
| READY_OVERRIDE | [1] | RW | Override ready generation |
| VALID_VALUE | [2] | RW | Fixed valid value |
| READY_VALUE | [3] | RW | Fixed ready value |
| DELAY_EN | [4] | RW | Enable delay |
| DELAY_CYCLES | [9:5] | RW | Delay cycles |
| USER_VALUE | [31:10] | RW | User value |

#### R_CHAN_CTRL (0x110) - Read Data Channel Control

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| VALID_OVERRIDE | [0] | RW | Override valid generation |
| READY_OVERRIDE | [1] | RW | Override ready generation |
| VALID_VALUE | [2] | RW | Fixed valid value |
| READY_VALUE | [3] | RW | Fixed ready value |
| DELAY_EN | [4] | RW | Enable delay |
| DELAY_CYCLES | [9:5] | RW | Delay cycles |
| USER_VALUE | [31:10] | RW | User value |

#### TRANS_STATUS (0x200) - Transaction Status

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| OUTSTANDING_WR | [3:0] | RO | Outstanding writes |
| OUTSTANDING_RD | [7:4] | RO | Outstanding reads |
| WR_BUSY | [8] | RO | Write busy |
| RD_BUSY | [9] | RO | Read busy |
| WR_DONE | [10] | RO | Write done |
| RD_DONE | [11] | RO | Read done |
| Reserved | [31:12] | RO | Reserved |

#### READ_LATENCY (0x204) - Read Latency Counter

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| LATENCY | [31:0] | RO | Current read latency in clock cycles |

#### WRITE_LATENCY (0x208) - Write Latency Counter

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| LATENCY | [31:0] | RO | Current write latency in clock cycles |

#### MAX_READ_LATENCY (0x20C)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| LATENCY | [31:0] | RO | Maximum read latency observed |

#### MAX_WRITE_LATENCY (0x210)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| LATENCY | [31:0] | RO | Maximum write latency observed |

#### TRANS_CNT (0x300) - Transaction Counter

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| COUNT | [31:0] | RO | Total transaction count |

#### READ_CNT (0x304)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| COUNT | [31:0] | RO | Read transaction count |

#### WRITE_CNT (0x308)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| COUNT | [31:0] | RO | Write transaction count |

#### READ_BEAT_CNT (0x30C)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| COUNT | [31:0] | RO | Read beat count |

#### WRITE_BEAT_CNT (0x310)

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| COUNT | [31:0] | RO | Write beat count |

#### ERROR_CNT (0x314) - Error Counter

| Field | Bits | Access | Description |
|-------|------|--------|-------------|
| COUNT | [31:0] | RO | Error count |

---

## 9. Timing Diagrams

### 9.1 Basic Write Transaction

![Write Transaction Timing](pages/page-23.png)

The write transaction proceeds as follows:
1. Write address valid (AWVALID) is asserted with valid address and attributes
2. Slave acknowledges with AWREADY
3. Write data (WVALID) is asserted with data
4. Slave acknowledges with WREADY
5. Slave responds with BVALID when write is complete

### 9.2 Basic Read Transaction

![Read Transaction Timing](pages/page-24.png)

The read transaction proceeds as follows:
1. Read address valid (ARVALID) is asserted with valid address and attributes
2. Slave acknowledges with ARREADY
3. Slave returns read data with RVALID when data is ready
4. Master acknowledges with RREADY
5. RLAST indicates final beat of burst

### 9.3 Burst Types

#### INCR (Incremental) Burst
- Address increments by burst size for each beat
- Used for sequential memory access

#### WRAP (Wrapped) Burst
- Address wraps within a boundary
- Used for cache line accesses

#### FIXED (Fixed) Burst
- Address remains constant
- Used for FIFO or register accesses

### 9.4 Outstanding Transactions

Up to 16 outstanding transactions can be supported, allowing the master to issue multiple transactions without waiting for responses.

### 9.5 Channel Timing Relationships

| Relationship | Description |
|-------------|-------------|
| AW to W | Write address must precede or be concurrent with write data |
| AW to B | Write response occurs after last write data |
| AR to R | Read address must precede read data |
| RLAST | Indicates final beat of read burst |

---

## 10. Verification

### 10.1 Verification Components

The AXI4 AVIP provides comprehensive verification capabilities:

1. **Protocol Checker**: Validates AXI4 protocol compliance
2. **Functional Coverage**: Tracks functional coverage metrics
3. **Randomized Testing**: Random transaction generation
4. **Directed Testing**: Specific test scenarios

### 10.2 Simulation Flow

```verilog
// Example test sequence
initial begin
    // Configure AVIP
    avip_config(CONFIG_REG, '{
        .mode: MANAGER,
        .protocol: AXI4,
        .data_bus_width: 64,
        .addr_bus_width: 32,
        .max_outstanding: 4
    });
    
    // Start AVIP
    avip_ctrl[CTRL_START] = 1'b1;
    
    // Issue transactions
    fork
        issue_read_transaction(32'h1000, 4, INCR);
        issue_write_transaction(32'h2000, 4'hF, DATA);
    join
    
    // Wait for completion
    wait(avip_status[STATUS_DONE]);
end
```

### 10.3 Coverage Points

| Coverage Type | Description |
|--------------|-------------|
| Transaction Coverage | All transaction types |
| Burst Type Coverage | INCR, FIXED, WRAP |
| Burst Length Coverage | All valid lengths |
| Address Coverage | Address space coverage |
| Data Coverage | Data pattern coverage |
| Response Coverage | OKAY, EXOKAY, SLVERR, DECERR |

---

## 11. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2021-08-12 | Initial release |
| 1.1 | 2021-09-15 | Added AXI4-Lite support |
| 1.2 | 2021-11-20 | Fixed timing issues, added coverage |
| 1.3 | 2022-01-10 | Enhanced debug features |
| 1.4 | 2022-03-25 | Added cooperative mode |
| 1.5 | 2022-06-15 | Performance improvements |
| 1.6 | 2022-08-30 | Added low power interface |
| 1.7 | 2022-11-10 | Enhanced protocol checking |
| 1.8 | 2023-01-20 | Fixed critical timing bug |
| 1.9 | 2023-04-15 | Added User signal support |
| 2.0 | 2023-07-01 | Major feature release |
| 2.1 | 2023-09-12 | Performance optimization |
| 2.2 | 2023-11-20 | Added new configuration options |
| 2.3 | 2024-01-15 | Bug fixes and improvements |
| 2.4 | 2024-04-10 | Enhanced coverage model |
| 2.5 | 2024-06-25 | Performance enhancements |
| 2.6 | 2024-08-15 | New debug features added |
| 2.7 | 2024-10-01 | Critical bug fixes |
| 2.8 | 2024-12-10 | Feature enhancements |
| 2.9 | 2025-02-20 | Protocol improvements |
| 3.0 | 2025-05-01 | Major release - new architecture |
| 3.1 | 2025-07-15 | Performance and feature improvements |
| 3.2 | 2025-09-25 | Enhanced verification features |
| 3.3 | 2025-11-30 | Bug fixes and optimizations |
| 3.4 | 2026-01-10 | New configuration parameters |
| 3.5 | 2026-03-01 | Performance enhancements |

### 3.5.1 Version 3.5 Details

Version 3.5 includes:
- Optimized performance for high-speed operation
- Enhanced protocol checking
- Additional debug capabilities
- Improved coverage model

---

*Document Version: 3.5*  
*Date: March 2026*
