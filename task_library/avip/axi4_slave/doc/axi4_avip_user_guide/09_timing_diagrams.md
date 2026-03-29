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
