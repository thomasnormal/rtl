Chapter 2
Architecture

APB AVIP Testbench Architecture has divided into the two top modules as HVL and HDL
top as shown in below fig 2.1

HVL TOP HDL TOP



APB SLAVE AGENT

ore APB SLAVE APB SLAVE AGENT BFM
PROXY
APB SCOREBOARD coverace © —
APB SLAVE
©

APB SLAVE
MONITOR

PROXY MONITOR BFM
ee









APB SLAVE APB SLAVE

SLAVE {)}--_] DRIVER PROXY " DRIVER BFM
SEQUENCER















APB MASTER AGENT



APB INTERFACE

APB VIRTUAL APB VIRTUAL
SEQUENCE SEQUENCER APB APB MASTER APB MASTER AGENT BFM
MASTER (> PROXY
APB APB COVERAGE a

stave | Ny SLAVE | Oy APB MASTER APB MASTER

VIRTUAL VIRTUAL MONITOR MONITOR BFM
SEQUENCE SEQUENCER PROXY

APB APB
APB APB MASTER APB MASTER
MASTER . MASTER | 7 A
virtua. | Pi VIRTUAL Y oeonencer LL oriver Proxy DRIVER BEM
SEQUENCE SEQUENCER

































Fig 2.1 apb avip Architecture

The whole idea of using Accelerated VIP is to push the synthesizable part of the testbench
into the separate top module along with the interface and it is named as HDL TOP and the
unsynthesizable part is pushed into the HVL TOP it provides the ability to run the longer tests
quickly. This particular testbench can be used for the simulation as well as the emulation
based on mode of operation.

HVL TOP has the design which is untimed and the transactions flow from both master virtual
sequence and slave virtual sequence onto the APB I/F through the BFM Proxy and BFM and
gets the data from monitor BFM and uses the data to do checks using scoreboard and
coverage.

11



HDL TOP consists of the design part which is timed and synthesizable, Clock and reset
signals are generated in the HDL TOP. Bus Functional Models (BFMs) i.e synthesizable part
of drivers and monitors are present in HDL TOP, BFMs also have the back pointers to it’s
proxy to call non - blocking methods which are defined in the proxy.

Tasks and functions within the drivers and monitors which are called by the driver and
monitor proxy inside the HVL. This is how the data is transferred between the HVL TOP and
HDL TOP.

HDL and HVL uses the transaction based communication to enable the information rich
transactions and since clock is generated within the HDL TOP inside the emulator it allows
the emulator to run at full speed.

12
