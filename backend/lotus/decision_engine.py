"""Sequential Decision Policy Engine with Out-Of-Distribution (OOD) Abstention.

Decides one of four outcomes for each unit:
1. Approve with limits (for specific secondary-life application(s))
2. Reject / recycle (insufficient performance across applications)
3. Escalate (borderline evidence; proceed to Stage 2 or Stage 3)
4. Abstain / quarantine (OOD or corrupted telemetry)

OOD Method Chosen:
Mahalanobis Distance with regularized covariance.
Rationale: It evaluates multivariate distance from the reference calibration centroid
while accounting for covariance between electrical and acoustic features. A chi-square
threshold (p < 0.005) flags statistical anomalies.
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
from scipy.spatial.distance import mahalanobis

from backend.data.loaders import BatteryRecord
from backend.electrical.stage0_veto import Stage0VetoEngine
from backend.electrical.stage2_screening import Stage2ScreeningPipeline
from backend.fusion.feature_fusion import MultimodalFusionEngine, RunMode
from backend.lotus.ltt_calibration import (
    CertifiedThresholdPolicy,
    APPLICATIONS,
    ApplicationCriteria,
    evaluate_stage3_ground_truth
)


class DecisionOutcome(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ESCALATE = "escalate"
    ABSTAIN = "abstain"


@dataclass
class ApplicationApproval:
    application_id: str
    application_name: str
    certified_risk_bound: float  # R(lambda, a)
    label_certified: str = "CERTIFIED"
    estimated_conditional_fail_rate: float = 0.0
    label_estimate: str = "ESTIMATE — NOT CONTROLLED"
    max_operating_c_rate: float = 0.5
    soc_window: Tuple[float, float] = (15.0, 85.0)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UnitDecisionRecord:
    unit_id: str
    decision: DecisionOutcome
    approved_applications: List[ApplicationApproval]
    rejected_applications: List[str]
    escalated_applications: List[str]
    is_ood: bool
    mahalanobis_distance: float
    stage0_passed: bool
    stage0_reasons: List[str]
    fused_features: Dict[str, float]
    decision_path: List[str]
    mean_test_time_s: float
    resolution_stage: str = "stage1"
    stage2_features: Optional[Dict[str, Any]] = None
    stage3_tested: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value
        return d


class MahalanobisOODDetector:
    """Detects Out-Of-Distribution (OOD) battery records using regularized Mahalanobis distance."""

    def __init__(self, threshold_distance: float = 5.5):
        self.threshold_distance = threshold_distance
        self.mean_vector: Optional[np.ndarray] = None
        self.inv_cov_matrix: Optional[np.ndarray] = None

    def fit(self, feature_vectors: np.ndarray):
        """Fits calibration population centroid and inverse covariance."""
        self.mean_vector = np.mean(feature_vectors, axis=0)
        cov = np.cov(feature_vectors, rowvar=False)
        # Regularize covariance to guarantee invertibility
        p = feature_vectors.shape[1]
        cov_reg = cov + np.eye(p) * 1e-4
        self.inv_cov_matrix = np.linalg.pinv(cov_reg)

    def compute_distance(self, vector: np.ndarray) -> float:
        if self.mean_vector is None or self.inv_cov_matrix is None:
            return 0.0
        dist = mahalanobis(vector, self.mean_vector, self.inv_cov_matrix)
        return float(dist)

    def is_ood(self, vector: np.ndarray) -> Tuple[bool, float]:
        dist = self.compute_distance(vector)
        return (dist > self.threshold_distance), dist


class SequentialDecisionEngine:
    """Executes sequential multimodal screening policy across all applications."""

    def __init__(self, policies: Dict[str, CertifiedThresholdPolicy]):
        self.policies = policies
        self.veto_engine = Stage0VetoEngine()
        self.fusion_engine = MultimodalFusionEngine()
        self.ood_detector = MahalanobisOODDetector()
        self.stage2_pipeline = Stage2ScreeningPipeline()

    def fit_calibration_population(self, reference_units: List[Union[BatteryRecord, Dict[str, Any]]]):
        """Fits OOD detector on the reference calibration sample feature distribution."""
        vectors = []
        for u in reference_units:
            fused = self.fusion_engine.fuse(u, mode=RunMode.FUSED)
            vectors.append(fused["vector"])
        if vectors:
            self.ood_detector.fit(np.array(vectors))

    def compute_screening_score(
        self,
        features: Dict[str, float],
        app_criteria: ApplicationCriteria
    ) -> float:
        """Computes Stage 1 fitness score matching calibration logic."""
        dcir = features.get("dcir_mohm", 20.0)
        tof = features.get("tof_us", 3.5)
        norm_dcir = min(2.5, dcir / app_criteria.max_dcir_mohm)
        norm_tof = min(2.5, (tof - 3.2) / max(0.1, app_criteria.max_tof_shift_us))
        penalty = 0.55 * norm_dcir + 0.45 * norm_tof
        return float(np.clip(1.0 - 0.5 * penalty, 0.0, 1.0))

    def compute_stage2_screening_score(
        self,
        extended_features: Dict[str, Any],
        app_criteria: ApplicationCriteria
    ) -> float:
        """Computes normalized kinetic health score S2 in [0, 1] for Stage-2 screening."""
        r_ohmic = float(extended_features.get("r_ohmic_mohm", 12.0))
        r_ct = float(extended_features.get("r_charge_transfer_mohm", 6.0))
        r_diff = float(extended_features.get("r_diffusion_mohm", 2.5))
        r_tot = r_ohmic + r_ct + r_diff

        pol_idx = float(extended_features.get("polarization_index", 0.70))
        recovery = float(extended_features.get("overpotential_recovery_ratio", 0.90))
        tau_slow = float(extended_features.get("tau_slow_s", 15.0))

        norm_r = min(2.5, r_tot / app_criteria.max_dcir_mohm)
        norm_pol = min(2.0, max(0.0, (pol_idx - 0.50) / 0.50))
        norm_tau = min(2.0, max(0.0, (tau_slow - 5.0) / 20.0))

        penalty = 0.50 * norm_r + 0.30 * norm_pol + 0.20 * norm_tau
        score = float(np.clip(1.0 - 0.55 * penalty * (1.1 - 0.2 * recovery), 0.0, 1.0))
        return score

    def evaluate_unit(
        self,
        record: Union[BatteryRecord, Dict[str, Any]],
        target_application: str = "solar_backup",
        allow_secondary_downgrade: bool = False,
        execute_stage3_fallback: bool = True
    ) -> UnitDecisionRecord:
        """Evaluates a unit through Stage 0 veto -> OOD check -> Stage 1 -> Stage 2 -> Stage 3 fallback."""
        unit_id = record.unit_id if isinstance(record, BatteryRecord) else record.get("unit_id", "UNKNOWN")
        decision_path = []

        # 1. Stage 0 Safety/Identity Veto
        veto_res = self.veto_engine.evaluate(record)
        if not veto_res.passed:
            decision_path.append(f"Stage 0 Veto Triggered: {', '.join(veto_res.reasons)}")
            decision_path.append("Disposition: Abstain / Quarantine")
            return UnitDecisionRecord(
                unit_id=unit_id,
                decision=DecisionOutcome.ABSTAIN,
                approved_applications=[],
                rejected_applications=list(self.policies.keys()),
                escalated_applications=[],
                is_ood=False,
                mahalanobis_distance=0.0,
                stage0_passed=False,
                stage0_reasons=veto_res.reasons,
                fused_features={},
                decision_path=decision_path,
                mean_test_time_s=5.0,
                resolution_stage="stage0",
                stage2_features=None,
                stage3_tested=False
            )

        decision_path.append("Stage 0 Veto Passed")

        # 2. Extract fused features
        fused = self.fusion_engine.fuse(record, mode=RunMode.FUSED)
        feats = fused["features"]
        decision_path.append("Stage 1 Multimodal Fingerprint Extracted (13 features)")

        # 3. OOD Abstention Check
        is_ood, ood_dist = self.ood_detector.is_ood(fused["vector"])
        if is_ood:
            decision_path.append(f"OOD Anomaly Detected: Mahalanobis distance {ood_dist:.2f} > threshold {self.ood_detector.threshold_distance:.2f}")
            decision_path.append("Disposition: Abstain / Quarantine (Unfamiliar distribution)")
            return UnitDecisionRecord(
                unit_id=unit_id,
                decision=DecisionOutcome.ABSTAIN,
                approved_applications=[],
                rejected_applications=[],
                escalated_applications=[],
                is_ood=True,
                mahalanobis_distance=round(ood_dist, 2),
                stage0_passed=True,
                stage0_reasons=[],
                fused_features=feats,
                decision_path=decision_path,
                mean_test_time_s=30.0,
                resolution_stage="stage1",
                stage2_features=None,
                stage3_tested=False
            )

        decision_path.append(f"OOD Check Passed (Mahalanobis dist = {ood_dist:.2f})")

        # 4. Multi-Application Policy Evaluation at Stage 1
        approved_apps: List[ApplicationApproval] = []
        rejected_apps: List[str] = []
        escalated_apps: List[str] = []

        for app_id, policy in self.policies.items():
            app_crit = APPLICATIONS[app_id]
            score = self.compute_screening_score(feats, app_crit)

            if score >= policy.lambda_approve_threshold:
                c_rate = 0.5 if app_id == "solar_backup" else (0.2 if app_id == "low_power_lighting" else 2.0)
                app_approval = ApplicationApproval(
                    application_id=app_id,
                    application_name=app_crit.name,
                    certified_risk_bound=policy.certified_risk_bound,
                    label_certified="CERTIFIED",
                    estimated_conditional_fail_rate=policy.uncontrolled_conditional_fail_rate,
                    label_estimate="ESTIMATE \u2014 NOT CONTROLLED",
                    max_operating_c_rate=c_rate,
                    soc_window=(15.0, 85.0) if app_id != "fast_charge_buffer" else (20.0, 80.0)
                )
                approved_apps.append(app_approval)
                decision_path.append(f"App '{app_id}': Approved at Stage 1 (Score {score:.3f} >= {policy.lambda_approve_threshold:.3f})")
            elif score <= policy.lambda_reject_threshold:
                rejected_apps.append(app_id)
                decision_path.append(f"App '{app_id}': Rejected at Stage 1 (Score {score:.3f} <= {policy.lambda_reject_threshold:.3f})")
            else:
                escalated_apps.append(app_id)
                decision_path.append(f"App '{app_id}': Escalated from Stage 1 (Score {score:.3f} between reject and approve thresholds)")

        # 5. Sequential Resolution for Target Application
        test_time_s = 30.0
        resolution_stage = "stage1"
        s2_ext = None
        stage3_tested = False

        if target_application in [a.application_id for a in approved_apps]:
            overall_decision = DecisionOutcome.APPROVE
            resolution_stage = "stage1"
            test_time_s = 30.0
            decision_path.append(f"Final Unit Outcome: APPROVE with limits for target '{target_application}' (Stage 1 Multimodal Fingerprint)")
        elif target_application in rejected_apps:
            if allow_secondary_downgrade and approved_apps:
                overall_decision = DecisionOutcome.APPROVE
                resolution_stage = "stage1"
                test_time_s = 30.0
                decision_path.append(f"Final Unit Outcome: APPROVE downgraded to secondary tier ({', '.join(a.application_id for a in approved_apps)})")
            else:
                overall_decision = DecisionOutcome.REJECT
                resolution_stage = "stage1"
                test_time_s = 30.0
                decision_path.append(f"Final Unit Outcome: REJECT / Recycle for '{target_application}' (Stage 1 Multimodal Fingerprint)")
        elif target_application in escalated_apps:
            # Stage 2 Extended Screening
            decision_path.append(f"Stage 1 Screening for '{target_application}': Borderline evidence -> ESCALATED TO STAGE 2")
            s2_res = self.stage2_pipeline.extract_extended_features(record)
            s2_ext = s2_res["extended_features"]
            target_crit = APPLICATIONS[target_application]
            target_pol = self.policies[target_application]
            s2_score = self.compute_stage2_screening_score(s2_ext, target_crit)
            decision_path.append(f"Stage 2 Extended Screening: Kinetic features extracted for '{target_application}' (S2 Score = {s2_score:.3f})")

            lam2_app = getattr(target_pol, "lambda_stage2_approve", 0.82)
            lam2_rej = getattr(target_pol, "lambda_stage2_reject", 0.65)

            if s2_score >= lam2_app:
                overall_decision = DecisionOutcome.APPROVE
                resolution_stage = "stage2"
                test_time_s = 630.0
                c_rate = 0.5 if target_application == "solar_backup" else (0.2 if target_application == "low_power_lighting" else 2.0)
                app_approval = ApplicationApproval(
                    application_id=target_application,
                    application_name=target_crit.name,
                    certified_risk_bound=target_pol.certified_risk_bound,
                    label_certified="CERTIFIED",
                    estimated_conditional_fail_rate=target_pol.uncontrolled_conditional_fail_rate,
                    label_estimate="ESTIMATE \u2014 NOT CONTROLLED",
                    max_operating_c_rate=c_rate,
                    soc_window=(15.0, 85.0) if target_application != "fast_charge_buffer" else (20.0, 80.0)
                )
                approved_apps.append(app_approval)
                decision_path.append(f"Stage 2 Kinetic Screening: APPROVED (Score {s2_score:.3f} >= {lam2_app:.3f})")
                decision_path.append(f"Final Unit Outcome: APPROVE with limits for target '{target_application}' (Stage 2 Kinetic Resolution)")
            elif s2_score <= lam2_rej:
                overall_decision = DecisionOutcome.REJECT
                resolution_stage = "stage2"
                test_time_s = 630.0
                rejected_apps.append(target_application)
                decision_path.append(f"Stage 2 Kinetic Screening: REJECTED (Score {s2_score:.3f} <= {lam2_rej:.3f})")
                decision_path.append(f"Final Unit Outcome: REJECT / Recycle for '{target_application}' (Stage 2 Kinetic Resolution)")
            else:
                # Stage 2 Unresolved -> ESCALATE TO STAGE 3 REFERENCE FALLBACK
                decision_path.append(f"Stage 2 Kinetic Screening: Unresolved (Score {s2_score:.3f} in uncertainty band) -> ESCALATED TO STAGE 3 REFERENCE FALLBACK")
                if not execute_stage3_fallback:
                    overall_decision = DecisionOutcome.ESCALATE
                    resolution_stage = "stage2_escalated"
                    test_time_s = 630.0
                    decision_path.append(f"Final Unit Outcome: ESCALATE (more evidence required for '{target_application}')")
                else:
                    resolution_stage = "stage3"
                    stage3_tested = True
                    test_time_s = 15030.0  # 30s Stage 1 + 600s Stage 2 + 14400s Stage 3
                    s3_pass = evaluate_stage3_ground_truth(record, target_crit)
                    if s3_pass:
                        overall_decision = DecisionOutcome.APPROVE
                        c_rate = 0.5 if target_application == "solar_backup" else (0.2 if target_application == "low_power_lighting" else 2.0)
                        app_approval = ApplicationApproval(
                            application_id=target_application,
                            application_name=target_crit.name,
                            certified_risk_bound=0.0,  # Stage 3 ground truth reference testing has ZERO risk against reference
                            label_certified="CERTIFIED",
                            estimated_conditional_fail_rate=0.0,
                            label_estimate="GROUND TRUTH VERIFIED",
                            max_operating_c_rate=c_rate,
                            soc_window=(15.0, 85.0) if target_application != "fast_charge_buffer" else (20.0, 80.0)
                        )
                        approved_apps.append(app_approval)
                        decision_path.append(f"Stage 3 Reference Test Completed: PASS (Ground Truth Confirmed)")
                        decision_path.append(f"Final Unit Outcome: APPROVE with limits for target '{target_application}' (Stage 3 Reference Standard)")
                    else:
                        overall_decision = DecisionOutcome.REJECT
                        rejected_apps.append(target_application)
                        decision_path.append(f"Stage 3 Reference Test Completed: FAIL (Ground Truth Defect Detected)")
                        decision_path.append(f"Final Unit Outcome: REJECT / Recycle for '{target_application}' (Stage 3 Reference Standard)")
        elif approved_apps:
            overall_decision = DecisionOutcome.APPROVE
            resolution_stage = "stage1"
            decision_path.append(f"Final Unit Outcome: APPROVE for alternative secondary tier ({', '.join(a.application_id for a in approved_apps)})")
        else:
            overall_decision = DecisionOutcome.REJECT
            resolution_stage = "stage1"
            decision_path.append("Final Unit Outcome: REJECT / Recycle")

        return UnitDecisionRecord(
            unit_id=unit_id,
            decision=overall_decision,
            approved_applications=approved_apps,
            rejected_applications=rejected_apps,
            escalated_applications=escalated_apps,
            is_ood=False,
            mahalanobis_distance=round(ood_dist, 2),
            stage0_passed=True,
            stage0_reasons=[],
            fused_features=feats,
            decision_path=decision_path,
            mean_test_time_s=round(test_time_s, 1),
            resolution_stage=resolution_stage,
            stage2_features=s2_ext,
            stage3_tested=stage3_tested
        )
