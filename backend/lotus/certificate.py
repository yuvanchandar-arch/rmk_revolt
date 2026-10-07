"""Lot Certificate & Per-Unit Evidence Record Generator.

Implements Section 5.8 of 01_project_details.md with mandatory dual-risk display:
1. Certified early-approval disagreement bound R(lambda, a) [label: CERTIFIED]
2. Estimated conditional fail-rate among approved units [label: ESTIMATE — NOT CONTROLLED]

Both fields are always distinctly separated and labeled in the generated data contract.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import time
import json

from backend.lotus.decision_engine import UnitDecisionRecord, DecisionOutcome
from backend.lotus.ltt_calibration import CertifiedThresholdPolicy


@dataclass
class DualRiskRecord:
    application_id: str
    application_name: str
    certified_early_approval_disagreement_bound: float
    label_certified: str  # Must be "CERTIFIED"
    estimated_conditional_fail_rate_among_approved: float
    label_estimate: str   # Must be "ESTIMATE — NOT CONTROLLED"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LotCertificate:
    lot_id: str
    lot_definition_provenance: Dict[str, Any]
    lot_size_N: int
    reference_sample_size_m: int
    confidence_one_minus_delta: float
    risk_target_epsilon_per_application: Dict[str, float]
    stage1_approval_count: int
    stage2_escalation_count: int
    stage3_full_test_count: int
    reject_quarantine_count: int
    stage_accounting_scope: str
    primary_target_application_unit_partition: Dict[str, int]
    mean_test_time_per_unit_s: float
    time_saved_vs_full_testing_pct: float
    dual_risk_metrics: List[DualRiskRecord]
    data_quality_score: float
    out_of_distribution_flags_count: int
    application_recommendations_and_limits: Dict[str, Any]
    per_unit_evidence_records: List[Dict[str, Any]]
    certificate_id: str
    issued_timestamp: str
    legal_disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class LotCertificateGenerator:
    """Generates traceable, compliant qualification certificates with exact dual-risk metrics."""

    def generate_certificate(
        self,
        lot_id: str,
        provenance: Dict[str, Any],
        lot_size: int,
        ref_sample_size: int,
        policies: Dict[str, CertifiedThresholdPolicy],
        decisions: List[UnitDecisionRecord],
        delta: float = 0.10,
        full_test_time_s: float = 14400.0  # 4 hours per unit
    ) -> LotCertificate:
        """Constructs Section 5.8 compliant LotCertificate."""
        # Counts from realized sequential execution
        n_approve = sum(1 for d in decisions if d.decision == DecisionOutcome.APPROVE)
        n_escalate = sum(
            1 for d in decisions
            if getattr(d, "resolution_stage", "stage1") in ["stage2", "stage3"]
            or any("escalat" in str(p).lower() for p in getattr(d, "decision_path", []))
        )
        # Real count of units that actually underwent full Stage 3 testing:
        # Reference units (m) + screened units that actually took the Stage 3 fallback path
        n_stage3_fallback = sum(
            1 for d in decisions
            if getattr(d, "stage3_tested", False)
            or getattr(d, "resolution_stage", "") == "stage3"
            or any("stage 3 reference test" in str(p).lower() for p in getattr(d, "decision_path", []))
        )
        n_stage3 = ref_sample_size + n_stage3_fallback
        n_reject_quarantine = sum(
            1 for d in decisions if d.decision in [DecisionOutcome.REJECT, DecisionOutcome.ABSTAIN]
        )
        n_ood = sum(1 for d in decisions if d.is_ood)

        # Time savings computation
        total_time_screened = sum(d.mean_test_time_s for d in decisions)
        total_time_ref = ref_sample_size * full_test_time_s
        total_lot_time = total_time_screened + total_time_ref
        mean_time_per_unit = total_lot_time / max(1, lot_size)

        baseline_time_all_stage3 = lot_size * full_test_time_s
        time_saved_pct = max(0.0, ((baseline_time_all_stage3 - total_lot_time) / baseline_time_all_stage3) * 100.0)

        # Dual-risk metrics per application
        dual_risk_list: List[DualRiskRecord] = []
        risk_targets: Dict[str, float] = {}
        for app_id, pol in policies.items():
            risk_targets[app_id] = pol.target_epsilon
            rec = DualRiskRecord(
                application_id=app_id,
                application_name=pol.application_id.replace("_", " ").title(),
                certified_early_approval_disagreement_bound=pol.certified_risk_bound,
                label_certified="CERTIFIED",
                estimated_conditional_fail_rate_among_approved=pol.uncontrolled_conditional_fail_rate,
                label_estimate="ESTIMATE — NOT CONTROLLED"
            )
            dual_risk_list.append(rec)

        # Data quality score (100% minus penalties for OOD or missing sensors)
        n_clean = sum(1 for d in decisions if d.stage0_passed and not d.is_ood)
        data_quality = round((n_clean / max(1, len(decisions))) * 100.0, 1)

        # Evidence traces per unit
        unit_records = []
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for d in decisions:
            u_dict = {
                "unit_id": d.unit_id,
                "primary_decision": d.decision.value,
                "approved_applications": [a.to_dict() for a in d.approved_applications],
                "is_ood": d.is_ood,
                "mahalanobis_distance": d.mahalanobis_distance,
                "stage0_passed": d.stage0_passed,
                "decision_path": d.decision_path,
                "test_duration_s": d.mean_test_time_s,
                "timestamp": now_str,
                "features_summary": {
                    k: d.fused_features[k] for k in ["ocv_v", "dcir_mohm", "tof_us", "peak_amplitude", "snr_db"]
                    if k in d.fused_features
                }
            }
            unit_records.append(u_dict)

        cert_id = f"CERT-{lot_id}-{int(time.time())}"
        disclaimer = (
            "LOTUS-EMAT Decision Support Platform — Agreement certified with internally defined "
            "Stage-3 reference protocol. Does not constitute a safety warranty or guaranteed physical safety. "
            "Conditional failure rate is an uncontrolled estimate and must be distinguished from certified risk bound."
        )

        return LotCertificate(
            lot_id=lot_id,
            lot_definition_provenance=provenance,
            lot_size_N=lot_size,
            reference_sample_size_m=ref_sample_size,
            confidence_one_minus_delta=round(1.0 - delta, 2),
            risk_target_epsilon_per_application=risk_targets,
            stage1_approval_count=n_approve,
            stage2_escalation_count=n_escalate,
            stage3_full_test_count=n_stage3,
            reject_quarantine_count=n_reject_quarantine,
            stage_accounting_scope=(
                "Stage-by-stage pipeline activity counts across the sequential screening protocol. "
                "These metrics represent process transitions, not a disjoint unit partition: "
                "'stage3_full_test_count' includes m reference units plus screening fallbacks; "
                "'stage2_escalation_count' tracks units routed through Stage 2 kinetic screening; "
                "'stage1_approval_count' and 'reject_quarantine_count' track final approved and rejected/quarantined units. "
                "See 'primary_target_application_unit_partition' for the exact disjoint unit partition summing to lot size N."
            ),
            primary_target_application_unit_partition={
                "screened_units_approved": n_approve,
                "screened_units_rejected_or_quarantined": n_reject_quarantine,
                "screened_units_total": len(decisions),
                "reference_sample_units_full_tested": ref_sample_size,
                "lot_total_units_N": lot_size,
                "partition_sum_check": n_approve + n_reject_quarantine + ref_sample_size
            },
            mean_test_time_per_unit_s=round(mean_time_per_unit, 1),
            time_saved_vs_full_testing_pct=round(time_saved_pct, 1),
            dual_risk_metrics=dual_risk_list,
            data_quality_score=data_quality,
            out_of_distribution_flags_count=n_ood,
            application_recommendations_and_limits={
                "solar_backup": {"max_c_rate": 0.5, "soc_min": 15.0, "soc_max": 85.0},
                "low_power_lighting": {"max_c_rate": 0.2, "soc_min": 10.0, "soc_max": 90.0},
                "fast_charge_buffer": {"max_c_rate": 2.0, "soc_min": 20.0, "soc_max": 80.0}
            },
            per_unit_evidence_records=unit_records,
            certificate_id=cert_id,
            issued_timestamp=now_str,
            legal_disclaimer=disclaimer
        )
