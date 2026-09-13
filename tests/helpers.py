import pandas as pd


def hdb_row(**overrides):
    """One in-window row that passes the January 2012 closed set."""
    base = {
        "month": "2012-01",
        "town": "ANG MO KIO",
        "flat_type": "3 ROOM",
        "block": "123",
        "street_name": "ANG MO KIO AVE 1",
        "storey_range": "07 TO 09",
        "floor_area_sqm": 67.0,
        "flat_model": "Improved",
        "lease_commence_date": 1980,
        "remaining_lease": pd.NA,
        "resale_price": 300000.0,
        "source_file": "unit.csv",
    }
    base.update(overrides)
    return base
