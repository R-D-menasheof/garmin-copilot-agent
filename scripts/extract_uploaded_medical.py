"""Download a user's in-app medical uploads for owner-side extraction (Phase 6.3).

Usage:
    python scripts/extract_uploaded_medical.py --user-id <oid>
    python scripts/extract_uploaded_medical.py --user-id <oid> --all
    python scripts/extract_uploaded_medical.py --user-id <oid> --mark-extracted <upload_id>

The mobile app lets users upload raw medical documents (PDF/image) into their
cloud area. This owner-operated script downloads those files locally so the
owner's Copilot/agent can read and extract them (build lab-trends, timeline
events, etc.) using its local tools — consistent with the agent-first model
where lab-trend authoring is an agent task, not automated parsing.

After the agent has processed a document and pushed its lab-trends, mark it
done with ``--mark-extracted <upload_id>`` so it is not re-downloaded.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _users import get_store

# Owner-side local staging area for a user's downloaded documents.
_DEFAULT_DEST = Path(__file__).resolve().parents[1] / "data" / "users"


def download_pending_uploads(store, dest_dir: Path | str, only_pending: bool = True) -> list[dict]:
    """Download a user's uploaded medical documents to a local directory.

    Args:
        store: A ``BlobStore`` scoped to the target user.
        dest_dir: Local directory to write the raw files into.
        only_pending: When True (default), skip uploads already marked extracted.

    Returns:
        A list of dicts: ``{id, filename, local_path, extracted}`` for each
        document written.
    """
    dest = Path(dest_dir)
    results: list[dict] = []
    for upload in store.load_medical_uploads():
        if only_pending and upload.extracted:
            continue
        content = store.load_medical_upload_content(upload.id)
        if content is None:
            continue
        dest.mkdir(parents=True, exist_ok=True)
        local_path = dest / f"{upload.id}_{upload.filename}"
        local_path.write_bytes(content)
        results.append(
            {
                "id": upload.id,
                "filename": upload.filename,
                "local_path": str(local_path),
                "extracted": upload.extracted,
            }
        )
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Download a user's in-app medical uploads for local extraction.",
    )
    parser.add_argument("--user-id", required=True, help="Target user's oid.")
    parser.add_argument(
        "--dest",
        default=None,
        help="Local destination dir. Defaults to data/users/<user-id>/medical/uploads/.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include already-extracted uploads (default: pending only).",
    )
    parser.add_argument(
        "--mark-extracted",
        metavar="UPLOAD_ID",
        default=None,
        help="Mark an upload as extracted (after the agent processed it).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(argv)
    store = get_store(args.user_id)

    if args.mark_extracted:
        store.mark_medical_upload_extracted(args.mark_extracted)
        print(f"Marked upload {args.mark_extracted} as extracted.")
        return 0

    dest = Path(args.dest) if args.dest else _DEFAULT_DEST / args.user_id / "medical" / "uploads"
    downloaded = download_pending_uploads(store, dest, only_pending=not args.all)

    if not downloaded:
        print("No documents to download.")
        return 0

    print(f"Downloaded {len(downloaded)} document(s) to {dest}:")
    for doc in downloaded:
        print(f"  - {doc['filename']}  ({doc['id']})  -> {doc['local_path']}")
    print("\nExtract them with your local tools, push lab-trends, then run")
    print("--mark-extracted <upload_id> for each processed document.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
