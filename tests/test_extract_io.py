from pathlib import Path

import pandas as pd

from hdb_etl.config import RESALE_IDENTIFIER_COL
from hdb_etl.extract import _safe_filename, ensure_raw_files, raw_inventory
from hdb_etl.io import write_outputs
from hdb_etl.transform import add_hashes, add_resale_identifier, hashed_zone


def test_safe_filename_appends_csv_and_strips_junk():
    assert _safe_filename("Resale Flat Prices").endswith(".csv")
    assert "/" not in _safe_filename("a/b.csv")


def test_ensure_raw_files_uses_existing_raw_and_does_not_copy(tmp_path: Path):
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    sample = raw / "already_there.csv"
    sample.write_text("month,town\n2012-01,ANG MO KIO\n", encoding="utf-8")
    found = ensure_raw_files(tmp_path)
    assert [p.name for p in found] == ["already_there.csv"]
    inventory = raw_inventory(found)
    assert inventory[0]["bytes"] == sample.stat().st_size


def test_ensure_raw_files_copies_local_drop(tmp_path: Path):
    src = tmp_path / "ResaleFlatPrices"
    src.mkdir()
    (src / "drop.csv").write_text("month,town\n2012-01,BEDOK\n", encoding="utf-8")
    found = ensure_raw_files(tmp_path)
    assert (tmp_path / "data" / "raw" / "drop.csv").exists()
    assert found[0].name == "drop.csv"
    # Second call is a no-op reuse of data/raw.
    again = ensure_raw_files(tmp_path)
    assert [p.name for p in again] == ["drop.csv"]


def test_write_outputs_five_zones_and_mixed_remaining_lease(tmp_path: Path):
    cleaned = pd.DataFrame([{"month": "2012-01", "town": "ANG MO KIO", "block": "19", "resale_price": 230000}])
    transformed = add_resale_identifier(
        cleaned.assign(flat_type="2 ROOM")
    )
    hashed = hashed_zone(add_hashes(transformed))
    quarantined = pd.DataFrame(
        [
            {"month": "2013-01", "remaining_lease": 70, "quarantine_reason": "unknown_town"},
            {"month": "2013-02", "remaining_lease": "74 years 06 months", "quarantine_reason": "duplicate_tie"},
        ]
    )
    written = write_outputs(
        root=tmp_path,
        cleaned=cleaned,
        transformed=transformed,
        hashed=hashed,
        quarantined=quarantined,
        domain_drift=pd.DataFrame(),
        profile_report={"row_count": 1},
        domain_table=pd.DataFrame([{"field": "town", "new_value_count": 0}]),
    )
    assert (tmp_path / "data" / "cleaned" / "cleaned.csv").exists()
    assert (tmp_path / "data" / "cleaned" / "cleaned.parquet").exists()
    assert (tmp_path / "data" / "transformed" / "transformed.csv").exists()
    assert (tmp_path / "data" / "hashed" / "hashed.csv").exists()
    assert (tmp_path / "data" / "quarantined" / "quarantined.parquet").exists()
    assert (tmp_path / "data" / "profiling" / "profile_summary.json").exists()
    hashed_cols = pd.read_csv(written["hashed"]["csv"]).columns
    assert RESALE_IDENTIFIER_COL not in hashed_cols
    assert "hashed_identifier" in hashed_cols
