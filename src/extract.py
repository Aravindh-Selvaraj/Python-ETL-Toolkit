import logging
import os
import time
import requests
from pydantic import ValidationError

from .schemas import UserRecord

logger = logging.getLogger(__name__)

# ── Retry configuration ───────────────────────────────────────────────────────
_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # delay = _BACKOFF_BASE ** attempt → 2s, 4s, 8s


class _ServerError(Exception):
    """Internal sentinel: 5xx response that should trigger a retry."""


def _build_headers() -> dict:
    """
    Builds HTTP request headers from environment variables.
    Only includes auth headers that are actually set — no empty/None values
    are sent to the API.

    Supports three common auth patterns:
      - API Key       → x-api-key header
      - Bearer Token  → Authorization: Bearer <token>
      - Generic Token → Authorization: Token <token>

    All values are read from the .env file (loaded by run_pipeline.py).
    """
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    api_key = os.getenv("ETL_API_KEY")
    bearer_token = os.getenv("ETL_BEARER_TOKEN")
    api_token = os.getenv("ETL_API_TOKEN")

    if api_key:
        headers["x-api-key"] = api_key
        logger.debug("Auth: API Key header attached.")

    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
        logger.debug("Auth: Bearer token header attached.")
    elif api_token:
        headers["Authorization"] = f"Token {api_token}"
        logger.debug("Auth: Token header attached.")

    return headers


def _fetch_with_retry(url: str, timeout: int = 15) -> requests.Response:
    """
    Performs an HTTP GET with exponential-backoff retry on transient failures.

    - 4xx client errors : raised immediately — no retry (request is wrong).
    - 5xx server errors : retried up to _MAX_RETRIES times.
    - Connection/timeout: same retry treatment as 5xx.
    """
    headers = _build_headers()
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)

            # 4xx: client-side — raise immediately, no retry
            if 400 <= response.status_code < 500:
                response.raise_for_status()

            # 5xx: server-side — use sentinel to trigger retry
            if response.status_code >= 500:
                raise _ServerError(f"Server returned {response.status_code}")

            return response

        except requests.exceptions.HTTPError:
            raise  # 4xx — propagate immediately

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                _ServerError) as exc:
            last_exc = exc
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                f"Extraction attempt {attempt}/{_MAX_RETRIES} failed: {exc}. "
                f"Retrying in {wait}s..."
            )
            if attempt < _MAX_RETRIES:
                time.sleep(wait)

    raise requests.exceptions.RetryError(
        f"All {_MAX_RETRIES} extraction attempts failed for URL: {url}"
    ) from last_exc


def extract_data(url: str) -> list[dict]:
    """
    Fetches and validates raw source records from an HTTP REST API endpoint.

    Steps:
      1. Build auth headers from environment variables (.env).
      2. Fetch JSON with exponential-backoff retry on transient failures.
      3. Validate each record against the UserRecord Pydantic schema.
      4. Return only the records that pass validation.

    Raises:
        requests.exceptions.RetryError : all retry attempts exhausted.
        requests.exceptions.HTTPError  : unrecoverable 4xx client error.
    """
    logger.info(f"Starting Extraction phase from: {url}")

    response = _fetch_with_retry(url)

    raw: list | dict = response.json()
    if not isinstance(raw, list):
        raw = [raw]

    logger.info(f"Fetched {len(raw)} raw records. Running schema validation...")

    valid_records: list[dict] = []
    invalid_count = 0

    for idx, record in enumerate(raw):
        try:
            validated = UserRecord.model_validate(record)
            valid_records.append(validated.model_dump())
        except ValidationError as e:
            invalid_count += 1
            logger.warning(
                f"Record [{idx}] failed schema validation and was skipped. "
                f"Errors: {e.errors(include_url=False)}"
            )

    logger.info(
        f"Extraction complete. Valid: {len(valid_records)}, "
        f"Skipped (invalid): {invalid_count}."
    )
    return valid_records
