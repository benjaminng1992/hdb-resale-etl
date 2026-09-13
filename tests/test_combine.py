import pandas as pd

from hdb_etl.combine import combine_master, load_raw_frames


def test_combine_unions_remaining_lease_and_filters_window(fixture_raw_dir):
    frames = load_raw_frames(sorted(fixture_raw_dir.glob("*.csv")))
    master = combine_master(frames)

    assert "remaining_lease" in master.columns
    assert master["month"].min() == "2012-01"
    assert master["month"].max() == "2015-01"
    assert (master["month"] == "2011-12").sum() == 0
    assert (master["month"] == "2017-01").sum() == 0
    # Early file has no remaining_lease; later file does — union keeps the column.
    nulls = master["remaining_lease"].isna().sum()
    assert nulls > 0
    assert master["remaining_lease"].notna().sum() > 0


def test_combine_does_not_rewrite_source_files(fixture_raw_dir):
    paths = sorted(fixture_raw_dir.glob("*.csv"))
    before = {p.name: p.read_bytes() for p in paths}
    frames = load_raw_frames(paths)
    combine_master(frames)
    after = {p.name: p.read_bytes() for p in paths}
    assert before == after


def test_load_raw_frames_tags_source_file(fixture_raw_dir):
    frames = load_raw_frames(sorted(fixture_raw_dir.glob("*.csv")))
    assert len(frames) == 2
    for name, frame in frames.items():
        assert (frame["source_file"] == name).all()


def test_combine_adds_missing_core_columns():
    frames = {
        "thin.csv": pd.DataFrame(
            [
                {
                    "month": "2012-06",
                    "town": "BEDOK",
                    "flat_type": "4 ROOM",
                    "block": "1",
                    "street_name": "BEDOK NTH",
                    "storey_range": "04 TO 06",
                    "floor_area_sqm": 90,
                    "flat_model": "Improved",
                    "lease_commence_date": 1985,
                    "resale_price": 400000,
                }
            ]
        )
    }
    master = combine_master(frames)
    assert "remaining_lease" in master.columns
    assert master["remaining_lease"].isna().all()
