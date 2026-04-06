"""HTTP client with rate limiting and retry logic for NTSB scraping."""

import time

import httpx
from loguru import logger

_BASE_URL = "https://data.ntsb.gov"
_USER_AGENT = "CROSSFIRE-Research/1.0 (academic research; polite crawler)"


def fetch_page(
    path: str,
    *,
    delay: float = 1.5,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> tuple[str | None, str | None]:
    """Fetch an HTML page from data.ntsb.gov.

    Returns (html_content, None) on success, (None, error_message) on failure.
    """
    url = f"{_BASE_URL}{path}" if path.startswith("/") else path
    return _request(url, delay=delay, timeout=timeout, max_retries=max_retries, as_bytes=False)


def fetch_binary(
    path: str,
    *,
    delay: float = 1.5,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> tuple[bytes | None, str | None]:
    """Fetch binary content (PDF) from data.ntsb.gov.

    Returns (bytes_content, None) on success, (None, error_message) on failure.
    """
    url = f"{_BASE_URL}{path}" if path.startswith("/") else path
    return _request(url, delay=delay, timeout=timeout, max_retries=max_retries, as_bytes=True)


def _request(
    url: str,
    *,
    delay: float,
    timeout: float,
    max_retries: int,
    as_bytes: bool,
) -> tuple:
    """Internal request with retry and rate limiting."""
    time.sleep(delay)

    last_error = None
    for attempt in range(1, max_retries + 2):  # 1 initial + max_retries
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, headers={"User-Agent": _USER_AGENT})
                response.raise_for_status()

                if as_bytes:
                    return response.content, None
                return response.text, None

        except httpx.TimeoutException as e:
            last_error = f"Timeout: {e}"
            if attempt <= max_retries:
                wait = 2**attempt
                logger.warning(f"Timeout fetching {url}, retrying in {wait}s (attempt {attempt}/{max_retries})")
                time.sleep(wait)

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status in (429, 503):
                last_error = f"HTTP {status}: {e}"
                if attempt <= max_retries:
                    wait = 2**attempt
                    logger.warning(f"HTTP {status} for {url}, retrying in {wait}s (attempt {attempt}/{max_retries})")
                    time.sleep(wait)
            else:
                logger.error(f"HTTP {status} fetching {url}: {e}")
                return None, f"HTTP {status}: {e}"

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return None, f"HTTP error: {e}"

    logger.error(f"Failed after {max_retries} retries for {url}: {last_error}")
    return None, f"Failed after {max_retries} retries: {last_error}"
