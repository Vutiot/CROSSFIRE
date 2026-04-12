#!/usr/bin/env python3
"""Download Grenfell Tower Inquiry Phase 2 hearing transcripts from the
Internet Archive Wayback Machine, extract text via pdfplumber, and organize
by inquiry module.

Usage:
    python scripts/scrape_grenfell.py --dry-run
    python scripts/scrape_grenfell.py --modules 1 --max-per-module 15
    python scripts/scrape_grenfell.py --modules 1,2 --max-per-module 10
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import httpx
import pdfplumber
from loguru import logger

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

RAW_DIR = project_root / "data" / "grenfell_raw"
EXTRACTED_DIR = project_root / "data" / "grenfell_extracted"

# ---------------------------------------------------------------------------
# CDX API endpoint
# ---------------------------------------------------------------------------
CDX_URL = (
    "https://web.archive.org/cdx/search/cdx"
    "?url=assets.grenfelltowerinquiry.org.uk/documents/transcript/*"
    "&output=json&fl=original,timestamp"
    "&collapse=urlkey&filter=statuscode:200&limit=5000"
)

WAYBACK_TEMPLATE = "https://web.archive.org/web/{timestamp}id_/{original}"

# ---------------------------------------------------------------------------
# Phase 2 module definitions (approximate date ranges)
# ---------------------------------------------------------------------------
MODULE_DEFS: dict[int, dict] = {
    1: {
        "slug": "module_1_cladding",
        "topic": "Refurbishment & cladding",
        "start": date(2020, 1, 1),
        "end": date(2020, 10, 31),
    },
    2: {
        "slug": "module_2_testing",
        "topic": "Testing & certification",
        "start": date(2020, 11, 1),
        "end": date(2021, 2, 28),
    },
    3: {
        "slug": "module_3_management",
        "topic": "Management & complaints",
        "start": date(2021, 3, 1),
        "end": date(2021, 11, 30),
    },
    6: {
        "slug": "module_6_building_regs",
        "topic": "Building regulations",
        "start": date(2021, 12, 1),
        "end": date(2022, 6, 30),
    },
}

# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------
# Matches patterns like:
#   Transcript 27 January 2020.pdf
#   Transcript 03 February 2020_0.pdf
#   Transcript - 10 March 2020.pdf
#   Trancript 5 June 2020.pdf  (typo variant)
_TRANSCRIPT_RE = re.compile(
    r"(?:Tran(?:s|)cript)\s*[-–]?\s*"
    r"(\d{1,2})\s+"
    r"([A-Za-z]+)\s+"
    r"(20(?:20|21|22))"
    r"(?:_\d+)?"
    r"\.pdf$",
    re.IGNORECASE,
)

# GTI - Day NNN.pdf pattern (late Phase 2)
_GTI_DAY_RE = re.compile(r"GTI\s*-\s*Day\s+(\d+)\.pdf$", re.IGNORECASE)

_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def _parse_transcript_date(filename: str) -> date | None:
    """Extract the hearing date from a transcript filename."""
    m = _TRANSCRIPT_RE.search(filename)
    if m:
        day, month_str, year = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month = _MONTH_MAP.get(month_str)
        if month:
            try:
                return date(year, month, day)
            except ValueError:
                return None
    return None


def _assign_module(d: date) -> int | None:
    """Return the module number for a given hearing date, or None."""
    for mod_num, mdef in MODULE_DEFS.items():
        if mdef["start"] <= d <= mdef["end"]:
            return mod_num
    return None


# ---------------------------------------------------------------------------
# CDX enumeration
# ---------------------------------------------------------------------------

def fetch_cdx_listing(client: httpx.Client) -> list[dict]:
    """Fetch the CDX listing and return deduplicated transcript entries.

    Each entry: {original, timestamp, filename, hearing_date, module}.
    """
    logger.info("Fetching CDX listing from Internet Archive...")
    for attempt in range(1, 4):
        try:
            resp = client.get(CDX_URL, timeout=90)
            resp.raise_for_status()
            break
        except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning(f"CDX request timed out (attempt {attempt}/3): {e}")
            if attempt == 3:
                raise
            time.sleep(3)
    rows = resp.json()

    if not rows or len(rows) < 2:
        logger.warning("CDX returned no results")
        return []

    # First row is header: ["original", "timestamp"]
    header = rows[0]
    assert header[0] == "original" and header[1] == "timestamp", f"Unexpected header: {header}"

    seen_urls: set[str] = set()
    entries: list[dict] = []

    for row in rows[1:]:
        original, timestamp = row[0], row[1]

        # Deduplicate by original URL
        if original in seen_urls:
            continue
        seen_urls.add(original)

        # Decode URL-encoded characters
        filename = unquote(original.split("/")[-1])

        hearing_date = _parse_transcript_date(filename)
        if hearing_date is None:
            continue

        module = _assign_module(hearing_date)
        if module is None:
            continue

        entries.append({
            "original": original,
            "timestamp": timestamp,
            "filename": filename,
            "hearing_date": hearing_date,
            "module": module,
        })

    # Sort by date within each module
    entries.sort(key=lambda e: (e["module"], e["hearing_date"]))
    return entries


# ---------------------------------------------------------------------------
# Download & extraction
# ---------------------------------------------------------------------------

def _safe_filename(filename: str) -> str:
    """Sanitize a filename: replace spaces and special chars."""
    name = filename.replace(" ", "_").replace("-", "_")
    name = re.sub(r"[^A-Za-z0-9_.]", "", name)
    return name


def download_pdf(client: httpx.Client, entry: dict, raw_dir: Path) -> Path | None:
    """Download a single PDF from Wayback. Returns the local path or None."""
    url = WAYBACK_TEMPLATE.format(
        timestamp=entry["timestamp"],
        original=entry["original"],
    )
    safe_name = _safe_filename(entry["filename"])
    local_path = raw_dir / safe_name

    if local_path.exists() and local_path.stat().st_size > 1000:
        logger.debug(f"Already exists: {safe_name}")
        return local_path

    logger.info(f"Downloading: {entry['filename']} ({entry['hearing_date']})")
    try:
        resp = client.get(url, timeout=60, follow_redirects=True)
        resp.raise_for_status()

        if not resp.content or len(resp.content) < 500:
            logger.warning(f"Response too small ({len(resp.content)} bytes), skipping: {safe_name}")
            return None

        # Verify it looks like a PDF
        if not resp.content[:5].startswith(b"%PDF"):
            logger.warning(f"Not a PDF (starts with {resp.content[:20]!r}), skipping: {safe_name}")
            return None

        local_path.write_bytes(resp.content)
        logger.info(f"  Saved: {safe_name} ({len(resp.content):,} bytes)")
        return local_path

    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP {e.response.status_code} for {safe_name}")
        return None
    except httpx.RequestError as e:
        logger.warning(f"Request error for {safe_name}: {e}")
        return None


def extract_text(pdf_path: Path, txt_path: Path) -> int:
    """Extract text from PDF via pdfplumber. Returns word count."""
    if txt_path.exists() and txt_path.stat().st_size > 0:
        text = txt_path.read_text(errors="replace")
        return len(text.split())

    try:
        pages_text: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
        full_text = "\n\n".join(pages_text)
        txt_path.write_text(full_text, encoding="utf-8")
        word_count = len(full_text.split())
        logger.info(f"  Extracted: {txt_path.name} ({word_count:,} words)")
        return word_count
    except Exception as e:
        logger.error(f"  Extraction failed for {pdf_path.name}: {e}")
        return 0


def write_extraction_meta(
    out_dir: Path, documents: list[dict], module_num: int
) -> None:
    """Write _extraction_meta.json for a module directory."""
    mdef = MODULE_DEFS[module_num]
    meta = {
        "source": "grenfell_tower_inquiry",
        "module": module_num,
        "module_topic": mdef["topic"],
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "documents": documents,
    }
    meta_path = out_dir / "_extraction_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)
    logger.info(f"Wrote metadata: {meta_path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(
    modules: list[int],
    max_per_module: int,
    dry_run: bool,
) -> None:
    """Main pipeline: enumerate, filter, download, extract."""
    headers = {
        "User-Agent": "CROSSFIRE-research/1.0 (academic; polite-crawl)",
    }

    with httpx.Client(headers=headers) as client:
        entries = fetch_cdx_listing(client)
        logger.info(f"Found {len(entries)} Phase 2 transcript entries total")

        # Group by module
        by_module: dict[int, list[dict]] = {}
        for e in entries:
            by_module.setdefault(e["module"], []).append(e)

        for mod in sorted(by_module):
            mdef = MODULE_DEFS[mod]
            count = len(by_module[mod])
            logger.info(f"  Module {mod} ({mdef['topic']}): {count} transcripts")

        # Filter to requested modules
        selected: dict[int, list[dict]] = {}
        for mod in modules:
            if mod not in by_module:
                logger.warning(f"Module {mod} has no transcripts in CDX listing")
                continue
            mod_entries = by_module[mod][:max_per_module]
            selected[mod] = mod_entries
            logger.info(
                f"Selected {len(mod_entries)} transcripts for module {mod} "
                f"(capped at {max_per_module})"
            )

        if dry_run:
            logger.info("=== DRY RUN — listing selected transcripts ===")
            for mod in sorted(selected):
                mdef = MODULE_DEFS[mod]
                logger.info(f"\nModule {mod}: {mdef['topic']}")
                for e in selected[mod]:
                    logger.info(f"  {e['hearing_date']}  {e['filename']}")
            total = sum(len(v) for v in selected.values())
            logger.info(f"\nTotal: {total} transcripts would be downloaded")
            return

        # Download and extract
        for mod in sorted(selected):
            mdef = MODULE_DEFS[mod]
            mod_slug = mdef["slug"]
            raw_mod_dir = RAW_DIR / mod_slug
            ext_mod_dir = EXTRACTED_DIR / mod_slug
            raw_mod_dir.mkdir(parents=True, exist_ok=True)
            ext_mod_dir.mkdir(parents=True, exist_ok=True)

            doc_metas: list[dict] = []
            downloaded = 0

            for i, entry in enumerate(selected[mod]):
                pdf_path = download_pdf(client, entry, raw_mod_dir)
                if pdf_path is None:
                    continue

                downloaded += 1
                safe_stem = pdf_path.stem
                txt_path = ext_mod_dir / f"{safe_stem}.txt"
                word_count = extract_text(pdf_path, txt_path)

                doc_metas.append({
                    "item_number": downloaded,
                    "title": f"Hearing Transcript - {entry['hearing_date'].isoformat()}",
                    "filename": txt_path.name,
                    "hearing_date": entry["hearing_date"].isoformat(),
                    "word_count": word_count,
                    "source_pdf": entry["filename"],
                })

                # Rate limit: 1.5s between downloads (polite to IA)
                if i < len(selected[mod]) - 1:
                    time.sleep(1.5)

            if doc_metas:
                write_extraction_meta(ext_mod_dir, doc_metas, mod)

            logger.info(
                f"Module {mod} ({mdef['topic']}): "
                f"{downloaded}/{len(selected[mod])} downloaded & extracted"
            )


def main() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level:<7} | {message}",
    )

    parser = argparse.ArgumentParser(
        description="Download Grenfell Tower Inquiry Phase 2 transcripts from Internet Archive."
    )
    parser.add_argument(
        "--modules",
        type=str,
        default="1,2",
        help="Comma-separated module numbers to download (default: 1,2)",
    )
    parser.add_argument(
        "--max-per-module",
        type=int,
        default=15,
        help="Maximum transcripts per module (default: 15)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List transcripts without downloading",
    )
    args = parser.parse_args()

    modules = [int(m.strip()) for m in args.modules.split(",")]
    for m in modules:
        if m not in MODULE_DEFS:
            logger.error(f"Unknown module {m}. Available: {sorted(MODULE_DEFS)}")
            sys.exit(1)

    logger.info("Grenfell Tower Inquiry — Transcript Scraper")
    logger.info(f"Modules: {modules} | Max per module: {args.max_per_module} | Dry run: {args.dry_run}")

    run(modules=modules, max_per_module=args.max_per_module, dry_run=args.dry_run)
    logger.info("Done.")


if __name__ == "__main__":
    main()
