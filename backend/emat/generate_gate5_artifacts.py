import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from backend.degradation.state_model import DegradationState, sample_degradation_parameters
from backend.emat.physics_simulator import EMATPhysicsSimulator
from backend.emat.noise_model import EMATNoiseModel
from backend.emat.dsp_receiver import SoftwareDefinedAcousticReceiver

def generate_gate5_artifacts():
    os.makedirs('reports/figures', exist_ok=True)
    sim = EMATPhysicsSimulator()
    nm = EMATNoiseModel()
    rx = SoftwareDefinedAcousticReceiver(fs_hz=sim.fs_hz)

    # 1. Before/After Plot for Healthy Cell at -15 dB SNR
    deg_healthy = sample_degradation_parameters(DegradationState.HEALTHY, seed=42)
    prop = sim.simulate_propagation(deg_healthy)
    clean = np.array(prop['echo_signal'])
    tx = sim.generate_chirp_tx()

    bursts = [
        nm.inject_noise(clean, sim.time_vector, target_snr_db=-15.0, seed=100 + b)['noisy_signal']
        for b in range(16)
    ]
    raw_noisy = bursts[0]
    res_dsp = rx.process(bursts, tx, sim.time_vector)

    t_us = sim.time_vector * 1e6
    t_comp_us = (sim.time_vector - 0.5 * sim.chirp_duration_s) * 1e6
    envelope = np.array(res_dsp['envelope'])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=150)

    # Raw Noisy Plot
    ax1.plot(t_us, raw_noisy, color='#ef4444', lw=1.0, alpha=0.85, label='Raw Noisy Signal (SNR ≈ -15 dB: Thermal + EMI + Rumble)')
    ax1.axvspan(prop['perturbed_tof_us'], prop['perturbed_tof_us'] + 2.5, color='#fbbf24', alpha=0.25, label=f"Buried Echo Window (True ToF = {prop['perturbed_tof_us']} us)")
    ax1.set_title('EMAT Raw Acoustic Channel: Echo Invisible in Deep Industrial Noise (-15 dB SNR)', fontsize=11, fontweight='bold')
    ax1.set_xlabel('Time (us)')
    ax1.set_ylabel('Amplitude (V)')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # Recovered Envelope Plot
    ax2.plot(t_comp_us, envelope, color='#0284c7', lw=1.8, label=f"Software-Defined Acoustic Receiver Output (SNR = {res_dsp['features']['snr_db']} dB)")
    ax2.axvline(res_dsp['features']['tof_us'], color='#10b981', ls='--', lw=2.0, label=f"Extracted Peak ToF = {res_dsp['features']['tof_us']} us")
    ax2.set_title('Recovered Ultrasonic Echo After Bandpass + Coherent Integration + Matched Filter', fontsize=11, fontweight='bold')
    ax2.set_xlabel('Compensated Time-of-Flight (us)')
    ax2.set_ylabel('Correlation Envelope Magnitude')
    ax2.set_xlim(0, 10)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = 'reports/figures/emat_dsp_recovery.png'
    plt.savefig(plot_path)
    plt.close()
    print('Plot saved to:', plot_path)

    # 2. Extract 10 units across 5 states
    states = [
        DegradationState.HEALTHY,
        DegradationState.MILD,
        DegradationState.MODERATE,
        DegradationState.PLATING,
        DegradationState.SEVERE
    ]
    print('=== EXTRACTED FEATURES TABLE (10 UNITS) ===')
    table_rows = []
    for s_idx, state in enumerate(states):
        for u_idx in range(2):
            unit_id = f"UNIT-{state.name[:3]}-{u_idx+1}"
            seed = 500 + s_idx * 10 + u_idx
            deg = sample_degradation_parameters(state, seed=seed)
            p = sim.simulate_propagation(deg)
            c = np.array(p['echo_signal'])
            b_list = [
                nm.inject_noise(c, sim.time_vector, target_snr_db=-14.0, seed=seed * 10 + b)['noisy_signal']
                for b in range(12)
            ]
            r = rx.process(b_list, tx, sim.time_vector)
            f = r['features']
            row = (
                unit_id, state.value, deg.capacity_fade_pct, p['perturbed_tof_us'],
                f['tof_us'], f['peak_amplitude'], f['integrated_energy'],
                f['echo_width_us'], f['attenuation_db'], f['snr_db'], f['repeatability']
            )
            table_rows.append(row)
            print(f"{unit_id} | {state.value} | True ToF: {p['perturbed_tof_us']} | Recov ToF: {f['tof_us']} | Peak Amp: {f['peak_amplitude']} | SNR: {f['snr_db']} dB | Rep: {f['repeatability']}")

    # Correlation calculation
    tofs = [r[4] for r in table_rows]
    indices = [s_idx for s_idx in range(5) for _ in range(2)]
    corr = float(np.corrcoef(indices, tofs)[0, 1])
    print(f"\nPearson correlation coefficient between Degradation State and Extracted ToF: {corr:.4f}")

if __name__ == '__main__':
    generate_gate5_artifacts()
