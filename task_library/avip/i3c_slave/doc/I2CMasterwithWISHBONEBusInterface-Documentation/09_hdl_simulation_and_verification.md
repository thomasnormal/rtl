## HDL Simulation and Verification

The I2C master with WISHBONE interface design is simulated using an I2C slave model (i2c_slave_model.v) and a WISHBONE master model (wb_master_model.v). The slave model emulates the responses of an I2C slave device by sending ACK when the address is matching and when the WRITE operation is completed. The master model contains several tasks to emulate WISHBONE READ, WRITE, and Compare commands normally issued by the microcontroller. The top-level testbench (tst_bench_top.v) controls the flow of the I2C operations. The START, WRITE, REPEATED START, READ, consecutive READ, ACK/NACK, STOP, and clock stretching operations are simulated with this testbench.

The following timing diagrams show the major timing milestones in the simulation:

![Figure 4: Writing Prescale Register with 0x64 and 0x00 at Addresses 0x00 and 0x01 Respectively](../output/pages/page-08.png)

![Figure 5: Initiate a START, SR[1] (Transfer in Progress) and SR[6] (Busy) Are Set](../output/pages/page-08.png)

![Figure 6: Transfer Slave Address + WR, Receive ACK from Slave, Transfer Slave Memory Address 0x01, Receive ACK from Slave, Release SR[1] (Transfer in Progress)](../output/pages/page-09.png)

![Figure 7: Clock Stretching by Slave, scl Line Held Low](../output/pages/page-09.png)

![Figure 8: Repeated START with Slave Address + RD Command](../output/pages/page-10.png)

![Figure 9: Consecutive READ from the Slave, Data Read are 0xA5, 0x5A, and 0x11](../output/pages/page-10.png)

![Figure 10: Slave Generates NACK, Master Issues a STOP](../output/pages/page-10.png)

---
