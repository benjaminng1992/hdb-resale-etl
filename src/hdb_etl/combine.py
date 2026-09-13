"""Load raw CSVs as-is and union them into a single master frame."""

from __future__ import annotations

import sys
from pathlib import Path

_src = Path(__file__).resolve().parents[1]
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import pandas as pd

from hdb_etl.config import CORE_COLUMNS, MONTH_END, MONTH_START


def load_raw_frames(raw_files: list[Path]) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for path in raw_files:
        frame = pd.read_csv(path)
        frame["source_file"] = path.name
        frames[path.name] = frame
    return frames


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out.columns = [str(c).strip() for c in out.columns]
    for column in CORE_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    return out


def combine_master(
    frames: dict[str, pd.DataFrame],
    month_start: str = MONTH_START,
    month_end: str = MONTH_END,
) -> pd.DataFrame:
    """Outer-union every raw file, then keep the assessment month window.

    The union includes `remaining_lease` even when a source file does not have it.
    Month filtering happens in memory; raw files are never rewritten.
    """
    aligned = []
    for name, frame in frames.items():
        piece = _normalise_columns(frame)
        piece["source_file"] = name
        aligned.append(piece[CORE_COLUMNS + ["source_file"]])

    master = pd.concat(aligned, ignore_index=True, sort=False)
    master["month"] = master["month"].astype("string").str.strip()
    master["town"] = master["town"].astype("string").str.strip()
    master["flat_type"] = master["flat_type"].astype("string").str.strip()
    master["flat_model"] = master["flat_model"].astype("string").str.strip()
    master["storey_range"] = master["storey_range"].astype("string").str.strip()
    master["block"] = master["block"].astype("string").str.strip()
    master["street_name"] = master["street_name"].astype("string").str.strip()
    master["floor_area_sqm"] = pd.to_numeric(master["floor_area_sqm"], errors="coerce")
    master["resale_price"] = pd.to_numeric(master["resale_price"], errors="coerce")
    master["lease_commence_date"] = pd.to_numeric(master["lease_commence_date"], errors="coerce")

    in_window = (master["month"] >= month_start) & (master["month"] <= month_end)
    return master.loc[in_window].reset_index(drop=True)


if __name__ == "__main__":
    raise SystemExit(
        "Do not run this file directly. From the project folder, with the venv on:\n"
        "  pip install -e .\n"
        "  python -m hdb_etl\n"
        "Or open notebooks/hdb_resale_etl.ipynb and Run All."
    )

