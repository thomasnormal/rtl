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
