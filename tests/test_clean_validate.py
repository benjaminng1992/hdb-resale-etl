import pandas as pd

from hdb_etl.clean import deduplicate
from hdb_etl.validate import apply_validation, build_jan2012_reference

from tests.helpers import hdb_row


def test_dedup_keeps_higher_price():
    frame = pd.DataFrame(
        [
            hdb_row(resale_price=300000),
            hdb_row(resale_price=320000),
            hdb_row(block="124", resale_price=310000),
        ]
    )
    cleaned, quarantined = deduplicate(frame)
    assert len(cleaned) == 2
    kept = cleaned.loc[cleaned["block"] == "123", "resale_price"].iloc[0]
    assert kept == 320000
    assert quarantined["quarantine_reason"].iloc[0] == "duplicate_lower_price"
    assert quarantined["resale_price"].iloc[0] == 300000


def test_dedup_tie_keeps_one():
    frame = pd.DataFrame([hdb_row(), hdb_row()])
    cleaned, quarantined = deduplicate(frame)
    assert len(cleaned) == 1
    assert list(quarantined["quarantine_reason"]) == ["duplicate_tie"]


def test_dedup_treats_null_remaining_lease_as_same_key():
    frame = pd.DataFrame(
        [
            hdb_row(remaining_lease=pd.NA, resale_price=300000),
            hdb_row(remaining_lease=pd.NA, resale_price=310000),
        ]
    )
    cleaned, quarantined = deduplicate(frame)
    assert len(cleaned) == 1
    assert cleaned["resale_price"].iloc[0] == 310000
    assert len(quarantined) == 1


def test_jan2012_reference_and_validation_flags():
    master = pd.DataFrame(
        [
            hdb_row(),
            hdb_row(month="2013-06", storey_range="01 TO 05", flat_model="DBSS", resale_price=500000),
            hdb_row(month="not-a-date", block="1"),
            hdb_row(month="2014-01", town="ATLANTIS"),
            hdb_row(month="2011-12"),
            hdb_row(resale_price=0),
            hdb_row(floor_area_sqm=-1),
            hdb_row(lease_commence_date=2020),
        ]
    )
    reference = build_jan2012_reference(master)
    assert "ANG MO KIO" in reference["town"]
    validated = apply_validation(master, reference)
    assert bool(validated.loc[0, "structural_fail"]) is False
    assert "unknown_storey_range" in validated.loc[1, "structural_reasons"]
    assert "unknown_flat_model" in validated.loc[1, "structural_reasons"]
    assert bool(validated.loc[1, "structural_fail"]) is True
    assert "invalid_month_format" in validated.loc[2, "structural_reasons"]
    assert "unknown_town" in validated.loc[3, "structural_reasons"]
    assert "month_out_of_window" in validated.loc[4, "structural_reasons"]
    assert "invalid_resale_price" in validated.loc[5, "structural_reasons"]
    assert "invalid_floor_area" in validated.loc[6, "structural_reasons"]
    assert "invalid_lease_commence" in validated.loc[7, "structural_reasons"]


def test_empty_jan2012_raises():
    master = pd.DataFrame([hdb_row(month="2015-01")])
    try:
        build_jan2012_reference(master)
    except ValueError as exc:
        assert "January 2012" in str(exc)
    else:
        raise AssertionError("expected ValueError")
