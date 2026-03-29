## Miscellaneous Features

In addition to supporting basic I2C operation, this design also supports the 10-bit addressing schedule specified in the I2C specification. The 10-bit addressing scheme expands the addressable slave devices from less than 128 to more than 1000. The 10-bit addressing differentiates itself from the 7-bit addressing by starting the address with 11110xx. The last two bits of this first address plus the following 8 bits on the I2C sda line define the 10-bit address. The data is still being transferred in byte format, as with the 7-bit addressing.

By the nature of open-drain signal, the I2C provides clock synchronization through a wired-AND connection on the scl line. This clock synchronization capability can be used as a handshake between the slave and master I2C devices. By holding the scl line low, the slave device tells the master to slow down the data transfer until the slave device is ready. This design detects the scl line to determine if the line is being held.

This design supports multiple masters and thus incorporates the arbitration lost detection. The master that loses the arbitration reports the status in Status Register bit 5. The arbitration is lost when the master detects a STOP condition which is not requested, or when the master drives the sda line high but the sda line is pulled low. The arbitration lost resets the bits in the Command Register to clear the current command for the master to start over again.

These features are described in detail in the I2C specification.

---
