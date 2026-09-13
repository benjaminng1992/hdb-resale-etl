"""Write the five mandated output zones plus profiling artefacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from hdb_etl.config import zone_dir


def write_table(frame: pd.DataFrame, directory: Path, stem: str) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    # Concatenated quarantine frames can mix int years and "YY years MM months" strings.
    if "remaining_lease" in out.columns:
        out["remaining_lease"] = out["remaining_lease"].astype("string")
    csv_path = directory / f"{stem}.csv"
    parquet_path = directory / f"{stem}.parquet"
    out.to_csv(csv_path, index=False)
    out.to_parquet(parquet_path, index=False)
    return {"csv": csv_path, "parquet": parquet_path}


def write_json(payload: Any, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path


def write_outputs(
    *,
    root: Path,
    cleaned: pd.DataFrame,
    transformed: pd.DataFrame,
    hashed: pd.DataFrame,
    quarantined: pd.DataFrame,
    domain_drift: pd.DataFrame,
    profile_report: dict[str, Any],
    domain_table: pd.DataFrame,
) -> dict[str, Any]:
    written = {
        "cleaned": write_table(cleaned, zone_dir("cleaned", root), "cleaned"),
        "transformed": write_table(transformed, zone_dir("transformed", root), "transformed"),
        "hashed": write_table(hashed, zone_dir("hashed", root), "hashed"),
        "quarantined": write_table(quarantined, zone_dir("quarantined", root), "quarantined"),
    }
    if not domain_drift.empty:
        written["domain_drift"] = write_table(domain_drift, zone_dir("quarantined", root), "domain_drift")

    profiling = zone_dir("profiling", root)
    written["profile_json"] = write_json(profile_report, profiling / "profile_summary.json")
    if not domain_table.empty:
        written["domain_csv"] = profiling / "domain_comparison.csv"
        domain_table.to_csv(written["domain_csv"], index=False)
    return written
