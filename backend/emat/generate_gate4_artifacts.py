import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from backend.degradation.state_model import DegradationState, sample_degradation_parameters
from backend.emat.physics_simulator import EMATPhysicsSimulator

def generate_gate4_artifacts():
    os.makedirs('reports/figures', exist_ok=True)
    sim = EMATPhysicsSimulator()

    states = [
        DegradationState.HEALTHY,
        DegradationState.MILD,
        DegradationState.MODERATE,
        DegradationState.PLATING,
        DegradationState.SEVERE
    ]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), dpi=150)

    # Chirp TX
    t_chirp = np.arange(int(sim.chirp_duration_s * sim.fs_hz)) * sim.dt * 1e6
    tx = sim.generate_chirp_tx()
    ax1.plot(t_chirp, tx, color='#0284c7', lw=1.5)
    ax1.set_title('EMAT Chirp Transmit Waveform (1.0 - 4.0 MHz, Windowed LFM)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Time (μs)')
    ax1.set_ylabel('Amplitude (V)')
    ax1.grid(True, alpha=0.3)

    # Echo responses across states
    colors = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#ef4444']
    results = []
    for state, color in zip(states, colors):
        deg = sample_degradation_parameters(state, seed=42)
        res = sim.simulate_propagation(deg)
        results.append(res)
        t_us = np.array(res['time_us'])
        echo = np.array(res['echo_signal'])
        ax2.plot(t_us, echo, label=f"{state.value} (ToF: {res['perturbed_tof_us']} μs, Amp: {res['peak_amplitude']:.3f})", color=color, lw=1.5)

    ax2.set_title('Acoustic Echo Response Across 5 Degradation States (Multilayer Propagation)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Round-Trip Time (μs)')
    ax2.set_ylabel('Echo Amplitude')
    ax2.legend(loc='upper right', framealpha=0.9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = 'reports/figures/emat_physics_states.png'
    plt.savefig(out_path)
    plt.close()

    print('Figure saved to:', out_path)
    print('=== ECHO RESPONSE TABLE ===')
    for r in results:
        print(f"{r['state']} | Base ToF: {r['base_tof_us']} us | Perturbed ToF: {r['perturbed_tof_us']} us | Shift: {r['tof_shift_us']} us | Peak Amp: {r['peak_amplitude']} | Energy: {r['echo_energy']:.2e} | Defect Thick: {r['plating_thickness_um']} um")

if __name__ == '__main__':
    generate_gate4_artifacts()
