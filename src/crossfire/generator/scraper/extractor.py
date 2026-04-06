"""Extract text from PDF documents and assess quality."""

import json
import string
from pathlib import Path

import pdfplumber
from loguru import logger

from .config import QualityThresholds, ScraperConfig
from .models import DocketManifest, ExtractionQuality, ExtractedDocument


def assess_quality(text: str, thresholds: QualityThresholds) -> ExtractionQuality:
    """Assess the quality of extracted text."""
    if not text or not text.strip():
        return ExtractionQuality(char_ratio=0.0, avg_word_length=0.0, word_count=0, line_count=0, passed=False)

    printable = set(string.printable)
    char_ratio = sum(1 for c in text if c in printable) / len(text) if text else 0.0

    words = text.split()
    word_count = len(words)
    avg_word_length = sum(len(w) for w in words) / word_count if word_count > 0 else 0.0
    line_count = text.count("\n") + 1

    passed = (
        char_ratio >= thresholds.min_char_ratio
        and word_count >= thresholds.min_word_count
        and thresholds.min_avg_word_length <= avg_word_length <= thresholds.max_avg_word_length
    )

    return ExtractionQuality(
        char_ratio=round(char_ratio, 4),
        avg_word_length=round(avg_word_length, 2),
        word_count=word_count,
        line_count=line_count,
        passed=passed,
    )


def extract_text_from_pdf(pdf_path: Path) -> tuple[str | None, str | None]:
    """Extract text from a PDF file. Returns (text, error)."""
    try:
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages.append(page_text)
        if not pages:
            return None, f"No text extracted from {pdf_path.name}"
        return "\n\n".join(pages), None
    except Exception as e:
        return None, f"PDF extraction failed for {pdf_path.name}: {e}"


def extract_docket_documents(
    manifest: DocketManifest,
    config: ScraperConfig,
) -> list[ExtractedDocument]:
    """Extract text from all downloaded PDFs for a docket.

    Returns list of ExtractedDocument with quality metrics.
    """
    raw_dir = config.raw_dir / manifest.ntsb_id
    extracted_dir = config.extracted_dir / manifest.ntsb_id
    extracted_dir.mkdir(parents=True, exist_ok=True)

    # Build lookup from item number to document entry
    doc_lookup = {d.item_number: d for d in manifest.documents}

    # Find all downloaded PDFs
    pdf_files = sorted(raw_dir.glob("*.pdf")) if raw_dir.exists() else []
    if not pdf_files:
        logger.warning(f"No PDF files found in {raw_dir}")
        return []

    results = []
    clean_count = 0

    for pdf_path in pdf_files:
        # Parse item number from filename (e.g., "001_TITLE.pdf" → 1)
        item_num = _parse_item_number(pdf_path.name)
        doc_entry = doc_lookup.get(item_num)
        title = doc_entry.title if doc_entry else pdf_path.stem
        group = doc_entry.group if doc_entry else ""

        text, error = extract_text_from_pdf(pdf_path)
        if error:
            logger.warning(f"  {manifest.ntsb_id}/{pdf_path.name}: {error}")
            results.append(
                ExtractedDocument(
                    ntsb_id=manifest.ntsb_id,
                    item_number=item_num,
                    title=title,
                    file_type="pdf",
                    group=group,
                )
            )
            continue

        quality = assess_quality(text, config.quality)

        if quality.passed:
            clean_count += 1
            # Save extracted text
            text_path = extracted_dir / f"{pdf_path.stem}.txt"
            text_path.write_text(text, encoding="utf-8")

        results.append(
            ExtractedDocument(
                ntsb_id=manifest.ntsb_id,
                item_number=item_num,
                title=title,
                file_type="pdf",
                text=text,
                quality=quality,
                group=group,
            )
        )

    total = len(results)
    rate = clean_count / total if total > 0 else 0.0
    logger.info(
        f"Docket {manifest.ntsb_id} — extracted {total} docs, "
        f"{clean_count} clean ({rate:.0%})"
    )

    # Save extraction metadata
    meta_path = extracted_dir / "_extraction_meta.json"
    meta = {
        "ntsb_id": manifest.ntsb_id,
        "total_pdfs": total,
        "clean_count": clean_count,
        "clean_rate": round(rate, 4),
        "documents": [
            {
                "item_number": d.item_number,
                "title": d.title,
                "word_count": d.quality.word_count if d.quality else 0,
                "passed": d.quality.passed if d.quality else False,
            }
            for d in results
        ],
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return results


def _parse_item_number(filename: str) -> int:
    """Parse item number from filename like '001_TITLE.pdf'."""
    parts = filename.split("_", 1)
    try:
        return int(parts[0])
    except (ValueError, IndexError):
        return 0
