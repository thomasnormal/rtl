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
