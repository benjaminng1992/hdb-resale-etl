"""CLI: python -m hdb_etl"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python -m hdb_etl` from a checkout without installing the package.
src = Path(__file__).resolve().parents[1]
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from hdb_etl.config import project_root
from hdb_etl.pipeline import run_pipeline


def main() -> None:
    result = run_pipeline(root=project_root(), persist=True)
    cleaned = result["cleaned"]
    print(f"Raw files: {len(result['raw_files'])}")
    print(f"Master (2012-01 to 2016-12): {len(result['master']):,} rows")
    print(f"Cleaned: {len(cleaned):,} rows")
    print(f"Quarantined: {len(result['quarantined']):,} rows")
    print(f"Transformed: {len(result['transformed']):,} rows")
    print(f"Hashed: {len(result['hashed']):,} rows")
    print(f"Outputs written under {result['root'] / 'data'}")


if __name__ == "__main__":
    main()
