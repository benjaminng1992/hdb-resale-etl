"""Deduplicate on the composite key, keeping the higher resale price."""

from __future__ import annotations

import pandas as pd

from hdb_etl.config import COMPOSITE_KEY_COLUMNS


def _key_columns(frame: pd.DataFrame) -> list[str]:
    columns = []
    for column in COMPOSITE_KEY_COLUMNS:
        if column == "remaining_lease" and "remaining_lease_source" in frame.columns:
            columns.append("remaining_lease_source")
        elif column in frame.columns:
            columns.append(column)
    return columns


def _key_frame(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Stringify keys so null remaining_lease values still match each other."""
    out = pd.DataFrame(index=frame.index)
    for column in keys:
        out[column] = frame[column].astype("string").fillna("__MISSING__")
    return out


def deduplicate(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep the max resale_price per composite key. Ties keep the first stable row."""
    if frame.empty:
        empty = frame.copy()
        return empty, empty

    work = frame.copy()
    keys = _key_columns(work)
    work["_row_id"] = range(len(work))
    work = work.sort_values(["resale_price", "_row_id"], ascending=[False, True])
    key_view = _key_frame(work, keys)
    work = pd.concat([work, key_view.add_prefix("_k_")], axis=1)
    key_cols = [f"_k_{c}" for c in keys]

    winner_ids = work.drop_duplicates(subset=key_cols, keep="first")["_row_id"]
    winners = work[work["_row_id"].isin(winner_ids)].copy()
    losers = work[~work["_row_id"].isin(winner_ids)].copy()

    if not losers.empty:
        max_price = winners[key_cols + ["resale_price"]].rename(columns={"resale_price": "kept_resale_price"})
        losers = losers.merge(max_price, on=key_cols, how="left")
        tied = losers["resale_price"] == losers["kept_resale_price"]
        losers["quarantine_reason"] = tied.map(
            lambda is_tie: "duplicate_tie" if is_tie else "duplicate_lower_price"
        )
        losers = losers.drop(columns=["kept_resale_price"], errors="ignore")

    drop_cols = ["_row_id", *key_cols]
    winners = winners.drop(columns=drop_cols).sort_values(["month", "town", "block"]).reset_index(drop=True)
    losers = losers.drop(columns=drop_cols, errors="ignore").reset_index(drop=True)
    return winners, losers
