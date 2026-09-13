"""Validation rules derived from the January 2012 authoritative slice."""

from __future__ import annotations

import re

import pandas as pd

from hdb_etl.config import MONTH_END, MONTH_START, REFERENCE_MONTH

MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
STOREY_PATTERN = re.compile(r"^\d{2} TO \d{2}$")


def build_jan2012_reference(master: pd.DataFrame) -> dict[str, set[str]]:
    """Closed-set domains taken only from month == 2012-01."""
    jan = master.loc[master["month"] == REFERENCE_MONTH]
    if jan.empty:
        raise ValueError("January 2012 slice is empty — cannot build the authoritative set.")
    return {
        "town": set(jan["town"].dropna().astype(str)),
        "flat_type": set(jan["flat_type"].dropna().astype(str)),
        "flat_model": set(jan["flat_model"].dropna().astype(str)),
        "storey_range": set(jan["storey_range"].dropna().astype(str)),
        "month_format": {REFERENCE_MONTH},
    }


def _flag(parts: list[str], message: str) -> None:
    if message not in parts:
        parts.append(message)


def apply_validation(
    master: pd.DataFrame,
    reference: dict[str, set[str]],
    month_start: str = MONTH_START,
    month_end: str = MONTH_END,
) -> pd.DataFrame:
    """Validate Date, Town, Flat Type, Flat Model, and storey_range against Jan 2012.

    Date: Jan 2012 established the YYYY-MM format. Allowed values are every month
    in the brief's window [2012-01, 2016-12] — a closed set of only 2012-01 would
    contradict the assigned period. Town, flat type, flat model, and storey_range
    are closed sets from January 2012. Failures are structural and leave Cleaned.
    """
    out = master.copy()
    structural: list[list[str]] = []

    towns = reference["town"]
    flat_types = reference["flat_type"]
    flat_models = reference["flat_model"]
    storeys = reference["storey_range"]

    for row in out.itertuples(index=False):
        hard: list[str] = []

        month = "" if pd.isna(row.month) else str(row.month)
        if not MONTH_PATTERN.match(month):
            _flag(hard, "invalid_month_format")
        elif month < month_start or month > month_end:
            _flag(hard, "month_out_of_window")

        town = "" if pd.isna(row.town) else str(row.town)
        if not town:
            _flag(hard, "missing_town")
        elif town not in towns:
            _flag(hard, "unknown_town")

        flat_type = "" if pd.isna(row.flat_type) else str(row.flat_type)
        if not flat_type:
            _flag(hard, "missing_flat_type")
        elif flat_type not in flat_types:
            _flag(hard, "unknown_flat_type")

        storey = "" if pd.isna(row.storey_range) else str(row.storey_range)
        if not storey:
            _flag(hard, "missing_storey_range")
        elif not STOREY_PATTERN.match(storey):
            _flag(hard, "malformed_storey_range")
        elif storey not in storeys:
            _flag(hard, "unknown_storey_range")

        model = "" if pd.isna(row.flat_model) else str(row.flat_model)
        if not model:
            _flag(hard, "missing_flat_model")
        elif model not in flat_models:
            _flag(hard, "unknown_flat_model")

        if pd.isna(row.block) or not str(row.block).strip():
            _flag(hard, "missing_block")
        if pd.isna(row.street_name) or not str(row.street_name).strip():
            _flag(hard, "missing_street_name")

        if pd.isna(row.floor_area_sqm) or row.floor_area_sqm <= 0:
            _flag(hard, "invalid_floor_area")
        if pd.isna(row.resale_price) or row.resale_price <= 0:
            _flag(hard, "invalid_resale_price")

        lease_year = row.lease_commence_date
        txn_year = int(month[:4]) if MONTH_PATTERN.match(month) else None
        if pd.isna(lease_year):
            _flag(hard, "invalid_lease_commence")
        else:
            lease_year_int = int(lease_year)
            if lease_year_int < 1960 or (txn_year is not None and lease_year_int > txn_year):
                _flag(hard, "invalid_lease_commence")

        structural.append(hard)

    out["structural_reasons"] = [";".join(items) for items in structural]
    out["structural_fail"] = out["structural_reasons"] != ""
    return out
