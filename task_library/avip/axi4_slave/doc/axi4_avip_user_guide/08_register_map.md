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
