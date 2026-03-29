Chapter |

Introduction



PENABLE



PSEl x
PADDR{31:0]





PWDATA[31:0]





APB PWRITE
MASTER PPROT[2:0]

APB
SLAVE

v



PSTRBJ[3:0]

¥



\Z\Zy VV

PSLVERR
PREADY

Me
<
Kk PRDATA[31:0]

















[
|
|

PCLK









PRESEIn









Fig: 1.1 APB AVIP

Master avip can communicate with the slave avip via APB interface. Master avip and slave
avip works on both simulator and emulator. To know more about avip, please go through the
link : SystemVerilog Testbench Acceleration | Acceleration

1.1 APB master avip

APB master avip starts the test in the hvl top and starts the randomised sequences in base_test
and will pass the paddr, pwrite, pselx and pwdata to APB master _driver proxy using uvm
sequencer and driver handshake. The APB master driver bfm gets the paddr, pwrite, pselx
and pwdata using inbound communication. The APB master driver bfm sends the paddr,
pwrite, pselx and pwdata that is sampled in APB master driver bfm and sends it back to the
APB master driver proxy. The APB master monitor bfm samples the master_tx and slave_tx
received from the APB interface and sends it to the APB master monitor proxy. The sampled
data received by APB master monitor bfm is sent to the APB master scoreboard and APB



master coverage. APB master scoreboard compares the driven data and sampled data. APB
master coverage is used to check the functional coverage of APB master.

To know more about inbound and outbound communication, please go through this link :
Inbound and Outbound Communication

1.2 APB slave avip

APB slave avip starts the test in the hvl top and starts the randomised sequences in base_test
and will pass the prdata, pslverr and pready to APB slave_driver proxy using uvm sequencer
and driver handshake. The APB slave driver bfm gets prdata,pslverr and pready using
inbound communication. The APB slave driver bfm sends the prdata, pslverr and pready that
is sampled in APB slave driver bfm and sends it back to the APB slave driver proxy. The
APB slave monitor bfm samples samples the master_tx and slave_tx received from the APB
interface and sends it to the APB slave monitor proxy. The sampled data received by APB
slave monitor bfm is sent to the APB slave scoreboard and APB slave coverage. APB slave
scoreboard compares the driven data and sampled data. APB slave coverage is used to check
the functional coverage of APB slave.

To know more about inbound and outbound communication, please go through this link :
Inbound and Outbound Communication

1.3 APB Interface

APB interface has the following interface pin level signals :







Signals Source Description

pelk Clock source Clock. The rising edge of PCLK times all
transferon the APB.

preset_n System bus equivalent Reset. The APB reset signal is active low.

This signal is normally connected directly
to the system bus reset signal



paddr APB bridge Address. This is the APB address bus.It can
be up to 32 bits wide and is a data access or
an instruction access.



pprot APB bridge Protection type. This signal indicates the
normal, privileged, or secure protection
level of the transaction and whether the
transaction is a data access or an instruction
access.















pselx

APB bridge

Select. The APB bridge unit generates this
signal to each peripheral bus slave. It
indicates that the slave device is selected
and that a data transfer is required. There is
a pselx signal for each slave.



penable

APB bridge

Enable. This signal indicates the second and
subsequent cycle of an APB transfer.



pwrite

APB bridge

Direction. This signal indicates an APB
write access when HIGH and an APB read
access when LOW.



pwdata

APB bridge

Write data. This bus is driven by the
peripheral bus bridge unit during the write
cycle when pwrite is HIGH. This bus can be
up to 32 bits wide.



pstrb

APB bridge

Write strobes. This signal indicates when
byte lanes to update during a write transfer.
There is one write strobe for each eight bits
of the write data bus. Therefore, pstrb[n]
corresponds to pwdata[(8n+7):(8n)]. Write
strobes must not be active during a read
transfer.



pready

Slave interface

Ready. The Slave uses this signal to extend
an APB transfer.



prdata

Slave interface

Read Data.The selected slave drives this
bus during read cycles when pwrite is
LOW. This bus can be up to 32-bits wide.





pslverr



Slave interface



This signal indicates a transfer failure. APB
peripherals are not required to support the
pslverr pin. This is true for both existing
and new APB peripheral designs. Where a
peripheral does not include this PIN then
the appropriate input to the APB bridge is
tied LOW.



To know more about the APB interface signals, please go to section 3./ Pin Interface.

1.4 apb_compile.f file

This file contains the following things :

1. All the directories needed

2. All the packages we needed





3. All the modules written
4. All the bfm interfaces written
5. The APB interface

«* If you want to add any file in the project, please add the file or folder in the

apb_compile.f file to make it compiled.

“+ If you want to add a class based component or object, you have to add that file in the
respective package file and then make sure to mention the directory and path in the

apb_compile.f file.

“+ If you want to add a module/interface or any static component, then mention the file

name along with the path of the file.

“* How to add:
To include directory: +incdir<path_ of the folder>

1.

2. To include file use file path/file name.extension
3. /is used to force a new line

** Current apb_compile.f file consists of all files directories and Packages mentioned in

fig. 1.2, fig. 1.3 and fig. 1.4.

a. Directories included :





+incdir+..
+incdir+..
+incdir+..
+incdir+..
+incdir+..
+incdir+..
+incdir+..
+incdir+..
+incdir+..
+incdir+..
+incdir+..
+incdir+..

~

i i i i i i i i

./src/globals/
./src/hvl_top/test/sequences/master_sequences/
./src/hvl_ top/master/

./src/hdl_ top/master_agent_bfm/

./src/hvl_ top/env/virtual sequencer/
./src/hvl_top/test/virtual_ sequences/
./src/hvl_ top/env

./src/hvl top/slave
./src/hvl_top/test/sequences/slave sequences/
./src/hvl_ top/test

./src/hdl_ top/slave_agent_bfm

./src/hdl_ top/apb interface



Fig: 1.2 Directories included in apb_compile.f file

b. Packages included:



~~ ~~ ™~ ™ ™ ™ ™



../src/globals/apb global_pkg.sv

../src/hvl_top/master/apb_ master_pkg.sv
../src/hvl_top/slave/apb slave pkg. sv
../src/hvl_top/test/sequences/master sequences/apb master seq pkg.sv
../src/hvl_top/test/sequences/slave sequences/apb slave seq pkg.sv
../src/hvl_top/env/apb env_pkg.sv
../src/hvl_top/test/virtual_sequences/apb virtual seq pkg.sv
../src/hvl_top/test/apb base test pkg.sv





Fig: 1.3 Packages included in apb_compile.f file





c. Static files included:



../src/hdl top/apb if/apb if.sv
../src/hdl_top/master_agent_bfm/apb master _driver_bfm.sv
../src/hdl_top/master_agent_bfm/apb master monitor bfm.sv
../src/hdl top/master agent bfm/apb master agent bfm.sv
../src/hdl top/slave agent bfm/apb slave driver bfm.sv
../src/hdl_top/slave agent _bfm/apb slave monitor bfm.sv
../src/hdl_top/slave agent _bfm/apb slave agent_bfm.sv
../src/hdl top/hdl_ top.sv

~~N NNN NN







Fig: 1.4 static files included in apb_compile.f file

In Makefile, we include the apb_compile.f file to compile all the files included.
Command used : irun -fapb_compile.f +UVM_TEST NAME=<test_name>
+uvm_verbosity=UVM_HIGH.



compile:
make clean compile;
make clean simulate;
vlib work;
vlog -sv \
+acc \
+cover \
+fcover \
-l apb compile.log \
-f ../apb compile. f







Fig: 1.5 APB_compile.f used in makefile for questa_sim tool







irun -c \
-clean \
-elaborate \
-coverage a \
-access +rwc \
-64 \
-sv \
-uvm \
+access+rw \
-f ../apb_compile.f \
-L apb compile.log \
-top worklib.hdl top:sv \
-top workLlib.hvl_ top:sv \
-nclibdirname INCA Libs \
-SVA





Fig 1.6 APB_compile.f used in makefile for cadence tool

10
