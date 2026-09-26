# NACHA-Return-Risk-Oracle

**Sub-Second ACH Return (R01/R10) Predictor & Micro-Deposit Risk Oracle (NACHA 0.50% Threshold Circuit Breaker)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![NACHA Operating Rules](https://img.shields.io/badge/NACHA-Risk%20Management%20Framework-blue.svg)](https://www.nacha.org/)
[![Unauthorized Return Cap](https://img.shields.io/badge/NACHA%20Cap-0.50%25%20(R05%2FR10)-red.svg)]()
[![Micro-Entries Rule](https://img.shields.io/badge/NACHA-Micro--Entry%20Rule%20Compliant-green.svg)]()
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0%20(Stdlib%20Only)-success.svg)]()
[![Evidence Vault](https://img.shields.io/badge/Evidence%20Vault-a2zsoc.com-purple.svg)](https://a2zsoc.com)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

---

## Executive Summary: Preventing Existential NACHA Origination Revocations

Originating Depository Financial Institutions (ODFIs) and ACH Originators operate under existential return rate caps codified in the **NACHA Operating Rules & Risk Management Framework**:

1. **The 0.50% Unauthorized Return Rate Cliff**:  
   If an originator's unauthorized return rate (codes **R05, R07, R10, R29, R51**) crosses **0.50%** (5 per 1,000 originations), NACHA initiates formal inquiries, levies severe financial penalties, and mandates originator de-banking.
2. **The 2-to-3 Business Day Blind Spot**:  
   Traditional originators submit ACH batch files blindly over FedACH or EPN and discover returned entries days later—after an unauthorized scam wave has already blown past the 0.50% threshold.
3. **The Micro-Entry Account Validation Mandate**:  
   NACHA rules explicitly require originators to conduct risk-based monitoring on micro-entries used for account validation to prevent credit-push testing and unauthorized ACH debits.

`nacha-return-risk-oracle` is a zero-dependency, sub-second pre-origination engine that predicts **R01 (Insufficient Funds)** and **R10 (Customer Advises Unauthorized)** returns *before* batch transmission, dynamically quarantining toxic entries to guarantee originators operate safely below the 0.50% threshold, Merkle-sealing compliance proofs to the **[a2zsoc.com](https://a2zsoc.com)** Sovereign Evidence Vault.

---

## System Architecture

```mermaid
flowchart TD
    subgraph ODFIIngress["ODFI / Originator Batch Generation"]
        RawBatch["Pending ACH Batch (PPD / WEB / CCD Entries)"]
    end

    subgraph RiskOracle["Sub-Second NACHA Risk Oracle"]
        subgraph NSFModel["Layer 1: R01 (Insufficient Funds) Model"]
            PaydayTiming["Bi-Weekly Payday Decay Curve (Days 0-2 vs 11-14)"]
            BalanceRatio["Balance-to-Debit Utilization Ratio"]
            RecidivismHistory["Chronic NSF Recidivism Tracker"]
        end

        subgraph UnauthModel["Layer 2: R10 / R05 Unauthorized Model"]
            MicroEntryCheck["NACHA Micro-Entry Validation Sentinel"]
            SECRisk["WEB (Internet) vs PPD Exposure Scorer"]
            DisputeHistory["Debtor Prior Unauthorized Complaint History"]
        end

        subgraph CircuitBreaker["Layer 3: 0.50% Threshold Circuit Breaker"]
            BatchProjector["Batch Unauthorized Return Rate Projector"]
            ThresholdCheck{"Projected Rate >= 0.45% or Toxic Hit?"}
            QuarantineAction["Isolate & Quarantine Toxic Items"]
            SafeDispatch["Approve Clean Entries for FedACH"]
        end
    end

    subgraph ClearingOutcomes["Federal Reserve FedACH / EPN"]
        FedACHTransmission["Clean Batch Submitted to FedACH"]
        RescheduledQueue["Delayed for Next Direct Deposit (Avoids $15 NSF Fee)"]
        AuditVault["a2zsoc.com Sovereign Evidence Vault"]
    end

    RawBatch --> PaydayTiming
    RawBatch --> BalanceRatio
    RawBatch --> RecidivismHistory

    RawBatch --> MicroEntryCheck
    RawBatch --> SECRisk
    RawBatch --> DisputeHistory

    PaydayTiming --> BatchProjector
    BalanceRatio --> BatchProjector
    RecidivismHistory --> BatchProjector
    MicroEntryCheck --> BatchProjector
    SECRisk --> BatchProjector
    DisputeHistory --> BatchProjector

    BatchProjector --> ThresholdCheck

    ThresholdCheck -->|Yes: Breach Risk| QuarantineAction
    ThresholdCheck -->|No: Safely < 0.5%| SafeDispatch

    QuarantineAction --> RescheduledQueue
    SafeDispatch --> FedACHTransmission
    SafeDispatch --> AuditVault
```

---

## Batch Governance Workflow: Guarding the 0.50% Ceiling

```mermaid
sequenceDiagram
    autonumber
    participant Orig as Originator / Payroll SaaS
    participant Oracle as NACHA Return Risk Oracle
    participant Breaker as 0.50% Circuit Breaker
    participant FedACH as Federal Reserve FedACH
    participant Vault as a2zsoc.com Evidence Vault

    Orig->>Oracle: Submit Pending Batch of 10,000 Debits ($1.5M Volume)
    Oracle->>Oracle: Predict R01 NSF Probabilities via Payday Timing
    Oracle->>Oracle: Predict R10 Unauthorized Risk (Flag Unvalidated Micro-Entries)
    
    rect rgb(255, 240, 240)
        Oracle->>Breaker: Check Initial Projected Unauthorized Rate (0.58% -> BREACH!)
        Breaker->>Breaker: Sort Entries by R10 Risk Descending
        Breaker->>Breaker: Quarantine 12 Toxic WEB Entries (Projected Rate Drops to 0.18%)
    end

    Breaker->>Vault: Merkle-Seal Pre-Origination Risk Audit Leaf
    Vault-->>Breaker: Proof 9c3dd8f8... Stored in Vault
    Breaker-->>Orig: Batch Filtered: 9,988 Dispatched, 12 Quarantined (NACHA Compliant)
    Orig->>FedACH: Transmit Clean File (0.18% Projected Rate)
```

---

## Core Capabilities

| Capability | NACHA Operating Rule | Risk Mitigation Guarantee |
|:---|:---|:---|
| **0.50% Threshold Circuit Breaker** | Risk Management Framework | Dynamically isolates toxic items to keep unauthorized return rates safely below 0.50% |
| **R01 NSF Predictive Timing** | Direct Deposit Timing Rules | Predicts balance depletion on days 11-14 of payroll cycle, preventing $15 ODFI return fees |
| **Micro-Entry Rule Sentinel** | Micro-Entries Rule | Identifies first-time debit pulls without completed micro-deposit validation |
| **WEB Debit Risk Scorer** | WEB SEC Code Guidelines | Flags anomalous high-value internet-initiated debit pulls |
| **Evidence Sealing** | RFC 3161 Merkle Tree | Tamper-evident ODFI pre-origination compliance logs to `a2zsoc.com` |

---

## Quickstart & CLI

```bash
# Clone the repository
git clone https://github.com/AAH20/nacha-return-risk-oracle.git
cd nacha-return-risk-oracle

# Run the complete 4-scenario NACHA batch risk demonstration
python3 -m nacha_return_risk_oracle.cli demo
```

---

## Automated Test Suite

`nacha-return-risk-oracle` features 100% test coverage using standard library `unittest`:

```bash
python3 -m unittest discover -s tests
```

Output:
```
.......
----------------------------------------------------------------------
Ran 7 tests in 0.000s

OK
```

---

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
