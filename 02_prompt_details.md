# PROMPT_DETAILS.md
## LOTUS-EMAT — Gated Build Contract for Antigravity

**Read `01_project_details.md` and `03_design_system_brief.md` fully before Gate 0.** They are the
ground truth. This file governs *how* you work, gate by gate. You are not permitted to skip, merge, or
reorder gates. You are not permitted to mark a gate passed unless every acceptance criterion in that
gate is literally true and verifiable by re-running the code yourself.

### Global Rules (apply to every gate, no exceptions)

1. **Sequential only.** Do not start Gate N+1 until Gate N's report exists at the required path and
   every item in its acceptance checklist is checked TRUE based on actual execution, not assumption.
2. **No fabricated results.** Every number in a report (times, percentages, risk bounds, counts) must
   come from actually running the code in this environment. If something can't run, the gate fails —
   say so in the report; do not invent a plausible-looking number.
3. **No scope creep, no scope skipping.** Build exactly what the gate asks. Do not silently add or omit
   features planned for a later gate.
4. **Report format is fixed.** Every gate report is a markdown file at `/reports/gate_XX_report.md`
   using the exact section headers given in that gate's "Required Report Sections." After saving, append
   one line to `/reports/MASTER_GATE_LOG.md`: `Gate XX — <name> — PASSED/FAILED — <timestamp>`.
5. **Terminology lock.** Use the exact terms from `01_project_details.md` Sections 3, 5.3(c), and 5.6
   everywhere (code, comments, UI, reports) — including the "Software-Defined Acoustic Receiver" naming
   correction and the CERTIFIED vs ESTIMATE risk-label distinction. Any violation fails the gate it
   appears in, even if the functional code works.
6. **If a gate fails:** state exactly which criterion failed and why, fix it, re-run, and only then
   write the report. The report only gets written once the gate actually passes.

---

## GATE 0 — Repository & Environment Scaffold

**Objective:** Stand up the project skeleton so every later gate has a consistent place to put code.

**Deliverables:**
- Repo structure: `/backend`, `/frontend`, `/data`, `/notebooks`, `/reports`, `/tests`
- `requirements.txt` / `pyproject.toml` with pinned versions for: numpy, scipy, pandas, scikit-learn,
  fastapi, uvicorn, pytest, plotly
- `README.md` stating the project in one paragraph (reuse Section 1 of project_details.md verbatim)
- Empty `MASTER_GATE_LOG.md` created in `/reports`
- A working `pytest` run (even with zero tests) confirming the environment executes cleanly

**Acceptance criteria (ALL required):**
- [ ] `pip install -r requirements.txt` (or equivalent) completes with no errors
- [ ] `pytest` runs and exits 0
- [ ] Folder structure exists exactly as listed above
- [ ] README reproduces the Section 1 summary without alteration

**Required Report Sections:** `## Objective` `## What Was Built` `## Commands Run and Their Output`
`## Acceptance Checklist (each item ticked with evidence)` `## Gate Status: PASSED`

---

## GATE 1 — Public Data Ingestion & Lot Simulator

**Objective:** Load NASA PCoE, CALCE, Oxford, and PulseBat (plus MIT/Stanford if accessible), and build
the lot-construction simulator described in Section 5.1.

**Deliverables:** `/backend/data/loaders.py` (one loader per dataset, documented schema out);
`/backend/data/lot_simulator.py` implementing same-source, mixed-age, cross-dataset, and
mixed-chemistry/anomalous lot construction; `/tests/test_lot_simulator.py`.

**Acceptance criteria:**
- [ ] Each dataset loader returns a consistent internal schema (documented in the report)
- [ ] PulseBat loader confirms all 3 chemistries / 6 usage histories / 3 formats are represented in the
      loaded data (counts shown in report)
- [ ] Lot simulator can produce all four lot types on demand, with a reproducible seed
- [ ] At least one dataset that cannot be ingested (if any) is explicitly documented as unavailable,
      with a fallback plan — never silently skipped
- [ ] `pytest` passes for this module

**Required Report Sections:** `## Objective` `## Datasets Ingested (with row/unit counts)`
`## Lot Types Demonstrated (with sample outputs)` `## Known Limitations` `## Acceptance Checklist`
`## Gate Status: PASSED`

---

## GATE 2 — Electrical Stage-0/1/2 Feature Extraction Pipeline

**Objective:** Implement the Section 5.2 features plus Stage 0 (safety/identity veto) and Stage 2
(extended screening) electrical logic.

**Deliverables:** `/backend/electrical/features.py`, `/backend/electrical/stage0_veto.py`,
`/backend/electrical/stage2_screening.py`, tests.

**Acceptance criteria:**
- [ ] All six Stage-1 electrical features computed and validated against at least one real unit from
      each ingested dataset (shown in report with actual numeric values, not placeholders)
- [ ] Stage 0 veto correctly quarantines at least one deliberately corrupted/implausible synthetic
      record (demonstrated, not just claimed)
- [ ] Stage 2 screening produces a distinct, richer feature set than Stage 1 for escalated units
- [ ] `pytest` passes

**Required Report Sections:** same pattern as Gate 1, plus `## Sample Feature Outputs (real numbers)`

---

## GATE 3 — Degradation State Model

**Objective:** Build the single, shared degradation-state generator (Section 5.4) that will drive both
electrical and acoustic perturbations consistently.

**Deliverables:** `/backend/degradation/state_model.py` implementing the five states with documented
capacity-fade, DCIR, ToF-shift, and amplitude/energy-attenuation ranges per state.

**Acceptance criteria:**
- [ ] All five states implemented with explicit, documented numeric ranges
- [ ] Same state + same seed → identical output (determinism proven in report with two runs shown side
      by side)
- [ ] Different seeds at the same state → output varies within the documented range, not outside it
      (shown with a small statistical check, e.g. 100 draws, min/max within bounds)
- [ ] `pytest` passes

**Required Report Sections:** standard pattern plus `## State Definitions Table (with ranges)`
`## Determinism Proof` `## Range-Compliance Check Results`

---

## GATE 4 — EMAT Acoustic Physics Simulator

**Objective:** Build the multilayer propagation model and chirp transmission described in Section
5.3(a), driven by Gate 3's degradation states.

**Deliverables:** `/backend/emat/physics_simulator.py`.

**Acceptance criteria:**
- [ ] Multilayer model implements all five layers named in Section 5.3(a) with configurable acoustic
      impedance, velocity, attenuation, thickness
- [ ] Chirp (or Golay) transmit waveform generation implemented and plotted
- [ ] Echo delay/amplitude demonstrably changes as a function of the Gate-3 degradation state (shown
      with a plot across all five states, delay/amplitude values tabulated)
- [ ] Code comments and docstrings use the "perturbs acoustic propagation characteristics" framing,
      NOT "clean reflection off a plating slab" language
- [ ] `pytest` passes

**Required Report Sections:** standard pattern plus `## Echo Response Across 5 Degradation States
(table + plot reference)` `## Framing Language Compliance Check`

---

## GATE 5 — EMAT Noise Model & DSP Recovery Pipeline

**Objective:** Implement Section 5.3(b) and 5.3(c): noise injection, matched filtering, and feature
extraction, and prove recovery works.

**Deliverables:** `/backend/emat/noise_model.py`, `/backend/emat/dsp_receiver.py`
(named exactly "Software-Defined Acoustic Receiver" in module docstring).

**Acceptance criteria:**
- [ ] Noise model injects white thermal noise, sinusoidal EMI, and low-frequency rumble, independently
      configurable
- [ ] A before/after plot is generated and saved showing the echo invisible in raw noisy signal and
      recovered as a sharp peak after matched filtering, at approximately −15 dB SNR or worse
- [ ] ToF, amplitude, energy, echo width, attenuation, SNR, and repeatability are all extracted and
      shown numerically for at least 10 simulated units spanning all 5 degradation states
  - [ ] Extracted ToF values correlate with the degradation state in the expected direction (report
      must show this correlation explicitly, e.g. a simple table or correlation coefficient)
- [ ] No instance of "Digital LNA" anywhere in code, comments, or report — only "Software-Defined
      Acoustic Receiver" / "Digital Matched-Filter Receiver"
- [ ] `pytest` passes

**Required Report Sections:** standard pattern plus `## Before/After Recovery Evidence (plot + SNR)`
`## Extracted Features Table (10+ units, 5 states)` `## ToF-vs-Degradation Correlation`
`## Naming Compliance Check`

---

## GATE 6 — Multimodal Feature Fusion

**Objective:** Combine electrical (Gate 2) and acoustic (Gate 5) features per unit; support the three
run modes from Section 5.5.

**Deliverables:** `/backend/fusion/feature_fusion.py`.

**Acceptance criteria:**
- [ ] Electrical-only, acoustic-only, and fused feature vectors all producible from the same unit on
      demand
- [ ] Fused vector schema documented (field list, source of each field)
- [ ] Demonstrated on at least 20 units drawn from Gate 1's lot simulator
- [ ] `pytest` passes

**Required Report Sections:** standard pattern plus `## Fused Feature Schema` `## 20-Unit Demonstration
Table`

---

## GATE 7 — LOTUS Statistical Calibration Engine

**Objective:** Implement Section 5.6 in full: lot-definition enforcement with auto sub-lot splitting,
random reference sampling with the documented sample-size formula, the exact risk definition R(λ,a),
and a from-scratch Learn-Then-Test calibration.

**Deliverables:** `/backend/lotus/lot_definition.py`, `/backend/lotus/sampling.py`,
`/backend/lotus/ltt_calibration.py`.

**Acceptance criteria:**
- [ ] A deliberately mixed batch (two chemistries forced together) is automatically split into sub-lots
      — demonstrated, not just asserted
- [ ] Sample-size table reproduced exactly: ε=10%→m≈22, ε=5%→m≈45, ε=2%→m≈114, ε=1%→m≈230 at 90%
      confidence (unit test asserts these values within rounding tolerance)
- [ ] R(λ,a) implemented exactly as the unconditional joint probability defined in Section 5.6 — a unit
      test must explicitly prove it is NOT computing P(fail|approve) by constructing a synthetic
      low-approval-rate scenario where the two values differ, and showing the code reports the correct
      (joint) one
- [ ] LTT calibration certifies a threshold set, at a configurable (ε, δ), on a synthetic reference
      sample, and the report shows the resulting certified threshold(s) and the selected lowest-mean-time
      policy among them
- [ ] "Escalation is always safe" property demonstrated: show that units reaching Stage 3 contribute
      zero counted error by construction
- [ ] `pytest` passes

**Required Report Sections:** standard pattern plus `## Sub-Lot Splitting Demonstration`
`## Sample-Size Table Verification` `## R(λ,a) vs P(fail|approve) Divergence Proof`
`## LTT Calibration Output` `## Escalation-Safety Proof`

---

## GATE 8 — Sequential Decision Policy Engine & Certificate Generator

**Objective:** Implement Section 5.7 (four-way decision + OOD abstention + multi-application approval)
and Section 5.8 (certificate generator with mandatory dual-risk display).

**Deliverables:** `/backend/lotus/decision_engine.py`, `/backend/lotus/certificate.py`.

**Acceptance criteria:**
- [ ] All four decisions (approve/reject/escalate/abstain) demonstrated on real simulated units
- [ ] A unit abstains correctly when its fused feature vector is injected as a deliberate
      out-of-distribution outlier (demonstrated)
- [ ] A single unit shown holding two different per-application approvals simultaneously, each with its
      own R(λ,a)
- [ ] Certificate output contains every field listed in Section 5.8, with the CERTIFIED and ESTIMATE
      risk values visually/textually distinct in the generated object (JSON or equivalent — frontend
      styling comes later, but the data contract must already separate them)
- [ ] `pytest` passes

**Required Report Sections:** standard pattern plus `## Four-Decision Demonstration`
`## OOD Abstention Proof` `## Multi-Application Approval Example` `## Sample Certificate Output (full
JSON)`

---

## GATE 9 — Backend API & Persistence Layer

**Objective:** Wire Gates 1–8 into a FastAPI service with a database, exposing endpoints the frontend
will consume, and a clean ingestion interface for future hardware data (Section 11).

**Deliverables:** `/backend/api/main.py` and route modules; SQLite schema + migration script;
OpenAPI docs auto-generated by FastAPI.

**Acceptance criteria:**
- [ ] Endpoints exist for: create/list lots, run a lot through the full pipeline, get lot certificate,
      get per-unit evidence record, list units with filters, get E0–E5 experiment results (stubbed if
      experiments not yet run — but the endpoint contract must exist)
- [ ] A generic `/ingest/sensor-reading` endpoint accepts a schema-validated external reading
      (documented as the future hardware bridge point) without touching statistical/decision modules
- [ ] Running the API and hitting each endpoint with a real request returns correct, non-mocked data
      (report shows actual curl/HTTP responses)
- [ ] `pytest` passes for API layer (using FastAPI's test client)

**Required Report Sections:** standard pattern plus `## Endpoint List with Sample Requests/Responses`
`## Hardware-Bridge Endpoint Confirmation`

---

## GATE 10 — Frontend Dashboard Core Pages

**Objective:** Build pages 1, 2, 3, 6, 7 from Section 8 (Operations Overview, Lot Registry, Lot Detail/
Live Calibration, Certificate Viewer, Shifted-Lot Demo), styled per `03_design_system_brief.md`.

**Deliverables:** `/frontend` React app with these pages routed and live-wired to Gate 9's API — no
mock/static data once the API is running.

**Acceptance criteria:**
- [ ] All five pages render and pull real data from the backend (screenshots or recorded output in
      report)
- [ ] Operations Overview shows the Section 6 worked-example lot (200 units, ε=5%, ~45 reference units)
      as the default seeded scenario, with the computed (not hardcoded) savings percentage
- [ ] Shifted-Lot Demo page actually triggers the sub-lot-splitting or elevated-escalation behavior
      from Gate 7/8 live, not a canned screenshot
- [ ] Visual style matches the mapped reference images in `03_design_system_brief.md` (layout, density,
      component language) while content is 100% LOTUS-EMAT terminology — zero copied reference content
      (no "EV Champ," "ZIPSURE," "AVILOO," "TWAICE," etc. anywhere)
- [ ] Dual-risk (CERTIFIED vs ESTIMATE) labeling is visually distinct on the certificate viewer

**Required Report Sections:** standard pattern plus `## Page-by-Page Screenshot/Output Evidence`
`## Design-Reference Compliance Check` `## Copied-Content Audit (confirm zero matches)`

---

## GATE 11 — EMAT Multiphysics Visualization Page

**Objective:** Build Section 9 in full — the single most important visual in the product.

**Deliverables:** `/frontend` EMAT page using Canvas or WebGL/Three.js, bound to live backend data from
Gates 4–5.

**Acceptance criteria:**
- [ ] All five required visual elements present (transducer, aluminum casing with eddy-current glow,
      graphite anode layer, dynamic plating-defect layer, animated propagating wavefront heatmap)
- [ ] Plating-defect layer thickness is provably data-driven: switching the degradation-state selector
      visibly changes rendered thickness (before/after screenshots required in report)
- [ ] Wavefront animation timing is synchronized to the actual simulated ToF value for the selected
      unit, not an arbitrary fixed animation duration (report must show the ToF value next to the
      animation duration/timing used)
- [ ] Live waveform panel (raw noisy vs. matched-filter-recovered) and extracted feature readout are
      present and update when a different unit/state is selected
- [ ] Page performs smoothly (no excessive frame drop) — basic performance note in report

**Required Report Sections:** standard pattern plus `## Five-Element Visual Checklist (with
screenshots)` `## Data-Binding Proof (state change → thickness change)` `## Timing-Sync Proof (ToF
value vs animation)` `## Performance Note`

---

## GATE 12 — Integration, Validation Experiments, Final Report

**Objective:** Run E0–E5 from Section 7 end-to-end against the full fused pipeline, and produce the
final consolidated project report.

**Deliverables:** `/notebooks/validation_E0_E5.ipynb` (or equivalent scripts), all required plots saved
to `/reports/figures/`, `/reports/FINAL_PROJECT_REPORT.md`.

**Acceptance criteria:**
- [ ] E0 (FDR-gap), E1 (shift validity), E2 (efficiency curve), E3 (sample-size sweep), E4 (ablations),
      E5 (headline figure, including the electrical-only vs fused comparison) all run and produce real
      output — not illustrative mockups
- [ ] Final report states explicitly, using Section 3's wording as a base: what is statistically
      certified, what is estimated-but-not-controlled, and what is explicitly not claimed
- [ ] Final report includes the worked numeric example from Section 6, computed from an actual pipeline
      run, not copied from this document
- [ ] Every page from Gates 10–11 is confirmed still working end-to-end in one final smoke-test pass

**Required Report Sections:** standard pattern plus `## E0–E5 Results Summary (with figure references)`
`## Honest Claims Statement (certified / estimated / not claimed)` `## Final Worked Example (actual
run)` `## End-to-End Smoke Test Confirmation` `## Gate Status: PASSED — PROJECT SOFTWARE PHASE COMPLETE`

---

## After Gate 12

Do not begin any hardware work. Stop and wait for explicit instruction to begin the hardware
integration phase described in Section 11 of `01_project_details.md`.
