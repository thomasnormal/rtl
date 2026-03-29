## Common Operation Sequence

The I2C Master supports common I2C operations. The sequence of I2C WRITE and I2C READ is described in this section.

### Initialize the I2C Master Core

1. Program the clock PRESCALE registers, PRERlo and PRERhi, with the desired value. This value is determined by the clock frequency and the speed of the I2C bus.
2. Enable the core by writing 8'h80 to the Control Register, CTR.

### Write to a slave device (no change in direction)

1. Set the Transmit Register TXR with a value of Slave address + Write bit.
2. Set the Command Register CR to 8'h90 to enable the START and WRITE. This starts the transmission on the I2C bus.
3. Check the Transfer In Progress (TIP) bit of the Status Register, SR, to make sure the command is done.
4. Set TXR with a slave memory address for the data to be written to.
5. Set CR with 8'h10 to enable a WRITE to send to the slave memory address.
6. Check the TIP bit of SR, to make sure the command is done.
7. Set TXR with 8-bit data for the slave device.
8. Set CR to 8'h10 to enable a WRITE to send data.
9. Check the TIP bit of SR, to make sure the command is done.
10. Repeat steps 7 to 9 to continue to send data to the slave device.
11. Set the TXR with the last byte of data.
12. Set CR to 8'h50 to enable a WRITE to send the last byte of data and then issue a STOP command.

### Read from a slave device (change in direction)

1. Set the Transmit Register TXR with a value of Slave address + Write bit.
2. Set the Command Register CR to 8'h90 to enable the START and WRITE. This starts the transmission on the I2C bus.
3. Check the Transfer In Progress (TIP) bit of the Status Register, SR, to make sure the command is done.
4. Set TXR with the slave memory address, where the data is to be read from.
5. Set CR with 8'h10 to enable a WRITE to send to the slave memory address.
6. Check the TIP bit of SR, to make sure the command is done.
7. Set TXR with a value of Slave address + READ bit.
8. Set CR with the 8'h90 to enable the START (repeated START in this case) and WRITE the value in TXR to the slave device.
9. Check the TIP bit of SR, to make sure the command is done.
10. Set CR with 8'h20 to issue a READ command and then an ACK command. This enables the reading of data from the slave device.
11. Check the TIP bit of SR, to make sure the command is done.
12. Repeat steps 10 and 11 to continue to read data from the slave device.
13. When the Master is ready to stop reading from the Slave, set CR to 8'h28. This will read the last byte of data and then issue a NACK.

---
