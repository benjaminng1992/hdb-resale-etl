"""Remaining lease, resale identifier, and irreversible hashes."""

from __future__ import annotations

import hashlib
import re

import pandas as pd

from hdb_etl.config import COMPOSITE_KEY_COLUMNS, LEASE_TERM_YEARS, RESALE_IDENTIFIER_COL

_NON_DIGIT = re.compile(r"[^0-9]")


def block_digits(block: object) -> str:
    """First three numeric characters of block, left-padded to width 3."""
    digits = _NON_DIGIT.sub("", "" if pd.isna(block) else str(block))
    if not digits:
        return "000"
    return digits[:3].zfill(3)


def first_two_digits_of_amount(amount: object) -> str:
    """Leading two digits of the integer average price (230000 -> 23)."""
    if pd.isna(amount):
        return "00"
    number = int(round(float(amount)))
    text = str(abs(number))
    return text[:2].zfill(2) if len(text) < 2 else text[:2]


def remaining_lease_parts(lease_commence_year: object, month: object) -> tuple[int, int]:
    """99-year lease from 1 Jan of commence year, remaining as-of 1st of month."""
    year_str, month_str = str(month).split("-")
    end_year = int(lease_commence_year) + LEASE_TERM_YEARS
    total_months = (end_year - int(year_str)) * 12 + (1 - int(month_str))
    total_months = max(total_months, 0)
    return total_months // 12, total_months % 12


def format_remaining_lease(years: int, months: int) -> str:
    unit = "month" if months == 1 else "months"
    return f"{years} years {months:02d} {unit}"


def add_remaining_lease(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out = out.rename(columns={"remaining_lease": "remaining_lease_source"})
    parts = [
        remaining_lease_parts(row.lease_commence_date, row.month)
        for row in out.itertuples(index=False)
    ]
    out["remaining_lease_years"] = [p[0] for p in parts]
    out["remaining_lease_months"] = [p[1] for p in parts]
    out["remaining_lease"] = [
        format_remaining_lease(years, months) for years, months in parts
    ]
    return out


def build_resale_identifier(block: object, avg_price: object, month: object, town: object) -> str:
    month_text = str(month)
    month_digits = month_text[5:7] if len(month_text) >= 7 else "00"
    town_initial = str(town).strip()[:1].upper() if not pd.isna(town) else "X"
    return (
        "S"
        + block_digits(block)
        + first_two_digits_of_amount(avg_price)
        + month_digits
        + town_initial
    )


def add_resale_identifier(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Build the business identifier from cleaned rows only (averages are not skewed by rejects)."""
    out = cleaned.copy()
    averages = (
        out.groupby(["month", "town", "flat_type"], dropna=False)["resale_price"]
        .mean()
        .rename("avg_resale_price_group")
        .reset_index()
    )
    out = out.merge(averages, on=["month", "town", "flat_type"], how="left")
    out[RESALE_IDENTIFIER_COL] = [
        build_resale_identifier(row.block, row.avg_resale_price_group, row.month, row.town)
        for row in out.itertuples(index=False)
    ]
    return out


def _canonical_key(row: pd.Series) -> str:
    pieces = []
    for column in COMPOSITE_KEY_COLUMNS:
        value = row[column] if column in row.index else ""
        if column == "remaining_lease":
            value = row["remaining_lease_source"] if "remaining_lease_source" in row.index else value
        pieces.append("" if pd.isna(value) else str(value))
    return "|".join(pieces)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def add_hashes(transformed: pd.DataFrame) -> pd.DataFrame:
    """Hash the constructed identifier, plus a uniqueness-preserving record hash."""
    out = transformed.copy()
    out["hashed_identifier"] = out[RESALE_IDENTIFIER_COL].map(sha256_hex)
    out["hashed_record_id"] = [_canonical_key(row) for _, row in out.iterrows()]
    out["hashed_record_id"] = out["hashed_record_id"].map(sha256_hex)
    return out


def hashed_zone(hashed: pd.DataFrame) -> pd.DataFrame:
    """Cleaned grain + irreversible hashes. Plaintext identifier is excluded."""
    drop = [c for c in (RESALE_IDENTIFIER_COL,) if c in hashed.columns]
    return hashed.drop(columns=drop)
