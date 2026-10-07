# PROJECT_DETAILS.md
## LOTUS-EMAT — Lot-Calibrated, Optimally-Stopped Qualification with Acoustic Fingerprinting
### Ground-Truth Specification for Autonomous Build (Antigravity)

**Status of this document:** This is the single source of truth for the entire project. Every other
file (prompt_details.md, design_system_brief.md, and any gate report) must be consistent with this
document. If a gate's output contradicts this document, the gate has failed, regardless of code quality.

**Scope of this document:** Software only. Hardware (EMAT transducer circuit, ESP32/STM32 controller,
sensors, low-voltage battery rig) is a later, separate integration phase and is explicitly out of
scope for every gate described in prompt_details.md. Nothing in the software build should assume
hardware is attached; everything must run standalone on simulated/public data and a software-defined
EMAT physics simulator.

---

## 1. One-Paragraph Project Summary

LOTUS-EMAT is a decision-support platform for qualifying retired EV batteries for second-life reuse.
For each incoming, traceable lot of batteries, the system randomly selects a small reference subset
and fully qualifies it (Stage 3). It uses that lot-specific evidence to statistically calibrate a
staged, multimodal screening policy — combining a fast electrical fingerprint (OCV, DCIR, relaxation,
temperature, imbalance) with a fast acoustic fingerprint captured via a low-power, software-defined
EMAT (Electromagnetic Acoustic Transducer) sensing channel — for the remaining units in that lot. Each
remaining battery is screened and assigned one of four outcomes: **Approve with limits** (for a
specific application), **Reject/recycle**, **Escalate** (more evidence needed), or **Abstain/quarantine**
(too unfamiliar or inconsistent to decide automatically). The system reports a statistically certified,
per-application risk bound — clearly distinguished from an uncontrolled estimate — rather than a single
opaque health score.

---

## 2. What This Project Is NOT (read this before writing any code)

- It is **not** a new SOH (state-of-health) predictor. SOH prediction is a solved, crowded research
  area and must never be presented as the contribution.
- It is **not** a claim that EMAT or ultrasonic lithium-plating detection is a new invention. Prior art
  exists (contactless EMAT battery characterization, ultrasonic plating detection). EMAT is a **sensing
  modality inside LOTUS**, not the headline novelty.
- It is **not** a safety certification system. It never claims to guarantee physical safety. It
  certifies agreement with an internally defined Stage-3 reference protocol, and says so explicitly
  everywhere a risk number is shown.
- It does **not** claim a controlled conditional failure rate among approved batteries (i.e.
  P(fail | approved)) unless a formal FDR/conditional-risk method (Phase 2, future work) is implemented.
  Wherever this quantity is shown, it must be labeled "estimate — not statistically controlled."
- It does **not** connect to real EV pack high voltage in software-only phases. All hardware safety
  boundaries are documented in Section 11 and apply to the later hardware phase only, but the software
  must be built as if these constraints are permanent and non-negotiable.

---

## 3. The Core Novelty Claim (exact wording — reuse verbatim in UI copy, reports, and docs)

> "LOTUS is a lot-calibrated, risk-controlled sequential protocol that uses a randomly selected
> full-test reference sample to minimize the time needed to qualify the remaining retired EV batteries
> in that lot, while bounding — per application, via a named finite-sample statistical method
> (Learn-Then-Test), and honestly distinguished from the uncontrolled conditional failure rate —
> early-approval disagreement with the full qualification protocol. EMAT acoustic fingerprinting is an
> additional, low-power, software-defined sensing modality that supplies evidence into this same
> decision engine; it does not decide anything on its own."

---

## 4. System Architecture (top level)

```
                         RETIRED EV BATTERY LOT (N units)
                                      │
                                      ▼
                     LOT DEFINITION & TRACEABILITY CHECK
            (chemistry, format, platform, fleet, storage, damage class)
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                          ▼
     RANDOM REFERENCE SAMPLE (m)                    REMAINING UNITS (N−m)
                 │                                          │
                 ▼                                          ▼
      FULL STAGE-3 QUALIFICATION               STAGE 0 — SAFETY/IDENTITY VETO
   (capacity, DCIR, self-discharge,                         │
    thermal, application criteria)                          ▼
                 │                          STAGE 1 — RAPID MULTIMODAL FINGERPRINT
                 │                      ┌───────────────────┴───────────────────┐
                 │                      ▼                                       ▼
                 │           ELECTRICAL FINGERPRINT                 ACOUSTIC FINGERPRINT (EMAT)
                 │       OCV, DCIR, relaxation slope/curvature     Chirp TX → multilayer propagation
                 │       temperature response, cell imbalance      → noise injection → matched filter
                 │                      │                          → ToF, amplitude, energy, SNR
                 │                      └───────────────┬───────────────────────┘
                 │                                      ▼
                 │                          MULTIMODAL FEATURE FUSION
                 │                                      │
                 └──────────────► LOT-SPECIFIC STATISTICAL CALIBRATION
                                     (Learn-Then-Test over threshold grid λ,
                                      per application a, risk bound ε, confidence 1−δ)
                                                      │
                                                      ▼
                                   SEQUENTIAL DECISION POLICY ENGINE
                              ┌───────────┬────────────┬─────────────┐
                              ▼           ▼            ▼             ▼
                          APPROVE     ESCALATE      REJECT        ABSTAIN
                      (with limits)  (Stage 2/3)   (recycle)    (quarantine)
                              │           │
                              │      STAGE 2 — extended screening (if escalated)
                              │           │
                              │      STAGE 3 — full reference protocol (if still unresolved)
                              │           │
                              └─────┬─────┘
                                    ▼
                    LOT CERTIFICATE + PER-UNIT EVIDENCE RECORD
                                    │
                                    ▼
                          DASHBOARD (web application)
```

---

## 5. Module-by-Module Technical Specification

### 5.1 Data Layer

**Public datasets to ingest (software gate, no hardware needed):**
- NASA PCoE battery aging dataset
- CALCE battery cycling datasets
- Oxford Battery Degradation Dataset
- MIT/Stanford fast-charging dataset (if accessible; else document as unavailable and proceed with the other three)
- **PulseBat** — 464 retired lithium-ion batteries spanning 3 cathode chemistries, 6 historical usage
  patterns, 3 physical formats, 6 capacity designs, with repeated multidimensional rapid pulse test
  data. This is the primary dataset for constructing heterogeneous/"shifted lot" scenarios because its
  population is heterogeneous by design.

All datasets are lab-controlled, not representative of damaged/unknown-history real retired EV packs.
This limitation must be stated in the data-layer documentation and in the final report — never hidden.

**Lot Simulator** must be able to construct, from the above sources:
- Same-source lots (nominal case)
- Mixed-age lots
- Cross-dataset lots (distribution shift)
- Mixed-chemistry/anomalous lots (for abstention/escalation testing), primarily via PulseBat

### 5.2 Electrical Fingerprint Module (Stage 1 electrical features)

Features to extract per unit, from early-cycle / rest / pulse segments where available in source data:
- Open-circuit voltage (OCV)
- DC internal-resistance proxy (ΔV/ΔI from a pulse)
- Voltage-relaxation slope and curvature after a pulse
- Surface-temperature response (where temperature channels exist in source data)
- Module/cell imbalance or voltage spread (where multi-cell data exists)
- Sensor-quality flag (missing/implausible data detection)

### 5.3 EMAT Acoustic Simulation & DSP Module

This module has three sequential internal stages, all pure software (NumPy/SciPy), no hardware
dependency:

**(a) Physics simulator ("the encoder").** Models a multilayer acoustic propagation path:
`EMAT transducer → aluminum casing → electrode stack → separator/electrolyte → graphite anode region →
degradation/plating proxy layer`. Each layer has defined acoustic impedance, wave velocity, attenuation,
and layer thickness. A controlled chirp (linear frequency sweep) or Golay-coded pulse is "transmitted"
into this layered model and a weak, delayed, attenuated echo is produced, whose exact delay/amplitude is
a function of the degradation state (Section 5.4). Framing requirement: document this explicitly as
**"degradation and plating perturb the acoustic propagation characteristics of the cell"** — not as a
literal clean reflection off a plating slab. This is a scientifically safer and more defensible framing
and must be used in all docstrings, comments, and UI copy.

**(b) Noise model ("the attenuator").** Injects, independently and with configurable magnitude:
white thermal noise, sinusoidal EMI (simulating motor/inverter interference), and low-frequency rumble
(simulating vibration). Target: realistic SNR degradation (e.g., down to roughly −15 dB) such that the
echo is not visible by eye on a raw plot — this must be demonstrable in a before/after plot.

**(c) Software-defined acoustic receiver ("the DSP pipeline").** Recovers the buried echo using:
matched filtering / pulse compression (cross-correlation against the known transmitted waveform), then
extracts: Time-of-Flight (ToF), peak amplitude, integrated energy, echo width, attenuation, SNR,
repeatability across repeated pulses, and basic frequency-domain features. **Naming requirement:** call
this the **"Software-Defined Acoustic Receiver"** or **"Digital Matched-Filter Receiver."** Never call
it a "Digital LNA" — a matched filter does not amplify an analog signal; it exploits waveform
correlation. This naming correction must be enforced in code comments, UI labels, and reports.

### 5.4 Degradation State Model (shared by both modalities)

A single, controlled degradation-state generator must drive **both** the electrical feature
perturbations and the EMAT physics-layer perturbations consistently, so that the two modalities are
provably linked to the same underlying ground-truth state (this is required for Gate 3/4 validation and
for the "conflicting evidence" demo scenario in Section 8). States, minimum set:
`Healthy → Mild degradation → Moderate degradation → Plating-associated degradation → Severe
degradation`. Each state must define: expected capacity-fade range, expected DCIR range, expected
acoustic ToF shift range, expected acoustic amplitude/energy attenuation range, and a documented
rationale for each mapping (even if simplified/illustrative — must be internally consistent and
reproducible, not random per run unless a seed is varied intentionally).

### 5.5 Multimodal Feature Fusion

Combines the electrical feature vector and the acoustic feature vector per unit into one fused feature
vector used for (a) the Stage-1 decision model and (b) LOTUS calibration. Must support three run modes
for comparison purposes (required for the headline experiment in Section 9):
1. Electrical-only
2. Acoustic-only
3. Electrical + Acoustic (fused) — the primary mode

### 5.6 LOTUS Statistical Calibration Engine

- **Lot definition enforcement:** a lot is a traceable group sharing chemistry, format, platform,
  fleet/source, storage condition class, and damage category. If an incoming batch mixes these
  attributes beyond a configurable tolerance, the engine must refuse to calibrate it as one lot and
  instead split it into sub-lots automatically. This behavior must be unit-tested explicitly.
- **Random reference sampling:** draws m units uniformly at random from the lot for full Stage-3
  qualification. Sample size m is either user-specified or computed from the zero-violation bound:
  `m ≈ ln(δ) / ln(1 − ε)` at a given confidence `1 − δ` and target risk `ε` (reference table: ε=10%→m≈22,
  ε=5%→m≈45, ε=2%→m≈114, ε=1%→m≈230, all at 90% confidence). This formula and table must appear in the
  code documentation and be covered by a unit test reproducing the table values.
- **Risk definition (exact, per application a):**
  `R(λ, a) = P( early-approve for application a ∧ would-fail-Stage-3-for-a )`
  This is an **unconditional joint probability**, evaluated separately per application. It is NOT
  `P(fail | approve)`. The code, the UI, and every report must keep these two quantities visually and
  textually separate at all times — this is a hard requirement validated at Gate 7.
- **Calibration method:** adapt **Learn-Then-Test (LTT)** — search a grid of candidate stage thresholds
  λ, and certify the subset of the grid for which `R(λ, a) ≤ ε` holds with confidence `1 − δ` over the
  randomness of the reference draw. Among certified thresholds, select the one minimizing expected mean
  test time. Must be implemented from first principles in Python (no proprietary dependency), with a
  named reference to Angelopoulos et al.'s Learn-Then-Test framework in documentation/comments.
- **Escalation-is-always-safe property:** any unit that reaches Stage 3 contributes zero error against
  the reference by construction. The only certified error is early acceptance. This must be explicitly
  tested.

### 5.7 Sequential Decision Policy Engine

At each stage, for each unit, decide one of: `approve(application)`, `reject`, `escalate`, `abstain`.
Abstention must trigger specifically when a unit's feature vector is out-of-distribution relative to
the lot's calibration population (implement at minimum one of: Mahalanobis distance, Isolation Forest,
or distance-to-centroid — document which was chosen and why). A single battery may hold multiple valid
per-application approvals simultaneously (e.g., approved for solar backup AND low-power lighting, but
not for fast-charge buffering), each carrying its own certified R(λ, a).

### 5.8 Lot Certificate & Per-Unit Evidence Record

### Appendix A: High-Assurance Battery Lot Certificate & Dashboard Field List (Section 5.8)

Every lot run must generate, at minimum, the following fields (exact names, used verbatim in UI and
reports):

```
Lot ID | Lot definition/provenance | Lot size N | Reference sample size m
Confidence (1−δ) | Risk target ε (per application)
Stage-1 approval count | Stage-2 escalation count | Stage-3 full-test count | Reject/quarantine count
Stage accounting scope clarification [label: stage_accounting_scope]
Primary target application unit partition (screened approved + screened rejected/quarantine + reference m = N)
Mean test time per unit | Time saved vs. full testing
Certified early-approval disagreement bound R(λ,a)  [label: CERTIFIED]
Estimated conditional fail-rate among approved units  [label: ESTIMATE — NOT CONTROLLED]
Data-quality score | Out-of-distribution flags
Application recommendation and operating limits (per unit)
Per-unit evidence record (full feature trace, decision path, timestamps)
```

*Accounting Scope Note:* As specified in Gate 12-R, `stage1_approval_count`, `stage2_escalation_count`, `stage3_full_test_count`, and `reject_quarantine_count` represent stage-by-stage pipeline activity counts across sequential protocol transitions (where `stage3_full_test_count` includes reference sample $m$ plus unresolved fallbacks, and `stage2_escalation_count` counts units routed to Stage 2). They are complemented by `primary_target_application_unit_partition`, which provides the clean, mutually exclusive per-unit disposition partition (`screened_units_approved` + `screened_units_rejected_or_quarantined` + `reference_sample_units_full_tested` = $N$).

The dual-risk display (CERTIFIED vs ESTIMATE, separately labeled, both always visible together, never
one without the other) is a hard, testable UI requirement — not a styling preference.

---

## 6. Worked Numeric Example (use this exact scenario as the default demo dataset / seed scenario)

A 200-unit lot (single fleet, NMC, same platform, similar storage history). At ε=5%, δ=10%, LOTUS draws
**45** reference units for full Stage-3 testing. Of the remaining **155**: ~100 clear Stage 1
confidently, ~40 escalate to Stage 2, ~15 require full Stage 3. Approximate total qualification time
should land near a **~60–70% reduction** versus testing all 200 units fully. This exact scenario (or a
close reproducible variant with the same order of magnitude) must be the default seeded demo lot shown
on first dashboard load, and the computed — not invented — savings percentage must appear on the
Overview page headline.

---

## 7. Validation Experiments (must all be implemented as runnable scripts/notebooks, not just described)

| ID | Name | Question | Required output |
|---|---|---|---|
| E0 | FDR-gap demonstration | Does the certified unconditional bound stay controlled while the uncontrolled conditional rate sometimes exceeds it? | Plot showing both quantities across many simulated low-approval-rate lots |
| E1 | Validity under shift | Does in-lot calibration hold where global calibration breaks? | Over ≥500 random lot draws, empirical violation rate ≤ δ for LOTUS; higher for a globally-calibrated baseline |
| E2 | Efficiency | Time saved at a fixed certified ε | Pareto curve: mean test time vs. ε |
| E3 | Sample-size sweep | How does m trade off against total time and certified bound? | Plot sweeping m |
| E4 | Ablations | What does each component contribute? | Remove escalation; remove OOD abstention; electrical-only; acoustic-only; single-stage; no veto — tabulated comparison |
| E5 | Headline figure | Core comparison | X: mean qualification time, Y: empirical early-approval disagreement rate, horizontal line at ε, curves for: Full test / Fixed-threshold cascade / SOH-only ML / Globally-calibrated / LOTUS electrical-only / LOTUS fused (electrical+acoustic) |

Baselines required: full Stage-3 testing of every unit; fixed hand-threshold cascade (mirroring a
published 3-stage inspection framework, cited as the closest prior art); SOH-only classifier;
uncalibrated ML with a confidence cutoff; conformal interval without a stopping policy; globally
(non-lot) calibrated LTT.

---

## 8. Dashboard Requirements (content spec — layout/style spec lives in 03_design_system_brief.md)

Minimum pages, each with a specific content purpose (style mapping defined separately):

1. **Operations Overview** — system-wide status: total lots processed, units approved/escalated/
   rejected/abstained (counts and %), aggregate time saved, active lots list, headline worked-example
   numbers from Section 6 on first load.
2. **Lot Registry / Batteries Table** — dense data table of all units across all lots: ID, lot, chemistry,
   decision, certified risk, application, timestamp — sortable/filterable.
3. **Lot Detail / Live Calibration View** — shows a single lot going through the pipeline live:
   reference sampling animation, calibration in progress, remaining units being screened one by one,
   with the "conflicting evidence → escalate" case explicitly demonstrable (Section 5.4 ties this to a
   reproducible scenario).
4. **EMAT Multiphysics Visualization Page** (dedicated page — required, see Section 9 below).
5. **Analytics & Reports** — E0–E5 experiment results, headline figure, time/cost savings, risk-target
   configuration controls.
6. **Lot Certificate / Evidence Record Viewer** — renders the Section 5.8 certificate for a selected
   lot or unit in a clean, printable/exportable format, with QR-style reference ID.
7. **Shifted-Lot Demo** — a dedicated, explicit demo flow: load a deliberately mixed/shifted lot, show
   the system refuse single-lot calibration and split into sub-lots, or show elevated escalation rate —
   this is a named required scenario, not optional polish.

All page content must reflect LOTUS-EMAT data and terminology exactly as specified in this document.
No placeholder/lorem-ipsum text, and no content copied from the design reference screenshots.

---

## 9. EMAT Multiphysics Visualization Page — Detailed Spec (mandatory, non-negotiable)

This page must render a **live, animated 2D cross-sectional view** of the battery cell during an EMAT
test, driven by real output from the Section 5.3 physics/DSP pipeline (not a canned/static GIF). Minimum
required visual elements, top to bottom of the cross-section:

1. **EMAT transducer** positioned above the cell, visually distinct, pulsing/active during transmit.
2. **Aluminum outer casing layer**, rendered with a glow/heat-map effect representing induced eddy
   currents during the EMAT excitation phase.
3. **Graphite anode layer**, positioned beneath the casing, with its own distinct color mapping.
4. **A dynamic lithium-plating defect layer** whose thickness visually changes according to the
   selected/simulated degradation state (Section 5.4) — this must be data-driven (bound to the actual
   state parameter), not a fixed illustration.
5. **The propagating ultrasonic wavefront** (bulk or Lamb-wave style), rendered as an animated colorful
   heat-map/color-gradient sweeping through the layered medium over time, synchronized to the actual
   simulated time-of-flight for the currently selected unit.

Supporting UI on the same page: live waveform panel (raw noisy signal vs. matched-filter-recovered
signal, mirroring the before/after plot from Section 5.3b), extracted feature readout (ToF, amplitude,
energy, SNR), and a state selector allowing the viewer to switch between Healthy → Severe degradation
states and watch the cross-section update accordingly. This page is the single most important visual
in the entire product for conveying "enterprise multiphysics software," and must not be a placeholder.

Technical implementation note (for the frontend gate): build this with HTML5 Canvas or WebGL/Three.js,
not a static image or external heavy physics engine; data (layer boundaries, wavefront position over
time, defect thickness) is computed in the Python backend and streamed/served to the frontend for
rendering, keeping the physics and the rendering cleanly separated.

---

## 10. Technology Stack

| Layer | Tools |
|---|---|
| Data & modeling | Python, pandas, NumPy, SciPy, scikit-learn |
| Acoustic simulation & DSP | NumPy, SciPy (signal module) |
| Statistical calibration | Custom Learn-Then-Test implementation in Python |
| Backend API | FastAPI |
| Database | SQLite (dev) with a schema portable to PostgreSQL |
| Frontend | React (with Canvas/WebGL for the EMAT visualization page specifically) |
| Visualization (analytics) | Plotly or an equivalent charting library consistent across pages |
| Testing | pytest for backend/statistics modules; component-level tests for frontend where practical |

---

## 11. Hardware Phase (reference only — not built by Antigravity in these gates)

Documented here only so the software is designed to accept real sensor data later without rearchitecting:
protected 18650 test cell/module or battery emulator; ESP32/STM32/Raspberry Pi; isolated voltage sensor;
Hall-effect or isolated current sensor; temperature sensor; fused, current-limited electronic load;
emergency cutoff. Hard safety boundary, permanent: never connect any hobby-level hardware directly to EV
pack high voltage; never induce real thermal runaway, lithium plating, internal shorts, overcharge,
over-discharge, or physical abuse for demo purposes. The backend API layer (Gate 9) must expose a clean
data-ingestion interface general enough that a future hardware bridge can push real sensor readings into
the same pipeline that currently consumes simulated/public data, without modification to the statistical
or decision-engine modules.

---

## 12. Definition of "Done" for the Entire Software Phase

The software phase is complete only when: all gates in `02_prompt_details.md` are passed with their
exact required reports saved; E0–E5 all run end-to-end and produce the specified plots/tables; the
dashboard's 7 pages are live, data-driven (no placeholder content), and visually consistent with
`03_design_system_brief.md`; the EMAT visualization page renders a live, data-bound, animated
cross-section as specified in Section 9; and a final consolidated project report (produced at the last
gate) states, in the exact terms of Section 3, what is proven, what is estimated, and what is
explicitly not claimed.
