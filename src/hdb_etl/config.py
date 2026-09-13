"""Shared paths, date window, and column contracts."""

from pathlib import Path

COLLECTION_ID = "189"
COLLECTION_METADATA_URL = (
    "https://api-production.data.gov.sg/v2/public/api/collections/"
    f"{COLLECTION_ID}/metadata"
)
DATASET_METADATA_URL = "https://api-production.data.gov.sg/v2/public/api/datasets/{dataset_id}/metadata"
INITIATE_DOWNLOAD_URL = (
    "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/initiate-download"
)
POLL_DOWNLOAD_URL = (
    "https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}/poll-download"
)

MONTH_START = "2012-01"
MONTH_END = "2016-12"
REFERENCE_MONTH = "2012-01"
LEASE_TERM_YEARS = 99

CORE_COLUMNS = [
    "month",
    "town",
    "flat_type",
    "block",
    "street_name",
    "storey_range",
    "floor_area_sqm",
    "flat_model",
    "lease_commence_date",
    "remaining_lease",
    "resale_price",
]

# Composite key = all source attributes except resale price.
COMPOSITE_KEY_COLUMNS = [c for c in CORE_COLUMNS if c != "resale_price"]
RESALE_IDENTIFIER_COL = "Resale Identifier"

OUTPUT_ZONES = ("raw", "cleaned", "transformed", "quarantined", "hashed", "profiling")


def project_root() -> Path:
    """Resolve the repository root from this file or the current working directory."""
    here = Path(__file__).resolve()
    for candidate in (here.parents[2], Path.cwd()):
        if (candidate / "src" / "hdb_etl").is_dir():
            return candidate
    return Path.cwd()


def data_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "data"


def zone_dir(zone: str, root: Path | None = None) -> Path:
    path = data_dir(root) / zone
    path.mkdir(parents=True, exist_ok=True)
    return path


def local_source_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / "ResaleFlatPrices"
