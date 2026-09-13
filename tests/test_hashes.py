import pandas as pd

from hdb_etl.config import RESALE_IDENTIFIER_COL
from hdb_etl.transform import add_hashes, add_resale_identifier, hashed_zone, sha256_hex


def test_hashed_identifier_is_sha256_of_resale_identifier():
    frame = pd.DataFrame(
        [
            {
                "month": "2012-01",
                "town": "ANG MO KIO",
                "flat_type": "2 ROOM",
                "block": "19",
                "resale_price": 230000,
                "street_name": "AVE 1",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 45,
                "flat_model": "Improved",
                "lease_commence_date": 1980,
                "remaining_lease_source": pd.NA,
            }
        ]
    )
    transformed = add_resale_identifier(frame)
    hashed = add_hashes(transformed)
    identifier = hashed[RESALE_IDENTIFIER_COL].iloc[0]
    assert hashed["hashed_identifier"].iloc[0] == sha256_hex(identifier)
    assert hashed["hashed_record_id"].is_unique


def test_hashed_zone_drops_plaintext_identifier():
    frame = pd.DataFrame(
        [
            {
                "month": "2012-01",
                "town": "BISHAN",
                "flat_type": "4 ROOM",
                "block": "6A",
                "resale_price": 450000,
            }
        ]
    )
    hashed = hashed_zone(add_hashes(add_resale_identifier(frame)))
    assert RESALE_IDENTIFIER_COL not in hashed.columns
    assert "hashed_identifier" in hashed.columns


def test_same_identifier_hashes_equal_record_ids_differ():
    frame = pd.DataFrame(
        [
            {
                "month": "2012-01",
                "town": "ANG MO KIO",
                "flat_type": "2 ROOM",
                "block": "19",
                "street_name": "AVE 1",
                "storey_range": "07 TO 09",
                "floor_area_sqm": 45,
                "flat_model": "Improved",
                "lease_commence_date": 1980,
                "remaining_lease_source": pd.NA,
                "resale_price": 230000,
            },
            {
                "month": "2012-01",
                "town": "ANG MO KIO",
                "flat_type": "2 ROOM",
                "block": "19",
                "street_name": "AVE 2",
                "storey_range": "10 TO 12",
                "floor_area_sqm": 45,
                "flat_model": "Improved",
                "lease_commence_date": 1981,
                "remaining_lease_source": pd.NA,
                "resale_price": 240000,
            },
        ]
    )
    hashed = add_hashes(add_resale_identifier(frame))
    assert hashed[RESALE_IDENTIFIER_COL].nunique() == 1
    assert hashed["hashed_identifier"].nunique() == 1
    assert hashed["hashed_record_id"].nunique() == 2
