from hdb_etl.combine import combine_master, load_raw_frames
from hdb_etl.config import RESALE_IDENTIFIER_COL
from hdb_etl.pipeline import run_pipeline
from hdb_etl.transform import build_resale_identifier


def test_fixture_pipeline_zones_and_identifier(tmp_path, fixture_raw_dir):
    # fixture_raw_dir already wrote tmp_path/data/raw/*.csv
    result = run_pipeline(root=tmp_path, persist=True, drop_anomalies=True)

    master = result["master"]
    assert len(master) == 7
    assert master["month"].min() == "2012-01"
    assert "2017-01" not in set(master["month"])

    reasons = result["quarantined"]["quarantine_reason"].astype(str)
    assert reasons.str.contains("duplicate_lower_price").any()
    assert reasons.str.contains("unknown_storey_range").any()
    assert reasons.str.contains("unknown_town").any()
    assert reasons.str.contains("unknown_flat_model").any()
    assert reasons.str.contains("price_anomaly").any()

    cleaned = result["cleaned"]
    assert len(cleaned) == 2
    assert set(cleaned["block"].astype(str)) == {"19", "30"}
    assert (cleaned["resale_price"] >= 50_000).all()

    transformed = result["transformed"]
    amk_2room = transformed.loc[transformed["block"].astype(str) == "19"].iloc[0]
    assert amk_2room[RESALE_IDENTIFIER_COL] == build_resale_identifier(
        "19", amk_2room["avg_resale_price_group"], "2012-01", "ANG MO KIO"
    )
    assert amk_2room[RESALE_IDENTIFIER_COL] == "S0192301A"

    hashed = result["hashed"]
    assert RESALE_IDENTIFIER_COL not in hashed.columns
    assert hashed["hashed_record_id"].is_unique
    assert (tmp_path / "data" / "cleaned" / "cleaned.csv").exists()
    assert (tmp_path / "data" / "raw" / "approval_to_2012.csv").exists()


def test_fixture_combine_keeps_all_attributes(fixture_raw_dir):
    frames = load_raw_frames(sorted(fixture_raw_dir.glob("*.csv")))
    master = combine_master(frames)
    assert "remaining_lease" in master.columns
    later = master.loc[master["month"] == "2015-01"]
    assert later["remaining_lease"].notna().any()
