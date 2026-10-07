import math
from backend.data.lot_simulator import LotSimulator
from backend.lotus.lot_definition import LotIntegrityEnforcer
from backend.lotus.sampling import compute_reference_sample_size, draw_reference_sample
from backend.lotus.ltt_calibration import (
    LTTCalibrationEngine,
    compute_unconditional_joint_risk,
    APPLICATIONS
)

def run_gate7_demo():
    print("=== 1. SUB-LOT SPLITTING DEMONSTRATION ===")
    sim = LotSimulator()
    mixed_lot = sim.create_mixed_chemistry_anomalous_lot("BATCH-MIXED-200", size=200, seed=42)
    enforcer = LotIntegrityEnforcer()
    is_homo, sub_lots, audit = enforcer.audit_and_split(mixed_lot.lot_id, mixed_lot.units)
    print(f"Is Homogeneous: {is_homo}")
    print(f"Action Taken: {audit['action_taken']}")
    print(f"Distinct groups count: {audit['distinct_groups_count']}")
    for s in sub_lots:
        print(f"  Sub-Lot ID: {s.sublot_id} | Size: {s.size} | Chemistry: {s.provenance['chemistry']} | Format: {s.provenance['format']} | Platform: {s.provenance['platform']}")

    print("\n=== 2. SAMPLE SIZE TABLE VERIFICATION (delta = 0.10) ===")
    table_cases = [0.10, 0.05, 0.02, 0.01]
    for eps in table_cases:
        m = compute_reference_sample_size(eps, delta=0.10)
        raw = math.log(0.10) / math.log(1.0 - eps)
        print(f"Target eps = {eps*100:4.1f}% | Raw m = {raw:7.3f} | Ceil m = {m}")

    print("\n=== 3. R(lambda, a) vs P(fail | approve) DIVERGENCE PROOF ===")
    # 100 units, 10 approved (2 fail Stage 3), 90 escalated/rejected
    decisions = ["approve"] * 10 + ["escalate"] * 50 + ["reject"] * 40
    stage3_passes = ([False] * 2 + [True] * 8) + ([False] * 30 + [True] * 60)
    r_joint, p_cond = compute_unconditional_joint_risk(decisions, stage3_passes)
    print(f"Unconditional Joint Risk R(lambda, a): {r_joint:.4f} (2.00%) [CERTIFIED TARGET]")
    print(f"Uncontrolled Conditional Fail Rate P(fail|approve): {p_cond:.4f} (20.00%) [ESTIMATE - NOT CONTROLLED]")
    print(f"Divergence factor: {p_cond / r_joint:.1f}x higher than unconditional risk!")

    print("\n=== 4. LTT CALIBRATION OUTPUT (Nominal 200 units, m=45 reference units) ===")
    nominal_lot = sim.create_same_source_lot("LOT-NOMINAL-NMC-200", size=200, seed=42)
    ref_units, rem_units = draw_reference_sample(nominal_lot.units, m=45, seed=42)
    calibrator = LTTCalibrationEngine()
    for app_id in ["solar_backup", "low_power_lighting", "fast_charge_buffer"]:
        policy = calibrator.calibrate_application(ref_units, app_id, epsilon=0.05, delta=0.10)
        print(f"App: {app_id:18s} | Lambda_Approve: {policy.lambda_approve_threshold:.3f} | Lambda_Reject: {policy.lambda_reject_threshold:.3f} | Certified Bound R <= {policy.certified_risk_bound:.4f} | Target eps: {policy.target_epsilon:.2f} | Mean Time: {policy.expected_mean_test_time_s:6.1f}s | Certified: {policy.is_certified}")

    print("\n=== 5. ESCALATION-SAFETY PROOF ===")
    decisions_esc = ["escalate"] * 50
    stage3_fail_all = [False] * 50
    r_esc, p_esc = compute_unconditional_joint_risk(decisions_esc, stage3_fail_all)
    print(f"Escalated unit count: 50 (100% fail Stage 3) -> R(lambda, a) error = {r_esc:.4f} (Zero counted error by construction)")

if __name__ == '__main__':
    run_gate7_demo()
