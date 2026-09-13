"""Grouped IQR heuristics for potentially anomalous prices and floor areas."""

from __future__ import annotations

import pandas as pd


def _iqr_bounds(series: pd.Series, fence: float = 1.5) -> tuple[float, float]:
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    return float(q1 - fence * iqr), float(q3 + fence * iqr)


def _flag_grouped(frame: pd.DataFrame, value_col: str, group_cols: list[str], flag_col: str) -> pd.Series:
    flags = pd.Series(False, index=frame.index)
    for _, group in frame.groupby(group_cols, dropna=False):
        values = group[value_col].dropna()
        if len(values) < 8:
            continue
        lower, upper = _iqr_bounds(values)
        if lower == upper:
            continue
        outlier = (group[value_col] < lower) | (group[value_col] > upper)
        flags.loc[group.index] = outlier.fillna(False)
    return flags


def flag_anomalies(frame: pd.DataFrame) -> pd.DataFrame:
    """Flag statistical outliers; rows stay in cleaned unless the caller drops them."""
    out = frame.copy()
    out["year"] = out["month"].astype(str).str.slice(0, 4)
    price_flag = _flag_grouped(out, "resale_price", ["town", "flat_type", "year"], "price_anomaly")
    area_flag = _flag_grouped(out, "floor_area_sqm", ["town", "flat_type"], "area_anomaly")
    sanity = (out["resale_price"] < 50_000) | (out["resale_price"] > 2_000_000)
    out["is_price_anomaly"] = price_flag | sanity
    out["is_area_anomaly"] = area_flag
    out["is_anomaly"] = out["is_price_anomaly"] | out["is_area_anomaly"]
    out = out.drop(columns=["year"])
    return out
