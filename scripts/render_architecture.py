"""Compose Part 2 PNGs using AWS Architecture Icon assets (mingrammer/diagrams pack)."""

from __future__ import annotations

import os
from pathlib import Path

import requests

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "architecture"
ICON_DIR = OUT / "icons"
ICON_DIR.mkdir(parents=True, exist_ok=True)

# AWS Architecture Icons as packaged by diagrams (same artwork as the AWS icon pack).
BASE = "https://raw.githubusercontent.com/mingrammer/diagrams/master/resources/aws"
ICONS = {
    "s3": f"{BASE}/storage/simple-storage-service-s3.png",
    "athena": f"{BASE}/analytics/athena.png",
    "glue": f"{BASE}/analytics/glue.png",
    "fargate": f"{BASE}/compute/fargate.png",
    "nat": f"{BASE}/network/nat-gateway.png",
    "tgw": f"{BASE}/network/transit-gateway.png",
    "endpoint": f"{BASE}/network/endpoint.png",
    "vpc": f"{BASE}/network/vpc.png",
    "kms": f"{BASE}/security/key-management-service.png",
    "iam": f"{BASE}/security/identity-and-access-management-iam.png",
    "cloudwatch": f"{BASE}/management/cloudwatch.png",
    "cloudtrail": f"{BASE}/management/cloudtrail.png",
    "sfn": f"{BASE}/integration/step-functions.png",
    "eventbridge": f"{BASE}/integration/eventbridge.png",
    "iam_role": f"{BASE}/security/identity-and-access-management-iam-role.png",
}

BG = "#0b1b2b"
TEXT = "#f4f7fb"
MUTED = "#b8c5d3"
LINE = "#d6deea"


def _fetch_icons() -> dict[str, Path]:
    paths = {}
    for name, url in ICONS.items():
        dest = ICON_DIR / f"{name}.png"
        if dest.exists() and dest.stat().st_size > 500:
            paths[name] = dest
            continue
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            dest.write_bytes(response.content)
        except Exception as exc:
            raise RuntimeError(f"Failed to download AWS icon {name} from {url}") from exc
        if dest.stat().st_size < 500:
            raise RuntimeError(f"Icon {name} looks empty: {url}")
        paths[name] = dest
    return paths


def _icon(ax, path: Path, x: float, y: float, zoom: float = 0.18):
    img = Image.open(path).convert("RGBA")
    ab = AnnotationBbox(OffsetImage(img, zoom=zoom), (x, y), frameon=False, zorder=5)
    ax.add_artist(ab)


def _region(ax, xy, w, h, title, edge, face):
    ax.add_patch(
        FancyBboxPatch(
            xy, w, h, boxstyle="round,pad=0.01,rounding_size=0.05",
            facecolor=face, edgecolor=edge, linewidth=1.4, linestyle="--",
        )
    )
    ax.text(xy[0] + 0.12, xy[1] + h - 0.18, title, color=edge, fontsize=8, fontweight="bold")


def _label(ax, x, y, title, sub=None):
    ax.text(x, y, title, ha="center", va="top", color=TEXT, fontsize=7.4, fontweight="bold")
    if sub:
        ax.text(x, y - 0.18, sub, ha="center", va="top", color=MUTED, fontsize=6.2)


def _arrow(ax, a, b):
    ax.add_patch(
        FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9, lw=1.05, color=LINE, shrinkA=6, shrinkB=8)
    )


def _service(ax, icons, key, x, y, title, sub, zoom=0.17):
    _icon(ax, icons[key], x, y + 0.28, zoom)
    _label(ax, x, y, title, sub)


def render_ingestion(icons: dict[str, Path]) -> Path:
    fig, ax = plt.subplots(figsize=(16.2, 9.2), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 16.2)
    ax.set_ylim(0, 9.2)
    ax.axis("off")
    ax.set_title(
        "Part 2.1  Batch ingestion — data.gov.sg (public) to HDB private VPC / S3   |   AWS Architecture Icons",
        color=TEXT, fontsize=12, loc="left", pad=8,
    )

    # Internet
    _region(ax, (0.2, 6.7), 2.6, 2.1, "Internet", "#ed7100", "#3b1d12")
    ax.text(1.5, 8.15, "data.gov.sg", ha="center", color=TEXT, fontsize=9, fontweight="bold")
    ax.text(1.5, 7.75, "Collection 189  HTTPS :443", ha="center", color=MUTED, fontsize=6.5)
    ax.text(1.5, 7.35, "initiate / poll / CSV >100MB", ha="center", color=MUTED, fontsize=6.5)

    _region(ax, (3.1, 0.55), 12.85, 8.25, "HDB data platform account  ·  ap-southeast-1  ·  VPC 10.1.0.0/16", "#5aa7c7", "#10263a")
    _region(ax, (3.3, 6.55), 5.7, 2.0, "Public subnet 10.0.0.0/24  ·  egress only", "#e0b44b", "#3d3317")
    _service(ax, icons, "nat", 4.5, 7.05, "NAT Gateway", "no inbound from internet")
    _service(ax, icons, "eventbridge", 6.4, 7.05, "EventBridge", "monthly cron")
    _service(ax, icons, "sfn", 8.1, 7.05, "Step Functions", "retry poll-download")

    _region(ax, (3.3, 2.55), 5.7, 3.75, "Private app subnet 10.1.1.0/24  ·  no public IPs", "#69c07a", "#163528")
    _service(ax, icons, "fargate", 4.5, 4.55, "ECS Fargate job", "stream 8MiB chunks")
    _service(ax, icons, "iam", 6.4, 4.55, "IAM task role", "s3:PutObject raw/*")
    _service(ax, icons, "kms", 8.1, 4.55, "KMS CMK", "SSE-KMS on all objects")
    _service(ax, icons, "cloudwatch", 5.2, 3.05, "CloudWatch", "job + flow logs")
    _service(ax, icons, "cloudtrail", 7.4, 3.05, "CloudTrail", "S3 data events")

    _region(ax, (9.25, 2.55), 6.4, 5.95, "S3 lake via Gateway VPC Endpoint  (not the internet)", "#e06b75", "#2b1720")
    _service(ax, icons, "endpoint", 10.3, 7.15, "S3 Gateway EP", "pl-s3 prefix list")
    _service(ax, icons, "s3", 12.0, 7.15, "s3://hdb-resale/", "immutable raw keys")
    _service(ax, icons, "glue", 14.0, 7.15, "Glue Catalog", "5 databases")
    _service(ax, icons, "s3", 10.6, 5.15, "raw/", "as-is CSVs")
    _service(ax, icons, "s3", 12.2, 5.15, "cleaned/", "passed DQ")
    _service(ax, icons, "s3", 13.8, 5.15, "transformed/", "Resale Identifier")
    _service(ax, icons, "s3", 10.6, 3.25, "quarantined/", "fails / dups / anomalies")
    _service(ax, icons, "s3", 12.2, 3.25, "hashed/", "SHA-256")
    _service(ax, icons, "glue", 13.8, 3.25, "athena-results/", "spill + Tableau")

    _arrow(ax, (2.8, 7.7), (4.1, 7.55))
    _arrow(ax, (4.5, 6.85), (4.5, 5.55))
    _arrow(ax, (5.6, 5.0), (10.0, 7.3))

    ax.text(
        0.25, 0.18,
        "Assumptions: outbound-only via NAT; S3 stays on the AWS network (gateway endpoint + aws:SourceVpce); "
        "files >100MB streamed (multipart), never held in Lambda memory. Details: architecture/ARCHITECTURE.md",
        color=MUTED, fontsize=7.0, va="bottom",
    )
    fig.tight_layout()
    path = OUT / "01-data-ingestion.png"
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return path


def render_exploitation(icons: dict[str, Path]) -> Path:
    fig, ax = plt.subplots(figsize=(16.2, 9.2), dpi=160)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 16.2)
    ax.set_ylim(0, 9.2)
    ax.axis("off")
    ax.set_title(
        "Part 2.2  Exploitation — Tableau (private VPC) to Athena JDBC over VPC endpoints   |   AWS Architecture Icons",
        color=TEXT, fontsize=12, loc="left", pad=8,
    )

    _region(ax, (0.2, 1.15), 6.55, 7.55, "Analytics VPC 10.2.0.0/16  ·  Tableau  ·  no public IPs", "#5aa7c7", "#10263a")
    ax.text(3.45, 8.15, "Tableau Server on AWS", ha="center", color=TEXT, fontsize=9, fontweight="bold")
    ax.text(3.45, 7.85, "Amazon Athena JDBC connector  ·  port 443  ·  workgroup hdb-ds", ha="center", color=MUTED, fontsize=6.6)
    ax.add_patch(FancyBboxPatch((0.45, 6.85), 6.05, 0.85, boxstyle="round,pad=0.01,rounding_size=0.04",
                                facecolor="#1c3f66", edgecolor="#2e73b6", lw=1.1))
    ax.text(3.45, 7.27, "JDBC URL → vpce-xxxx.athena.ap-southeast-1.vpce.amazonaws.com:443", ha="center", color=TEXT, fontsize=6.8)

    _service(ax, icons, "endpoint", 1.35, 5.35, "Interface EP", "Athena")
    _service(ax, icons, "endpoint", 3.45, 5.35, "Interface EP", "Glue + STS")
    _service(ax, icons, "endpoint", 5.55, 5.35, "S3 Gateway EP", "results + curated")
    _service(ax, icons, "iam", 2.15, 3.15, "IAM role", "hdb-tableau-athena")
    _service(ax, icons, "iam_role", 4.75, 3.15, "sg-tableau", "egress 443 to EP SGs only")

    _region(ax, (7.0, 3.55), 2.15, 2.5, "Shared", "#e0b44b", "#3d3317")
    _service(ax, icons, "tgw", 8.05, 4.35, "Transit GW", "optional VPC-VPC")

    _region(ax, (9.4, 1.15), 6.55, 7.55, "Data plane / regional APIs  ·  private only", "#69c07a", "#163528")
    _service(ax, icons, "athena", 11.0, 7.15, "Amazon Athena", "workgroup hdb-ds, encrypted")
    _service(ax, icons, "glue", 13.5, 7.15, "Glue Catalog", "cleaned / transformed / hashed")
    _service(ax, icons, "s3", 11.0, 5.15, "S3 curated", "SSE-KMS  ·  two VPCE IDs")
    _service(ax, icons, "s3", 13.5, 5.15, "athena-results/", "Tableau staging dir")
    _service(ax, icons, "kms", 11.0, 3.15, "KMS CMK", "same key as ingest")
    _service(ax, icons, "cloudtrail", 13.5, 3.15, "CloudTrail", "query + object access")

    _arrow(ax, (6.7, 7.15), (10.3, 7.45))
    _arrow(ax, (6.7, 5.7), (7.2, 5.0))
    _arrow(ax, (9.1, 4.8), (10.3, 7.2))
    _arrow(ax, (11.0, 6.85), (11.0, 5.85))

    ax.text(
        0.25, 0.22,
        "Req 3–4: Tableau uses the Athena JDBC driver against the Interface VPC endpoint (not the public Athena API). "
        "S3 reads/results use a Gateway endpoint. sg-tableau cannot reach 0.0.0.0/0. See ARCHITECTURE.md for JDBC, IAM, CIDRs.",
        color=MUTED, fontsize=7.0, va="bottom",
    )
    fig.tight_layout()
    path = OUT / "02-data-exploitation.png"
    fig.savefig(path, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    icons = _fetch_icons()
    print(_fetch_icons() and render_ingestion(icons))
    print(render_exploitation(icons))


if __name__ == "__main__":
    main()
