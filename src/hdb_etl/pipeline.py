"""End-to-end orchestration used by the notebook and `python -m hdb_etl`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from hdb_etl.anomalies import flag_anomalies
from hdb_etl.clean import deduplicate
from hdb_etl.combine import combine_master, load_raw_frames
from hdb_etl.config import MONTH_END, MONTH_START, RESALE_IDENTIFIER_COL, project_root
from hdb_etl.extract import ensure_raw_files, raw_inventory
from hdb_etl.io import write_outputs
from hdb_etl.profile import domain_comparison, month_counts, profile_dataset
from hdb_etl.transform import add_hashes, add_remaining_lease, add_resale_identifier, hashed_zone
from hdb_etl.validate import apply_validation, build_jan2012_reference


def run_pipeline(
    root: Path | None = None,
    drop_anomalies: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    """Run extract → profile → validate → clean → transform → write zones."""
    root = root or project_root()
    raw_files = ensure_raw_files(root)
    frames = load_raw_frames(raw_files)
    master = combine_master(frames, month_start=MONTH_START, month_end=MONTH_END)

    reference = build_jan2012_reference(master)
    profile_report = profile_dataset(master, frames)
    domain_table = domain_comparison(
        master,
        {k: v for k, v in reference.items() if k != "month_format"},
    )
    profile_report["jan2012_reference_sizes"] = {k: len(v) for k, v in reference.items()}
    profile_report["month_counts"] = month_counts(master).to_dict(orient="records")

    validated = apply_validation(master, reference)
    structural = validated.loc[validated["structural_fail"]].copy()
    if not structural.empty:
        structural["quarantine_reason"] = structural["structural_reasons"]

    working = validated.loc[~validated["structural_fail"]].copy()
    working = add_remaining_lease(working)
    cleaned, duplicates = deduplicate(working)
    cleaned = flag_anomalies(cleaned)

    anomaly_rows = cleaned.loc[cleaned["is_anomaly"]].copy()
    if not anomaly_rows.empty:
        reasons = []
        for row in anomaly_rows.itertuples(index=False):
            tags = []
            if getattr(row, "is_price_anomaly", False):
                tags.append("price_anomaly")
            if getattr(row, "is_area_anomaly", False):
                tags.append("area_anomaly")
            reasons.append(";".join(tags) if tags else "anomaly")
        anomaly_rows["quarantine_reason"] = reasons

    if drop_anomalies:
        cleaned = cleaned.loc[~cleaned["is_anomaly"]].copy()

    # Rows that fail the Jan 2012 closed set (new flat models, 5-storey bands, …)
    # are already in `structural` and are not copied again.
    domain_drift = structural.loc[
        structural["structural_reasons"].str.contains("unknown_storey_range|unknown_flat_model", na=False)
    ].copy() if not structural.empty else structural.copy()

    quarantined = pd.concat(
        [
            structural,
            duplicates,
            anomaly_rows,
        ],
        ignore_index=True,
        sort=False,
    )

    transformed = add_resale_identifier(cleaned)
    hashed_full = add_hashes(transformed)
    hashed = hashed_zone(hashed_full)

    identifier_uniques = (
        int(transformed[RESALE_IDENTIFIER_COL].nunique()) if not transformed.empty else 0
    )
    record_uniques = int(hashed_full["hashed_record_id"].nunique()) if not hashed_full.empty else 0
    profile_report["identifier_uniqueness"] = {
        "cleaned_rows": int(len(transformed)),
        "distinct_resale_identifier": identifier_uniques,
        "identifier_collisions": int(len(transformed) - identifier_uniques),
        "distinct_hashed_record_id": record_uniques,
    }

    written: dict[str, Any] = {}
    if persist:
        written = write_outputs(
            root=root,
            cleaned=cleaned,
            transformed=transformed,
            hashed=hashed,
            quarantined=quarantined,
            domain_drift=domain_drift,
            profile_report=profile_report,
            domain_table=domain_table,
        )

    return {
        "root": root,
        "raw_files": raw_files,
        "raw_inventory": raw_inventory(raw_files),
        "frames": frames,
        "master": master,
        "reference": reference,
        "profile_report": profile_report,
        "domain_table": domain_table,
        "validated": validated,
        "cleaned": cleaned,
        "transformed": transformed,
        "hashed": hashed,
        "hashed_full": hashed_full,
        "quarantined": quarantined,
        "domain_drift": domain_drift,
        "duplicates": duplicates,
        "structural": structural,
        "written": written,
    }
