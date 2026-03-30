# AHB-AVIP
This section collects the front matter from the original PDF in a markdown-native format.
## Table of Contents
| Section | Page |
| --- | ---: |
| Chapter 1 - Introduction | 7 |
| 1.1 Key features | 7 |
| Chapter 2 - Architecture | 8 |
| 2.1 AHB AVIP Testbench Architecture | 8 |
| Chapter 3 - Implementation | 10 |
| 3.1 Pin Interface | 10 |
| 3.2 Testbench Components | 12 |
| Chapter 4 - Directory Structure | 34 |
| 4.1 Package Content | 34 |
| Chapter 5 - Configuration | 37 |
| 5.1 Global package variables | 37 |
| 5.2 Master agent configuration | 39 |
| 5.3 Slave agent configuration | 39 |
| 5.4 Environment configuration | 39 |
| Chapter 6 - Verification Plan | 41 |
| 6.1 Verification plan | 41 |
| 6.2 Template of Verification Plan | 41 |
| 6.3 Sections for different test scenarios | 42 |
| Chapter 7 - Assertion Plan | 43 |
| 7.1 Assertion Plan overview | 43 |
| 7.2 Template of Assertion Plan | 44 |
| 7.3 Master Assertion Condition | 44 |
| 7.4 Slave Assertion Condition | 46 |
| 7.4.1 checkSlaveHrdataValid | 46 |
| Chapter 8 - Coverage Plan | 48 |
| 8.1 Template of Coverage Plan | 48 |
| 8.2 Functional Coverage | 48 |
| 8.3 Uvm_Subscriber | 48 |
| 8.4 Covergroup | 50 |
| 8.4 Bucket | 51 |
| 8.5 Coverpoints | 52 |
| 8.6 Cross Coverpoints | 52 |
| 8.7 Creation of the covergroup | 53 |
| 8.8 Sampling of the covergroup | 53 |
| 8.9 Checking for the coverage | 53 |
| Chapter 9 - Test Cases | 57 |
| 9.1 Test Flow | 57 |
| 9.2 AHB Test Cases FlowChart | 57 |
| 9.3 Transaction | 58 |
| 9.4 Sequences | 64 |
| 9.5 Virtual sequences | 67 |
| 9.6 Test Cases | 70 |
| Chapter 10 - Simulation Results and Waveform | 75 |
| Chapter 11 - References | 76 |
## List of Figures
| Figure | Title | Page |
| --- | --- | ---: |
| Fig 2.1 | AHP_AVIP Architecture | 8 |
| Fig 3.1 | HDL Top | 13 |
| Fig 3.2 | AHB driver bfm instantiation in AHB master agent bfm code snippet | 14 |
| Fig 3.3 | AHB monitor bfm instantiation in AHB master agent bfm code snippet | 14 |
| Fig 3.4 | AHB slave driver bfm instantiation in AHB slave agent bfm code snippet | 15 |
| Fig 3.5 | AHB slave monitor bfm instantiation in AHB slave agent bfm code snippet | 16 |
| Fig 3.6 | HVL Top | 17 |
| Fig 3.7 | Connection of the analysis ports of the monitor to the scoreboard analysis fifo | 18 |
| Fig 3.8 | Shows the declaration of slave and master analysis port in the slave and master monitor proxy | 19 |
| Fig 3.9 | Shows the declaration of master and slave analysis fifo in the scoreboard | 19 |
| Fig 3.10 | Creation of the master and slave analysis port | 19 |
| Fig 3.11 | Connection done between the analysis port and analysis fifo export in the env class | 20 |
| Fig 3.12 | Use of get method to get the packet from monitor analysis port | 20 |
| Fig 3.13 | The comparison of the master hwdata with slave hwdata | 20 |
| Fig 3.14 | Flow chart of the scoreboard run phase | 21 |
| Fig 3.15 | Flow chart of the scoreboard report phase | 22 |
| Fig 3.16 | AHB master agent build phase code snippet | 23 |
| Fig 3.17 | AHB master agent connect phase code snippet | 24 |
| Fig 3.18 | Flowchart of communication between ahb master driver proxy and ahb master driver bfm | 25 |
| Fig 3.19 | run phase of ahb master driver proxy code snippet | 26 |
| Fig 3.20 | Flowchart of ahb master monitor proxy and ahb master monitor bfm communication | 26 |
| Fig 3.21 | AHB slave agent build phase code snippet | 27 |
| Fig 3.22 | AHB slave agent connect phase code snippet | 28 |
| Fig 3.23 | Flowchart of ahb slave driver bfm and slave driver proxy communication | 29 |
| Fig 3.24 | AHB slave driver proxy run phase code snippet | 30 |
| Fig 3.25 | Flowchart of ahb slave monitor bfm and slave monitor proxy communication | 31 |
| Fig 3.26 | run phase of ahb slave monitor proxy code snippet | 31 |
| Fig 4.1 | Package Structure of AHB_AVIP | 34 |
| Fig 5.1 | Verification plan template | 41 |
| Fig 7.1 | checkHaddrAlignment Assertion | 44 |
| Fig 7.2 | checkStrobe Assertion | 45 |
| Fig 7.3 | checkHrespOKayForValid Assertion | 46 |
| Fig 7.4 | checkSlaveHrdataValid Assertion | 46 |
| Fig 8.1 | uvm_subscriber | 49 |
| Fig 8.2 | Monitor and coverage connection | 49 |
| Fig 8.3 | Write function | 50 |
| Fig 8.4 | Covergroup | 50 |
| Fig 8.5 | option.comment | 51 |
| Fig 8.6 | Bucket | 51 |
| Fig 8.7 | Coverpoint | 52 |
| Fig 8.8 | Cross Coverpoints | 52 |
| Fig 8.9 | Illegal bins | 52 |
| Fig 8.10 | Creation of covergroup | 53 |
| Fig 8.11 | Sampling of the covergroup | 53 |
| Fig 8.12 | Simulation log file path | 53 |
| Fig 8.13 | Coverage report path | 54 |
| Fig 8.14 | HTML window showing all coverage | 54 |
| Fig 8.15 | All coverpoints present in the Master Covergroup | 55 |
| Fig 8.16 | All coverpoints present in the Slave Covergroup | 55 |
| Fig 8.17 | Individual Coverpoint Hit | 56 |
| Fig 9.1 | Test flow | 57 |
| Fig 9.2 | AHB test cases flow chart | 57 |
| Fig 9.3 | Constraints of Ahb Master transaction | 60 |
| Fig 9.4 | do_compare method of Master Transaction | 61 |
| Fig 9.5 | do_copy method of Master Transaction | 61 |
| Fig 9.6 | Constraints of Ahb Slave transaction | 62 |
| Fig 9.7 | do_compare method of Slave Transaction | 63 |
| Fig 9.8 | do_copy method of Slave Transaction | 63 |
| Fig 9.9 | Flow chart for sequence methods | 64 |
| Fig 9.10 | Master sequence body method | 65 |
| Fig 9.11 | Constraints Of Master Sequence | 66 |
| Fig 9.12 | Slave sequence body method | 67 |
| Fig 9.13 | Virtual base sequence | 67 |
| Fig 9.14 | Virtual base sequence body | 68 |
| Fig 9.15 | Virtual Single Write sequence body | 68 |
| Fig 9.16 | Base test | 70 |
| Fig 9.17 | Setup Environment Config | 71 |
| Fig 9.18 | Master Agent Config setup | 71 |
| Fig 9.19 | Slave Agent Config setup | 72 |
| Fig 9.20 | Example for Single Write test | 72 |
| Fig 9.21 | Run phase of Single Write test | 73 |
## List of Tables
| Table | Title | Page |
| --- | --- | ---: |
| Table 1 | AHB pins used to interface to external devices | 10 |
| Table 2 | UVM verbosity Priorities | 32 |
| Table 3 | Descriptions of each Verbosity level | 32 |
| Table 4 | Directory Path | 35 |
| Table 5 | Global package variables | 37 |
| Table 6 | AhbMasterAgentConfig | 39 |
| Table 7 | AhbSlaveAgentConfig | 39 |
| Table 8 | AhbEnvironmentConfig | 39 |
| Table 9 | Checking coverage closure for the different transactions and burst transfers | 42 |
| Table 10 | Transaction Signals | 58 |
| Table 11 | Describing constraints of AhbMasterTransaction | 60 |
| Table 12 | Constraints of Ahb Slave transaction | 62 |
| Table 13 | Sequence methods | 64 |
| Table 14 | Describing master and slave sequences | 65 |
| Table 15 | Describing virtual sequences | 68 |
| Table 16 | Tests | 73 |
| Table 17 | Testlists | 74 |
## List of Abbreviations
| Abbreviation | Description |
| --- | --- |
| `uvm` | universal verification methodology |
| `ahb` | advanced high performance |
| `avip` | accelerated verification intellectual property |
| `hdl` | hardware descriptive language |
| `hvl` | hardware verification language |
| `bfm` | bus functional model |
| `tlm` | transaction level modelling |
| `hclk` | system clock |
