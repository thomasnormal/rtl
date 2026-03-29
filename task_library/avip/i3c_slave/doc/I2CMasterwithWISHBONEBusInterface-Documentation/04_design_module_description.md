## Design Module Description

The design has four main modules as shown in Figure 1. These include one top-level module and three lower-level modules, which are the register module, the byte command module and a bit command module.

Figure 1 in the source PDF shows the four main modules and their hierarchy.

### Top-level Module (i2c_master_top.v)

In addition to connecting all the functional blocks together, this module generates byte-wide data, acknowledgement, and interrupt for the WISHBONE interface. Depending on the parameter ARST_LVL, the reset polarity is determined and distributed to all the modules.

### Internal Registers Module (i2c_master_registers.v)

A 2-bit by 8-bit register space constitutes the internal register structure of the I2C core. The space houses the six 8-bit registers listed in Table 2. The addresses not used are reserved for future expansion of the core.

### Table 2. Internal Register List

| Name | Address | Width | Access | Description |
|------|---------|-------|--------|-------------|
| PRERlo | 0x00 | 8 | RW | Clock Prescale register lo-byte |
| PRERhi | 0x01 | 8 | RW | Clock Prescale register hi-byte |
| CTR | 0x02 | 8 | RW | Control register |
| TXR | 0x03 | 8 | W | Transmit register |
| RXR | 0x03 | 8 | R | Receive register |
| CR | 0x04 | 8 | W | Command register |
| SR | 0x04 | 8 | R | Status register |

The Prescale Register (address = 0x00 and 0x01) is used to prescale the scl clock line based on the master clock. Since the design is driven by a (5 × scl frequency) internally, the prescale register is programmed according to the equation [master clock frequency / (5 × (sclk frequency)) - 1]. The content of this register can only be modified when the core is not enabled.

Only two bits of the Control Register (address = 0x02) are used for this design. The MSB of this register is the most critical one because it enables or disables the entire I2C core. The core will not respond to any command unless this bit is set.

The Transmit Register and the Receive Register share the same address (address = 0x03) depending on the direction of data transfer. The data to be transmitted via I2C will be stored in the Transmit Register, while the byte received via I2C is available in the Receive register.

The Status Register and the Command Register share the same address (address = 0x04). The Status Register allows the monitoring of the I2C operations, while the Command Register stores the next command for the next I2C operation. Unlike the rest of the registers, the bits in the Command Register are cleared automatically after each operation. Therefore this register has to be written for each start, write, read, or stop of the I2C operation. Table 3 provides a detailed description of each bit in the internal registers.

### Table 3. Description of Internal Register Bits

| Internal Register | Bit # | Access | Description |
|-------------------|-------|--------|-------------|
| **Control Register (0x02)** | | | |
| | 7 | RW | EN, I2C core enable bit. '1' = the core is enabled; '0' = the core is disabled. |
| | 6 | RW | IEN, I2C core interrupt enable bit. '1' = interrupt is enabled; '0' = interrupt is disabled. |
| | 5:0 | RW | Reserved |
| **Transmit Register (0x03)** | | | |
| | 7:1 | W | Next byte to be transmitted via I2C |
| | 0 | W | This bit represents the RW bit during slave address transfer: '1' = reading from slave; '0' = writing to slave |
| **Receive Register (0x03)** | 7:0 | R | Last byte received via I2C |
| **Status Register (0x04)** | | | |
| | 7 | R | RxACK, Received acknowledge from slave. '1' = No acknowledge received; '0' = Acknowledge received |
| | 6 | R | Busy, indicates the I2C bus busy. '1' = START signal is detected; '0' = STOP signal is detected |
| | 5 | R | AL, Arbitration lost. This bit is set when the core lost arbitration. |
| | 4:2 | R | Reserved |
| | 1 | R | TIP, Transfer in progress. '1' = transferring data; '0' = transfer is completed |
| | 0 | R | IF, Interrupt Flag. This bit is set when an interrupt is pending. |
| **Command Register (0x04)** | | | |
| | 7 | W | STA, generate (repeated) start condition |
| | 6 | W | STO, generate stop condition |
| | 5 | W | RD, read from slave |
| | 4 | W | WR, write to slave |
| | 3 | W | ACK, when a receiver, sent ACK ('0') or NACK ('1') |
| | 2:1 | W | Reserved |
| | 0 | W | IACK, Interrupt acknowledge. When set, clears a pending interrupt. |

---
