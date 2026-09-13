# Part 2 — Architecture

I put the AWS design here. Target store is S3. No extra coding for this part.

| File | What it is |
| --- | --- |
| [01-data-ingestion.png](01-data-ingestion.png) | Public data.gov.sg into a private VPC / S3, including files >100 MB |
| [02-data-exploitation.png](02-data-exploitation.png) | Tableau in another private VPC → Athena JDBC. Traffic stays private |
| [01-data-ingestion.drawio](01-data-ingestion.drawio) | diagrams.net + AWS Architecture Icons (`mxgraph.aws4`) |
| [02-data-exploitation.drawio](02-data-exploitation.drawio) | Same, exploitation view |
| [ARCHITECTURE.md](ARCHITECTURE.md) | CIDRs, IAM, JDBC, security groups, and the assumptions I made |

To rebuild the PNGs (downloads the AWS icons once into `icons/`):

```bash
python scripts/render_architecture.py
```

Icons: [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/).
