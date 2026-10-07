# Gate 05 Report: EMAT Noise Model & DSP Recovery Pipeline

## Objective
Implement Section 5.3(b) and 5.3(c) of `01_project_details.md`: acoustic channel noise injection (thermal noise, sinusoidal EMI, low-frequency rumble), the **Software-Defined Acoustic Receiver** (digital matched-filter pulse compression receiver), and ultrasonic degradation feature extraction, proving robust echo recovery at −15 dB SNR or worse.

## What Was Built
1. **Noise Model (`/backend/emat/noise_model.py`)**:
   - Implemented `EMATNoiseModel` generating three independent noise channels:
     - Broadband Johnson-Nyquist white thermal noise
     - Sinusoidal EMI (simulating inverter/motor harmonics at 60 kHz, 200 kHz, 1.2 MHz)
     - Low-frequency mechanical rumble (< 20 kHz vibration)
   - Supports independent configuration and calibrated target SNR injection (down to −15 dB).
2. **Software-Defined Acoustic Receiver (`/backend/emat/dsp_receiver.py`)**:
   - Front-end 4th-order Butterworth bandpass filter (0.8 MHz – 4.5 MHz)
   - Multi-burst coherent pulse integration (averaging across repeated bursts)
   - Matched filter / pulse compression against normalized transmit chirp
   - Analytic signal envelope extraction via Hilbert transform
   - Extraction of all 8 acoustic features: `tof_us`, `peak_amplitude`, `integrated_energy`, `echo_width_us`, `attenuation_db`, `snr_db`, `repeatability`, `center_frequency_mhz`.

## Before/After Recovery Evidence (plot + SNR)

Plot Reference: `reports/figures/emat_dsp_recovery.png`.
- **Raw Input Signal**: Signal-to-Noise Ratio is approximately **−15.0 dB**. In the raw time-domain record, the weak acoustic echo is completely submerged beneath combined thermal background, industrial EMI, and vibration rumble (maximum peak-to-noise ratio < 3.5σ; echo cannot be detected visually).
- **Recovered Output Signal**: Following bandpass conditioning, coherent burst accumulation (16 pulses), and matched filter cross-correlation, the receiver produces a sharp, clean correlation peak at **ToF = 3.60 μs** with an output post-processing SNR of **+19.2 dB** (a net processing gain exceeding **34 dB**).

## Extracted Features Table (10+ units, 5 states)

Ten simulated battery units spanning all 5 degradation states evaluated under realistic noisy conditions (−14 dB input SNR):

| Unit ID | Degradation State | True ToF (μs) | Recovered ToF (μs) | Peak Amplitude | Energy (V²·s) | Echo FWHM (μs) | Attenuation (dB) | Post-SNR (dB) | Repeatability | Center Freq (MHz) |
|---|---|---|---|---|---|---|---|---|---|---|
| **UNIT-HEA-1** | Healthy | 3.455 | 3.600 | 2.0540 | $3.57 \times 10^{-6}$ | 0.850 | +2.73 | 19.20 | 0.985 | 2.50 |
| **UNIT-HEA-2** | Healthy | 3.399 | 3.600 | 1.8086 | $3.12 \times 10^{-6}$ | 0.850 | +1.62 | 19.61 | 0.985 | 2.50 |
| **UNIT-MIL-1** | Mild degradation | 3.616 | 3.800 | 1.3051 | $2.24 \times 10^{-6}$ | 0.900 | -1.21 | 19.90 | 0.981 | 2.50 |
| **UNIT-MIL-2** | Mild degradation | 3.640 | 3.850 | 1.3430 | $2.31 \times 10^{-6}$ | 0.900 | -0.96 | 18.37 | 0.982 | 2.50 |
| **UNIT-MOD-1** | Moderate degradation | 3.966 | 4.150 | 0.6839 | $1.15 \times 10^{-6}$ | 1.050 | -6.82 | 19.98 | 0.965 | 2.45 |
| **UNIT-MOD-2** | Moderate degradation | 4.136 | 4.300 | 0.5437 | $8.90 \times 10^{-7}$ | 1.100 | -8.82 | 16.18 | 0.958 | 2.45 |
| **UNIT-PLA-1** | Plating-associated | 5.046 | 5.250 | 0.3032 | $4.80 \times 10^{-7}$ | 1.350 | -13.89 | 17.07 | 0.943 | 2.40 |
| **UNIT-PLA-2** | Plating-associated | 4.748 | 4.950 | 0.3320 | $5.20 \times 10^{-7}$ | 1.300 | -13.10 | 16.27 | 0.946 | 2.40 |
| **UNIT-SEV-1** | Severe degradation | 5.144 | 5.350 | 0.2075 | $3.10 \times 10^{-7}$ | 1.650 | -17.18 | 19.44 | 0.933 | 2.35 |
| **UNIT-SEV-2** | Severe degradation | 5.385 | 5.600 | 0.1023 | $1.40 \times 10^{-7}$ | 1.800 | -23.32 | 18.94 | 0.915 | 2.30 |

## ToF-vs-Degradation Correlation
- **Pearson Correlation Coefficient ($r$)**: **0.9705** between ordinal degradation severity (0 = Healthy, 4 = Severe) and extracted Time-of-Flight.
- The strong positive correlation confirms that acoustic wave speed reduction and interfacial dispersion reliably reflect degradation progression, matching theoretical acoustic wave propagation in layered battery media.

## Naming Compliance Check
- **Zero occurrences** of prohibited receiver naming across the entire codebase, comments, docstrings, and reports (verified by `test_naming_compliance_no_prohibited_terms`).
- The receiver is consistently named **"Software-Defined Acoustic Receiver"** (with secondary alias **"Digital Matched-Filter Receiver"**).

## Acceptance Checklist
- [x] Noise model injects white thermal noise, sinusoidal EMI, and low-frequency rumble, independently configurable — *Evidence: Verified by `test_noise_model_independent_components`.*
- [x] A before/after plot is generated and saved showing the echo invisible in raw noisy signal and recovered as a sharp peak after matched filtering, at approximately −15 dB SNR or worse — *Evidence: Generated and saved to `reports/figures/emat_dsp_recovery.png` with −15 dB input SNR.*
- [x] ToF, amplitude, energy, echo width, attenuation, SNR, and repeatability are all extracted and shown numerically for at least 10 simulated units spanning all 5 degradation states — *Evidence: All 8 features populated in the 10-unit table above.*
- [x] Extracted ToF values correlate with the degradation state in the expected direction ($r = 0.9705 > 0.90$) — *Evidence: Verified by `test_feature_extraction_and_tof_correlation_ten_units`.*
- [x] No instance of prohibited receiver naming anywhere in code, comments, or report — only "Software-Defined Acoustic Receiver" / "Digital Matched-Filter Receiver" — *Evidence: Verified by `test_naming_compliance_no_prohibited_terms`.*
- [x] `pytest` passes — *Evidence: `python -m pytest tests/test_emat_dsp.py` passed with 4 passed in 1.73s.*

## Gate Status: PASSED
