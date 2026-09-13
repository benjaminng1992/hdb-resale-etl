"""Checks against the publisher CSVs in data/raw/ (skipped if those files are absent)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from hdb_etl.combine import combine_master, load_raw_frames
from hdb_etl.config import RESALE_IDENTIFIER_COL
from hdb_etl.pipeline import run_pipeline
from hdb_etl.profile import profile_dataset
from hdb_etl.validate import apply_validation, build_jan2012_reference

REPO = Path(__file__).resolve().parents[1]


def test_real_master_window_and_schema_union(real_raw_files):
    frames = load_raw_frames(real_raw_files)
    master = combine_master(frames)
    assert len(master) == 92_544
    assert master["month"].min() == "2012-01"
    assert master["month"].max() == "2016-12"
    assert master["month"].nunique() == 60
    assert "remaining_lease" in master.columns
    # Pre-2015 files have no remaining_lease; 2015–2016 do.
    assert master["remaining_lease"].isna().sum() > 0
    assert master["remaining_lease"].notna().sum() > 0
    report = profile_dataset(master, frames)
    assert report["row_count"] == 92_544


def test_real_jan2012_domains(real_raw_files):
    master = combine_master(load_raw_frames(real_raw_files))
    jan = master.loc[master["month"] == "2012-01"]
    assert len(jan) == 1559
    reference = build_jan2012_reference(master)
    assert len(reference["town"]) == 26
    assert "ANG MO KIO" in reference["town"]
    assert "MULTI-GENERATION" in reference["flat_type"]
    validated = apply_validation(master, reference)
    # 5-storey bands and later models fail the Jan 2012 closed set.
    fails = validated.loc[validated["structural_fail"], "structural_reasons"]
    assert fails.str.contains("unknown_storey_range").any()
    assert fails.str.contains("unknown_flat_model").any()


def test_real_pipeline_output_contract():
    raw = REPO / "data" / "raw"
    if not list(raw.glob("*.csv")):
        pytest.skip("Real HDB CSVs are not in data/raw/")
    result = run_pipeline(root=REPO, persist=False, drop_anomalies=True)
    cleaned, transformed, hashed, quarantined = (
        result["cleaned"],
        result["transformed"],
        result["hashed"],
        result["quarantined"],
    )
    assert len(result["master"]) == 92_544
    assert len(cleaned) == len(transformed) == len(hashed)
    assert len(cleaned) < len(result["master"])
    assert len(quarantined) > 0
    assert RESALE_IDENTIFIER_COL in transformed.columns
    assert RESALE_IDENTIFIER_COL not in hashed.columns
    assert hashed["hashed_record_id"].is_unique
    assert transformed[RESALE_IDENTIFIER_COL].str.fullmatch(r"S\d{3}\d{2}\d{2}[A-Z]").all()
    assert "quarantine_reason" in quarantined.columns
    # Brief example pattern: first char S, last char is town initial.
    amk = transformed.loc[transformed["town"] == "ANG MO KIO"]
    assert amk[RESALE_IDENTIFIER_COL].str.endswith("A").all()
    # Remaining lease is years + months on cleaned rows.
    assert cleaned["remaining_lease"].str.contains(r"years").all()
