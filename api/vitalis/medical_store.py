"""Medical store — SSOT for importing and managing medical records.

Stores medical documents (PDFs, HTML reports, plain text) in category
subfolders under ``data/medical/``. Each document gets a subfolder named
``YYYY-MM-DD_slug/`` containing the original file, an ``extracted.json``
sidecar with extracted text and metadata, and an optional ``notes.md``.

A master ``index.json`` tracks all imported records and can be rebuilt
at any time from the folder structure.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_BASE = _PROJECT_ROOT / "data" / "medical"
_TESSDATA_DIR = _PROJECT_ROOT / "data" / ".tessdata"

# Hebrew Unicode range for language detection
_HEBREW_RANGE = re.compile(r"[\u0590-\u05FF]")


class MedicalStore:
    """Import, store, and query medical documents."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir else _DEFAULT_BASE
        self._base.mkdir(parents=True, exist_ok=True)

    # ── Import ─────────────────────────────────────────────────────────

    def import_document(
        self,
        file_path: str | Path,
        category: "MedicalCategory",
        date_: date,
        title: str,
        language: str = "auto",
        tags: list[str] | None = None,
        notes: str = "",
    ) -> "MedicalRecord":
        """Import a medical document into the store.

        Copies the original file, extracts text (for supported formats),
        writes a sidecar ``extracted.json``, and updates the master index.

        Args:
            file_path: Path to the source document.
            category: Medical category (blood_test, doctor_visit, etc.).
            date_: Date of the medical record.
            title: Human-readable title.
            language: Language code ('he', 'en') or 'auto' for detection.
            tags: Optional tags for categorisation.
            notes: Optional free-text notes.

        Returns:
            The created MedicalRecord.
        """
        from vitalis.models import MedicalRecord

        src = Path(file_path)
        slug = self._slugify(title)
        folder_name = f"{date_.isoformat()}_{slug}"
        folder = self._base / category.value / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        # Copy original file
        dest = folder / f"original{src.suffix.lower()}"
        shutil.copy2(src, dest)

        # Extract text
        extracted_text = self._extract_text(dest)

        # Detect language
        if language == "auto":
            language = self._detect_language(extracted_text)

        # Build relative source path (relative to data/medical/)
        source_file = f"{category.value}/{folder_name}/original{src.suffix.lower()}"

        record = MedicalRecord(
            category=category,
            date=date_,
            title=title,
            language=language,
            source_file=source_file,
            extracted_text=extracted_text,
            tags=tags or [],
            notes=notes,
        )

        # Write extracted.json sidecar
        self._write_extracted_json(folder, record)

        # Update index
        self._update_index(record)

        logger.info(
            "Imported %s → %s/%s",
            src.name, category.value, folder_name,
        )
        return record

    # ── Read ───────────────────────────────────────────────────────────

    def list_records(
        self,
        category: "MedicalCategory | None" = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list["MedicalRecord"]:
        """List medical records, optionally filtered.

        Args:
            category: Filter by category.
            start_date: Include records on or after this date.
            end_date: Include records on or before this date.

        Returns:
            List of matching MedicalRecord objects.
        """
        index = self.load_index()
        records = index.records

        if category is not None:
            records = [r for r in records if r.category == category]
        if start_date is not None:
            records = [r for r in records if r.date >= start_date]
        if end_date is not None:
            records = [r for r in records if r.date <= end_date]

        return records

    def load_record(
        self,
        category: "MedicalCategory",
        folder_name: str,
    ) -> "MedicalRecord | None":
        """Load a single record from its extracted.json sidecar.

        Args:
            category: The record's category.
            folder_name: The date-slug folder name (e.g. '2026-03-01_cbc').

        Returns:
            MedicalRecord or None if not found.
        """
        from vitalis.models import MedicalRecord

        folder = self._base / category.value / folder_name
        extracted_path = folder / "extracted.json"
        if not extracted_path.exists():
            return None

        data = self._read_json(extracted_path)
        if data is None:
            return None

        return MedicalRecord.model_validate(data)

    def get_extracted_text(
        self,
        category: "MedicalCategory",
        folder_name: str,
    ) -> str:
        """Get the extracted text for a specific record.

        Returns:
            Extracted text string, or empty string if not found.
        """
        record = self.load_record(category, folder_name)
        return record.extracted_text if record else ""

    def load_index(self) -> "MedicalIndex":
        """Load the master index.

        Returns:
            MedicalIndex with all tracked records.
        """
        from vitalis.models import MedicalIndex

        index_path = self._base / "index.json"
        if not index_path.exists():
            return MedicalIndex()

        data = self._read_json(index_path)
        if data is None:
            return MedicalIndex()

        return MedicalIndex.model_validate(data)

    # ── Search ─────────────────────────────────────────────────────────

    def search_records(self, query: str) -> list["MedicalRecord"]:
        """Search records by text content (case-insensitive).

        Args:
            query: Text to search for in extracted text.

        Returns:
            List of matching MedicalRecord objects.
        """
        index = self.load_index()
        query_lower = query.lower()
        return [
            r for r in index.records
            if query_lower in r.extracted_text.lower()
        ]

    # ── Index Management ───────────────────────────────────────────────

    def rebuild_index(self) -> "MedicalIndex":
        """Rebuild the master index by scanning all category folders.

        Returns:
            The rebuilt MedicalIndex.
        """
        from vitalis.models import MedicalCategory, MedicalIndex, MedicalRecord

        records: list[MedicalRecord] = []

        for cat in MedicalCategory:
            cat_dir = self._base / cat.value
            if not cat_dir.exists():
                continue
            for folder in sorted(cat_dir.iterdir()):
                if not folder.is_dir() or folder.name.startswith("."):
                    continue
                extracted_path = folder / "extracted.json"
                if not extracted_path.exists():
                    continue
                data = self._read_json(extracted_path)
                if data is not None:
                    records.append(MedicalRecord.model_validate(data))

        index = MedicalIndex(
            records=records,
            last_updated=datetime.now().isoformat(),
        )
        self._write_json(self._base / "index.json", index.model_dump(mode="json"))
        logger.info("Rebuilt index: %d records", len(records))
        return index

    # ── Text Extraction ────────────────────────────────────────────────

    def _extract_text(self, path: Path) -> str:
        """Extract text from a document based on file extension.

        Supported: .pdf (PyMuPDF), .html/.htm (BeautifulSoup), .txt/.md (direct).
        Images (.jpg, .png, etc.) return empty string.
        """
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(path)
        elif suffix in (".html", ".htm"):
            return self._extract_html(path)
        elif suffix in (".txt", ".md"):
            return path.read_text(encoding="utf-8")
        else:
            # Images and other binary formats — no extraction
            return ""

    @staticmethod
    def _extract_pdf(path: Path) -> str:
        """Extract text from a PDF using PyMuPDF, with OCR fallback.

        If PyMuPDF finds no text (vector/scanned PDFs), renders pages
        to images and runs Tesseract OCR with Hebrew + English.
        """
        import fitz

        text_parts: list[str] = []
        with fitz.open(str(path)) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        text = "\n".join(text_parts).strip()

        # If we got meaningful text, return it
        if len(text) > 20:
            return text

        # Fallback: OCR via Tesseract
        return MedicalStore._ocr_pdf(path)

    @staticmethod
    def _ocr_pdf(path: Path) -> str:
        """OCR a PDF by rendering pages to images and running Tesseract."""
        try:
            import fitz
            import pytesseract
            from PIL import Image
            import io
        except ImportError as exc:
            logger.warning("OCR dependencies not available: %s", exc)
            return ""

        # Configure Tesseract path on Windows
        tesseract_path = Path("C:/Program Files/Tesseract-OCR/tesseract.exe")
        if tesseract_path.exists():
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)

        # Set tessdata directory if local one exists
        env = None
        if _TESSDATA_DIR.exists():
            env = {"TESSDATA_PREFIX": str(_TESSDATA_DIR)}

        # Determine available languages
        lang = "eng"
        heb_file = _TESSDATA_DIR / "heb.traineddata" if _TESSDATA_DIR.exists() else None
        if heb_file and heb_file.exists():
            lang = "heb+eng"

        import os
        old_env = os.environ.get("TESSDATA_PREFIX")
        if env:
            os.environ["TESSDATA_PREFIX"] = env["TESSDATA_PREFIX"]

        try:
            text_parts: list[str] = []
            with fitz.open(str(path)) as doc:
                for page in doc:
                    # Render page at 300 DPI for good OCR quality
                    pix = page.get_pixmap(dpi=300)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    page_text = pytesseract.image_to_string(img, lang=lang)
                    text_parts.append(page_text)
        finally:
            if old_env is not None:
                os.environ["TESSDATA_PREFIX"] = old_env
            elif "TESSDATA_PREFIX" in os.environ:
                del os.environ["TESSDATA_PREFIX"]

        result = "\n".join(text_parts).strip()
        if result:
            logger.info("OCR extracted %d chars from %s", len(result), path.name)
        return result

    @staticmethod
    def _extract_html(path: Path) -> str:
        """Extract text from HTML using BeautifulSoup."""
        from bs4 import BeautifulSoup

        html = path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator="\n").strip()

    # ── Language Detection ─────────────────────────────────────────────

    @staticmethod
    def _detect_language(text: str) -> str:
        """Detect document language using Hebrew Unicode range heuristic.

        Returns 'he' if significant Hebrew characters found, else 'en'.
        """
        if not text:
            return "en"
        hebrew_chars = len(_HEBREW_RANGE.findall(text))
        # If more than 5% of non-whitespace chars are Hebrew, classify as Hebrew
        non_ws = len(re.sub(r"\s", "", text))
        if non_ws > 0 and hebrew_chars / non_ws > 0.05:
            return "he"
        return "en"

    # ── Slug Generation ────────────────────────────────────────────────

    @staticmethod
    def _slugify(title: str) -> str:
        """Convert a title to a filesystem-safe slug.

        Preserves Hebrew characters. Lowercases ASCII, replaces spaces
        and special chars with hyphens, collapses multiple hyphens.
        """
        # Lowercase ASCII only, keep Hebrew and other Unicode letters
        slug = ""
        for ch in title:
            if ch.isascii():
                slug += ch.lower()
            else:
                slug += ch
        # Replace non-alphanumeric (preserving Unicode letters) with hyphens
        slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        slug = slug.strip("-")
        return slug

    # ── Index Helpers ──────────────────────────────────────────────────

    def _update_index(self, record: "MedicalRecord") -> None:
        """Add or update a record in the master index."""
        index = self.load_index()

        # Remove existing record with same source_file (overwrite)
        index.records = [
            r for r in index.records
            if r.source_file != record.source_file
        ]
        index.records.append(record)
        index.last_updated = datetime.now().isoformat()

        self._write_json(
            self._base / "index.json",
            index.model_dump(mode="json"),
        )

    def _write_extracted_json(self, folder: Path, record: "MedicalRecord") -> None:
        """Write extracted.json sidecar to a record folder."""
        self._write_json(
            folder / "extracted.json",
            record.model_dump(mode="json"),
        )

    # ── File I/O ───────────────────────────────────────────────────────

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.write_text(
            json.dumps(data, default=str, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Could not read %s: %s", path, exc)
            return None
