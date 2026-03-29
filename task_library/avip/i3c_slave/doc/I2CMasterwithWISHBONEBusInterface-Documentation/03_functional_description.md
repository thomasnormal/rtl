## Functional Description

The I2C master core supports the critical features described in the I2C specification and is suitable for most applications involving I2C slave control. The design responds to the read/write cycles initiated by the microcontroller through the WISHBONE interface. It provides the correct sequences of commands and data to the I2C slave device and then transfers the required data from the I2C slave device through the two open-drain wires. The I2C master with WISHBONE interface offloads the microcontroller from needing to administrate many details of the I2C commands and operation sequences.

### Table 1. Pin Descriptions

| Signal | Width | Type | Description |
|--------|-------|------|-------------|
| **WISHBONE Interface** | | | |
| wb_clk_i | 1 | Input | Master clock |
| wb_rst_i | 1 | Input | Synchronous reset, active high |
| arst_i | 1 | Input | Asynchronous reset |
| wb_adr_i | 3 | Input | Lower address bits |
| wb_dat_i | 8 | Input | Data towards the core |
| wb_dat_o | 8 | Output | Data from the core |
| wb_we_i | 1 | Input | Write enable input |
| wb_stb_i | 1 | Input | Strobe signal/core select input |
| wb_cyc_i | 1 | Input | Valid bus cycle input |
| wb_ack_o | 1 | Output | Bus cycle acknowledge output |
| wb_inta_o | 1 | Output | Interrupt signal output |
| **I2C Interface** | | | |
| scl | 1 | Bidi | Serial clock line |
| sda | 1 | Bidi | Serial data line |

The signals ending in "_i" indicate an input and those ending in "_o" indicate an output. All signals on WISHBONE side are synchronous to the master clock. The two I2C wires, scl and sda, must be open-drain signals and are externally pulled up to Vcc through resistors.

---
