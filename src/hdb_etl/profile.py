"""Lightweight data profiler — no extra framework required."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _series_profile(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna()
    profile: dict[str, Any] = {
        "dtype": str(series.dtype),
        "nulls": int(series.isna().sum()),
        "null_pct": round(float(series.isna().mean()) * 100, 2),
        "nunique": int(series.nunique(dropna=True)),
    }
    if pd.api.types.is_numeric_dtype(series):
        if non_null.empty:
            profile.update({"min": None, "max": None, "mean": None})
        else:
            profile.update(
                {
                    "min": float(non_null.min()),
                    "max": float(non_null.max()),
                    "mean": float(non_null.mean()),
                }
            )
    else:
        profile["sample_values"] = [str(v) for v in non_null.astype(str).value_counts().head(8).index]
    return profile


def profile_dataset(master: pd.DataFrame, frames: dict[str, pd.DataFrame] | None = None) -> dict[str, Any]:
    source_counts = (
        master["source_file"].value_counts().rename_axis("source_file").reset_index(name="rows")
        if "source_file" in master.columns
        else pd.DataFrame()
    )
    report: dict[str, Any] = {
        "row_count": int(len(master)),
        "column_count": int(master.shape[1]),
        "columns": list(master.columns),
        "month_min": None if master.empty else str(master["month"].min()),
        "month_max": None if master.empty else str(master["month"].max()),
        "nunique_months": int(master["month"].nunique()) if not master.empty else 0,
        "source_counts": source_counts.to_dict(orient="records"),
        "columns_profile": {col: _series_profile(master[col]) for col in master.columns},
    }
    if frames:
        report["raw_file_schemas"] = {
            name: {"rows": int(len(frame)), "columns": list(frame.columns)}
            for name, frame in frames.items()
        }
    return report


def domain_comparison(master: pd.DataFrame, reference_values: dict[str, set[str]]) -> pd.DataFrame:
    rows = []
    for field, allowed in reference_values.items():
        observed = set(master[field].dropna().astype(str).unique())
        extra = sorted(observed - allowed)
        missing = sorted(allowed - observed)
        rows.append(
            {
                "field": field,
                "reference_count": len(allowed),
                "observed_count": len(observed),
                "new_values": ", ".join(extra) if extra else "",
                "new_value_count": len(extra),
                "reference_only": ", ".join(missing) if missing else "",
            }
        )
    return pd.DataFrame(rows)


def month_counts(master: pd.DataFrame) -> pd.DataFrame:
    return (
        master.groupby("month", dropna=False)
        .size()
        .rename("rows")
        .reset_index()
        .sort_values("month")
    )
