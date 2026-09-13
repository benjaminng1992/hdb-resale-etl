import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from tests.helpers import hdb_row

@pytest.fixture
def jan2012_master():
    return pd.DataFrame(
        [
            hdb_row(),
            hdb_row(block="124", flat_type="4 ROOM", storey_range="10 TO 12", resale_price=450000),
        ]
    )


@pytest.fixture
def fixture_raw_dir(tmp_path: Path) -> Path:
    """Tiny publisher-shaped CSVs: schema drift, window edges, dups, domain fails."""
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)

    early = pd.DataFrame(
        [
            # Out of the 2012-01..2016-12 window — stays in Raw only.
            {
                "month": "2011-12",
                "town": "ANG MO KIO",
                "flat_type": "3 ROOM",
                "block": "1",
                "street_name": "ANG MO KIO AVE 1",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 67,
                "flat_model": "Improved",
                "lease_commence_date": 1980,
                "resale_price": 250000,
            },
            {
                "month": "2012-01",
                "town": "ANG MO KIO",
                "flat_type": "2 ROOM",
                "block": "19",
                "street_name": "ANG MO KIO AVE 4",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 45,
                "flat_model": "Improved",
                "lease_commence_date": 1980,
                "resale_price": 230000,
            },
            # Same composite key, lower price — quarantined as duplicate.
            {
                "month": "2012-01",
                "town": "ANG MO KIO",
                "flat_type": "2 ROOM",
                "block": "19",
                "street_name": "ANG MO KIO AVE 4",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 45,
                "flat_model": "Improved",
                "lease_commence_date": 1980,
                "resale_price": 200000,
            },
            # Jan 2012 closed-set misses.
            {
                "month": "2013-06",
                "town": "ANG MO KIO",
                "flat_type": "3 ROOM",
                "block": "50",
                "street_name": "ANG MO KIO AVE 1",
                "storey_range": "01 TO 05",
                "floor_area_sqm": 67,
                "flat_model": "Improved",
                "lease_commence_date": 1980,
                "resale_price": 400000,
            },
            {
                "month": "2014-01",
                "town": "ATLANTIS",
                "flat_type": "3 ROOM",
                "block": "1",
                "street_name": "SEA VIEW",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 67,
                "flat_model": "Improved",
                "lease_commence_date": 1980,
                "resale_price": 300000,
            },
            # Sanity-band price anomaly.
            {
                "month": "2012-01",
                "town": "ANG MO KIO",
                "flat_type": "3 ROOM",
                "block": "20",
                "street_name": "ANG MO KIO AVE 1",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 67,
                "flat_model": "Improved",
                "lease_commence_date": 1980,
                "resale_price": 10000,
            },
        ]
    )
    later = pd.DataFrame(
        [
            {
                "month": "2015-01",
                "town": "ANG MO KIO",
                "flat_type": "3 ROOM",
                "block": "30",
                "street_name": "ANG MO KIO AVE 1",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 67,
                "flat_model": "Improved",
                "lease_commence_date": 1986,
                "remaining_lease": 70,
                "resale_price": 350000,
            },
            {
                "month": "2015-01",
                "town": "ANG MO KIO",
                "flat_type": "3 ROOM",
                "block": "31",
                "street_name": "ANG MO KIO AVE 1",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 67,
                "flat_model": "DBSS",
                "lease_commence_date": 1986,
                "remaining_lease": 70,
                "resale_price": 400000,
            },
            {
                "month": "2017-01",
                "town": "ANG MO KIO",
                "flat_type": "3 ROOM",
                "block": "32",
                "street_name": "ANG MO KIO AVE 1",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 67,
                "flat_model": "Improved",
                "lease_commence_date": 1986,
                "remaining_lease": 70,
                "resale_price": 400000,
            },
        ]
    )
    early.to_csv(raw / "approval_to_2012.csv", index=False)
    later.to_csv(raw / "registration_2015.csv", index=False)
    return raw


@pytest.fixture
def real_raw_files() -> list[Path]:
    raw = ROOT / "data" / "raw"
    files = sorted(raw.glob("*.csv"))
    if len(files) < 3:
        pytest.skip("Real HDB CSVs are not in data/raw/")
    return files
