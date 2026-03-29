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
