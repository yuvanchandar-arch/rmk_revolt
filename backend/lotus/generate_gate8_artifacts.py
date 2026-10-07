import json
from backend.data.lot_simulator import LotSimulator
from backend.data.loaders import BatteryRecord
from backend.lotus.sampling import draw_reference_sample
from backend.lotus.ltt_calibration import LTTCalibrationEngine
from backend.lotus.decision_engine import SequentialDecisionEngine, DecisionOutcome
from backend.lotus.certificate import LotCertificateGenerator

def run_gate8_artifacts():
    sim = LotSimulator()
    lot = sim.create_same_source_lot("LOT-NOMINAL-NMC-200", size=200, seed=42)
    ref_units, remaining = draw_reference_sample(lot.units, m=45, seed=42)

    calibrator = LTTCalibrationEngine()
    policies = {
        app_id: calibrator.calibrate_application(ref_units, app_id, epsilon=0.05, delta=0.10)
        for app_id in ["solar_backup", "low_power_lighting", "fast_charge_buffer"]
    }

    engine = SequentialDecisionEngine(policies=policies)
    engine.fit_calibration_population(ref_units)

    print("=== 1. FOUR-DECISION DEMONSTRATION ===")
    # 1. Stage-1 Approved Unit
    u_s1 = next(u for u in remaining if engine.evaluate_unit(u, target_application="solar_backup").resolution_stage == "stage1")
    res_s1 = engine.evaluate_unit(u_s1, target_application="solar_backup")
    print(f"STAGE-1 RESOLVED: Unit {res_s1.unit_id} -> {res_s1.decision.value} | Path: {res_s1.decision_path[-1]}")

    # 2. Stage-2 Kinetic Resolved Unit
    u_s2 = next(u for u in remaining if engine.evaluate_unit(u, target_application="solar_backup").resolution_stage == "stage2")
    res_s2 = engine.evaluate_unit(u_s2, target_application="solar_backup")
    print(f"STAGE-2 RESOLVED: Unit {res_s2.unit_id} -> {res_s2.decision.value} | Path: {res_s2.decision_path[-1]}")

    # 3. Stage-3 Fallback Unit
    u_s3 = next(u for u in remaining if engine.evaluate_unit(u, target_application="solar_backup").resolution_stage == "stage3")
    res_s3 = engine.evaluate_unit(u_s3, target_application="solar_backup")
    print(f"STAGE-3 FALLBACK: Unit {res_s3.unit_id} -> {res_s3.decision.value} | Fallback Cycler Tested: {res_s3.stage3_tested} | Path: {res_s3.decision_path[-1]}")

    # Abstain
    ood_synthetic = BatteryRecord(
        unit_id="UNIT-OOD-DEMO",
        dataset_source="PulseBat",
        chemistry="NMC",
        format="pouch",
        platform="Platform-NMC-Pouch",
        fleet_source="MetroEV-Delivery-FleetA",
        usage_history="delivery",
        nominal_capacity_ah=2.5,
        measured_capacity_ah=1.8,
        capacity_fade_pct=28.0,
        cycle_count=800,
        storage_condition_class="controlled_ambient",
        damage_category="none",
        time_series={},
        early_features={
            "ocv_v": 3.96,
            "dcir_mohm": 175.0,  # Extreme resistance anomaly
            "cell_imbalance_mv": 90.0,
            "sensor_quality_flag": 1
        }
    )
    res_ood = engine.evaluate_unit(ood_synthetic)
    print(f"ABSTAIN: Unit {res_ood.unit_id} -> {res_ood.decision.value} | Is OOD: {res_ood.is_ood} | Mahalanobis Dist: {res_ood.mahalanobis_distance} | Path: {res_ood.decision_path[-1]}")

    print("\n=== 2. MULTI-APPLICATION APPROVAL EXAMPLE ===")
    for u in remaining:
        res = engine.evaluate_unit(u, target_application="solar_backup")
        apps = [a.application_id for a in res.approved_applications]
        if "solar_backup" in apps and "low_power_lighting" in apps:
            print(f"Unit ID: {res.unit_id}")
            for a in res.approved_applications:
                print(f"  -> Approved for '{a.application_name}' ({a.application_id}) | R(lambda, a): {a.certified_risk_bound} [{a.label_certified}] | Cond. Fail Rate: {a.estimated_conditional_fail_rate} [{a.label_estimate}] | Max C-rate: {a.max_operating_c_rate}C | SoC Window: {a.soc_window}")
            break

    print("\n=== 3. CERTIFICATE GENERATION & DUAL-RISK AUDIT ===")
    decisions = [engine.evaluate_unit(u, target_application="solar_backup") for u in remaining]
    cert_gen = LotCertificateGenerator()
    cert = cert_gen.generate_certificate(
        lot_id=lot.lot_id,
        provenance=lot.provenance,
        lot_size=lot.size,
        ref_sample_size=len(ref_units),
        policies=policies,
        decisions=decisions
    )

    cert_json = cert.to_json(indent=2)
    with open("reports/sample_lot_certificate.json", "w", encoding="utf-8") as f:
        f.write(cert_json)
    print("Full Certificate JSON written to: reports/sample_lot_certificate.json")
    print(f"Lot Size N: {cert.lot_size_N} | Reference m: {cert.reference_sample_size_m}")
    print(f"Stage 1 Approvals: {cert.stage1_approval_count} | Escalations: {cert.stage2_escalation_count} | Reject/Quarantine: {cert.reject_quarantine_count}")
    print(f"Mean Test Time: {cert.mean_test_time_per_unit_s}s | Time Saved vs Full Testing: {cert.time_saved_vs_full_testing_pct}%")
    print("Dual Risk Metrics:")
    for m in cert.dual_risk_metrics:
        print(f"  [{m.application_id}] Certified Bound: {m.certified_early_approval_disagreement_bound} [{m.label_certified}] vs Est. Fail Rate: {m.estimated_conditional_fail_rate_among_approved} [{m.label_estimate}]")

if __name__ == '__main__':
    run_gate8_artifacts()
