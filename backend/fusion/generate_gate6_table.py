from backend.data.lot_simulator import LotSimulator
from backend.fusion.feature_fusion import MultimodalFusionEngine, RunMode

sim = LotSimulator()
lot = sim.create_same_source_lot('LOT-NOMINAL-NMC-200', size=20, seed=42)
engine = MultimodalFusionEngine()

print('| Unit ID | Fade (%) | OCV (V) | DCIR (mOhm) | Rel Slope (V/s) | ToF (us) | Peak Amp | SNR (dB) | State |')
print('|---|---|---|---|---|---|---|---|---|')
for u in lot.units:
    res = engine.fuse(u, mode=RunMode.FUSED)
    f = res['features']
    print(f"| {u.unit_id} | {u.capacity_fade_pct:.1f}% | {f['ocv_v']:.3f} | {f['dcir_mohm']:.1f} | {f['relaxation_slope']:.4f} | {f['tof_us']:.3f} | {f['peak_amplitude']:.3f} | {f['snr_db']:.1f} | {res['degradation_state']} |")
