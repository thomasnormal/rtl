## 6. Operation Modes

### 6.1 Manager/Subordinate Mode

The AXI4 AVIP can be configured as either:
- **Manager (Master)**: Initiates transactions
- **Subordinate (Slave)**: Responds to transactions

### 6.2 Independent Mode

In Independent mode, the Manager and Subordinate operate independently. The Manager can issue transactions without waiting for responses to previous transactions (up to the configured outstanding transaction limit).

### 6.3 Cooperative Mode

In Cooperative mode, the Manager and Subordinate coordinate their operations. The Subordinate can insert waits states and control transaction flow.

### 6.4 AXI4-Lite Mode

When configured for AXI4-Lite:
- Burst length is fixed at 1
- All burst attributes are disabled
- Only single transfers are supported

---
