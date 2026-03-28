# Chapter 2 Signal Descriptions

This chapter describes the AMBA APB signals. It contains the following section:

- *AMBA APB signals* on page 2-2.

## 2.1 AMBA APB signals

Table 2-1 lists the APB signals.

### Table 2-1 APB signal descriptions

| Signal | Source | Description |
|---|---|---|
| **PCLK** | Clock source | Clock. The rising edge of **PCLK** times all transfers on the APB. |
| **PRESETn** | System bus equivalent | Reset. The APB reset signal is active LOW. This signal is normally connected directly to the system bus reset signal. |
| **PADDR** | APB bridge | Address. This is the APB address bus. It can be up to 32 bits wide and is driven by the peripheral bus bridge unit. |
| **PPROT** | APB bridge | Protection type. This signal indicates the normal, privileged, or secure protection level of the transaction and whether the transaction is a data access or an instruction access. |
| **PSELx** | APB bridge | Select. The APB bridge unit generates this signal to each peripheral bus slave. It indicates that the slave device is selected and that a data transfer is required. There is a **PSELx** signal for each slave. |
| **PENABLE** | APB bridge | Enable. This signal indicates the second and subsequent cycles of an APB transfer. |
| **PWRITE** | APB bridge | Direction. This signal indicates an APB write access when HIGH and an APB read access when LOW. |
| **PWDATA** | APB bridge | Write data. This bus is driven by the peripheral bus bridge unit during write cycles when **PWRITE** is HIGH. This bus can be up to 32 bits wide. |
| **PSTRB** | APB bridge | Write strobes. This signal indicates which byte lanes to update during a write transfer. There is one write strobe for each eight bits of the write data bus. Therefore, **PSTRB[n]** corresponds to **PWDATA[(8n + 7):(8n)]**. Write strobes must not be active during a read transfer. |
| **PREADY** | Slave interface | Ready. The slave uses this signal to extend an APB transfer. |
| **PRDATA** | Slave interface | Read Data. The selected slave drives this bus during read cycles when **PWRITE** is LOW. This bus can be up to 32-bits wide. |
| **PSLVERR** | Slave interface | This signal indicates a transfer failure. APB peripherals are not required to support the **PSLVERR** pin. This is true for both existing and new APB peripheral designs. Where a peripheral does not include this pin then the appropriate input to the APB bridge is tied LOW. |

### 2.1.1 Data buses

The APB protocol has two independent data buses, one for read data and one for write data. The buses can be up to 32 bits wide. Because the buses do not have their own individual handshake signals, it is not possible for data transfers to occur on both buses at the same time.
