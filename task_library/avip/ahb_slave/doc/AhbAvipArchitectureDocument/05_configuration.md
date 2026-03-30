# Chapter 5 - Configuration

## 5.1 Global Package Variables

The AHB AVIP global package defines the core sizing parameters, agent enables, memory layout
settings, and common transaction types used across the environment.

| Name | Type | Description |
| --- | --- | --- |
| `NO_OF_MASTERS` | `integer` | Number of masters connected to the AHB interface. |
| `NO_OF_SLAVES` | `integer` | Number of slaves connected to the AHB interface. |
| `MASTER_AGENT_ACTIVE` | `bit` | Enables or disables the master agent. |
| `SLAVE_AGENT_ACTIVE` | `bit` | Enables or disables the slave agent. |
| `ADDR_WIDTH` | `int` | Address width. |
| `DATA_WIDTH` | `int` | Data width. |
| `HMASTER_WIDTH` | `int` | Bit width for the `HMASTER` signal. |
| `HPROT_WIDTH` | `int` | Bit width for the `HPROT` signal. |
| `SLAVE_MEMORY_SIZE` | `int` | Size of the addressable memory region assigned to a slave. |
| `SLAVE_MEMORY_GAP` | `int` | Address spacing between consecutive slave regions. |
| `MEMORY_WIDTH` | `int` | Width of the underlying memory model. |
| `LENGTH` | `int` | Maximum array size used to store burst transfers. |
| `ahbTransferCharStruct` | `struct` | Structure that holds transaction packet data. |
| `ahbTransferConfigStruct` | `struct` | Structure that holds configuration packet data. |

The package also defines the common enumerated types used across the BFM and transaction code:

- `ahbBurstEnum`: `SINGLE`, `INCR`, `WRAP4`, `INCR4`, `WRAP8`, `INCR8`, `WRAP16`, `INCR16`
- `ahbTransferEnum`: `IDLE`, `BUSY`, `NONSEQ`, `SEQ`
- `ahbRespEnum`: `OKAY`, `ERROR`
- `ahbHsizeEnum`: `BYTE`, `HALFWORD`, `WORD`, `DOUBLEWORD`, `LINE4`, `LINE8`, `LINE16`, `LINE32`
- `ahbProtectionEnum`: normal and privileged, secure and non-secure, data and instruction protection encodings
- `ahbWriteEnum`: `WRITE` and `READ`

The document groups configuration into three major classes:

1. Environment configuration
2. Master-agent configuration
3. Slave-agent configuration

## 5.2 Master Agent Configuration

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `is_active` | `enum` | `UVM_ACTIVE` | Configures the agent as active, with sequencer/driver/monitor, or passive, with monitor only. |
| `hasCoverage` | `bit` | `'d1` | Enables master-agent coverage. |
| `noOfWaitStates` | `int` | `` `d0 `` | Number of extra wait states inserted before a transaction starts. |

## 5.3 Slave Agent Configuration

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `is_active` | `enum` | `UVM_ACTIVE` | Configures the slave agent as active or passive. |
| `hasCoverage` | `bit` | `'d1` | Enables slave-agent coverage. |
| `noOfWaitStates` | `int` | `` `d0 `` | Number of wait states introduced by the slave; declared `rand` for randomization. |

## 5.4 Environment Configuration

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `hasScoreboard` | `bit` | `1` | Enables the scoreboard, which receives transaction-level objects over TLM analysis ports. |
| `hasVirtualSequencer` | `bit` | `1` | Enables the virtual sequencer that coordinates the master and slave sequencers. |
| `noOfSlaves` | `integer` | `'h1` | Number of slaves connected to the interface. |
| `noOfMasters` | `integer` | `'h1` | Number of masters connected to the interface. |
