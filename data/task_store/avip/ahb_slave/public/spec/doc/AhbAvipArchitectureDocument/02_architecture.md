# Chapter 2 - Architecture


<!-- page 9 -->

![Figure 2.1: AHB-AVIP Architecture](figures/figure-009.png)

Chapter 2
                                     Architecture


2.1 AHB AVIP Testbench Architecture

The Accelerated VIP (AVIP) for AHB is structured into two distinct top modules: HVL TOP
and HDL TOP, as depicted in Figure 2.1. This division separates the synthesizable and un-
synthesizable components of the testbench, optimizing its functionality for both simulation and
emulation modes.




                                   Fig 2.1 AHP_AVIP Architecture

The HDL TOP contains the synthesizable components, including the interface, clock, and reset
signal generation, allowing it to run efficiently in emulators. It houses the Bus Functional
Models (BFMs), which consist of drivers and monitors with back-pointers to their proxies,
enabling non-blocking method calls defined in the HVL.

In contrast, the HVL TOP includes the un-synthesizable and untimed components, handling
transaction flow from the master and slave virtual sequences through the BFM Proxy and BFM
to the AHB interface. Data collected by the monitor BFMs is passed to the scoreboard for
checking and coverage collection, ensuring robust verification.




AHB_AVIP                                                                                    8



<!-- page 10 -->

Communication between the two modules is transaction-based, enabling the exchange of
information-rich transactions. Tasks and functions within the HDL TOP interact seamlessly
with their proxies in the HVL TOP, facilitating efficient data transfer.

The clock generation within the HDL TOP inside the emulator ensures the emulator operates
at full speed, enabling faster execution of longer tests. This modular approach provides a clear
separation of concerns, ensuring scalability and efficiency in verifying AHB designs across
simulation and emulation platforms.




AHB_AVIP                                                                                     9

