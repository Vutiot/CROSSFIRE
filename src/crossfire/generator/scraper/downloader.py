"""Download documents from NTSB docket manifests."""

from pathlib import Path

from loguru import logger

from .config import ScraperConfig
from .http_client import fetch_binary
from .models import DocketManifest


def download_docket_documents(
    manifest: DocketManifest,
    config: ScraperConfig,
) -> tuple[list[Path], str | None]:
    """Download all PDF documents from a docket manifest.

    Returns (list_of_downloaded_paths, error_or_None).
    Skips non-PDF files (CSV, XLSX, video). Continues on individual download failures.
    """
    docket_dir = config.raw_dir / manifest.ntsb_id
    docket_dir.mkdir(parents=True, exist_ok=True)

    pdf_docs = [d for d in manifest.documents if d.file_type == "pdf"]
    logger.info(f"Docket {manifest.ntsb_id} — downloading {len(pdf_docs)} PDFs (skipping {len(manifest.documents) - len(pdf_docs)} non-PDF)")

    downloaded = []
    errors = []

    for doc in pdf_docs:
        filename = f"{doc.item_number:03d}_{_safe_filename(doc.title)}.pdf"
        filepath = docket_dir / filename

        if filepath.exists() and filepath.stat().st_size > 0:
            logger.debug(f"  Already downloaded: {filename}")
            downloaded.append(filepath)
            continue

        content, error = fetch_binary(
            doc.download_url,
            delay=config.request_delay,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

        if error:
            logger.warning(f"  Failed to download item {doc.item_number} ({doc.title[:50]}): {error}")
            errors.append(f"Item {doc.item_number}: {error}")
            continue

        filepath.write_bytes(content)
        downloaded.append(filepath)
        logger.debug(f"  Downloaded: {filename} ({len(content)} bytes)")

    logger.info(f"Docket {manifest.ntsb_id} — downloaded {len(downloaded)}/{len(pdf_docs)} PDFs")

    if not downloaded:
        return [], f"No documents downloaded for {manifest.ntsb_id}"

    return downloaded, None


def _safe_filename(title: str, max_len: int = 80) -> str:
    """Convert a document title to a safe filename."""
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    safe = "_".join(safe.split())  # normalize whitespace
    return safe[:max_len]
