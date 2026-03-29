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
