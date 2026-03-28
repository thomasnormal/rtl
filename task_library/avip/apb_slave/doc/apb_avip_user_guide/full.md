APB AVIP Project

USER GUIDE

 
 

Contents
List of Tables

List of Figures

Chapter 1
Introduction
1.1 APB master avip
1.2 APB slave avip
1.3 APB Interface
1.4 apb_compile.f file

Chapter 2
Architecture

Chapter 3
Steps to run Test Cases

3.1 Git steps

3.2 Mentor’s Questasim
3.2.1 Compilation
3.2.2 Simulation
3.2.3 Regression
3.2.4 Coverage

3.3 Cadence
3.3.1 Compilation
3.3.2 Simulation
3.3.3 Coverage

Chapter 4
Debug Tips
4.1 APB Debugging Flow
4.1.1 Check for Configuration Values
4.1.1(a) Master agent configurations
4.1.1(b) Slave agent configurations
4.1.1(c) Environment configuration
4.1.2 Check for transfer size
4.1.3 Check for transaction values
4.1.4 Check for master and slave converter data packets
4.1.5 Check for data received from BFM
4.1.6 Check for data received from monitor BFM
4.2 Scoreboard Checks
4.3 Coverage Debug
4.4 Waveform Viewer

NNDDWDUUNH NY WN

—
—

NO NO NN NN RRR RR Ke eS =
BW WW OO wo fh HBR HWW WC

WWW WwWwWNnN NN NNN N NN WK
NWWnNnrR OD WDWANADA VMN wv
 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

Chapter 5 38
References 38

List of Tables

Table No | Table Name Page No

Table 4.1 | master configurations 27

Table 4.2 | slave configurations 28

Table 4.3 | environment configurations 29
List of Figures

Figure No_ | Name of the Figure Page No

1.1 APB AVIP 5

1.2 Directories included in apb_compile.f file 7

1.3 Packages included in apb_compile.f file 8

1.4 Static files included in apb_compile.f file 8

1.5 apb_compile.f used in makefile for questa_sim tool 8

1.6 apb_compile.f used in makefile for cadence tool 9

2.1 apb avip architecture 10

3.1 Usage of the make command 13

3.2 Questasim WLF window 14

3.3 Screenshot of adding waves in wave window 15

3.4 Wave window 15

 

 

 

 

 
 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

3.5 Screenshot of unlocking the wave window 16
3.6 Screenshot of unlocked the wave window with signals 16
3.7 Screenshot showing way to see the name of the signals 17
3.8 Files in questasim after the regression 18
3.9 Coverage Report 19
3.10 Screenshot of opening covergroups 20
3.11 Screenshot of opening slave covergroup 20
3.12 Shows way to open slave covergroup coverage report 20
3.13 Screenshot of coverpints and cross coverpoints 21
3.14 PADDR _CP coverpoint report 21
3.15 Usage of make command in cadence 22
3.16 Simulation report in Cadence 23
4.1 Debugging flow 24
4.2 Master_agent_config values 25
4.3 Slave _agent_config values 26
4.4 Env_config values 27
4.5 Transfer size for pwdata 27
4.6 Master_tx values 28
4.7 Slave_tx values 28
4.8 Converted data of master req 29
4.9 Converted data of slave req 29
4.10 Master bfm_ struct data 30
4.11 Slave bfm_struct data 30
4.12 Master_driver_bfm values 30
4.13 Slave_driver_bfm values 31
4.14 Master_monitor values 31
4.15 Slave monitor values 31

 

 

 

 
 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

 

4.16 Scoreboard checks 32
4.17 Coverage for master 32
4.18 Coverage for slave 32
4.19 Master and slave coverage 33
4.20 Instance of cover group 33
4.21 Master_coverage coverpoint 33
4.22 Master_coverage crosses coverpoints 34
4.23 Slave_coverage coverpoint 34
4.24 Slave_coverage crosses coverpoints 34
4.25 Waveform for the 8 bit write when reset is low 35
4.26 Waveform for 8-bit write idle-state 36
4.27 Waveform for 8-bit write setup-state 36
4.28 Waveform for 8-bit write access-state 37
4.29 Waveform for the 8 bit write transfer with repeat of 5 times 37

 

 
 

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
 

Chapter 3

Steps to run Test Cases

3.1 Git steps

1.

Checking for git, open the terminal type the command

git version

The output will either tell you which version of Git is installed or alert you that git is
an unknown command. If it's an unknown command, install Git using following link
guide to install git in other platforms

Copy the ssh public key and do the clone of the APB_avip repository in the terminal
find the apb_avip GitHub repository here

git clone git@github.com:mirafra-software-technologies/apb_avip.git

After cloning, change the directory to the cloned repository

cd apb_avip

After cloning you will be in the main branch 1.e, the production branch

git branch

Do the pull for the cloned repository to be in sync

git pull origin main

Fetch all branches in the apb_avip repository

git fetch

Check all branches present in the apb_avip repository
git branch -a

To switch from the main branch to another branch

git checkout origin <branch_name>

Do the pull for the cloned repository to be in sync

git pull origin <branch_name>

Note: To run any test case you should be inside the cloned directory i.e, apb_avip [apb_avip
is considered as root path]

13
 

3.2 Mentor’s Questasim

1.

Change the directory to questasim directory where the makefile is present
Path for the mentioned directory is apb_avip/sim/questasim

Note: To Compile, simulate, regression and for coverage you must be in the specified
path i.e, apb_avip/sim/questasim

To view the usage for running test cases, type the command
make

Fig 3.1 shows the usage to compile, simulate, and regression

make target <options> <variable>=<value>

To compile use:
make compile

To simulate individual test:
make simulate test=<test name> uvm verbosity=<VERBOSITY LEVEL>

Example: :
make simulate test=base test uvm verbosity=UVM HIGH

To run regression:
make regression testlist name=<regression testlist name.list>

Fig 3.1 Usage of the make command

3.2.1 Compilation

1.

Use the following command to compile
make compile

Open the log file apb_compile.log to view the compiled files
gvim apb_compile.log

3.2.2 Simulation

1.

After compilation, use the following command to simulate individual test cases
make simulate test=<test_name> uvm_verbosity=<VERBOSITY LEVEL>
Example:

To view the log file
gvim <test_name>/<test_name>.log

Ex: gvim apb_8b_write_test/apb_8b_write_test.log

14
 

Note: The path for the log file will be displayed in the simulation report along with
the name of the simulated test

3. To view waveform
vsim -view <test_name>/waveform.wlf &
Ex: vsim -view apb_8b_write_test/waveform.wlf &

Note: The command to view the waveform will be displayed in the simulation report
along with the name of the simulated test

4. As you run the above command, the new WLF Questasim window will appear as
shown in fig 3.2

 

File Edit View Add Bookmarks Window Help

8 waveform - Default

B-s@OSCG 2G 2 C-Me BO-Me  %8-3-CH-9B
* Instance Design unit Design unittype (Top Category Visibility Total coverage Ass
=) wf hdl_top hdl_top Module DU Instance +acce<...

af intf apb_if Interface DU Instance +acc=<...

-) af apb_slave_agent_b... hdl_top vViGenerateBlock - +acc=<...

-- wz apb_slave_agen... apb_slave_... Module DU Instance +acc=<...

Af intf apb_if Interface DU Instance tacc=<...

= af apb_slave_dr... apb_slave_... Interface DU Instance tacc=<...

4 wait_for_s... apb_slave_... Task - tacce<...

44 wait_for_a... apb_slave_... Task - +acc=<...

= af apb_slave_m... apb_slave_... Interface DU Instance +acc=<...

44 sample_d... apb_slave_... Task . +acc=<...

-) 44 apb_master_agent... apb_master... Module DU Instance +acc=<...

A intf apb_if Interface DU Instance tacc=<...

= wf apb_master_drv... apb_master... Interface DU Instance tacc=<...

wf drive_to_bfm  apb_master... Task - +acce<...

af drive_setup_... apb_master... Task . +acc=<...

af waiting_in_a... apb_master... Task - +acc=<...

af detect_wait_... apb_master... Task - +acc=<...

-} wd apb_master_mo... apb_master... Interface DU Instance t+acc=<...

wi sample_data apb_master... Task - tacc=<...

+) af uvm_pkg uvm_pkg ViPackage Package +acce<...
+) af questa_uvm_pkg questa_uv... ViPackage Package +acce<...

 

 

Fig 3.2 Questasim WLF window

5. Right-click on intf and select Add Wave as shown in the image 3.3 to add the signals
to the wave window

15
 

cE eerie je] x]

   
     
 

 

 

* Instance Design unit Design unit type (Top Category Visibility Total coverage Assertionshit Asse
=) af hdl_top right click on intf ule DU Instance +acc=<...
; rface DU Instance t+acce<.,,,
-) a ap ew Declaration ViGenerateBlock - +acc=<...
= g SEE soduie DU Instance ¢acc=<...
Interface DU Instance tacc=<...
> ”>_. Interface DU Instance +acc=<...
Task - +acce<...

Pas
clickonadd waves |k - +acc=<..,
- ee | | =<...
Add Wave Ctri+W > nterface DU Instance tacc=<
>... Task +acc=<..,

ter... Module DU Instance +acc=<...

=f ap Add Wave New
A” T ” Interface DU Instance tacc=<...
=) gf Add Dataflow Ctrl+D ter... Interface DU Instance +acce<...
Add to ter... Task - +acce<..,
ter... Task - +acc=<..,
Copy Ctrl+C ter... Task - +acc=<.,,
Find... Ctrl+F ter... Task - +acc=<..,
~ wd Save Selected... ter... Interface DU Instance +acc=<...
ter... Task - tacc=<...
+) af uvm_ Expand Selected viPackage Package +acce<...

Collapse Selected

Bi Library | Collapse All =

4 Transcrip

 

#77 ie 0 ,
a// Test A »
# apb 8b w xy yened as dataset “waveform”
VSIM 1> Show »

Fig 3.3 Screenshot of adding waves in wave window

6. After adding wave, click on Wave window as shown in the Fig 3.3

 

i
Onstolus {hdl_top/intf/pready
2 la shwetapatil@HweServer:questa_sim a Questa Sim 10.6c (WLF View) Clare >

 

 

 

Fig 3.4 Wave window

7. Click as shown in the fig 3.4 to unlock the waveform window

16
 

 

 

KClick here to unlock the window]

 

 

 

 

Fig 3.5 Screenshot of unlocking the wave window

You will be able to get a separate wave window as shown in the Fig 3.5

 

File Edit View Add Format Tools Bookmarks Window Help

 

 

a Da eee
POOSS (OBO DME OPAAH Pati*Ladt 7499-9 KHSucib goey.ils

> w) Be i, QQA SYS LI @
\: a ~

Em UT sae PO

 

CU ae

aR LU ae
6-4 {hdl top/intfipr...
RC uu Ce
TO LU) ae

1h

6-4 [hdl top/intf/pselx} ‘hd
RC LU ae
[eC LU
SLU) ae
Le LU a
[ee LUT

1h0
EPR C
Vhl

Cary

BL od
rh)
Eyer
Mu

Bub)

Nee 000080 ne ony)

n ] 6

eT ark PicAWe OTT

Fig 3.6 Screenshot of unlocked the wave window with signals

ATE

9078ed77

 

Click on the icon signal toggle leaf name marked in fig 3.6 to see the signals as shown

17

 

 
 

 

lal hap

eles a lhl

Pha lhl

penable 1'ho

paddr 32'h00000014
lial) lhl

pstrb ror]

pwdata Bye le: bal
lesb aap

prdata ByMibe tet e et
elas 1'ho

pprot Bhi)

 

 

 

Fig 3.7 Screenshot showing way to see the name of the signals

10. For the analysis of waveform, go through the link below

Waveform Viewer

3.2.3 Regression
1. Torun regression for all test case
make regression testlist_ name=<regression_testlist_name.list>
Ex: make regression testlist_ name=apb_regression.list

Note: You can find all the test case names in the path given below
APB_avip/src/hvl_top/testlists/apb_regression.list

2. After regression, you can view the individual files as shown fig 3.7

ls

18
 

 

apb 16b write test 26122021-220236

apb 24b write test 26122021-220239

apb 8b read test 26122021-220245

apb 8b write read test 26122021-220242
apb 8b write test 26122021-220228

 

 

 

Fig 3.8 Files in questasim after the regression

3. To view the log files of individual test, select the interested test case file, go inside
that directory

Ex:Interested in the test case apb_Sb_write_test

Go inside the directory of interested testcase with the date
apb_8b_write_test_26122021-220228

Inside this directory, you will be able to find the log file of the interested test case
apb_8b_write_test.log

Path:

apb_8b_write_test_26122021-220228/apb_8b_write_test.log

3.2.4 Coverage

1. To see coverage
a. After simulating

For the individual test, use the command firefox
firefox apb_8b_write_test/html_cov_report/index.html &
Ex: firefox apb_8b_write_test/html_cov_report/index.html &

Note: The command to see the coverage will be displayed in the simulation report
along with the name of the simulated test

b. After the regression,
e To view the coverages of all test cases, type the below command

firefox merged_cov_html_report/index.html &

Note: The command to see the coverage will be displayed in the simulation report
along with the name of the simulated test

e To view the coverage for individual test case
See the list of files generated after regression, which is shown in fig 3.7.

Select the interested test case file, go inside that directory

19
 

Ex:

Interested in the test case apb_8b_write_test

Go inside the directory of interested testcase with the date
ADD

Inside this directory, you will be able to find the html coverage file of the interested
test case

html_cov_report/
Inside it would be the html file
covsummary.html

Command to view coverage report for the above test case will be

ADD

2. The coverage report window appears as shown in fig 3.8

 

Questa Coverage Report x | +

 

 

 

 

 

 

ee ® file:///hy Mwork.. pb_avip/sim/questa_sim/apb_8b_write_test/html_cov_report/page: +» © yy hoe =
@ Centos Wiki @ Documentation @ Forums
EEG
[ESRI Design pesunits, | QUesta Coverage Report
: Shot tep Number of tests run: 1
mapb Passed: 1
4 Warning: 0
) wlapb_slave_pkg
» glapb_slave_seq_pkg Error: 0
) glapb_master_pkg Fatal: 0
#! zlapb_master_seq_pkg
Hf) wlapb_env_pkg List of tests included in report..
 wlapb_virtual_seq_pkg
 gapb_base test_pkg List of global attributes included in report...
A
4 List of Design Units included in report...
A
A
4 Coverage Summary by Structure: Coverage Summary by Type:
Design Scope « Hits % « Commer) Total Coverage:
Coverage
hvl top 100.00% 10.00% ‘Type< Bins « Hits « Misses « Weight «
hdl_top 45.15% | 58.55% | Covergroups, 4303 14 4289 1
sb _elasie_scromt hfs lO Liem elas _sccont hfs _h AA 2LOL 5? 9M. Chotems cute 1nAD AAQ ROR 4
cP | BBB shwetapati@HweServerquesta-sim || @@y Questa Coverage Report - Mozilla Fi.

 

 

 

Fig 3.9 Coverage Report

3. Scroll down to the coverage summary by type and click on covergroups shown in fig
3.9.

20
 

 

 

Coverage Summary by Type:

 

     

(36.20%) 39.50%

=< -

 

 

 

 

 

(Covergroups> 44021 23) 1.47.72% 60.62%
Statements 1185) 452! 733) 1/38.14%) 38.14%
Branches 902. 231. 671. 1/25.60%| 25.60%
FEC

Conditions 13 4 9 1/30.76% 30.76%
Toggles 1107. 469 638. 1 42.36% 42.36%

 

 

 

 

3.10 Screenshot of opening covergroups

4. After opening covergroup you will be able to see the summary.click on as shown in
the fig 3.10 to slave covergroup

 

Covergroups Coverage Summary:

Search:

 

slave_pkg/apb_slave_coverage/apb_slave_cover: 2150 6 2144 0.27% 19.54% 19.54%

 

 

 

 

3.11 Screenshot of opening slave covergroup

5. If clicked on slave covergroup, further it opens to another window, again click on the
slave covergroup as shown in fig 3.11

 

Questa Covergroup Coverage Report

Search: | cvg:apb_slave_covergroup

 

click on slave coverage
© Covergro pb slave covergroun > 2150 6 2148 O.27% 19.54% 19.54%

© Instance \/apb_slave_pkg::apb_slave_coverage::apb_slave_covergroup 2150 6 2144 (0.27% «= 19.54% 19.54%

 

 

 

3.12 Shows way to open slave covergroup coverage report

21
 

6. Further, you will be able to see coverpoints and crosses as shown in fig 3.12

 

Scope: /apb_slave_pkg/apb_slave_coverage

Covergroup type:

apb_slave_covergroup

Coverpoints 102 5 4.90%

Crosses 2048 1 0.04%

Search:

@ pappr cP 32 1 31 3.12% 3.12%
© PRDATA CP 32 1 31 3.12% 3.12%
6 PSELX_CP 2 1 1 50.00% 50.00%
@ psLvERR cP 2 1 1 50.00% 50.00%
© pwoata cp 32 0 32 0.00% 0.00%
6 PWRITE_CP 2 1 1 50.00% 50.00%

 

3.12

3.12

0.00

 

Fig 3.13 Screenshot of Coverpints and cross coverpoints

7. Click on individual coverpoints and crosses to see the bins hit, here PADDR_CP is

individual coverpoint in fig 3.13

 

Scope: /apb_slave_pkg/apb_slave_coverage
Covergroup type: apb slave covergroup
Coverpoint: PADDR_CP
Search:

Se ee ee,
addr[0) 1 5
addr[1] 1 0
addr[2) 1 0
addr[3] 1 0
addr[4] 1 0
addr[5} 1 0
addr[6] 1 0
addr[7] 1 0
addr[8] 1 0
addr[9} 1 0
addr[10] 1 0

 

 

 

Fig. 3.14 PADDR_CP coverpoint report

22
 

8. For the analysis of coverage report, click on the link Coverage Debug

3.3 Cadence
1. Change the directory to questasim directory where the makefile is present
Path for the mentioned directory is APB_avip/sim/cadence_sim

Note: To Compile, simulate, regression and for coverage you must be in the specified
path i.e, apb_avip/sim/cadence_sim

2. To view the usage for running test cases, type the command
make

Fig 3. shows the usage to compile, simulate, and regression

make target <options> <variable>=<value>

To compile use:
make compile

To simulate use:
make simulate test=<test name> uvm verbosity=<VERBOSITY LEVEL>

Example: :
make simulate test=base test uvm verbosity=UVM HIGH

Fig 3.15 Usage of make command in cadence

3.3.1 Compilation
1. Use the following command to compile
make compile
2. Open the log file apb_compile.log to view the compiled files
vim apb_compile.log
3.3.2 Simulation
1. After compilation, use the following command to simulate individual test cases
make simulate test=<test_name> uvm_verbosity=<VERBOSITY LEVEL>

Example:

23
 

Note: You can find all the test case names in the path given below
apb_avip/src/hvl_top/testlists/apb_simple_fd_regression.list

2. To view the log file
gvim <test_name>/<test_name>.log

Ex: gvim apb_8b_write_test/apb_8b_write_test.log

Note: The path for the log file will be displayed in the simulation report along with
the name of the simulated test

Simulator Errors

 

UVM Fatal

Number of demoted UVM FATAL reports : e
Number of caught UVM FATAL reports : 0
UVM FATAL : 0

UVM Errors

Number of demoted UVM ERROR reports : 0
Number of caught UVM ERROR reports ; 0
UVM_ERROR : 0

UVM Warnings

Number of demoted UVM WARNING reports: 0
Number of caught UVM WARNING reports : 0
UVM WARNING : 0

 
   
    
 
 

name: apb 8b write test
Log file path: apb_8b write test/apb 8b write test.log
Wa m: vsim -view apb 8b write test/wavefor

 

[MSIS@vl-08 cadence sim]$ Jj

Fig 3.16 Simulation report in cadence

3. To view waveform
simvision waves.shm/

Ex: simvision waves.shm/

Note: The command to view the waveform will be displayed in the simulation report
along with the name of the simulated test as waveform shown in the fig 3.15

3.3.3 Coverage

Command to see the coverage after simulation : imc -load cov_work/scope/test

24
 

Chapter 4
Debug Tips

As design complexity continues to increase, which is contributing to new challenges in
verification and debugging. Fortunately, new solutions and methodologies (such as UVM)
have emerged to address growing design complexity. Yet, even with the productivity gains
that can be achieved with the adoption of UVM, newer debugging challenges specifically
related to UVM need to be addressed.

Here apb_8b_write_test has been used as an example test case in order to show the below
debugging flow of the APB protocol and all the info’s have been runned using UVM_HIGH
verbosity

4.1 APB Debugging Flow

Initially, open with a log file which is inside the test folder that has been run and then follow
the below procedure in order to have a debug flow.

Inside log file

 

Check for config
values

For each test

Check for transfer
size for address,
wdata and rdata

For Each
Transaction

Check for master_tx
and slave_tx values

Check for master
and slave converter
data packets

 

   
  

 

 

 

 

 
   
   
  

Check for data
received from BFM

 

 

Check for data
received from
Monitor BFM

 
 

 

Fig 4.1 Debugging flow

25
 

4.1.1 Check for Configuration Values

At this stage, the user is trying to check for all the values related to master agent, slave agent
and environment configurations which have been generated from the test.

For more information on Configurations please visit the following link:

Configuration Doc

4.1.1(a) Master agent configurations

Master agent configurations Includes

Table 4.1 master configurations

 

Configurations

conditions for the configurations

 

No of Slaves

which should not equal to zero

 

has_coverage

Which indicates the coverage connection

 

master_min_addr_range_array[0]

Which indicate the minimum address range for master

 

master_max_addr_range_array[0]

 

 

Which indicate the maximum address range for master

 

 

 

 

# UVM_INFO ../../src/hvl_top/test/apb base test.sv(73) @ 0: uvm_test_top (apb_s>_write_tesf)
# APB MASTER AGENT CONFIG

$v nee eee eee ee ee eee eee eee

# Name Type Size Value

owen ne eee eee ee ee ee ee ee eee eens

# apb master_agent_config apb master agent config - @497 master_agent.con
# is active integral 1 1 fig 7 -

# has coverage integral 1 1

# no_of_ slaves integral 32 ‘dl

# = master_min_addr_ range array[0] integral 32 "ha

# = master_max_addr_range array[0] integral 32 *h1003

$e n nee  eeeeeeeee

 

Figure 4.2 shows the different config values that have been set in master agent config class

Fig 4.2 master_agent_config values

4.1.1(b) Slave agent configurations

Slave agent configurations Includes

26

 
 

Table 4.2 slave configurations

 

 

 

 

 

Configurations conditions for the configurations
has_coverage Which indicates the coverage connection
Slave_id Tells which slave is selected
max_address Which indicates the maximum address for slave
min_address Which indicates the minimum address for slave

 

 

 

 

 

mt 1NFo ../../src/hvl_top/test/apb base test.sv(133) @ 0: uvm_test_top [apb_8> write test]
# APB SLAVE CONFIG[0]

# ------------ - ee ee ee ee ee ee ee ee ee ee ee ee eee eee

# Name Type Size Value

owen nn eee
# apb slave _agent_config[0] apb slave agent config - @502 apb_slave_agent_config
# is active string 10 UVM ACTIVE

# slave _id integral 32 ‘do

# has coverage integral 1 1

# =  max_address integral 32 "h1003

# min_address integral 32 "h4

Hw ne ee ee ee ee ee ee ee eee

 

 

Fig 4.3 slave_agent_config values

Figure 4.3 shows the different config values that has been set in slave agent config class

4.1.1(c) Environment configuration

Environment configuration includes

Table 4.3 environment configurations

 

 

 

 

Configurations conditions for the configurations
has_scoreboard which tells how many scoreboards are connected to env. Which has to be at least 1
has_virtual_seqr which tells how many virtual seqr are connected to env Which has to be at least 1
No_ of slaves Tells how many slaves are connected Which shouldn’t be 0

 

 

 

 

27

 
 

 

¥

# UVM_INFO ../../src/hvl_top/test/apb base test.sv(78) @ 0: uvm test top [apb_8b write test]
# APB ENV CONFIG

fone eee een ee eee eee eee eee eee

# Name Type Size Value

fon ne nee ee ee eee eee

# apb_env_cfg h apb env_config - @496 apb_env_config
# has scoreboard integral 1 1

# has virtual_seqr integral 1 1

# no_of_ slaves integral 32 ‘dl

fone eee eee eee ee ee ee ee eee eee

 

 

 

Fig 4.4 env_config values

Figure 4.4 shows the different config values that has been set in env config class

4.1.2 Check for transfer size

APB transfers the data based on pstrobe signal. Each pstrobe lane can transfer a byte data.
The pstrobe lane becomes high based on transfer size declaration only.

+ Name Type Size Value

 

Fig 4.5 Transfer size for pwdata

4.1.3 Check for transaction values

Once the config values and size of the transfers are correct then check for the data to be
transmitted from master_tx class or from slave_tx class

Initially check for the idle state of the transaction.(Ex: In this case pselx = 0 and penable = ).

Once the present is high based on the pclk edge,when the pselx becomes high the data will be
sampled on the same clock edge.

28
 

 

# UVM_INFO ../../src/hvl_top/master//apb mast : uvm_test_top.apb env.apb master_agent.apb_master_seqr_h@

 

 

HR HH HH HH

 

 

 

 

 

err

no_of wait
choose pa

 

 

 

 

Fig 4.7 slave_tx values

Figure 4.6 and 4.7 shows the transaction data related to the master and slaves side.

4.1.4 Check for master and slave converter data packets

In the master and slave converter class the data coming from the req will convert into struct
packet in from class and once the data driving and sampling done the data can be revert back
to req using to_class method.

29
 

 

 

UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter

../../src/hvl_top/master/ /apb nas ter seq item [converterisv(ss) @ 340:

[apb master_seq item conv] ----------------------------- +--+ 2 ee eee e eee eee

../../src/hvl_top/master//apb_ master seq item converter.sv(92) @ 340:

[apb master_seq item conv_class] After randomize pprot = 101

../../src/hvl_top/master//apb_ master seq item converter.sv(96) @ 340:

[apb master_seq item conv_class] After randomize pselx = 0000000000000001

../../src/hvl_top/master//apb_master_seq item converter.sv(99) @ 340:

[apb master_seq item conv_class] After randomize pwrite = 1

../../src/hvl_top/master//apb_ master seq item converter.sv(102) @ 340:

[apb master_seq item conv_class] After randomize paddr = 14

../../Sr¢/hvl_top/master//apb master S€q item cofverteFisv(105) @ 340:

[apb master_seq item conv_class] After randomize pwdata = 9078ed77

../../Sr¢/hvl_top/master//apb master S€q item cofverterisv(108) @ 340:

[apb master_seq item conv_class] After randomize pwdta = 0100

../../stc/hv\_top/master//apb master séq item converterisv(112) @ 340:

[apb master_seq item conv_class] After randomize pslverr = 0

../../src/hvl_top/master//apb_ master seq item converter.sv(115) @ 340:

[apb master_seq item conv_class] After randomize prdata = 0

../../sr¢/hwl_top/master//apb master séq item converterisv(118) @ 340:

[apb master_seq item _conv_class] After randomize no of wait states =0

../../sr¢/hvl_top/master//apb master S€q item cofiverterisv(120) @ 340:

[apb master_seq item conv] ---------------------------------------------- E-

  

 

 

 

 

Fig 4.8 converted data of master req

 

 

UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter
UVM_INFO
reporter

../../src/hv\_top/s ave /apb Save S64 i ten COAVEFEEFISV(93) @ 340:

[apb seq item conv_to class] --

ween eee eeeee SLAVE SEQ ITEM CONVERTER TO CLASS--------------------

../../src/hv_top/slave/apb_ Slave! Séq, item converteFisv(96) @ 340:

[apb seq item _conv_class] After randomizing the paddr=14

../../St¢/h\_top/slave/apb Slave Seq, item Converter/Sv(100) @ 340:

[apb seq item _conv_ class] After randomizing the pwdata=9078ed77

../../src/hvl_top/slave/apb_slave_seq item converter.sv(104) @ 340:

[apb seq item _conv_class] After randomizing the psel=1
../../src/hvl_top/slave/apb slave seq item converter.sv(108) @ 340:
[apb seq item conv_class] After randomizing the pprot=5b
../../src/hvl_top/slave/ (112) @ 340:
[apb seq item conv_class] After randomizing the pslverr=0

../../St¢/h_top/slave/apb Slave Seq, item Converter.sv(116) @ 340:

[apb seq item conv_class] After randomizing the pwrite=1

../../src¢/hvl_top/slave/apb_slave_seq item converter.sv(119) @ 340:

[apb seq item conv_class] After randomizing the prdata=0

../../stc/hv\_top/slave/apb Slave seq item convérter.sv(122) @ 340:

[apb seq item _conv_class] After randomizing the no of wait states=0

../../St¢/h\_top/slave/apb Slave seq, item Converter.sv(124) @ 340:

[apb seq item conv_to class] --

 

 

 

 

 

 

Fig 4.9 converted data of slave req

30

 
 

4.1.5 Check for data received from BFM

Once the data has been randomized and sent to master or slave BFMs. The master driver
BFM will drive paddr,pwrite,pstrobe,pwdtata signals and samples the prdata,pslverr,pready
depending on configurations of master and similarly slave driver BFM will drive the
prdata,pready,pslverr signal and samples the paddr,psel,pwrite,pwdata depending on
configurations of slave.

The master driver BFM will print both the all the signals which has been driven by the master
and sampled data master and similarly slave driver BFM will print all the signal which

has been driven by the slave and sampled data. At the end both the master BFM and

slave BFM data has to be the same.

 

# UVM_INFO ../../src/hdl_top/master_agent_bfm/apb_master_driver_bfm.sv(83) @ 290: reporter [APB MASTER DRIVER BFM] data_packet=
# ‘{pwrite:1, pslverr:0, pprot:5, pselx:1, pstrb:4, prdata:0, paddr:20, pwdata:2423844215, no_of_wait_states:0}

 

 

 

Fig 4.10 master bfm_struct data

 

# UVM_INFO ../../src/hvl_top/slave/apb_slave driver proxy.sv(210) @ 350: uvm_test_top.apb env.apb slave agent _h[@].apb slave drv proxy h
# [DEBUG_NA] AFTER PSLVERR_CHECK_1 struct ::
‘{pwrite:1, pslverr:0, pprot:5, pselx:1, pstrb:4, prdata:@, paddr:20, pwdata:2423844215, no of wait states:0}

 

 

 

Fig 4.11 slave bfm_struct data

The fig 4.10 and 4.11 shows the data with respect to pwrite,pradata,pwdata,pprot,pslverr,pstrb
signals of both master and slave end before converting back to req using to_class converter.

 

# UVM_INFO ../../src/hvl_top/master/
er_proxy] REQ-MASTER_TX

 

v(109) @ 110: uvm_test_top.apb env.apb_master_agent.apb_master_drv_proxy_h [apb_master_dri

 

 

 

 

Fig 4.12 master_driver_bfm values

31
 

 

    
 

k UVM_INFO ../../src/hvl_top/slave/ay ‘ive

V p //111) @ 190: uvm_test_top.apb env.apb slave_agent_h[0].apb slave drv_proxy_h [DEBUG_NA] AFTER
PSLVERR_CHECK_5 -struct:: ‘{pwrite:1, pslverr:0, pprot

, pselx:1, pstrb:4, prdata:0, paddr:3200, pwdata:3909941715, no_of_wait_states:0}

 

SH HH HH HH H

 

 

Fig 4.13 slave_driver_bfm values

Fig 4.13 and 4.14 shows the psel, paddr, pwrite, pwdata, pready, prdata, pslverr, pprot values
from master and slave bfm driver after converting back to req.

4.1.6 Check for data received from monitor BFM

Once the data has been driven or sampled monitor will capture the data and it will print the
driven and sampled data in the req form or transaction level

 

   

# UVM INFO ../../src/hvl_top/master//apb_ ma mon. proxy 8) @ 220: uvm_test_top.apb env.apb master_agent.apb_master_mon_proxy_h [apb_master_moni

FF FEF FEF TF FF

 

 

 

Fig 4.14 master_monitor values

 

  

k UVM_INFO ../../src/hvl_top/slave/apb slave monitor prc
tor_proxy] Received packet from SLAVE MONITOR BFM: ,

 

y.Sv(100) @ 220: uvm_test_top.apb_env.apb_slave_agent_h[0].apb_slave_mon_proxy_h [apb_slave_moni

# Name Type Size Value
Bonen ee eee

  

# apb slave tx apb slave tx - 1273

eR HH HH

*

 

 

 

Fig 4.15 slave_monitor values

32

 
 

4.2 Scoreboard Checks

And finally we have scoreboard checks which basically compares the paddr, pwrite, prdata,
pwdata, pprot data of master with the slave side

 

# -------- ~~ 2 ee ee ee ee ee eee ee ee ee eee SCOREBOARD COMPARISIONS - - - -------------------------- 2-2-2 ee eee eee eee eee
# UVM_INFO ../../src/hvl_top/env/apb_scoreboard.sv(162) @ 280: uvm_test_top.apb_env.apb_ scoreboard h [apb_ scoreboard]

# apb_pwdata from master and slave is equal

# UVM_INFO ../../src/hvl_top/env/apb scoreboard.sv(164) @ 280: uvm_test_top.apb_env.apb scoreboard _h [SB_PWDATA MATCHED]
# Master PWDATA = 'hf60966cO and Slave PWDATA = 'hf60966c0

# UVM_INFO ../../src/hvl_top/env/apb scoreboard. sv(188) @ 280: uvm_test_top.apb env.apb scoreboard h [apb scoreboard]

# apb_paddr from master and slave is equal

# UVM_INFO ../../src/hvl_top/env/apb scoreboard.sv(190) @ 280: uvm_test_top.apb_env.apb_scoreboard_h [SB_PADDR_MATCH]

# Master PADDR = 'hf60966cO0 and Slave PADDR = 'hf60966c0

# UVM_INFO ../../src/hvl_top/env/apb scoreboard.sv(216) @ 280: uvm_test_top.apb_env.apb scoreboard h [apb scoreboard]

# apb_pwrite from master and slave is equal

# UVM_INFO ../../src/hvl_top/env/apb scoreboardisyv(218) @ 280: uvm_test_top.apb_env.apb scoreboard _h [SB_PWRITE_ MATCH]
# Master PWRITE = ‘hl and Slave PWRITE = ‘hl

# UVM_INFO ../../src/hvl_top/env/apb_scoreboard.syv(246) @ 280: uvm_test_top.apb_env.apb scoreboard _h [apb_scoreboard]

# apb_prdata from master and slave is equal

# UVM_INFO ../../src/hvl_top/env/apb scoreboard.sv(248) @ 280: uvm_test_top.apb_env.apb scoreboard _h [SB_PRDATA MATCHED]
# Master PRDATA = 'hO and Slave PRDATA = ‘hd

# UVM_INFO ../../src/hvl_top/env/apb scoreboard.sv(260) @ 280: uvm_test_top.apb_env.apb scoreboard h [apb scoreboard]

# apb_prdata from master and slave is equal

# UVM_INFO ../../src/hvl_top/env/apbyscoreboardysv (262) @ 280: uvm_test_top.apb_env.apb_ scoreboard _h [SB_PPROT MATCHED]
# Master PPROT = 'h3 and Slave PPROT = ‘h3

# UVM_INFO ../../src/hvl_top/env/apb scoreboardisyv(302) @ 280: uvm_test_top.apb_env.apb scoreboard _h [apb scoreboard] --
#H ~~ - eee eee en ee ee ee ee eee eee eee END OF SCOREBOARD COMPARISIONS - --------------------------------------

 

 

 

Fig 4.16 scoreboard_checks

4.3 Coverage Debug

Coverage is a metric which basically tells how much percentage of verification has been done
to the dut.

Go to the log file, Here it will get you the complete master and slave coverage for the
particular test we are running.

 

# UVM_INFO ../../src/hvl_top/master//apb master coverage.sv(148) @ 350:

# uvm_test_top.apb env.apb master_agent.apb master_cov_h [apb master coverage] APB Master Agent Coverage = 58.75 %

 

 

 

Fig 4.17 coverage for master

 

UVM_INFO ../../src/hvl_top/slave/apb_slave_coverage.sv(118) @ 350:

|ivm_test_top.apb_env.apb_slave_agent_h[0].apb_slave_cov_h [apb slave coverage] Slave Agent Coverage = 62.50 %

 

 

 

Fig 4.18 coverage for slave

For individual bins checking goto the below html file.
firefox apb_8b_write_test/html_cov_report/index.html &

33
 

Inside that check for covergroups in the coverage summary then check for the instance
created for master and slave coverage

 

Covergroups Coverage Summary:

Search:

a ee ee ee ee ee ee
© Japb_master_pkg/apb_master_coverage/apb_master_covergroup 34 15 19 44.11% (58.74% (58.75%
© work.apb_master_pkg::apb_master coverage/apb master covergroup 34 15 19 44.11% — (BB.749%6 58.75%
@ /apb_slave_pkg/apb_slave_coveragelapb_slave_covergroup 10 6 4 60.00% (62.50%) 62.50%
© work.apb_slave_pkg::apb_slave_coverage/apb slave _covergroup 10 6 4 60.00% (62.50%. 62.50%

 

 

 

 

Fig 4.19 master and slave coverage

 

© Covergroup apb_master_covergroup 34 15 19 44.11% = | 58.7496 58.75%

 

@ instance Vapb_master_pkg::apb_master_c....verage::apb_master_covergroup 34 15 19 44.11% | 58.74% 58.75%

 

 

 

 

 

 

Fig 4.20 instance of cover group

Then click on the master covergroup instance to check the individual bins which are hitted
and missed. And here you can even check cross coverages between pwdata, prdata, paddr,
pstrobe.

 

ae a ee eee eee ee)
@ pappR cP 1 1 0 100.00% 100.00% 100.00%
@ PPROT_CP 8 5 3 62.50% 62.50% 62.50%
© PRDATA CP 1 1 0 100.00% 100.00% 100.00%
© pseEL_cP 1 1 0 100.00% 100.00% 100.00%
@ PSLVERR_CP 2 1 1 50.00% 50.00% 50.00%
@ PSTRB_CP 16 4 12 25.00% 25.00% 25.00%
@ pwoaTa ce 1 0 1 0.00% 0.00% 0.00%
© pware cp 2 1 1 50.00% 50.00% 50.00%

 

 

 

Fig 4.21 master_coverage coverpoint

Figure 4.21 shows all the coverpoints included in master coverage

34
 

 

© papp R_CP X PRDATA CP 1 1 0 100.00% 100.00% 100.00%

@ paDDR _CP_X PWDATA CP 1 0 1 0.00% 0.00% 0.00%

 

 

Fig 4.22 master_coverage crosses coverpoints

Figure 4.22 shows all the cross coverpoints included in master coverage

If you click on the slave covergroup instance to check the individual bins which are hitted
and missed. And here you can even check cross coverages between pwdata , prdata, paddr,

 

pstrobe.
a a ee ee ee ee)
@ papprR cP 1 1 0 100.00% 100.00% 100.00%
@ pRDATA CP 1 1 0 100.00% 100.00% 100.00%
© PSELx_cP 1 1 0 100.00% 100.00% 100.00%
@© PSLVERR CP 2 1 1 50.00% 50.00% 50.00%
© pwoaTa cP 1 0 1 0.00% 0.00% 0.00%
@ PWRITE CP 2 1 1 50.00% 50.00% 50.00%

 

 

Fig 4.23 slave_coverage coverpoint

Figure 4.23 shows all the coverpoints included in slave coverage

 

© PADDR_X_PRDATA_ 1 1 0 100.00% 100.00% 100.00%

© PADDR _X_PWDATA_ 1 0 1 0.00% 0.00% 0.00%

 

Fig 4.24 slave_coverage crosses coverpoints

Figure 4.24 shows all the cross coverpoints included in slave coverage

35

 

 

 
4.4 Waveform Viewer

 

32'h00000014
Pape
32'h9078ed77
4'ha

ACCESS

 

Fig 4.25 waveform for the 8 bit write when reset is low

1. In the waveform, initially check for the generation of the system clock(pclk), after
every 10ns it will be toggled as shown in figure 4.25. Once the pclk is done check for
the reset condition(Active low reset) if the reset is low the other signals such as pselx,
penable, paddr, pstrb, pwrite, pwdata, pprot, prdata, pready, pslverr signals should be
in unknown state.

2. Once the reset is high at the next posedge of pclk the psel and penable should come to
idle state i.e., pselx = 0, penable = 0. The other signals paddr, pstrb, pwrite, pwdata,
pprot, prdata, pready, pslverr should be in unknown state.

‘mn o
l'h1
1'h1
a
rer eee ee |
Shs
L'hL

1'h1

reali telelelolon e|
apo

re Lie os ae
P|

ACCESS

  

Fig 4.26 waveform for 8-bit write idle-state

3. After the idle phase is completed, pselx signal should select a slave and penable should be
low which means APB is in SETUP phase i.e., pselx = SLAVE NUMBER, penable = 0.
So, all the signals should be known data.

36
 

 

 

L'h1
1'h1
ae
l'ho
rahe ee ee ee |
cl

ae el lars] +) ‘mae d

Sa aia) iano
e-“& paddr 32'"ho0000014
+ ee Pd hee
“& pwdata 32"h9078ed77
+ oe aad] eae)

* state ACCESS

 

Fig 4.27 waveform for 8-bit write setup-phase

4. Now APB will be in the access phase i.e., pselx =SLAVE_ NUMBER and penable =1, then
check for pready if it is high the access state should end else it should enter wait state and the
transaction is completed.

Fae

a preset_n

#® pready

@ psiverr
ea prdata
+ Beas) is

“& penable

a
e paddr eal hlilele lite -2 0)
me pselx hee
+ eas Le] Ma tists he)
+ a es] Pat

ae et ACCESS

 

Fig 4.28 waveform for 8-bit write access-phase

 

TS a a2

 

Fig 4.29 waveform for the 8 bit write transfer with repeat of 5 times
Figure 4.29 shows the waveform for 5 consecutive write transfers.

37
 

Chapter 5

References

https://github.com/git-guides/install-git

apb_avip_architectural_document

38
