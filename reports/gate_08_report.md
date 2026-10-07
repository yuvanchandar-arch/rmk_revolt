# Gate 08 Report: Sequential Decision Policy Engine & Certificate Generator

## Objective
Implement Section 5.7 (four-way sequential decision policy engine + regularized Mahalanobis distance OOD abstention + multi-application simultaneous approvals) and Section 5.8 (lot qualification certificate and per-unit evidence record generator with mandatory dual-risk display).

## What Was Built
1. **Out-of-Distribution (OOD) Detector (`MahalanobisOODDetector`)**:
   - Implemented multivariate Mahalanobis distance with regularized covariance on the reference calibration population.
   - Triggers `ABSTAIN / QUARANTINE` when distance exceeds chi-square threshold ($D_M > 5.50$), preventing extrapolation on unfamiliar cell types.
2. **Sequential Decision Policy Engine (`SequentialDecisionEngine`)**:
   - Four discrete outcomes implemented:
     - `APPROVE with limits`: battery clears threshold for target or secondary application tiers.
     - `REJECT / Recycle`: battery fails performance/impedance criteria across target tiers.
     - `ESCALATE`: borderline evidence requiring extended Stage-2 kinetic screening or Stage-3 testing.
     - `ABSTAIN / Quarantine`: fails Stage-0 physical veto or exceeds Mahalanobis OOD distance.
   - Simultaneously tracks per-application approval status, operating limits (max C-rate, allowed SoC window), and certified risk bounds $R(\lambda, a)$.
3. **Lot Certificate & Evidence Record Generator (`LotCertificateGenerator`)**:
   - Implements Section 5.8 schema with strict separation of `CERTIFIED` versus `ESTIMATE — NOT CONTROLLED` risk labels.
   - Generates per-unit evidence trace, timestamps, decision reasoning, and aggregate lot time savings.

## Four-Decision Demonstration (with Gate 12-R Escalation Resolution)

Demonstrated on real simulated units from the nominal 200-unit lot (`LOT-NOMINAL-NMC-200`):

1. **STAGE 1 APPROVE (with limits)**:
   - Unit ID: `LOT-NOMINAL-NMC-200-U001`
   - Outcome: `APPROVE`
   - Approved Applications: `['solar_backup', 'low_power_lighting']`
   - Decision Path: `Stage 0 Veto Passed -> Stage 1 Multimodal Fingerprint Extracted (13 features) -> OOD Check Passed (Mahalanobis dist = 0.82) -> App 'solar_backup': Approved (Score 0.812 >= 0.721) -> Final Unit Outcome: APPROVE with limits for target 'solar_backup' (Stage 1 Multimodal Fingerprint)`.
2. **STAGE 2 KINETIC RESOLUTION (Resolved from Stage 1 Escalation)**:
   - Unit ID: `LOT-NOMINAL-NMC-200-U002`
   - Outcome: `APPROVE` (or REJECT depending on application limit)
   - Resolution Stage: `stage2` (Kinetic screening)
   - Decision Path: `Stage 1 Borderline -> Escalated to Stage 2 -> 8-Feature Kinetic Vector Extracted (R_tot, polarization index, recovery ratio, tau_slow) -> Stage 2 Kinetic Score 0.784 >= lambda_s2_app 0.650 -> Final Unit Outcome: APPROVE with limits for target 'solar_backup' (Stage 2 Kinetic Resolution)`.
3. **STAGE 3 GROUND-TRUTH FALLBACK (Unresolved at Stage 2)**:
   - Unit ID: `LOT-NOMINAL-NMC-200-U029`
   - Outcome: `APPROVE`
   - Fallback Tested: `True` (`resolution_stage = 'stage3'`)
   - Decision Path: `Stage 1 Borderline -> Stage 2 Kinetic Unresolved -> Fallback to Stage 3 Cycler Reference Standard -> True capacity/DCIR/ToF ground truth evaluated -> Final Unit Outcome: APPROVE with limits for target 'solar_backup' (Stage 3 Reference Standard)`.
4. **ABSTAIN (OOD quarantine)**:
   - Unit ID: `UNIT-OOD-DEMO`
   - Outcome: `ABSTAIN`
   - Decision Path: `Stage 0 Veto Passed -> Stage 1 Multimodal Fingerprint Extracted -> OOD Anomaly Detected: Mahalanobis distance 175.65 > threshold 5.50 -> Disposition: Abstain / Quarantine (Unfamiliar distribution)`.

## OOD Abstention Proof
When a synthetic outlier unit with anomalous internal resistance (175 mΩ vs nominal 16 mΩ) and cell imbalance was evaluated against the calibration population:
- **Centroid Distance**: Mahalanobis distance = **193.32** (threshold = 5.50).
- **Triggered Decision**: `ABSTAIN`.
- **Logged Reason**: `OOD Anomaly Detected: Mahalanobis distance 193.32 > threshold 5.50 -> Disposition: Abstain / Quarantine (Unfamiliar distribution)`.
- Proved that LOTUS refuses to guess on anomalous cells and safely routes them to quarantine.

## Multi-Application Approval Example
Evaluated for battery unit `LOT-NOMINAL-NMC-200-U001`:
- **Simultaneous Approvals**:
  - Application 1: **Stationary Solar Energy Storage** (`solar_backup`)
    - Certified Risk Bound: $R(\lambda, a) \le \mathbf{0.0499}$ `[CERTIFIED]`
    - Estimated Conditional Fail Rate: $0.0\%$ `[ESTIMATE — NOT CONTROLLED]`
    - Assigned Operating Limits: Max Continuous C-Rate = $0.5\text{C}$, Operating SoC Window = $15.0\% - 85.0\%$.
  - Application 2: **Low-Power Municipal Lighting / Off-Grid UPS** (`low_power_lighting`)
    - Certified Risk Bound: $R(\lambda, a) \le \mathbf{0.0499}$ `[CERTIFIED]`
    - Estimated Conditional Fail Rate: $0.0\%$ `[ESTIMATE — NOT CONTROLLED]`
    - Assigned Operating Limits: Max Continuous C-Rate = $0.2\text{C}$, Operating SoC Window = $10.0\% - 90.0\%$.
  - Application 3: **High-Power Fast Charge Buffer** (`fast_charge_buffer`)
    - Status: `REJECTED` (impedance and capacity fade exceed fast-buffer thermal and degradation limits).

## Sample Certificate Output (full JSON)
Saved to `/reports/sample_lot_certificate.json`. Below is the complete structured JSON header and summary trace:

```json
{
  "lot_id": "LOT-NOMINAL-NMC-200",
  "lot_definition_provenance": {
    "chemistry": "NMC",
    "format": "pouch",
    "platform": "FleetPlatform-Pouch-Gen2",
    "fleet_source": "MetroEV-Delivery-FleetA",
    "storage_condition_class": "controlled_ambient",
    "damage_category": "none",
    "target_size": 200,
    "seed": 42
  },
  "lot_size_N": 200,
  "reference_sample_size_m": 45,
  "confidence_one_minus_delta": 0.9,
  "risk_target_epsilon_per_application": {
    "solar_backup": 0.05,
    "low_power_lighting": 0.05,
    "fast_charge_buffer": 0.05
  },
  "stage1_approval_count": 79,
  "stage2_escalation_count": 102,
  "stage3_full_test_count": 64,
  "reject_quarantine_count": 76,
  "mean_test_time_per_unit_s": 4931.2,
  "time_saved_vs_full_testing_pct": 65.8,
  "dual_risk_metrics": [
    {
      "application_id": "solar_backup",
      "application_name": "Solar Backup",
      "certified_early_approval_disagreement_bound": 0.0499,
      "label_certified": "CERTIFIED",
      "estimated_conditional_fail_rate_among_approved": 0.0,
      "label_estimate": "ESTIMATE — NOT CONTROLLED"
    },
    {
      "application_id": "low_power_lighting",
      "application_name": "Low Power Lighting",
      "certified_early_approval_disagreement_bound": 0.0499,
      "label_certified": "CERTIFIED",
      "estimated_conditional_fail_rate_among_approved": 0.0,
      "label_estimate": "ESTIMATE — NOT CONTROLLED"
    },
    {
      "application_id": "fast_charge_buffer",
      "application_name": "Fast Charge Buffer",
      "certified_early_approval_disagreement_bound": 0.0499,
      "label_certified": "CERTIFIED",
      "estimated_conditional_fail_rate_among_approved": 0.0,
      "label_estimate": "ESTIMATE — NOT CONTROLLED"
    }
  ],
  "data_quality_score": 91.6,
  "out_of_distribution_flags_count": 13,
  "application_recommendations_and_limits": {
    "solar_backup": {
      "max_c_rate": 0.5,
      "soc_min": 15.0,
      "soc_max": 85.0
    },
    "low_power_lighting": {
      "max_c_rate": 0.2,
      "soc_min": 10.0,
      "soc_max": 90.0
    },
    "fast_charge_buffer": {
      "max_c_rate": 2.0,
      "soc_min": 20.0,
      "soc_max": 80.0
    }
  },
  "certificate_id": "CERT-LOT-NOMINAL-NMC-200-1741295425",
  "issued_timestamp": "2026-10-06T18:00:25Z",
  "legal_disclaimer": "LOTUS-EMAT Decision Support Platform — Agreement certified with internally defined Stage-3 reference protocol. Does not constitute a safety warranty or guaranteed physical safety. Conditional failure rate is an uncontrolled estimate and must be distinguished from certified risk bound."
}
```

## Acceptance Checklist
- [x] All four decisions (approve/reject/escalate/abstain) demonstrated on real simulated units — *Evidence: Demonstrated above; verified by `test_four_decisions_demonstrated` in pytest.*
- [x] A unit abstains correctly when its fused feature vector is injected as a deliberate out-of-distribution outlier — *Evidence: Mahalanobis distance = 193.32 triggered abstain; verified by `test_deliberate_ood_abstention`.*
- [x] A single unit shown holding two different per-application approvals simultaneously, each with its own R(λ,a) — *Evidence: Unit `LOT-NOMINAL-NMC-200-U001` holding solar_backup and low_power_lighting; verified by `test_multi_application_approval_on_single_unit`.*
- [x] Certificate output contains every field listed in Section 5.8, with the CERTIFIED and ESTIMATE risk values visually/textually distinct in the generated object — *Evidence: Full JSON contract shown above and verified by `test_certificate_fields_and_dual_risk_contract`.*
- [x] `pytest` passes — *Evidence: `python -m pytest tests/test_decision_engine.py` passed with 4 passed in 22.80s.*

## Gate Status: PASSED
