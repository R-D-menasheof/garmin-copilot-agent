"""Copy existing global blobs into per-user scope (``users/{owner_id}/...``).

This is the one-time multi-user migration. It is deliberately conservative:

SAFETY GUARANTEES
- **Copy-only.** Originals are never moved or deleted — this script has no
  delete capability whatsoever.
- **Dry-run by default.** You must pass ``--apply`` to write anything.
- **Verify.** Each copy is read back and compared to the source.
- **Idempotent / non-clobber.** A target that already exists is skipped, so a
  re-run never overwrites newer per-user data.
- **Food cache stays global.** ``food_cache/`` is shared across users and is
  left exactly where it is.

Usage::

    # Preview (writes nothing):
    python scripts/migrate_to_multiuser.py --owner-id roei

    # Actually copy (after reviewing the preview):
    python scripts/migrate_to_multiuser.py --owner-id roei --apply

The Azure connection string is read from ``AZURE_STORAGE_CONNECTION_STRING`` or
from ``api/local.settings.json``; it is never printed.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.migrate")

# Shared, non-personal — stays at the global path.
GLOBAL_KEEP_PREFIX = "food_cache/"
# Already migrated — never re-scope.
USER_PREFIX = "users/"


@dataclass
class MigrationReport:
    """Outcome of a migration run."""

    to_copy: list[tuple[str, str]] = field(default_factory=list)
    copied: list[tuple[str, str]] = field(default_factory=list)
    verified: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    skipped_global: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)


def _source_blobs(existing: set[str]) -> list[str]:
    """Return blob names that should be scoped to a user."""
    out = []
    for name in sorted(existing):
        if name.startswith(USER_PREFIX):
            continue
        if name.startswith(GLOBAL_KEEP_PREFIX):
            continue
        out.append(name)
    return out


def migrate_blobs(
    container,
    owner_id: str,
    dry_run: bool = True,
    verify: bool = True,
) -> MigrationReport:
    """Copy global blobs into ``users/{owner_id}/`` scope.

    Args:
        container: An Azure ``ContainerClient`` (or compatible) exposing
            ``list_blobs`` and ``get_blob_client``.
        owner_id: The user id to scope the existing data under.
        dry_run: When True (default), only report; write nothing.
        verify: When True, read each copy back and compare to the source.

    Returns:
        A :class:`MigrationReport` describing what happened.
    """
    report = MigrationReport()
    existing = {b.name for b in container.list_blobs()}
    report.skipped_global = [n for n in existing if n.startswith(GLOBAL_KEEP_PREFIX)]

    for src in _source_blobs(existing):
        dst = f"{USER_PREFIX}{owner_id}/{src}"
        report.to_copy.append((src, dst))

        if dry_run:
            continue

        if dst in existing:
            report.skipped_existing.append(dst)
            continue

        try:
            data = container.get_blob_client(src).download_blob().readall()
            # overwrite=False: extra guard — we already skip existing targets.
            container.get_blob_client(dst).upload_blob(data, overwrite=False)
            existing.add(dst)
            report.copied.append((src, dst))

            if verify:
                back = container.get_blob_client(dst).download_blob().readall()
                if back == data:
                    report.verified.append(dst)
                else:
                    report.failed.append((dst, "verify mismatch"))
        except Exception as exc:  # noqa: BLE001 — record & continue
            report.failed.append((src, str(exc)))
            logger.error("Failed to copy %s: %s", src, exc)

    return report


# ── CLI plumbing ───────────────────────────────────────────────────


def _load_connection_string() -> str:
    """Read the storage connection string from env or local.settings.json."""
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
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Copy global Vitalis blobs into per-user scope (copy-only, safe).",
    )
    parser.add_argument(
        "--owner-id",
        required=True,
        help="User id to scope existing data under (e.g. 'roei' or an Entra oid).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually copy. Without this flag the run is a dry-run preview.",
    )
    parser.add_argument(
        "--container",
        default="vitalis-data",
        help="Blob container name (default: vitalis-data).",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip the read-back verification step (not recommended).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    from azure.storage.blob import BlobServiceClient  # lazy import

    client = BlobServiceClient.from_connection_string(_load_connection_string())
    container = client.get_container_client(args.container)

    dry_run = not args.apply
    mode = "DRY-RUN (no writes)" if dry_run else "APPLY (copying)"
    logger.info("Migration %s — owner_id=%s, container=%s", mode, args.owner_id, args.container)

    report = migrate_blobs(
        container, owner_id=args.owner_id, dry_run=dry_run, verify=not args.no_verify,
    )

    logger.info("Blobs to scope under users/%s/: %d", args.owner_id, len(report.to_copy))
    for src, dst in report.to_copy:
        prefix = "WOULD COPY" if dry_run else "copied"
        logger.info("  %s  %s -> %s", prefix, src, dst)
    logger.info("Food-cache blobs left global: %d", len(report.skipped_global))

    if not dry_run:
        logger.info("Copied: %d | Verified: %d | Skipped existing: %d | Failed: %d",
                    len(report.copied), len(report.verified),
                    len(report.skipped_existing), len(report.failed))
        if report.failed:
            for name, err in report.failed:
                logger.error("  FAILED %s: %s", name, err)
            return 1
    else:
        logger.info("Dry-run complete. Re-run with --apply to copy. Originals are never touched.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
