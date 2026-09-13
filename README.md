# HDB resale flat prices ETL

This is my submission for the Senior Data Engineer technical test.

**Part 1** is a Python pipeline on HDB resale transactions from [data.gov.sg collection 189](https://data.gov.sg/collections/189/view), January 2012 to December 2016. I wrote it in pandas. The in-window table is about 92k rows; I did not add Spark or Airflow for that volume.

**Part 2** is architecture only. No extra coding. Target store is S3.

Public repo: https://github.com/benjaminng1992/hdb-resale-etl

## How to run

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The file I expect reviewers to run is the notebook. Open it and **Run All**, top to bottom:

```bash
jupyter notebook notebooks/hdb_resale_etl.ipynb
```

That is the same pipeline as:

```bash
python -m hdb_etl
```

Do not click Run on files under `src/hdb_etl/` (for example `combine.py`). Those are library modules. If you do, you will get `ModuleNotFoundError` or a message telling you to use `python -m hdb_etl`.

Raw CSVs are already in `data/raw/`. I left them as I got them from the publisher. If that folder is empty, extract will pull collection 189. Do not edit the raw files.

```bash
pytest -q
```

## Insights and assumptions

I put the judgements and trade-offs in **[docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md)**.

That file is where I explain, among other things:

- why January 2012 as a closed set quarantines most Mar 2012–Dec 2014 storey bands
- how I compute remaining lease (99 years from 1 Jan of `lease_commence_date`)
- why hashing `Resale Identifier` cannot stay unique, and what I did about it
- row counts from the last run (also in `data/profiling/profile_summary.json`)

That is also where I explain why Cleaned is 76,959 and Quarantined is 15,585.

## Part 1 — what I am submitting

| Requirement | Where it is |
| --- | --- |
| Notebook | [notebooks/hdb_resale_etl.ipynb](notebooks/hdb_resale_etl.ipynb) |
| Pipeline code | [src/hdb_etl/](src/hdb_etl/) |
| Input files (as-is) | [data/raw/](data/raw/) |
| Cleaned | [data/cleaned/](data/cleaned/) |
| Transformed (`Resale Identifier`) | [data/transformed/](data/transformed/) |
| Quarantined (fails, dups, anomalies) | [data/quarantined/](data/quarantined/) |
| Hashed (no plaintext identifier) | [data/hashed/](data/hashed/) |
| Profiling | [data/profiling/](data/profiling/) |
| Insights and assumptions | [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md) |
| Tests | [tests/](tests/) |

Each table zone has CSV and Parquet.

## Part 2 — what I am submitting

Part 2 is design, not another dataset. I assumed HDB’s platform is AWS, region `ap-southeast-1`, target store S3. I documented the rest of the assumptions in [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) and [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md).

| Requirement | Where it is |
| --- | --- |
| Data ingestion (public data.gov.sg → private VPC → S3, including files >100 MB) | [architecture/01-data-ingestion.png](architecture/01-data-ingestion.png) |
| Data exploitation (Tableau in another private VPC → Athena JDBC, traffic stays private) | [architecture/02-data-exploitation.png](architecture/02-data-exploitation.png) |
| Editable diagrams (AWS Architecture Icons) | [architecture/01-data-ingestion.drawio](architecture/01-data-ingestion.drawio), [architecture/02-data-exploitation.drawio](architecture/02-data-exploitation.drawio) |
| Security, scale, IAM, JDBC, CIDRs | [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) |
| Same public git repo | this repository |
| Do not upload the assignment paper | `Data Engineering Technical Test.pdf` is gitignored and is not in this repo |

Icons: [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/). To rebuild the PNGs:

```bash
python scripts/render_architecture.py
```
