#!/usr/bin/env python3
"""Download Chicago COPA (Civilian Office of Police Accountability) case
documents for closed police shooting cases.

Fetches case metadata from the Chicago SODA API, scrapes the COPA case portal
for PDF links, downloads PDFs, and extracts text via pdfplumber.

Usage:
    python scripts/scrape_copa.py --dry-run --max-cases 5
    python scripts/scrape_copa.py --max-cases 10
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pdfplumber
from bs4 import BeautifulSoup
from loguru import logger

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

RAW_DIR = project_root / "data" / "copa_raw"
EXTRACTED_DIR = project_root / "data" / "copa_extracted"

# ---------------------------------------------------------------------------
# SODA API endpoint — closed police shooting cases
# ---------------------------------------------------------------------------
SODA_BASE_URL = "https://data.cityofchicago.org/resource/mft5-nfa8.json"
SODA_PARAMS = {
    "$select": "log_no,complaint_date,case_type,current_status,current_category,police_shooting",
    "$where": "police_shooting='Yes' AND current_status='Closed'",
    "$order": "complaint_date DESC",
}

# Very recent cases (< ~1 year old) rarely have documents posted.
# Default to a date range known to have full document packages.
DEFAULT_BEFORE_DATE = "2024-01-01"

CASE_PORTAL_URL = "https://www.chicagocopa.org/case/{log_no}/"

HEADERS = {
    "User-Agent": "CROSSFIRE-Research/1.0 (academic research)",
}

# Rate limits (seconds)
PAGE_FETCH_DELAY = 2.0
DOWNLOAD_DELAY = 1.5


# ---------------------------------------------------------------------------
# Document type classification
# ---------------------------------------------------------------------------
def classify_copa(filename: str) -> str:
    """Classify a COPA document by its filename into a document type."""
    lower = filename.lower()
    if "fsr" in lower or "final_summary" in lower or "final-summary" in lower:
        return "final_summary_report"
    if "trr" in lower or "tactical" in lower:
        return "tactical_response_report"
    if "ocir" in lower or "case-incident" in lower or "original-case" in lower:
        return "case_incident_report"
    if "arrest" in lower:
        return "arrest_report"
    if "concur" in lower:
        return "superintendent_concurrence"
    return "document"


# ---------------------------------------------------------------------------
# SODA API
# ---------------------------------------------------------------------------
def _build_soda_url(max_cases: int, before_date: str | None = None) -> str:
    """Build the SODA API URL with raw query params ($ must not be encoded)."""
    from urllib.parse import quote

    params = dict(SODA_PARAMS)
    if before_date:
        params["$where"] += f" AND complaint_date<'{before_date}'"

    safe_chars = "=',() <>"
    parts = []
    for k, v in params.items():
        parts.append(f"{k}={quote(v, safe=safe_chars)}")
    parts.append(f"$limit={max_cases}")
    return SODA_BASE_URL + "?" + "&".join(parts)


def fetch_case_list(
    client: httpx.Client, max_cases: int, before_date: str | None = None
) -> list[dict]:
    """Fetch closed police shooting cases from SODA API."""
    url = _build_soda_url(max_cases, before_date)
    logger.info(f"Fetching case list from SODA API (limit={max_cases})...")

    for attempt in range(1, 4):
        try:
            resp = client.get(url, timeout=30)
            resp.raise_for_status()
            cases = resp.json()
            logger.info(f"SODA API returned {len(cases)} cases")
            return cases
        except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            logger.warning(f"SODA request timed out (attempt {attempt}/3): {e}")
            if attempt == 3:
                raise
            time.sleep(3)
        except httpx.HTTPStatusError as e:
            logger.error(f"SODA API error: HTTP {e.response.status_code}")
            raise

    return []


# ---------------------------------------------------------------------------
# Case portal scraping
# ---------------------------------------------------------------------------
def scrape_pdf_links(client: httpx.Client, log_no: str) -> list[str]:
    """Scrape the COPA case portal page for PDF download links.

    Returns a list of absolute PDF URLs.
    """
    url = CASE_PORTAL_URL.format(log_no=log_no)
    logger.info(f"Scraping case portal: {url}")

    try:
        resp = client.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"Case page 404 for {log_no} — no documents posted")
        else:
            logger.warning(f"HTTP {e.response.status_code} for case {log_no}")
        return []
    except httpx.RequestError as e:
        logger.warning(f"Request error for case {log_no}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdf_links: list[str] = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "wp-content/uploads" in href and href.lower().endswith(".pdf"):
            # Skip site-wide boilerplate links (consent decree, ordinance)
            if "chicagopoliceconsentdecree.org" in href:
                continue
            # Ensure absolute URL
            if href.startswith("/"):
                href = f"https://www.chicagocopa.org{href}"
            elif not href.startswith("http"):
                href = f"https://www.chicagocopa.org/{href}"
            pdf_links.append(href)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_links: list[str] = []
    for link in pdf_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    logger.info(f"  Found {len(unique_links)} PDF links for case {log_no}")
    return unique_links


# ---------------------------------------------------------------------------
# Download & extraction
# ---------------------------------------------------------------------------
def _safe_filename(url: str) -> str:
    """Extract and sanitize a filename from a URL."""
    raw_name = url.split("/")[-1].split("?")[0]
    # Replace URL-encoded chars
    raw_name = raw_name.replace("%20", "_")
    # Keep only safe chars
    name = re.sub(r"[^A-Za-z0-9._\-]", "_", raw_name)
    return name


def download_pdf(
    client: httpx.Client, url: str, raw_dir: Path
) -> Path | None:
    """Download a single PDF. Returns the local path or None."""
    filename = _safe_filename(url)
    local_path = raw_dir / filename

    if local_path.exists() and local_path.stat().st_size > 1000:
        logger.debug(f"  Already exists: {filename}")
        return local_path

    try:
        resp = client.get(url, timeout=60, follow_redirects=True)
        resp.raise_for_status()

        if not resp.content or len(resp.content) < 500:
            logger.warning(
                f"  Response too small ({len(resp.content)} bytes), skipping: {filename}"
            )
            return None

        if not resp.content[:5].startswith(b"%PDF"):
            logger.warning(
                f"  Not a PDF (starts with {resp.content[:20]!r}), skipping: {filename}"
            )
            return None

        local_path.write_bytes(resp.content)
        logger.info(f"  Downloaded: {filename} ({len(resp.content):,} bytes)")
        return local_path

    except httpx.HTTPStatusError as e:
        logger.warning(f"  HTTP {e.response.status_code} for {filename}")
        return None
    except httpx.RequestError as e:
        logger.warning(f"  Request error for {filename}: {e}")
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
    out_dir: Path, documents: list[dict], case_info: dict
) -> None:
    """Write _extraction_meta.json for a case directory."""
    meta = {
        "source": "chicago_copa",
        "log_no": case_info.get("log_no", "unknown"),
        "complaint_date": case_info.get("complaint_date", ""),
        "case_type": case_info.get("case_type", ""),
        "current_category": case_info.get("current_category", ""),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "documents": documents,
    }
    meta_path = out_dir / "_extraction_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)
    logger.info(f"  Wrote metadata: {meta_path.name}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def run(max_cases: int, dry_run: bool, before_date: str | None = None) -> None:
    """Main pipeline: fetch case list, scrape PDF links, download, extract."""
    with httpx.Client(headers=HEADERS) as client:
        cases = fetch_case_list(client, max_cases, before_date)

        if not cases:
            logger.warning("No cases returned from SODA API")
            return

        if dry_run:
            logger.info("=== DRY RUN — listing cases and PDF links ===")
            for i, case in enumerate(cases):
                log_no = case.get("log_no", "unknown")
                complaint_date = case.get("complaint_date", "N/A")
                category = case.get("current_category", "N/A")
                logger.info(
                    f"\n  [{i + 1}/{len(cases)}] Case {log_no} "
                    f"(filed {complaint_date[:10] if complaint_date else 'N/A'}, "
                    f"category: {category})"
                )
                time.sleep(PAGE_FETCH_DELAY)
                pdf_links = scrape_pdf_links(client, log_no)
                for link in pdf_links:
                    filename = _safe_filename(link)
                    doc_type = classify_copa(filename)
                    logger.info(f"    [{doc_type}] {filename}")

            logger.info(f"\nTotal: {len(cases)} cases listed")
            return

        # Download and extract
        total_downloaded = 0
        total_extracted = 0

        for i, case in enumerate(cases):
            log_no = case.get("log_no", "unknown")
            complaint_date = case.get("complaint_date", "N/A")
            logger.info(
                f"\n[{i + 1}/{len(cases)}] Processing case {log_no} "
                f"(filed {complaint_date[:10] if complaint_date else 'N/A'})"
            )

            # Rate limit between page fetches
            if i > 0:
                time.sleep(PAGE_FETCH_DELAY)

            pdf_links = scrape_pdf_links(client, log_no)
            if not pdf_links:
                logger.info(f"  No PDFs found for case {log_no}, skipping")
                continue

            # Create case directories
            raw_case_dir = RAW_DIR / log_no
            ext_case_dir = EXTRACTED_DIR / log_no
            raw_case_dir.mkdir(parents=True, exist_ok=True)
            ext_case_dir.mkdir(parents=True, exist_ok=True)

            doc_metas: list[dict] = []
            case_downloaded = 0

            for j, pdf_url in enumerate(pdf_links):
                # Rate limit between downloads
                if j > 0:
                    time.sleep(DOWNLOAD_DELAY)

                pdf_path = download_pdf(client, pdf_url, raw_case_dir)
                if pdf_path is None:
                    continue

                case_downloaded += 1
                total_downloaded += 1

                # Extract text
                txt_name = pdf_path.stem + ".txt"
                txt_path = ext_case_dir / txt_name
                word_count = extract_text(pdf_path, txt_path)

                if word_count > 0:
                    total_extracted += 1

                doc_type = classify_copa(pdf_path.name)
                title = pdf_path.stem.replace("_", " ").replace("-", " ")

                doc_metas.append({
                    "item_number": case_downloaded,
                    "title": title,
                    "filename": txt_name,
                    "document_type": doc_type,
                    "word_count": word_count,
                    "source_pdf": pdf_path.name,
                    "source_url": pdf_url,
                })

            if doc_metas:
                write_extraction_meta(ext_case_dir, doc_metas, case)

            logger.info(
                f"  Case {log_no}: {case_downloaded}/{len(pdf_links)} "
                f"downloaded & extracted"
            )

        logger.info(
            f"\nPipeline complete: {total_downloaded} PDFs downloaded, "
            f"{total_extracted} texts extracted across {len(cases)} cases"
        )


def main() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level:<7} | {message}",
    )

    parser = argparse.ArgumentParser(
        description="Download Chicago COPA closed police shooting case documents."
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=10,
        help="Maximum number of cases to process (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List cases and PDF links without downloading",
    )
    parser.add_argument(
        "--before",
        type=str,
        default=DEFAULT_BEFORE_DATE,
        help=(
            f"Only fetch cases filed before this date (YYYY-MM-DD). "
            f"Recent cases rarely have documents posted. (default: {DEFAULT_BEFORE_DATE})"
        ),
    )
    args = parser.parse_args()

    logger.info("Chicago COPA — Case Document Scraper")
    logger.info(f"Max cases: {args.max_cases} | Before: {args.before} | Dry run: {args.dry_run}")

    run(max_cases=args.max_cases, dry_run=args.dry_run, before_date=args.before)
    logger.info("Done.")


if __name__ == "__main__":
    main()
