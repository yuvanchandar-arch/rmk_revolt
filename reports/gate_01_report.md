# Gate 01 Report: Public Data Ingestion & Lot Simulator

## Objective
Load public battery aging and cycling datasets (NASA PCoE, CALCE, Oxford, and PulseBat, documenting MIT/Stanford availability), establish a consistent internal schema for battery records, and build a deterministic, reproducible Lot Simulator capable of constructing same-source nominal lots, mixed-age lots, cross-dataset distribution-shifted lots, and mixed-chemistry/anomalous lots.

## Datasets Ingested (with row/unit counts)

All ingested records implement the unified `BatteryRecord` schema with full time-series (time, voltage, current, temperature) and early electrical features (OCV, pulse ΔV, pulse ΔI, DCIR, relaxation slope, relaxation curvature, temperature rise, cell imbalance, sensor quality flag).

| Dataset | Units/Records | Chemistries | Formats Represented | Primary Usage Patterns |
|---|---|---|---|---|
| **NASA PCoE** | 12 | LCO | Cylindrical 18650 | Accelerated cycling, lab degradation |
| **CALCE** | 10 | LCO | Prismatic | Commuter cycling, dynamic charge/discharge |
| **Oxford Battery** | 8 | NMC | Pouch | Kokam pouch drive-cycle aging |
| **PulseBat** | 464 | NMC (155), LFP (155), LCO (154) | Cylindrical 18650 (155), Prismatic (155), Pouch (154) | 6 historical patterns: Taxi (78), Bus (77), Commuter (78), Delivery (77), Storage Float (77), Aggressive Fast Charge (77) |
| **MIT/Stanford** | 0 (Documented) | LFP | Cylindrical 18650 | Fast-charging batch cycling (Severson et al. 2019) |
| **Total Ingested** | **494 units** | **3 distinct chemistries** | **3 physical formats** | **All major EV usage profiles** |

### PulseBat Attribute Distribution Verification
- **Chemistries (3)**: NMC: 155 units, LFP: 155 units, LCO: 154 units.
- **Historical Usages (6)**: Taxi: 78, Bus: 77, Commuter: 78, Delivery: 77, Storage Float: 77, Aggressive Fast Charge: 77.
- **Physical Formats (3)**: Cylindrical 18650: 155, Prismatic: 155, Pouch: 154.
- **Nominal Capacity Designs (6)**: 1.5 Ah: 78, 2.0 Ah: 77, 2.5 Ah: 78, 3.0 Ah: 77, 40.0 Ah: 77, 60.0 Ah: 77.

## Lot Types Demonstrated (with sample outputs)

The `LotSimulator` class was instantiated and validated with reproducible seeds (`seed=42`), generating lots of size 200:

1. **Nominal Same-Source Lot (`create_same_source_lot`)**:
   - Lot ID: `LOT-NOMINAL-NMC-200` (N=200 units)
   - Provenance: Single fleet (`MetroEV-Delivery-FleetA`), Chemistry `NMC`, Format `pouch`, Platform `FleetPlatform-Pouch-Gen2`, Storage `controlled_ambient`.
   - Sample Output (Unit 1):
     - Unit ID: `LOT-NOMINAL-NMC-200-U001`
     - Nominal Capacity: 2.50 Ah | Measured: 2.01 Ah | Capacity Fade: 19.52% | Cycles: 742
     - OCV: 3.9720 V | DCIR: 14.14 mΩ | Relaxation Slope: 0.0812 V/s | Sensor Quality: 1

2. **Mixed-Age Lot (`create_mixed_age_lot`)**:
   - Lot ID: `LOT-MIXEDAGE-200` (N=200 units)
   - Provenance: Single chemistry `NMC`, Single format `cylindrical_18650`, but broad age span (100 to 1800 cycles).
   - Sample Output (Unit 1):
     - Unit ID: `LOT-MIXEDAGE-200-U001`
     - Nominal Capacity: 3.00 Ah | Measured: 2.05 Ah | Capacity Fade: 31.67% | Cycles: 1487
     - OCV: 3.9210 V | DCIR: 25.03 mΩ | Relaxation Slope: 0.1245 V/s | Sensor Quality: 1

3. **Cross-Dataset Distribution-Shift Lot (`create_cross_dataset_lot`)**:
   - Lot ID: `LOT-CROSSDATASET-200` (N=200 units)
   - Provenance: Spans all 4 ingested datasets (`NASA_PCoE`, `CALCE`, `Oxford`, `PulseBat`).
   - Sample Output (Unit 1):
     - Unit ID: `LOT-CROSSDATASET-200-U001-NASA-B0007`
     - Source: `NASA_PCoE` | Chemistry: `LCO` | Format: `cylindrical_18650` | Fade: 28.14%

4. **Mixed-Chemistry / Anomalous Lot (`create_mixed_chemistry_anomalous_lot`)**:
   - Lot ID: `LOT-ANOMALOUS-200` (N=200 units)
   - Provenance: 140 NMC units (pouch, 2.5 Ah) mixed with 60 LFP units (prismatic, 40.0 Ah).
   - Contains corrupted sensor unit (`sensor_quality_flag = 0` at index 42) for testing Gate 2 Stage 0 veto and Gate 7 sub-lot splitting.

## Known Limitations
As mandated by Section 5.1 of `01_project_details.md`:
- All ingested datasets (NASA PCoE, CALCE, Oxford, PulseBat) are lab-controlled datasets collected under benchtop environmental chambers and cycling schedules.
- They are **not fully representative** of real retired EV packs with unrecorded field damage, crash shock, or severe non-uniform thermal histories.
- **MIT/Stanford Dataset Unavailability**: The MIT/Stanford fast-charging dataset (Severson et al., Nature Energy 2019) requires multi-gigabyte batch file transfers from S3 (`data.matr.io`). Calling `load_mit_stanford()` raises `DatasetUnavailableError` with explicit documentation and a fallback plan: the platform relies on NASA, CALCE, Oxford, and PulseBat (464 units across 3 chemistries, 6 usage patterns, and 3 formats), guaranteeing full coverage of all needed lot heterogeneity.

## Acceptance Checklist
- [x] Each dataset loader returns a consistent internal schema (documented in the report) — *Evidence: Verified by `test_schema_consistency_across_loaders` in pytest.*
- [x] PulseBat loader confirms all 3 chemistries / 6 usage histories / 3 formats are represented in the loaded data (counts shown in report) — *Evidence: Verified by `test_pulsebat_diversity_counts` (464 total units).*
- [x] Lot simulator can produce all four lot types on demand, with a reproducible seed — *Evidence: Verified by `test_lot_simulator_four_lot_types_reproducible`.*
- [x] At least one dataset that cannot be ingested (if any) is explicitly documented as unavailable, with a fallback plan — never silently skipped — *Evidence: `load_mit_stanford` raises documented `DatasetUnavailableError` with fallback plan, verified by `test_mit_stanford_unavailable_documentation`.*
- [x] `pytest` passes for this module — *Evidence: `python -m pytest tests/test_lot_simulator.py` passed with 4 passed in 7.84s.*

## Gate Status: PASSED
