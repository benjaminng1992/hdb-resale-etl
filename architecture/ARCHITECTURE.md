# Part 2 — Ingestion and exploitation architecture

I assumed HDB’s platform is AWS, region **ap-southeast-1**, target store **Amazon S3**. These notes go with the two PNGs and the draw.io files. I did not re-platform the Part 1 Python onto AWS in this repo; this is the design I would run it on.

Icons: [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/).

---

## 1. Data ingestion (public data.gov.sg → private VPC → S3)

The brief wants batch ingest from data.gov.sg, including files **> 100 MB**, while the platform stays in **private VPCs**.

### Network

| Segment | CIDR (my assumption) | What I put here | Internet |
| --- | --- | --- | --- |
| Ingress VPC / public subnet | `10.0.0.0/24` (2 AZs) | NAT Gateway only | Outbound HTTPS (443) to data.gov.sg |
| Data VPC / private app subnet | `10.1.1.0/24`, `10.1.2.0/24` | ECS Fargate (or Glue) ingest job | None. No public IPs |
| Data VPC / private endpoint subnet | `10.1.10.0/24` | Interface endpoints if I need them | None |
| S3 | n/a (gateway prefix list) | Raw / cleaned / transformed / quarantined / hashed | None — **S3 Gateway endpoint** |

I do not open an inbound path from the internet. data.gov.sg is public, so the job pulls it through NAT. S3 traffic does not go through NAT. I send it over the AWS network with a Gateway VPC endpoint.

```
data.gov.sg (public HTTPS)
        │  TLS 1.2+, chunked GET
        ▼
   NAT Gateway (public subnet, IGW only for outbound return path)
        │
        ▼
   ECS Fargate task / Glue job  (private subnet, security group sg-ingest)
        │  multipart PUT, SSE-KMS
        ▼
   S3 Gateway endpoint  →  s3://hdb-resale-{env}/
```

### Files over 100 MB

data.gov.sg’s download API is initiate → poll → URL. I would run:

1. EventBridge rule `cron(0 18 1 * ? *)` — monthly, after HDB usually publishes.
2. Step Functions: `InitiateDownload → Wait → PollDownload (retry) → StreamToS3`.
3. HTTP GET with `stream=True`, 8 MiB chunks. I would not load the whole file into memory. That is why I would not use a plain Lambda for the 2017+ file as it grows.
4. S3 multipart upload (16 MiB parts), checksums on complete.
5. Object key: `raw/collection=189/dt={yyyy-mm-dd}/{dataset_id}.csv`. Raw objects stay as written. A re-run gets a new `dt=`.

I sized the Fargate task at 1 vCPU / 4 GB for streaming. If the team already lives in Glue, Python Shell is fine instead.

### Security (ingest)

- **IAM task role** `hdb-resale-ingest`: `s3:PutObject` on `raw/*` only; `kms:Decrypt` / `GenerateDataKey` on the lake CMK; no `s3:DeleteObject` on raw.
- **Bucket policy**: deny anything that is not from the data-VPC S3 gateway endpoint (`aws:SourceVpce = vpce-s3-data`).
- **KMS**: CMK `alias/hdb-resale`. Key policy allows the ingest role and the Athena query role only.
- **Security group `sg-ingest`**: egress 443 to `0.0.0.0/0` (NAT) and to the S3 prefix list; no ingress.
- **Logging**: VPC Flow Logs → CloudWatch; CloudTrail data events on the bucket; GuardDuty on the account.

### Five lake prefixes

Same grain as Part 1: `s3://hdb-resale-{env}/{raw,cleaned,transformed,quarantined,hashed}/` plus `athena-results/`. I would give Glue Catalog databases the same five names so Athena and Tableau keep stable tables after each monthly run.

---

## 2. Data exploitation (Tableau in another private VPC → Athena)

This is the block in the brief:

> The Data Science Team is using Tableau on AWS for analysis. It resides in **another private VPC**.  
> 3. Data integration via **Athena Driver** ([Tableau Amazon Athena connector](https://help.tableau.com/current/pro/desktop/en-us/examples_amazonathena.htm)).  
> 4. Network traffic must stay **private**.

### Why I did not point Tableau at the public Athena API

Athena’s default endpoint is public. If Tableau sat in a private VPC and called Athena over the internet, that fails requirement 4. So I put **Interface VPC endpoints** for Athena, Glue, and STS **in the Tableau VPC**, and an **S3 Gateway endpoint** in that VPC for results and curated reads. Query traffic stays on AWS.

### Components

| Component | Where | Role |
| --- | --- | --- |
| Tableau Server (or Tableau Cloud Bridge / on-AWS host) | Analytics VPC `10.2.0.0/16`, private subnet `10.2.1.0/24` | BI tool. **Amazon Athena JDBC connector** |
| Interface endpoint `com.amazonaws.ap-southeast-1.athena` | Analytics VPC, endpoint subnet `10.2.10.0/24` | Private `StartQueryExecution` / `GetQueryResults` |
| Interface endpoint `com.amazonaws.ap-southeast-1.glue` | Same | Catalog `GetTable` / `GetPartitions` |
| Interface endpoint `com.amazonaws.ap-southeast-1.sts` | Same | Role assumption for the Tableau instance profile |
| S3 Gateway endpoint | Analytics VPC route tables | Read `s3://hdb-resale-…/cleaned\|transformed\|hashed` and write `athena-results/` |
| Transit Gateway | Shared | Only if the lake is in another account/VPC. Not required for the Athena API itself |
| Athena workgroup `hdb-ds` | Regional | Result location, encryption, bytes-scanned cap |
| Glue Data Catalog | Regional | Databases: `hdb_cleaned`, `hdb_transformed`, `hdb_hashed`, `hdb_quarantined` |

### Tableau connection (Athena driver)

I followed [Tableau’s Athena connector](https://help.tableau.com/current/pro/desktop/en-us/examples_amazonathena.htm):

- Driver: **Amazon Athena JDBC** (`AthenaJDBC42.jar` or the one bundled with Tableau).
- Server: the **VPC endpoint DNS**, not the public `athena.ap-southeast-1.amazonaws.com`. Example: `vpce-xxxxxxxx.athena.ap-southeast-1.vpce.amazonaws.com`.
- Port: **443**.
- S3 staging directory: `s3://hdb-resale-{env}/athena-results/tableau/`.
- Workgroup: `hdb-ds`.
- Auth: instance profile / IAM role `hdb-tableau-athena`. No long-lived keys on the box.
- Catalog: `AwsDataCatalog`. Default database: `hdb_cleaned`. `hdb_hashed` if they need the irreversible id. `hdb_quarantined` is ops-only.

I would turn Private DNS on for the interface endpoints, so a regional hostname still lands on the endpoint ENI, not the public VIP.

### Keeping traffic private (requirement 4)

```
Tableau (10.2.1.15, sg-tableau)
    │  TCP 443
    ├──────── Interface EP (Athena) ──► Athena control plane
    ├──────── Interface EP (Glue)   ──► Glue Catalog
    ├──────── Interface EP (STS)    ──► STS AssumeRole
    └──────── S3 Gateway EP         ──► curated prefixes + athena-results
```

- `sg-tableau`: egress 443 **only** to `sg-vpce-analytics`. No 0.0.0.0/0, no NAT for Athena.
- `sg-vpce-analytics`: ingress 443 from `sg-tableau` only.
- S3 bucket policy also allows `aws:SourceVpce` in **{data-vpc-s3-ep, analytics-vpc-s3-ep}**.
- NACL on the analytics private subnet: allow established + 443 to the endpoint subnet. Deny the rest inbound from other VPCs except TGW if I use it.
- Tableau has **no public IP** and no inbound from the internet. Admins go through SSM Session Manager or a management VPC. I would not put a jump host on 22/3389 from 0.0.0.0/0.

### IAM sketch (Tableau role)

```json
{
  "Effect": "Allow",
  "Action": [
    "athena:StartQueryExecution",
    "athena:GetQueryExecution",
    "athena:GetQueryResults",
    "athena:StopQueryExecution",
    "glue:GetDatabase",
    "glue:GetTable",
    "glue:GetPartitions"
  ],
  "Resource": "*"
}
```

Plus `s3:GetObject` on `cleaned/*`, `transformed/*`, `hashed/*` and `s3:PutObject` / `GetObject` on `athena-results/tableau/*`. Tableau does not get `raw/*`.

### Scale, cost, and how I would keep this maintainable

- Athena workgroup bytes-scanned cap (e.g. 50 GB/query) so a bad workbook cannot run away.
- Parquet + Glue partitions on `month` (and `town` if DS filters that way). Part 1 already writes Parquet.
- Result reuse in the workgroup for the same SQL.
- Monthly ingest is a new partition. Tableau extracts can refresh on the same EventBridge schedule.
- Lake Formation later, if quarantine reasons must stay off the DS project.

---

## 3. Other assumptions

- One AWS account is enough for this test. In production I would split data and analytics accounts and share the KMS key.
- Region is `ap-southeast-1` (HDB / Singapore).
- data.gov.sg stays a public HTTPS API. I did not assume a GovTech peer.
- Tableau on AWS means Tableau Server, or a Bridge, in this VPC. Tableau Cloud would need Private Connect / a Bridge — same endpoint pattern on that host.
- The Glue/Fargate job would run the Part 1 Python. I did not rewrite it here.

---

## 4. Files in this folder

| File | What it is |
| --- | --- |
| [01-data-ingestion.png](01-data-ingestion.png) | Ingest PNG |
| [02-data-exploitation.png](02-data-exploitation.png) | Tableau + Athena driver, private path |
| [01-data-ingestion.drawio](01-data-ingestion.drawio) | Editable, AWS icon library |
| [02-data-exploitation.drawio](02-data-exploitation.drawio) | Editable, exploitation view |

I did not commit `Data Engineering Technical Test.pdf`.
