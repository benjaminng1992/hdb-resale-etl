"""Extract collection 189 from data.gov.sg, with a local-file fallback."""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

import requests

from hdb_etl.config import (
    COLLECTION_ID,
    COLLECTION_METADATA_URL,
    INITIATE_DOWNLOAD_URL,
    POLL_DOWNLOAD_URL,
    local_source_dir,
    zone_dir,
)

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "hdb-resale-etl/1.0"})


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\- ()]+", "_", name).strip()
    if not cleaned.lower().endswith(".csv"):
        cleaned = f"{cleaned}.csv"
    return cleaned


def fetch_collection_datasets(timeout: int = 60) -> list[dict]:
    """Return dataset metadata for collection 189."""
    response = _SESSION.get(
        COLLECTION_METADATA_URL,
        params={"withDatasetMetadata": "true"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") not in (0, 200, None) and payload.get("errorMsg"):
        raise RuntimeError(f"Collection metadata error: {payload}")
    return payload["data"].get("datasetMetadata", [])


def _poll_download_url(dataset_id: str, timeout: int = 60, attempts: int = 20) -> str:
    _SESSION.get(INITIATE_DOWNLOAD_URL.format(dataset_id=dataset_id), timeout=timeout)
    for _ in range(attempts):
        poll = _SESSION.get(POLL_DOWNLOAD_URL.format(dataset_id=dataset_id), timeout=timeout)
        poll.raise_for_status()
        body = poll.json().get("data", {})
        url = body.get("url")
        status = str(body.get("status", "")).lower()
        if url:
            return url
        if status in {"failed", "error"}:
            raise RuntimeError(f"Download failed for {dataset_id}: {body}")
        time.sleep(1.5)
    raise TimeoutError(f"Timed out waiting for download URL for {dataset_id}")


def _stream_to_file(url: str, dest: Path, timeout: int = 120) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with _SESSION.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    tmp.replace(dest)


def download_collection(raw_dir: Path) -> list[Path]:
    """Download every CSV in collection 189 into the raw zone."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for dataset in fetch_collection_datasets():
        dataset_id = dataset["datasetId"]
        filename = _safe_filename(dataset.get("name") or dataset_id)
        dest = raw_dir / filename
        url = _poll_download_url(dataset_id)
        _stream_to_file(url, dest)
        written.append(dest)
    return sorted(written)


def _copy_local_sources(root: Path, raw_dir: Path) -> list[Path]:
    source_dir = local_source_dir(root)
    if not source_dir.is_dir():
        return []
    copied: list[Path] = []
    for src in sorted(source_dir.glob("*.csv")):
        dest = raw_dir / src.name
        if not dest.exists() or dest.stat().st_size != src.stat().st_size:
            shutil.copy2(src, dest)
        copied.append(dest)
    return copied


def ensure_raw_files(root: Path | None = None, prefer_local: bool = True) -> list[Path]:
    """Populate data/raw/ from local files or the public API. Never edits file contents.

    Local CSVs already supplied in ResaleFlatPrices/ are copied as-is. If they are
    missing, files are streamed from data.gov.sg collection 189.
    """
    from hdb_etl.config import project_root

    root = root or project_root()
    raw_dir = zone_dir("raw", root)
    existing = sorted(raw_dir.glob("*.csv"))
    if existing:
        return existing

    if prefer_local:
        copied = _copy_local_sources(root, raw_dir)
        if copied:
            return copied

    try:
        return download_collection(raw_dir)
    except Exception:
        copied = _copy_local_sources(root, raw_dir)
        if copied:
            return copied
        raise


def raw_inventory(raw_files: list[Path]) -> list[dict]:
    return [
        {
            "file": path.name,
            "bytes": path.stat().st_size,
            "collection_id": COLLECTION_ID,
        }
        for path in raw_files
    ]
