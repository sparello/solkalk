"""Simple on-disk cache for fetched time series (CSV, no extra dependencies).

The key is a file name the caller builds from source + parameters, e.g.
``strang_59.33_18.07_2024``. Complete historical years never change and can
be cached forever. The current year should not be cached by the caller; there
is no TTL.

Time series (STRÅNG, ENTSO-E) are read back with a UTC index; daily exchange
rates (ECB) with ``tz=None`` so the index stays naive dates.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_key(*parts: object) -> str:
    """Build a file-safe cache key from arbitrary parts."""
    return "_".join(_SAFE.sub("-", str(part)) for part in parts)


class DiskCache:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        return self.directory / f"{key}.csv"

    def has(self, key: str) -> bool:
        return self.path(key).exists()

    def get_frame(self, key: str, *, tz: str | None = "UTC") -> pd.DataFrame:
        frame = pd.read_csv(self.path(key), index_col=0, parse_dates=True)
        if tz is not None and frame.index.tz is None:
            frame.index = pd.DatetimeIndex(frame.index, tz=tz)
        elif tz is None and frame.index.tz is not None:
            frame.index = frame.index.tz_convert("UTC").tz_localize(None)
        return frame

    def put_frame(self, key: str, frame: pd.DataFrame) -> None:
        frame.to_csv(self.path(key))

    def get_or_fetch(
        self, key: str, fetch: Callable[[], pd.DataFrame], *, tz: str | None = "UTC"
    ) -> pd.DataFrame:
        """Return the cached frame, or run ``fetch``, store and return it."""
        if self.has(key):
            return self.get_frame(key, tz=tz)
        frame = fetch()
        self.put_frame(key, frame)
        return frame

    def clear(self) -> int:
        count = 0
        for file in self.directory.glob("*.csv"):
            file.unlink()
            count += 1
        return count
