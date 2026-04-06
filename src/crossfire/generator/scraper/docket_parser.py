"""Parse NTSB docket pages into structured document listings."""

import re

from bs4 import BeautifulSoup
from loguru import logger

from .config import DocketTarget
from .http_client import fetch_page
from .models import DocketManifest, DocumentEntry

# Map group number prefixes to human-readable group names
_GROUP_NAMES = {
    "1": "Hearing Documents",
    "2": "Operational Factors",
    "6": "Survival Factors",
    "7": "Structures",
    "9": "Systems",
    "10": "Flight Data Recorder",
    "11": "Manufacturing & Human Performance",
    "12": "Cockpit Voice Recorder",
    "15": "Materials",
}

_GROUP_PREFIX_RE = re.compile(r"^(\d{1,2})-?[A-Z]?\s")


def _infer_group(title: str) -> str:
    """Infer investigation group from the document title prefix."""
    m = _GROUP_PREFIX_RE.match(title)
    if m:
        num = m.group(1)
        return _GROUP_NAMES.get(num, f"Group {num}")

    title_upper = title.upper()
    for keyword, group in [
        ("OPERATIONAL FACTORS", "Operational Factors"),
        ("SURVIVAL FACTORS", "Survival Factors"),
        ("STRUCTURES", "Structures"),
        ("SYSTEMS", "Systems"),
        ("FLIGHT DATA RECORDER", "Flight Data Recorder"),
        ("FDR", "Flight Data Recorder"),
        ("COCKPIT VOICE RECORDER", "Cockpit Voice Recorder"),
        ("CVR", "Cockpit Voice Recorder"),
        ("MANUFACTURING", "Manufacturing & Human Performance"),
        ("HUMAN PERFORMANCE", "Manufacturing & Human Performance"),
        ("MATERIALS", "Materials"),
        ("HEARING", "Hearing Documents"),
        ("BOEING", "Party Submissions"),
        ("SPIRIT", "Party Submissions"),
        ("FAA", "Regulatory"),
        ("BOARD MEETING", "Board Meeting"),
    ]:
        if keyword in title_upper:
            return group
    return "Other"


def parse_docket_html(html: str, ntsb_id: str, url: str) -> DocketManifest:
    """Parse a docket page HTML into a DocketManifest."""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")

    # The document table is the largest table (usually the 3rd one)
    doc_table = max(tables, key=lambda t: len(t.find_all("tr"))) if tables else None
    if not doc_table:
        logger.warning(f"No document table found for {ntsb_id}")
        return DocketManifest(ntsb_id=ntsb_id, url=url)

    rows = doc_table.find_all("tr")
    documents = []

    for row in rows[1:]:  # skip header
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        item_text = cells[0].get_text(strip=True)
        if not item_text.isdigit():
            continue

        title = cells[1].get_text(strip=True)
        page_count_text = cells[2].get_text(strip=True)
        page_count = int(page_count_text) if page_count_text.isdigit() else 0

        # File type from column 4
        file_type_text = cells[4].get_text(strip=True).lower()

        # Download link from column 5
        link = cells[5].find("a")
        if not link:
            continue
        href = link.get("href", "")
        if not href:
            continue

        # Determine actual file extension from URL
        file_ext = "pdf"
        if "FileExtension=" in href:
            file_ext = href.split("FileExtension=")[1].split("&")[0].lower()

        documents.append(
            DocumentEntry(
                item_number=int(item_text),
                title=title,
                file_type=file_ext,
                page_count=page_count,
                download_url=href,
                group=_infer_group(title),
            )
        )

    manifest = DocketManifest(
        ntsb_id=ntsb_id,
        url=url,
        document_count=len(documents),
        documents=documents,
    )
    logger.info(f"Docket {ntsb_id} — found {len(documents)} documents")
    return manifest


def fetch_docket_manifest(
    target: DocketTarget | str,
    *,
    delay: float = 1.5,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> tuple[DocketManifest | None, str | None]:
    """Fetch and parse a docket page. Returns (manifest, error).

    Supports both NTSBNumber and ProjectID access. Falls back from NTSBNumber to
    ProjectID if the first attempt returns no documents.
    """
    if isinstance(target, str):
        target = DocketTarget(ntsb_id=target)

    ntsb_id = target.ntsb_id

    # Try NTSBNumber first
    path = f"/Docket/?NTSBNumber={ntsb_id}"
    url = f"https://data.ntsb.gov{path}"

    html, error = fetch_page(path, delay=delay, timeout=timeout, max_retries=max_retries)
    if error:
        return None, f"Failed to fetch docket {ntsb_id}: {error}"

    manifest = parse_docket_html(html, ntsb_id, url)

    # If NTSBNumber returned no docs, try ProjectID
    if manifest.document_count == 0 and target.project_id is not None:
        logger.info(f"Docket {ntsb_id} empty via NTSBNumber, trying ProjectID {target.project_id}")
        path = f"/Docket/?ProjectID={target.project_id}"
        url = f"https://data.ntsb.gov{path}"

        html, error = fetch_page(path, delay=delay, timeout=timeout, max_retries=max_retries)
        if error:
            return None, f"Failed to fetch docket {ntsb_id} via ProjectID: {error}"

        manifest = parse_docket_html(html, ntsb_id, url)

    if manifest.document_count == 0:
        return None, f"No documents found in docket {ntsb_id}"

    return manifest, None
