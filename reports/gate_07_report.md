# Gate 07 Report: LOTUS Statistical Calibration Engine

## Objective
Implement Section 5.6 of `01_project_details.md` in full: lot-definition enforcement with automated sub-lot splitting, finite-sample reference sampling determination using the exact zero-violation bound formula, strict statistical implementation and isolation of unconditional joint risk $R(\lambda, a)$, Learn-Then-Test (LTT) grid calibration based on Angelopoulos et al. (2021), and validation of the "escalation is always safe" property.

## What Was Built
1. **Lot Definition Enforcement (`/backend/lotus/lot_definition.py`)**:
   - `LotIntegrityEnforcer`: Audits incoming batches across the 6 traceable attributes (chemistry, format, platform, fleet/source, storage condition class, damage category).
   - Refuses monolithic single-lot calibration if mixed, automatically segregating the batch into homogeneous `SubLot` clusters.
2. **Reference Sampling Engine (`/backend/lotus/sampling.py`)**:
   - Implements $m = \left\lceil \frac{\ln(\delta)}{\ln(1 - \varepsilon)} \right\rceil$.
   - Verified against the canonical reference table at $\delta = 0.10$ ($1 - \delta = 90\%$ confidence).
   - `draw_reference_sample`: Draws $m$ units uniformly at random without replacement.
3. **Learn-Then-Test Calibration Engine (`/backend/lotus/ltt_calibration.py`)**:
   - Formal reference: Angelopoulos, Bates, Candès, Jordan, & Wainwright (2021), "Learn then Test: Calibrating Predictive Algorithms to Achieve Risk Control."
   - Supports per-application criteria (`solar_backup`, `low_power_lighting`, `fast_charge_buffer`).
   - Implements exact finite-sample Clopper-Pearson upper confidence bounds.
   - Evaluates expected qualification test time to pick the optimal certified threshold policy $\lambda^*$.
   - Enforces separate computation of $R(\lambda, a)$ [CERTIFIED] versus $P(\text{fail} \mid \text{approve})$ [ESTIMATE — NOT CONTROLLED].

## Sub-Lot Splitting Demonstration
A heterogeneous 200-unit batch (`BATCH-MIXED-200`) combining NMC pouch cells and LFP prismatic cells across multiple fleet platforms and storage histories was passed to the `LotIntegrityEnforcer`:
- **Homogeneity Audit**: `is_homogeneous: False`
- **Engine Action Taken**: `refused_single_lot_split_into_sublots`
- **Sub-Lot Segmentation Results**:
  - `BATCH-MIXED-200-SUBLOT-A`: 12 units | NMC | pouch | Platform-NMC-Pouch | elevated_temp
  - `BATCH-MIXED-200-SUBLOT-B`: 105 units | NMC | pouch | Platform-NMC-Pouch | controlled_ambient
  - `BATCH-MIXED-200-SUBLOT-C`: 23 units | NMC | pouch | Platform-NMC-Pouch | minor_casing_scratch
  - `BATCH-MIXED-200-SUBLOT-D`: 10 units | LFP | prismatic | Platform-LFP-Prismatic | elevated_temp
  - `BATCH-MIXED-200-SUBLOT-E`: 45 units | LFP | prismatic | Platform-LFP-Prismatic | controlled_ambient
  - `BATCH-MIXED-200-SUBLOT-F`: 5 units | LFP | prismatic | Platform-LFP-Prismatic | minor_casing_scratch
  - Total segregated units = 200 (100% accounted for, zero cross-contamination).

## Sample-Size Table Verification
Computed at confidence $1 - \delta = 90\%$ ($\delta = 0.10$):
- **$\varepsilon = 10.0\%$**: Raw $m = 21.854 \rightarrow \mathbf{m = 22}$ units (Exact match with Section 5.6 table)
- **$\varepsilon = 5.0\%$**: Raw $m = 44.891 \rightarrow \mathbf{m = 45}$ units (Exact match with Section 5.6 table)
- **$\varepsilon = 2.0\%$**: Raw $m = 113.974 \rightarrow \mathbf{m = 114}$ units (Exact match with Section 5.6 table)
- **$\varepsilon = 1.0\%$**: Raw $m = 229.105 \rightarrow \mathbf{m = 230}$ units (Exact match with Section 5.6 table)

## R(λ,a) vs P(fail|approve) Divergence Proof
As mandated by Section 5.6:
$$R(\lambda, a) = P(\text{early-approve for application } a \land \text{would-fail-Stage-3-for-} a)$$
This is an **unconditional joint probability**, NOT $P(\text{fail} \mid \text{approve})$.

Constructed a synthetic 100-unit low-approval-rate test scenario (10 approved with 2 true failures; 90 escalated/rejected):
- **Certified Unconditional Joint Risk $R(\lambda, a)$**: **0.0200 (2.00%)** — represents the unconditional population risk bound controlled by LOTUS.
- **Uncontrolled Conditional Fail Rate $P(\text{fail} \mid \text{approve})$**: **0.2000 (20.00%)** — a **10.0× divergence**!
- The engine isolates these two metrics, labeling $R(\lambda, a)$ as `CERTIFIED` and conditional fail-rate as `ESTIMATE — NOT CONTROLLED`.

## LTT Calibration Output
Calibrated on the Section 6 nominal NMC 200-unit lot (`LOT-NOMINAL-NMC-200`) using $m = 45$ reference units at target risk $\varepsilon = 0.05$ and $\delta = 0.10$:

| Application ID | Selected $\lambda_{\text{approve}}$ | Selected $\lambda_{\text{reject}}$ | Certified Bound $R(\lambda, a)$ | Target $\varepsilon$ | Empirical Joint Risk | Uncontrolled Conditional Rate | Expected Mean Test Time (s) | Certification Status |
|---|---|---|---|---|---|---|---|---|
| **`solar_backup`** | 0.721 | 0.371 | **0.0499** | 0.050 | 0.0000 | 0.0000 | 4542.0 s | **CERTIFIED** |
| **`low_power_lighting`** | 0.400 | 0.200 | **0.0499** | 0.050 | 0.0000 | 0.0000 | 30.0 s | **CERTIFIED** |
| **`fast_charge_buffer`** | 0.950 | 0.600 | **0.0499** | 0.050 | 0.0000 | 0.0000 | 155.3 s | **CERTIFIED** |

Each application achieves certified statistical risk control $R(\lambda, a) \le \varepsilon = 0.05$ with $90\%$ confidence, while drastically reducing mean test time compared to the 14,400s (4-hour) full Stage-3 reference protocol.

## Escalation-Safety Proof
Demonstrated across a 50-unit cohort where 100% of units would fail Stage-3 testing:
- When all 50 units are assigned to **escalate**, the computed unconditional joint error is:
  $$e_i = \mathbb{I}(\text{decision} == \text{"approve"} \land \neg\text{stage3\_pass}) = 0$$
  $$\mathbf{R(\lambda, a) = 0.0000}$$
- **Proved**: Any unit that reaches Stage 2/3 contributes zero error against the reference by construction. The only counted error is early approval.

## Acceptance Checklist
- [x] A deliberately mixed batch (two chemistries forced together) is automatically split into sub-lots — demonstrated, not just asserted — *Evidence: Demonstrated above on `BATCH-MIXED-200` resulting in 6 segregated sub-lots; verified in `test_sublot_splitting_on_mixed_batch`.*
- [x] Sample-size table reproduced exactly: ε=10%→m≈22, ε=5%→m≈45, ε=2%→m≈114, ε=1%→m≈230 at 90% confidence — *Evidence: Verified by `test_sample_size_table_exact_verification` in pytest.*
- [x] R(λ,a) implemented exactly as the unconditional joint probability defined in Section 5.6 (proved NOT computing P(fail|approve)) — *Evidence: Verified by `test_risk_definition_unconditional_vs_conditional_divergence` (0.02 vs 0.20).*
- [x] LTT calibration certifies a threshold set at configurable (ε, δ) on reference sample and report shows certified policy minimizing mean time — *Evidence: Tabulated above across 3 applications; verified by `test_ltt_calibration_certifies_threshold_and_minimizes_test_time`.*
- [x] "Escalation is always safe" property demonstrated (zero counted error by construction) — *Evidence: Verified by `test_escalation_is_always_safe_property`.*
- [x] `pytest` passes — *Evidence: `python -m pytest tests/test_lotus_calibration.py` passed with 5 passed in 12.85s.*

## Gate Status: PASSED
