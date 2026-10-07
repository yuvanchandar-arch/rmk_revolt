"""Tests for data loaders and lot simulator (Gate 1)."""

import pytest
from backend.data.loaders import (
    load_nasa_pcoe,
    load_calce,
    load_oxford,
    load_pulsebat,
    load_mit_stanford,
    DatasetUnavailableError,
    BatteryRecord
)
from backend.data.lot_simulator import LotSimulator, Lot


def test_schema_consistency_across_loaders():
    """Verify that every dataset loader returns BatteryRecord objects with identical attributes."""
    loaders = [
        ("NASA", load_nasa_pcoe),
        ("CALCE", load_calce),
        ("Oxford", load_oxford),
        ("PulseBat", load_pulsebat)
    ]
    expected_fields = {
        "unit_id", "dataset_source", "chemistry", "format", "platform",
        "fleet_source", "usage_history", "nominal_capacity_ah",
        "measured_capacity_ah", "capacity_fade_pct", "cycle_count",
        "storage_condition_class", "damage_category", "time_series", "early_features"
    }
    expected_early_feats = {
        "ocv_v", "pulse_delta_v", "pulse_delta_i", "dcir_mohm",
        "relaxation_slope", "relaxation_curvature", "temp_rise_c",
        "cell_imbalance_mv", "sensor_quality_flag"
    }

    for name, loader in loaders:
        records = loader()
        assert len(records) > 0, f"{name} returned empty record list"
        for rec in records:
            assert isinstance(rec, BatteryRecord)
            rec_dict = rec.to_dict()
            assert expected_fields.issubset(rec_dict.keys()), f"Missing fields in {name}"
            assert expected_early_feats.issubset(rec.early_features.keys()), f"Missing early features in {name}"
            assert len(rec.time_series["time_s"]) > 0
            assert len(rec.time_series["voltage_v"]) == len(rec.time_series["time_s"])


def test_pulsebat_diversity_counts():
    """PulseBat loader must confirm all 3 chemistries, 6 usage histories, and 3 formats."""
    records = load_pulsebat()
    assert len(records) == 464, f"PulseBat must have exactly 464 records, got {len(records)}"

    chemistries = {r.chemistry for r in records}
    usage_histories = {r.usage_history for r in records}
    formats = {r.format for r in records}
    capacities = {r.nominal_capacity_ah for r in records}

    assert chemistries == {"NMC", "LFP", "LCO"}, f"Unexpected chemistries: {chemistries}"
    expected_usages = {"taxi", "bus", "commuter", "delivery", "storage_float", "aggressive_fast_charge"}
    assert usage_histories == expected_usages, f"Unexpected usages: {usage_histories}"
    assert formats == {"cylindrical_18650", "prismatic", "pouch"}, f"Unexpected formats: {formats}"
    assert capacities == {1.5, 2.0, 2.5, 3.0, 40.0, 60.0}, f"Unexpected capacities: {capacities}"


def test_mit_stanford_unavailable_documentation():
    """MIT/Stanford dataset must explicitly document unavailability and fallback plan."""
    with pytest.raises(DatasetUnavailableError) as exc_info:
        load_mit_stanford()
    assert "unavailable" in str(exc_info.value).lower()
    assert "fallback plan" in str(exc_info.value).lower()


def test_lot_simulator_four_lot_types_reproducible():
    """Verify all four lot types can be produced on demand with a reproducible seed."""
    sim = LotSimulator()

    # 1. Nominal same-source lot
    lot_nominal = sim.create_same_source_lot(lot_id="LOT-NOMINAL-1", size=200, seed=42)
    assert isinstance(lot_nominal, Lot)
    assert lot_nominal.lot_type == "same_source"
    assert lot_nominal.size == 200
    assert all(u.chemistry == "NMC" for u in lot_nominal.units)

    # Determinism check
    lot_nominal_dup = sim.create_same_source_lot(lot_id="LOT-NOMINAL-1", size=200, seed=42)
    assert lot_nominal.units[0].early_features == lot_nominal_dup.units[0].early_features
    assert lot_nominal.units[-1].early_features == lot_nominal_dup.units[-1].early_features

    # 2. Mixed-age lot
    lot_mixed_age = sim.create_mixed_age_lot(lot_id="LOT-MIXEDAGE-1", size=150, seed=42)
    assert lot_mixed_age.lot_type == "mixed_age"
    assert lot_mixed_age.size == 150
    cycles = [u.cycle_count for u in lot_mixed_age.units]
    assert max(cycles) - min(cycles) > 500  # Wide variance

    # 3. Cross-dataset lot
    lot_cross = sim.create_cross_dataset_lot(lot_id="LOT-CROSS-1", size=100, seed=42)
    assert lot_cross.lot_type == "cross_dataset"
    assert lot_cross.size == 100
    sources = {u.dataset_source for u in lot_cross.units}
    assert len(sources) > 1  # Spans multiple datasets

    # 4. Mixed-chemistry / anomalous lot
    lot_anom = sim.create_mixed_chemistry_anomalous_lot(lot_id="LOT-ANOM-1", size=120, seed=42)
    assert lot_anom.lot_type == "mixed_chemistry_anomalous"
    assert lot_anom.size == 120
    anom_chems = {u.chemistry for u in lot_anom.units}
    assert "NMC" in anom_chems and "LFP" in anom_chems
    # Check corrupted unit exists
    corrupt_units = [u for u in lot_anom.units if u.early_features["sensor_quality_flag"] == 0]
    assert len(corrupt_units) >= 1
