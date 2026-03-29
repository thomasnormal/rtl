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
