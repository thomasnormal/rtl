# Chapter 5 - Configuration


<!-- page 38 -->

Chapter 5

                                              Configuration

5.1 Global package variables

Table 5: Global package variables

  Name                              Type       Description

  NO_OF_MASTERS                     integer    Specifies no of master connected to the AHB interface

  NO_OF_SLAVES                      integer    Specifies no of slave connected to the AHB interface

  MASTER_AGENT_ACTIVE               bit        Determines whether master agent is active or not

  SLAVE_AGENT_ACTIVE                bit        Determines whether slave agent is active or not

  ADDR_WIDTH                        int        Specifies the address width

  DATA_WIDTH                        int        Specifies the data width

  HMASTER_WIDTH                     int        Determines the required bit-width for the HMASTER signal

  HPROT_WIDTH                       int        Specifies the bit-width of the HPROT signal

  SLAVE_MEMORY_SIZE                 int        Determines the size of the addressable memory region for a slave

                                               Determines the gap or spacing between the address regions
  SLAVE_MEMORY_GAP                  int
                                               assigned to consecutive slaves

  MEMORY_WIDTH                      int        Determines the data width of a memory module

  LENGTH                            int        Specifies the maximum size of the array to store burst transfers

                                               Used to represent the type of burst transaction
                                                 SINGLE = 3'b000
                                                 INCR       = 3'b001
                                                 WRAP4 = 3'b010
  ahbBurstEnum                      enum         INCR4      = 3'b011
                                                 WRAP8 = 3'b100
                                                 INCR8      = 3'b101
                                                 WRAP16 = 3'b110
                                                 INCR16 = 3'b111

                                               Used to represent the type of transfer
                                                 IDLE       = 2'b00
  ahbTransferEnum                   enum
                                                 BUSY       = 2'b01
                                                 NONSEQ = 2'b10




AHB_AVIP                                                                                                          37



<!-- page 39 -->

                                      SEQ         = 2'b11

                                    Used to represent the type of resp
 ahbRespEnum               enum       OKAY        = 1'b0
                                      ERROR       = 1'b1

                                    Used to represent the size of the transaction
                                     BYTE               = 3'b000     // 8 bits
                                     HALFWORD           = 3'b001     // 16 bits
                                     WORD               = 3'b010     // 32 bits
 ahbHsizeEnum              enum      DOUBLEWORD = 3'b011 // 64 bits
                                     LINE4              = 3'b110 // 128 bits (4-word line)
                                     LINE8              = 3'b101, // 256 bits (8-word line)
                                     LINE16             = 3'b110, // 512 bits
                                     LINE32             = 3'b111 // 1024 bits

                                     Used to represent the protection type for transaction
                                      NORMAL_SECURE_DATA                               = 4'b0000,
                                      NORMAL_SECURE_INSTRUCTION                       = 4'b0001,
                                      NORMAL_NONSECURE_DATA                            = 4'b0010,
 ahbProtectionEnum         enum       NORMAL_NONSECURE_INSTRUCTION                    = 4'b0011,
                                      PRIVILEGED_SECURE_DATA                           = 4'b0100,
                                      PRIVILEGED_SECURE_INSTRUCTION                    = 4'b0101,
                                      PRIVILEGED_NONSECURE_DATA                        = 4'b0110,
                                      PRIVILEGED_NONSECURE_INSTRUCTION = 4'b0111

                                      WRITE=1’b1 : write transfer happen
 ahbWriteEnum              enum
                                      READ=1’b0 : read transfer happen

 ahbTransferCharStruct     struct   Structure to hold the packet data.

 ahbTransferConfigStruct   struct   Structure to hold the configuration data.




Configuration used
  1. Env configuration
  2. Master Agent configuration
  3. Slave Agent configuration




AHB_AVIP                                                                                            38



<!-- page 40 -->

5.2 Master agent configuration

Table 6:AhbMasterAgentConfig


       Name                Type             Default value                                Description

      is_active            enum              UVM_ACTIVE            It will be used for configuring an agent as an active
                                                                   agent means it has sequencer, driver and monitor or
                                                                   passive agent which has monitor only.


    hasCoverage                 bit                   ‘d1          Used for enabling the master agent coverage


                                                                   Defines the number of extra wait states before
   noOfWaitStates               int                   `d0
                                                                   initiating a transaction.



5.3 Slave agent configuration

Table 7: AhbSlaveAgentConfig


      Name              Type              Default value                                 Description

     is_active          enum             UVM_ACTIVE              It will be used for configuring agent as an active agent
                                                                 means it has sequencer, driver and monitor and if it’s a
                                                                 passive agent then it will have only monitor

   hasCoverage            bit                   ‘d1              Used for enabling the slave agent coverage.

                                                                 Defines the number of wait states the slave introduces
  noOfWaitStates          int                   `d0
                                                                 (declared as rand for randomization).



5.4 Environment configuration


Table 8: AhbEnvironmentConfig


        Name            Type          Default value         Description

    hasScoreboard         bit               1               Enables the scoreboard, it usually receives the transaction level
                                                            objects via TLM ANALYSIS PORT.




AHB_AVIP                                                                                                                    39



<!-- page 41 -->

                                       Enables the virtual sequencer which has master and slave
 hasVirtualSequencer     bit     1
                                       sequencer

    noOfSlaves         integer   ‘h1   Number of slaves connected to the SPI interface


    noOfMasters        integer   ‘h1   Number of Masters connected to the SPI interface




AHB_AVIP                                                                                          40

