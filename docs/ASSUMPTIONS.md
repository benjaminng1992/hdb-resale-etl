# Insights and assumptions

These are the calls I made for the January 2012 – December 2016 HDB resale ETL. I followed the brief’s wording for validation and the five output zones. Where two sentences collide, I wrote the choice here.

## Results from this run

From my last run (also in `data/profiling/profile_summary.json`):

| Metric | Value |
| --- | --- |
| Master (2012-01 … 2016-12) | 92,544 |
| Cleaned / transformed / hashed | 76,959 |
| Quarantined | 15,585 |
| `unknown_storey_range` | 6,975 (incl. 56 also `unknown_flat_model`) |
| `unknown_flat_model` only | 436 |
| Duplicate losers | 1,383 |
| Price / area anomalies | 6,791 |

## Scope and sources

I treat collection [189 on data.gov.sg](https://data.gov.sg/collections/189/view) as the system of record. Extract lists child datasets from the public metadata API, then copies the local files or streams the official download API. I never edit the raw files.

The window I used is **2012-01 through 2016-12**. Out-of-window rows stay in **Raw**. I drop them from the master with a `month` filter.

Before March 2012 HDB published **approval date**; from March 2012, **registration date**. I treat `month` as “the month HDB published”, not a reconstructed event time. I did not try to align those two calendars.

## Schema union

I kept **every attribute seen in any file** on the master. `remaining_lease` exists as a column for 2012–2014 rows and is null there. That is expected; the publisher only added it from 2015.

I add `source_file` for lineage. It is not part of the composite key.

## January 2012 as the authoritative set (requirement 3)

I took January 2012 (from the 2000–Feb 2012 file) as the closed set for **Town, Flat Type, Flat Model, and storey_range**. Rows that fail leave Cleaned and go only to Quarantined.

| Field | What I enforced | What I do on failure |
| --- | --- | --- |
| Date / `month` | Format from Jan 2012 (`YYYY-MM`) and in `[2012-01, 2016-12]` | Quarantine. A closed set of only `2012-01` would contradict the assigned window. |
| Town | Closed set of Jan 2012 towns | Quarantine |
| Flat type | Closed set of Jan 2012 types | Quarantine |
| Flat model | Closed set of Jan 2012 models | Quarantine (`DBSS`, `Type S1`, `Type S2`, …) |
| `storey_range` | Closed set of Jan 2012 3-storey bands | Quarantine (Mar 2012–Dec 2014 5-storey bands, later 37 TO 39 / 40 TO 42, …) |

This is the trade-off the brief asked me to explain. HDB changed storey banding when they switched to registration date. If I apply January 2012 as written, I quarantine most of March 2012–December 2014. That is what “authoritative set” means to me. You can see the cost in `data/profiling/domain_comparison.csv` and the `quarantine_reason` counts.

I did **not** rewrite 5-storey bands into 3-storey bands. That would invent values HDB did not publish.

## Remaining lease

The source year is year-only, so I start the 99-year lease on **1 January of `lease_commence_date`**. I compute remaining as-of the **first day of the transaction month**, then round **down** to years and months.

Check I used: commence 1986, month 2015-01 → **70 years 00 months**. That matches the 2015–2016 source field of `70`.

I keep the publisher field as `remaining_lease_source`. The string I compute is `remaining_lease`.

## Composite key and duplicates

I take the key as all **source** columns except `resale_price`. I do not put the computed remaining-lease columns in the key, or every row would look unique after I derive them.

Where keys collide, I keep the higher `resale_price` in Cleaned. The rest go to Quarantined as `duplicate_lower_price` or `duplicate_tie`.

## Anomalies (requirements 6–7)

The publisher data may look clean. I still built the checks.

- Tukey 1.5 × IQR on `resale_price` within `town + flat_type + year`, and on `floor_area_sqm` within `town + flat_type`. I skip groups with fewer than 8 rows so I do not over-flag small cells.
- Sanity band: price `< 50,000` or `> 2,000,000`.

I also flag missing keys, malformed storey text, non-positive area or price, and lease years that are missing, before 1960, or after the sale year. Some of those do not fire on this extract. The tests show the mechanism on synthetic rows.

I do **not** leave anomalies in Cleaned. The brief’s Cleaned zone is “dataset that passes the data quality requirements”, so they sit only in Quarantined (`price_anomaly` / `area_anomaly`).

## Resale Identifier and hashing

I named the column **`Resale Identifier`**, as specified.

```
S + 019 + 23 + 01 + A  →  S0192301A
```

(block `19`, group average `$230,000`, month `2012-01`, town `ANG MO KIO`)

- Block: I strip non-digits, take the first three, and left-pad.
- Average: mean `resale_price` of **cleaned** rows by `month`, `town`, `flat_type`. I do not let quarantined rows pull the average around.
- Last two digits: calendar month. Final character: first character of `town`.

That 9-character rule ignores street, storey, area, model, and lease year, so the id is **not unique**. SHA-256 of a colliding string still collides.

What I put in the hashed zone:

- `hashed_identifier` = SHA-256(`Resale Identifier`) — irreversible form of the specified id
- `hashed_record_id` = SHA-256(canonical composite key) — one irreversible id per cleaned row

I leave plaintext `Resale Identifier` out of the hashed zone.

## Output zones

| Zone | What I put there |
| --- | --- |
| Raw | Source CSVs as I downloaded / copied them |
| Cleaned | Passed Jan 2012 + extra DQ; remaining lease; max-price survivor; **no** anomalies |
| Transformed | Cleaned + `Resale Identifier` |
| Quarantined | Jan 2012 failures, duplicate losers, anomalies; `quarantine_reason` set |
| Hashed | Cleaned grain + `hashed_identifier` + `hashed_record_id` |

I write CSV and Parquet for every table zone.

## Part 2

I designed ingestion and **Tableau → Athena (private)** in [architecture/ARCHITECTURE.md](../architecture/ARCHITECTURE.md) and the two PNGs. I used official AWS Architecture Icons in the draw.io sources (`mxgraph.aws4`) and in the PNGs.

Assumptions I wrote down there: region `ap-southeast-1`, one AWS account is enough for this test, data.gov.sg stays a public HTTPS API, Tableau on AWS means Tableau Server (or a Bridge) in the analytics VPC. I did not re-implement Part 1 as a Glue job in this repo.

I did not commit `Data Engineering Technical Test.pdf`.

## What I deliberately did not do

- Spark / Airflow / dbt for ~92k in-window rows.
- Recoding storey bands or flat-model case to force rows into Cleaned.
- Uploading the assignment PDF.
