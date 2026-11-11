"""Shared HTTP fetching with retries.

Every data source goes through ``get_text`` so tests can mock it with
``responses`` and retry behaviour is identical everywhere. Error messages and
tracebacks never contain API keys: ``redact_url`` masks secret query parameters
and the underlying ``requests`` exception is not chained.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable

import requests

DEFAULT_TIMEOUT_S = 120
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY_S = 5

# Status codes that will not improve by retrying
_FATAL_STATUS = {400, 401, 403, 404}
_SECRET_QUERY_PARAMS = re.compile(
    r"(securityToken|api_key|apikey|token|key)=([^&\s]+)", re.IGNORECASE
)


class FetchError(RuntimeError):
    """The fetch failed for good (after retries, or on a fatal status)."""


def redact_url(url: str) -> str:
    """Mask secret query parameters so they never reach logs or error messages."""
    return _SECRET_QUERY_PARAMS.sub(lambda m: f"{m.group(1)}=***", url)


def get_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    retries: int = DEFAULT_RETRIES,
    retry_delay_s: float = DEFAULT_RETRY_DELAY_S,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """GET ``url`` and return the body as text.

    Retries on network errors and 5xx. Fatal 4xx raise ``FetchError`` at once.
    ``sleep`` is injectable for tests.
    """
    last_reason = "no attempt made"
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout_s)
        except requests.RequestException as error:
            # requests puts the full URL, secrets included, in its messages
            last_reason = f"{type(error).__name__}: {redact_url(str(error))}"
        else:
            if response.status_code in _FATAL_STATUS:
                raise FetchError(f"HTTP {response.status_code} for {redact_url(url)}")
            if response.ok:
                return response.text
            last_reason = f"HTTP {response.status_code}"

        if attempt < retries:
            sleep(retry_delay_s)

    # ``from None``: the original exception must not ride along in the traceback,
    # because its message and request object carry the unredacted URL.
    raise FetchError(
        f"Gave up after {retries} attempts: {redact_url(url)} ({last_reason})"
    ) from None
