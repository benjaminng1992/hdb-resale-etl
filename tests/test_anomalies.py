import pandas as pd

from hdb_etl.anomalies import flag_anomalies

from tests.helpers import hdb_row


def test_sanity_band_flags_implausible_price():
    frame = pd.DataFrame(
        [
            hdb_row(block="1", resale_price=300000),
            hdb_row(block="2", resale_price=10_000),
            hdb_row(block="3", resale_price=3_000_000),
        ]
    )
    out = flag_anomalies(frame)
    cheap = out.loc[out["block"] == "2"].iloc[0]
    rich = out.loc[out["block"] == "3"].iloc[0]
    mid = out.loc[out["block"] == "1"].iloc[0]
    assert bool(cheap["is_price_anomaly"]) is True
    assert bool(rich["is_price_anomaly"]) is True
    assert bool(mid["is_price_anomaly"]) is False


def test_iqr_flags_outlier_when_group_is_large_enough():
    rows = [hdb_row(block=str(i), resale_price=300000 + i * 100) for i in range(12)]
    rows.append(hdb_row(block="99", resale_price=1_100_000))
    out = flag_anomalies(pd.DataFrame(rows))
    flagged = out.loc[out["block"] == "99", "is_price_anomaly"].iloc[0]
    assert bool(flagged) is True
    assert out.loc[out["block"] != "99", "is_price_anomaly"].sum() == 0


def test_iqr_skips_tiny_groups():
    frame = pd.DataFrame(
        [
            hdb_row(block="1", resale_price=300000),
            hdb_row(block="2", resale_price=1_100_000),
        ]
    )
    out = flag_anomalies(frame)
    # Group has < 8 rows, so IQR is not applied; 1.1M is inside the sanity ceiling.
    assert bool(out.loc[out["block"] == "2", "is_price_anomaly"].iloc[0]) is False
