"""Download every blob in the Vitalis container to a local folder.

A read-only safety snapshot to run BEFORE any migration. Downloads only —
it never writes to or deletes from the cloud.

Usage::

    python scripts/backup_cloud.py
    python scripts/backup_cloud.py --dest data/cloud-backup-2026-07-03

The backup lands under ``data/`` (gitignored) by default. The Azure connection
string is read from ``AZURE_STORAGE_CONNECTION_STRING`` or
``api/local.settings.json`` and is never printed.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.backup")


@dataclass
class BackupReport:
    """Outcome of a backup run."""

    count: int = 0
    names: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


def backup_container(container, dest_dir) -> BackupReport:
    """Download every blob to ``dest_dir``, preserving blob paths.

    Args:
        container: An Azure ``ContainerClient`` (or compatible).
        dest_dir: Local destination directory (created if missing).

    Returns:
        A :class:`BackupReport`.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    report = BackupReport()

    for blob in container.list_blobs():
        name = blob.name
        try:
            data = container.get_blob_client(name).download_blob().readall()
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data if isinstance(data, bytes) else str(data).encode())
            report.count += 1
            report.names.append(name)
        except Exception as exc:  # noqa: BLE001 — record & continue
            report.failed.append((name, str(exc)))
            logger.error("Failed to back up %s: %s", name, exc)

    return report


# ── CLI plumbing ───────────────────────────────────────────────────


def _load_connection_string() -> str:
    conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
    if conn:
        return conn
    settings = Path(__file__).resolve().parents[1] / "api" / "local.settings.json"
    if settings.exists():
        data = json.loads(settings.read_text(encoding="utf-8"))
        conn = data.get("Values", {}).get("AZURE_STORAGE_CONNECTION_STRING", "")
    if not conn:
        raise SystemExit(
            "No storage connection string found. Set AZURE_STORAGE_CONNECTION_STRING "
            "or populate api/local.settings.json."
        )
    return conn


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download all Vitalis cloud blobs to a local folder (safety snapshot).",
    )
    default_dest = f"data/cloud-backup-{datetime.now():%Y-%m-%d_%H%M%S}"
    parser.add_argument(
        "--dest",
        default=default_dest,
        help=f"Destination folder (default: {default_dest}).",
    )
    parser.add_argument(
        "--container",
        default="vitalis-data",
        help="Blob container name (default: vitalis-data).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from azure.storage.blob import BlobServiceClient  # lazy import

    client = BlobServiceClient.from_connection_string(_load_connection_string())
    container = client.get_container_client(args.container)

    logger.info("Backing up container '%s' -> %s", args.container, args.dest)
    report = backup_container(container, args.dest)
    logger.info("Backed up %d blobs. Failed: %d", report.count, len(report.failed))
    if report.failed:
        for name, err in report.failed:
            logger.error("  FAILED %s: %s", name, err)
        return 1
    logger.info("Backup complete. Cloud was not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
