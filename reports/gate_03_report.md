# Gate 03 Report: Degradation State Model

## Objective
Build the single, shared degradation-state generator (Section 5.4 of `01_project_details.md`) that will drive both electrical feature perturbations and EMAT acoustic physics-layer perturbations consistently and provably linked to the same underlying ground-truth state.

## What Was Built
- `/backend/degradation/state_model.py`: Implemented the five canonical degradation states (`Healthy`, `Mild degradation`, `Moderate degradation`, `Plating-associated degradation`, `Severe degradation`).
- Each state specifies explicit physical numeric bounds for capacity fade (%), DCIR (mΩ), acoustic Time-of-Flight shift (μs), acoustic amplitude attenuation (dB), acoustic energy attenuation (dB), and lithium plating proxy defect thickness (μm), backed by physical electrochemical rationales.
- Deterministic sampling function `sample_degradation_parameters(state, seed)` ensuring strict reproducibility.
- Test suite `/tests/test_degradation.py` confirming range compliance, determinism, and state completeness.

## State Definitions Table (with ranges)

| Degradation State | Capacity Fade (%) | DCIR (mΩ) | Acoustic ToF Shift (μs) | Amp Attenuation (dB) | Energy Attenuation (dB) | Plating Defect Thickness (μm) | Underlying Electrochemical & Acoustic Rationale |
|---|---|---|---|---|---|---|---|
| **Healthy** | [0.0, 8.0] | [15.0, 22.0] | [0.00, 0.25] | [-1.5, 0.0] | [-2.0, 0.0] | [0.0, 0.0] | Pristine electrode active material and uniform electrolyte wetting; negligible SEI impedance; high acoustic transmission with minimal scattering. |
| **Mild degradation** | [8.0, 16.0] | [22.0, 28.0] | [0.25, 0.60] | [-4.0, -1.5] | [-5.0, -2.0] | [0.0, 0.5] | Early SEI formation consuming cyclable lithium; slight rise in charge transfer resistance; minor acoustic boundary mismatch at separator interface. |
| **Moderate degradation** | [16.0, 24.0] | [28.0, 38.0] | [0.60, 1.10] | [-7.5, -4.0] | [-9.0, -5.0] | [0.5, 1.5] | Thickening passivation layers and micro-cracking of active cathode particles; increased interfacial resistance; moderate wave dispersion and velocity reduction. |
| **Plating-associated degradation** | [24.0, 32.0] | [38.0, 52.0] | [1.10, 1.80] | [-12.0, -7.5] | [-14.0, -9.0] | [2.0, 8.0] | Metallic lithium deposits at graphite anode boundary perturbing acoustic boundary conditions; pronounced ultrasonic wave delay and interfacial acoustic scattering. |
| **Severe degradation** | [32.0, 48.0] | [52.0, 85.0] | [1.80, 2.80] | [-18.0, -12.0] | [-22.0, -14.0] | [8.0, 20.0] | Extensive active material loss, severe electrolyte dry-out, and heavy dead lithium deposits; dramatic impedance surge and massive acoustic signal damping. |

## Determinism Proof
Proven by executing `sample_degradation_parameters(state, seed=42)` across two completely independent invocations. Below are the side-by-side execution outputs:

- **Healthy**: Run 1 = `{'state': 'Healthy', 'capacity_fade_pct': 6.19, 'dcir_mohm': 18.07, 'tof_shift_us': 0.215, 'amp_attenuation_db': -0.45, 'energy_attenuation_db': -1.81, 'plating_thickness_um': 0.0}` | Run 2 = identical (`Matches: True`).
- **Mild degradation**: Run 1 = `{'state': 'Mild degradation', 'capacity_fade_pct': 14.19, 'dcir_mohm': 24.63, 'tof_shift_us': 0.551, 'amp_attenuation_db': -2.26, 'energy_attenuation_db': -4.72, 'plating_thickness_um': 0.49}` | Run 2 = identical (`Matches: True`).
- **Moderate degradation**: Run 1 = `{'state': 'Moderate degradation', 'capacity_fade_pct': 22.19, 'dcir_mohm': 32.39, 'tof_shift_us': 1.029, 'amp_attenuation_db': -5.06, 'energy_attenuation_db': -8.62, 'plating_thickness_um': 1.48}` | Run 2 = identical (`Matches: True`).
- **Plating-associated degradation**: Run 1 = `{'state': 'Plating-associated degradation', 'capacity_fade_pct': 30.19, 'dcir_mohm': 44.14, 'tof_shift_us': 1.701, 'amp_attenuation_db': -8.86, 'energy_attenuation_db': -13.53, 'plating_thickness_um': 7.85}` | Run 2 = identical (`Matches: True`).
- **Severe degradation**: Run 1 = `{'state': 'Severe degradation', 'capacity_fade_pct': 44.38, 'dcir_mohm': 66.48, 'tof_shift_us': 2.659, 'amp_attenuation_db': -13.82, 'energy_attenuation_db': -21.25, 'plating_thickness_um': 19.71}` | Run 2 = identical (`Matches: True`).

## Range-Compliance Check Results
Evaluated over 100 independent random seeds per state (500 total draws). Observed empirical minimum and maximum bounds strictly conform within the specified intervals:
- **Healthy**: Fade [0.03%, 7.98%], DCIR [15.00 mΩ, 21.95 mΩ], ToF Shift [0.005 μs, 0.245 μs].
- **Mild degradation**: Fade [8.03%, 15.98%], DCIR [22.00 mΩ, 27.95 mΩ], ToF Shift [0.257 μs, 0.593 μs].
- **Moderate degradation**: Fade [16.03%, 23.98%], DCIR [28.00 mΩ, 37.92 mΩ], ToF Shift [0.610 μs, 1.090 μs].
- **Plating-associated degradation**: Fade [24.03%, 31.98%], DCIR [38.00 mΩ, 51.89 mΩ], ToF Shift [1.114 μs, 1.787 μs].
- **Severe degradation**: Fade [32.06%, 47.96%], DCIR [52.01 mΩ, 84.74 mΩ], ToF Shift [1.820 μs, 2.781 μs].

Zero boundary violations were observed across all parameters.

## Acceptance Checklist
- [x] All five states implemented with explicit, documented numeric ranges — *Evidence: Documented in `backend/degradation/state_model.py` and tabulated above.*
- [x] Same state + same seed → identical output (determinism proven in report with two runs shown side by side) — *Evidence: Side-by-side run outputs displayed above; verified in `test_determinism_same_seed_identical_output`.*
- [x] Different seeds at the same state → output varies within the documented range, not outside it (shown with a small statistical check, e.g. 100 draws, min/max within bounds) — *Evidence: 100 draws per state summarized above; verified in `test_range_compliance_over_100_seeds`.*
- [x] `pytest` passes — *Evidence: `python -m pytest tests/test_degradation.py` passed with 3 passed in 0.24s.*

## Gate Status: PASSED
