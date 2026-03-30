# Chapter 9 - Test Cases
<!-- page 58 -->
![Figure 9.1: Test flow](figures/figure-058-1.png)
Chapter 9
                                      Test Cases
9.1 Test Flow
  In the test, there is virtual sequence and in virtual sequence, sequences are there,
  sequence_item get started in sequences, sequences will start in virtual sequence and virtual
  sequence will start in Test.
                                         Fig 9.1 Test flow
9.2 AHB Test Cases FlowChart
                                 Fig 9.2 AHB test cases flow chart
AHB_AVIP                                                                                57
<!-- page 59 -->
9.3 Transaction
Table 10:Transaction Signals
           Variables           Type                            Description
              haddr             bit    Address. This is the AHB address bus. It can be up to 32
                                       bits wide.
              hselx             bit    Master asserts the hselx to select the slave device
                                       hwrite signal decides whether write data transfer happens
                                       from the master side or read data transfer happens to the
                                       master.
              hburst           enum    Burst type: Defines whether the transfer is a single
                                       transaction or part of a burst.
           hmastlock             bit   Indicates a lockedtransfer. When 1, the master keeps
                                       control of the bus until the transaction completes. When 0,
                                       normal arbitration applies.
              hprot             enum   Protection control: Defines the type of access for a
                                       transaction.
              hsize             enum   Transfer size: Defines the number of bytes in each
                                       transfer (byte, halfword, word, etc.).
             hnonsec             bit
                                       Security attribute: Defines whether the transfer is secure
                                       or non-secure.
             hmaster             bit   Indicates which master is performing the transfer in a
                                       multi-master system.
              htrans            enum   Indicates the type of transfer on the bus. It defines whether
                                       the transfer is Busy, idle, sequential, or non-sequential.
             hwdata              bit   Write data bus: Carries data from the master to the slave
                                       during a write operation.
AHB_AVIP                                                                                        58
<!-- page 60 -->
                                            Write strobe signals: Indicate which byte lanes in hwdata
           hwstrb                  bit
                                            are valid during a write transfer.
                                            Write enable signal: Defines whether the transaction is a
           hwrite                 enum
                                            read (0) or write (1) operation.
                                            Read data bus: Carries data from the slave to the master
            hrdata                 bit
                                            during a read operation.
                                            Slave Ready Signal: Indicates whether the slave is ready
        hreadyout                  bit      to complete the current transfer.
                                            Transfer response: Indicates whether the current transfer
            hresp                 enum
                                            was successful or encountered an error.
                                            Exclusive Access OK Signal: Indicates whether an
           hexokay                 bit      exclusive transfer was successful.
                                            Final Ready Signal: Indicates whether the current transfer
           hready                  bit
                                            is complete and the next transfer can begin.
                                            Counts the number of wait states inserted before a transfer
  noOfWaitStatesDetected           int
                                            is completed.
       busyControl                bit       Indicates if the master is in a BUSY state. Prevents new
                                            transactions from starting.
9.3.1 AhbMasterTransaction
  ● AhbMasterTransaction class is extended from the uvm_sequence_item holds the data
      items required to drive stimulus to dut.
  ● Declared all the variables (haddr, hselx, hburst, hmastlock, hprot, hsize, hnonsec,
      hmaster, htrans, hwdata, hwstrb, hwrite, hrdata, hreadyout, hresp, hexokay, hready
      hready, noOfWaitStatesDetected, busyControl).
  ● Constraint declared for slave select and data transfer based on transfer size.
AHB_AVIP                                                                                            59
<!-- page 61 -->
![Figure 9.3: Constraints of Ahb Master transaction](figures/figure-061.png)
                                      Fig 9.3 Constraints of Ahb Master transaction
Table 11: Describing constraints of AhbMasterTransaction
        Constraint                                  Description
                         The constraint ensures that the number of active write strobes (hwstrb) matches the transfer size
strobleValue             (hsize), setting 1, 2, 4, or 8 active bits for BYTE, HALFWORD, WORD, and DOUBLEWORD
                         transfers, respectively.
                         The constraint ensures that the hwdata size corresponds to the burst type, setting 4, 8, 16, or 1
burstsize
                         beats for WRAP4/INCR4, WRAP8/INCR8, WRAP16/INCR16, and other cases, respectively.
                         The constraint ensures that hwstrb size matches the burst type, while the busyState constraint
strobesize               enforces the same size mapping for busyControl, setting values of 4, 8, or 16 for
                         WRAP4/INCR4, WRAP8/INCR8, and WRAP16/INCR16, respectively.
busyState                The constraint ensures that the busyControl size corresponds to the burst type, assigning values
                         4, 8, or 16 for WRAP4/INCR4, WRAP8/INCR8, and WRAP16/INCR16, respectively.
     ● Written functions for do_copy, do_compare, do_print methods, $casting is used to copy
             the data member values and compare the data member values and by using a printer,
             printing the AhbMasterTransaction signals.
AHB_AVIP                                                                                                                     60
<!-- page 62 -->
![Figure 9.4: do_compare method of Master Transaction](figures/figure-062-1.png)
![Figure 9.5: do_copy method of Master Transaction](figures/figure-062-2.png)
           Fig 9.4 do_compare method of Master Transaction
            Fig 9.5 do_copy method of Master Transaction
AHB_AVIP                                                     61
<!-- page 63 -->
![Figure 9.6: Constraints of Ahb Slave transaction](figures/figure-063.png)
9.3.2 AhbSlaveTransaction
    ● AhbSlaveTransaction class is extended from the uvm_sequence_item holds the data
         items required to drive stimulus to dut
    ● Declared all the variables (haddr, hselx, hburst, hmastlock, hprot, hsize, hnonsec,
         hmaster, htrans, hwdata, hwstrb, hwrite, hrdata, hreadyout, hresp, hexokay, hready
         hready, noOfWaitStatesDetected, busyControl)
                                       Fig 9.6 Constraints of Ahb Slave transaction
Table 12: Constraints of Ahb Slave transaction
           Constraint                                                     Description
 chooseDataPacketC1             This constraint, chooseDataPacketC1, ensures that the variable choosePacketData is softly
                                assigned the value 0 by default
                                This constraint, ensures that the size of the hrdata array is always 16. This means that any
        readDataSize            read operation must retrieve exactly 16 data elements, enforcing a fixed data width for
                                read transactions
                                This constraint, waitState, defines a soft condition on noOfWaitStates such that its default
          waitState
                                or preferred value is 0
AHB_AVIP                                                                                                                  62
<!-- page 64 -->
![Figure 9.7: do_compare method of Slave Transaction](figures/figure-064-1.png)
![Figure 9.8: do_copy method of Slave Transaction](figures/figure-064-2.png)
           Fig 9.7 do_compare method of Slave Transaction
            Fig 9.8 do_copy method of Slave Transaction
AHB_AVIP                                                    63
<!-- page 65 -->
![Figure 9.9: Flow chart for sequence methods](figures/figure-065.png)
9.4 Sequences
A UVM Sequence is an object that contains a behavior for generating stimulus. A sequence
generates a series of sequence_item’s and sends it to the driver via sequencer, Sequence is
written by extending the uvm_sequence.
9.4.1 Methods
Table 13: Sequence methods
              Method                                                   Description
              new                                   Creates and initializes a new sequence object
           start_item        This method will send the request item to the sequencer, which will forward it to the driver
        req.randomize()                                 Generate the transaction(seq_item).
           finish_item                                 Wait for acknowledgement or response
                                     Fig 9.9 Flow chart for sequence methods
AHB_AVIP                                                                                                             64
<!-- page 66 -->
![Figure 9.10: Master sequence body method](figures/figure-066-1.png)
![Figure 9.11: Constraints Of Master Sequence](figures/figure-066-2.png)
Table 14: Describing master and slave sequences
     Sections     Master sequences          Slave sequences       Description
  BaseSequence    AhbMasterBaseSequen       AhbSlaveBaseSequen    Base class is extended from uvm_sequence and
                  ce                       ce                     parameterized             with            transaction
                                                                  (AhbMasterTransaction, AhbSlaveTransaction)
  Data            AhbMasterSequence        AhbSlaveSequence       Extended from base sequence. Based on a request
  transfers                                                       from the driver, the task will drive the transactions.
                                                                  In between start_ item and finish_ item , the task
                                                                  body randomizes the transaction object (req) with
                                                                  inline constraints, assigning values from sequence
                                                                  variables, and reports a fatal error if randomization
                                                                  fails.
In the master sequence body, req is created, and start_item(req) initiates the sequence. The
transaction (req) is then randomized with inline constraints, assigning values from sequence
variables (master signals), followed by finish_item(req) to complete the sequence.
                                        Fig 9.10 Master sequence body method
AHB_AVIP                                                                                                             65
<!-- page 67 -->
![Figure 9.12: Slave sequence body method](figures/figure-067.png)
                               Fig 9.11 Constraints Of Master Sequence
In the slave sequence body, req is created, and start_item(req) initiates the sequence. The
transaction (req) is then randomized with inline constraints, assigning values from sequence
variables (slave signals), followed by finish_item(req) to complete the sequence.
AHB_AVIP                                                                                66
<!-- page 68 -->
![Figure 9.13: Virtual base sequence](figures/figure-068.png)
                                Fig 9.12 Slave sequence body method
9.5 Virtual sequences
A virtual sequence is a container to start multiple sequences on different sequencers in the
environment. This virtual sequence is usually executed by a virtual sequencer which has
handles to real sequencers. This need for a virtual sequence arises when you require different
sequences to be run on different environments.
9.5.1 Virtual sequence base class
Virtual sequence base class is extended from uvm_sequence and parameterized with
uvm_transaction. Declaring p_sequencer as macro , handles virtual sequencer and master, slave
sequencer and environment config.
                                    Fig 9.13 Virtual base sequence
AHB_AVIP                                                                                  67
<!-- page 69 -->
![Figure 9.14: Virtual base sequence body](figures/figure-069-1.png)
In virtual sequence body method, Getting the env configurations and Dynamic casting of
p_sequencer and m_sequencer. Connect the master sequencer and slave sequencer in sequencer
with local master sequencer and slave sequencer.
                                            Fig 9.14 Virtual base sequence body
     In the virtual sequence body method, creating master and slave sequence handles and starts
the master and slave sequence within fork join and master sequence within repeat statement.
                                         Fig 9.15 Virtual Single Write sequence body
Table 15: Describing virtual sequences
       Virtual sequences                              Description
   AhbVirtualSingleWriteSequence             Inside the Single Write Virtual Sequence, extending from base class. Declaring
                                             handles for master and slave sequences, Using inline constraints to randomize the
                                             master sequence with BYTE, HALFWORD, and WORD transfer sizes, enforcing a
                                             write operation, NONSEQ transfer type, and SINGLE burst type.
AHB_AVIP                                                                                                             68
<!-- page 70 -->
 AhbVirtualSingleReadSequence         Inside the Single Write Virtual Sequence, extending from base class. Declaring
                                      handles for master and slave sequences. Using inline constraints to randomize the
                                      master sequence with BYTE, HALFWORD, and WORD transfer sizes, enforcing a
                                      read operation, NONSEQ transfer type, and SINGLE burst type.
 AhbVirtualWriteSequence              Inside the Write Virtual Sequence, extending from base class. Declaring handles for
                                      master and slave sequences. Using inline constraints to randomize the master sequence
                                      with BYTE, HALFWORD, and WORD transfer sizes, enforcing a write operation,
                                      NONSEQ transfer type, and distributing the burst type across multiple values like
                                      WRAP4, INCR4, WRAP8, INCR8, WRAP16, INCR16.
 AhbVirtualReadSequence               Inside the Read Virtual Sequence, extending from base class. Declaring handles for
                                      master and slave sequences. Using inline constraints to randomize the master sequence
                                      with BYTE, HALFWORD, and WORD transfer sizes, enforcing a read operation,
                                      NONSEQ transfer type, and distributing the burst type across multiple values like
                                      WRAP4, INCR4, WRAP8, INCR8, WRAP16, INCR16.
 AhbVirtualWriteWithBusySequence      Inside the Write Virtual Sequence, extending from base class. Declaring and
                                      constructing master and slave sequence handles. Using inline constraints to
                                      randomize the master sequence with BYTE, HALFWORD, and WORD transfer sizes,
                                      enforcing a write operation, NONSEQ transfer type, and distributing the burst type
                                      across multiple values like WRAP4, INCR4, WRAP8, INCR8, WRAP16, INCR16. Additionally,
                                      busyControlSeq is randomized to introduce bus busy conditions
 AhbVirtualReadWithBusySequence       Inside the Read Virtual Sequence, extending from base class. Declaring and
                                      constructing master and slave sequence handles. Using inline constraints to randomize
                                      the master sequence with BYTE, HALFWORD, and WORD transfer sizes, enforcing
                                      a read operation, NONSEQ transfer type, and distributing the burst type across
                                      multiple values like WRAP4, INCR4, WRAP8, INCR8, WRAP16, INCR16.
                                      Additionally, busyControlSeq is randomized to introduce bus busy conditions
 AhbSingleVirtualWriteWithWaitState   Inside the Write with wait state Virtual Sequence, extending from base class. Declaring and
 Sequence                             constructing master and slave sequence handles. Using inline constraints to
                                      randomize the master sequence with BYTE, HALFWORD, and WORD transfer sizes,
                                      enforcing a write operation, NONSEQ transfer type and SINGLE burst type.
 AhbSingleVirtualReadWithWaitState    Inside the Read with wait state Virtual Sequence, extending from base class. Declaring and
 Sequence                             constructing master and slave sequence handles. Using inline constraints to
                                      randomize the master sequence with BYTE, HALFWORD, and WORD transfer sizes,
                                      enforcing a read operation, NONSEQ transfer type and SINGLE burst type.
AHB_AVIP                                                                                                            69
<!-- page 71 -->
![Figure 9.16: Base test](figures/figure-071.png)
  AhbVirtualWriteWithWaitState       Inside the Write with wait state Virtual Sequence, extending from base class. Declaring and
  Sequence                           constructing master and slave sequence handles. Using inline constraints to
                                     randomize the master sequence with BYTE, HALFWORD, and WORD transfer sizes,
                                     enforcing a write operation, NONSEQ transfer type, and distributing the burst type
                                     across multiple values like WRAP4, INCR4, WRAP8, INCR8, WRAP16, INCR16.
  AhbVirtualReadWithWaitState        Inside the Read with wait state Virtual Sequence, extending from base class. Declaring and
  Sequence                           constructing master and slave sequence handles. Using inline constraints to
                                     randomize the master sequence with BYTE, HALFWORD, and WORD transfer sizes,
                                     enforcing a read operation, NONSEQ transfer type, and distributing the burst type
                                     across multiple values like WRAP4, INCR4, WRAP8, INCR8, WRAP16, INCR16.
  AhbWriteFollowedByReadVirtualSeq   Inside the Write Followed by Read Virtual Sequence, extending from base class.
  uence                              Declaring handles for master and slave sequences, Using inline constraints to
                                     randomize the master sequence with BYTE, HALFWORD, and WORD transfer sizes, enforcing
                                     a write operation followed by read operation, NONSEQ transfer type, and SINGLE
                                     burst type.
9.6 Test Cases
The uvm_test class defines the test scenario and verification goals.
A) In base test, declaring the handles for environment config and environment class.
                                             Fig 9.16 Base test
B) In build phase, calling the setupAhbEnvironmentConfig and constructing the environment
    handle
C) Inside setupAhbEnvironmentConfig function, constructing the environment config class
    handle. With the help of this ahbEnvironmentConfig handle all the required fields in the
AHB_AVIP                                                                                                           70
<!-- page 72 -->
![Figure 9.17: Setup Environment Config](figures/figure-072-1.png)
![Figure 9.18: Master Agent Config setup](figures/figure-072-2.png)
   config class have been set up with respective values and then calling the
   setupAhbMasterAgentConfig and setupAhbSlaveAgentConfig functions.
                                 Fig 9.17 Setup Environment Config
In setupAhbMasterAgentConfig function, AhbMasterAgentConfig class handle which is in
AhbEnvironmentConfig class has been constructed with the help of this handle all the required
fields(hasCoverage, is_active) in AhbMasterAgentConfig class has been setup.
                                 Fig 9.18 Master Agent Config setup
AHB_AVIP                                                                                 71
<!-- page 73 -->
![Figure 9.19: Slave Agent Config setup](figures/figure-073-1.png)
![Figure 9.20: Example for Single Write test](figures/figure-073-2.png)
D) In setupAhbSlaveAgentConfigfunction, for each slave agent configuration trying to
    construct AhbSlaveAgentConfig class handle which is in AhbEnvironmentConfig class
    with the help of this handle all the required fields (hasCoverage, is_active) in
    AhbSlaveAgentConfig class has been setup followed by the end of the elaboration phase
    used to print the topology.
                                    Fig 9.19 Slave Agent Config setup
Extend the AhbSingleWrite from base test and declare virtual sequence handle then create
virtual sequence in test, and start the virtual sequence in run_phase, raise and drop objection.
                                  Fig 9.20 Example for Single Write test
AHB_AVIP                                                                                     72
<!-- page 74 -->
![Figure 9.21: Run phase of Single Write test](figures/figure-074.png)
                                 Fig 9.21 Run phase of Single Write test
Table 16: Tests
            Test names                                             Description
         AhbSingleWriteTest       Extend test from base test and created the Single Write virtual sequence handle
                                  and starting the sequences in between phase raise and drop objection.
         AhbSingleReadTest        Extend test from base test and created the Single Read virtual sequence handle
                                  and starting the sequences in between phase raise and drop objection.
            AhbWriteTest          Extend test from base test and created the Write virtual sequence handle and
                                  starting the sequences in between phase raise and drop objection.
            AhbReadTest           Extend test from base test and created the Read virtual sequence handle and
                                  starting the sequences in between phase raise and drop objection.
       AhbWriteWithBusyTest       Extend test from base test and created the Write with Busy virtual sequence
                                  handle and starting the sequences in between phase raise and drop objection.
       AhbReadWithBusyTest        Extend test from base test and created the Read with Busy virtual sequence
                                  handle and starting the sequences in between phase raise and drop objection.
     AhbWriteWithWaitStateTest    Extend test from base test and created the Write with wait state virtual sequence
                                  handle and starting the sequences in between phase raise and drop objection.
AHB_AVIP                                                                                                       73
<!-- page 75 -->
      AhbReadWithWaitStateTest              Extend test from base test and created the Read with wait state virtual sequence
                                            handle and starting the sequences in between phase raise and drop objection.
    AhbWriteFollowedByReadTest              Extend test from base test and created the Single Write virtual sequence handle
                                            and Single Read virtual sequence handle and starting the sequences in between
                                            phase raise and drop objection.
9.7 Testlists
Regression list for AHB
Table 17:Testlists
                         TestCase Names                                               Description
                      AhbSingleWriteTest                              Checks for a Single Transfer Write operation
                      AhbSingleReadTest                                Checks for a Single Transfer Read operation
                         AhbWriteTest                               Checks for Other Burst Transfers Write operation
                         AhbReadTest                                Checks for Other Burst Transfers Read operation
                     AhbWriteWithBusyTest                               Check for Busy Trans for Write Operation
                     AhbReadWithBusyTest                                Check for Busy Trans for Read Operation
             AhbSingleWriteWithWaitStateTest                   Check for Wait state between transfers for Write Operation
                                                                                 of Single Burst Transfer
             AhbSingleReadWithWaitStateTest                    Check for Wait state between transfers for Read Operation
                                                                                 of Single Burst Transfer
                AhbWriteWithWaitStateTest                      Check for Wait state between transfers for Write Operation
                AhbReadWithWaitStateTest                       Check for Wait state between transfers for Read Operation
               AhbWriteFollowedByReadTest                       Checks for a Single Transfer Write operation followed by
                                                                                      Read operation
AHB_AVIP                                                                                                                74
