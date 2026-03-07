"""Vitalis Medical Import CLI — import medical documents.

Usage:
    python scripts/import_medical.py --file path/to/doc.pdf --category blood_test --date 2026-03-01 --title "Lipid Panel"
    python scripts/import_medical.py --file path/to/doc.pdf --category blood_test   # date=today, title from filename
    python scripts/import_medical.py --rebuild-index                                # rebuild index from folders

Categories: blood_test, doctor_visit, imaging, prescription, vaccination
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# Ensure src/ package is importable when running as a script
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root / "src"))

from vitalis.medical_store import MedicalStore  # noqa: E402
from vitalis.models import MedicalCategory  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("vitalis.import_medical")

_CATEGORY_MAP = {
    "blood_test": MedicalCategory.BLOOD_TEST,
    "doctor_visit": MedicalCategory.DOCTOR_VISIT,
    "imaging": MedicalCategory.IMAGING,
    "prescription": MedicalCategory.PRESCRIPTION,
    "vaccination": MedicalCategory.VACCINATION,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(
        description="Import medical documents into Vitalis.",
    )
    p.add_argument(
        "--file",
        type=Path,
        help="Path to the document to import.",
    )
    p.add_argument(
        "--category",
        choices=list(_CATEGORY_MAP.keys()),
        help="Document category.",
    )
    p.add_argument(
        "--date",
        dest="record_date",
        type=date.fromisoformat,
        default=None,
        help="Record date (YYYY-MM-DD). Defaults to today.",
    )
    p.add_argument(
        "--title",
        default=None,
        help="Document title. Defaults to filename without extension.",
    )
    p.add_argument(
        "--language",
        choices=["he", "en", "auto"],
        default="auto",
        help="Document language (default: auto-detect).",
    )
    p.add_argument(
        "--tags",
        nargs="*",
        default=None,
        help="Optional tags for the record.",
    )
    p.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Rebuild the master index from folder structure.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the import CLI."""
    args = parse_args(argv)
    store = MedicalStore()

    if args.rebuild_index:
        index = store.rebuild_index()
        logger.info("Index rebuilt: %d records", len(index.records))
        return

    if not args.file:
        logger.error("--file is required (or use --rebuild-index)")
        sys.exit(1)

    if not args.file.exists():
        logger.error("File not found: %s", args.file)
        sys.exit(1)

    if not args.category:
        logger.error("--category is required")
        sys.exit(1)

    record_date = args.record_date or date.today()
    title = args.title or args.file.stem.replace("_", " ").replace("-", " ")
    category = _CATEGORY_MAP[args.category]

    record = store.import_document(
        file_path=args.file,
        category=category,
        date_=record_date,
        title=title,
        language=args.language,
        tags=args.tags,
    )

    logger.info("Imported: %s", record.title)
    logger.info("  Category:  %s", record.category.value)
    logger.info("  Date:      %s", record.date)
    logger.info("  Language:  %s", record.language)
    logger.info("  Source:    %s", record.source_file)
    if record.extracted_text:
        preview = record.extracted_text[:100].replace("\n", " ")
        logger.info("  Preview:   %s...", preview)


if __name__ == "__main__":
    main()
