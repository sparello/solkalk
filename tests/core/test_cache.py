"""Tests for solkalk.core.cache."""

import pandas as pd

from solkalk.core.cache import DiskCache, safe_key


def test_safe_key():
    assert safe_key("strang", 59.33, 18.07, 2024) == "strang_59.33_18.07_2024"
    assert "/" not in safe_key("a/b", "c d")


def test_get_or_fetch_calls_fetch_once(tmp_path, strang_week):
    cache = DiskCache(tmp_path)
    calls = []

    def fetch():
        calls.append(1)
        return strang_week

    cache.get_or_fetch("k", fetch)
    second = cache.get_or_fetch("k", fetch)
    assert calls == [1]
    assert cache.has("k")
    pd.testing.assert_frame_equal(second, strang_week, check_freq=False)
    assert str(second.index.tz) == "UTC"


def test_daily_rates_roundtrip_stay_naive(tmp_path, ecb_rates_jan):
    from solkalk.features.prices import ecb_exchange_rates

    cache = DiskCache(tmp_path)
    cache.put_frame("ecb", ecb_rates_jan.to_frame())
    again = cache.get_frame("ecb", tz=None)["rate"]
    assert again.index.tz is None
    # and forward_fill must work on what came out of the cache
    assert len(ecb_exchange_rates.forward_fill(again, "2025-01-02", "2025-01-08")) == 7


def test_clear(tmp_path, strang_week):
    cache = DiskCache(tmp_path)
    cache.put_frame("a", strang_week)
    cache.put_frame("b", strang_week)
    assert cache.clear() == 2
    assert not cache.has("a")


def test_get_frame_tz_none_strips_utc(tmp_path, strang_week):
    cache = DiskCache(tmp_path)
    cache.put_frame("utc", strang_week)
    naive = cache.get_frame("utc", tz=None)
    assert naive.index.tz is None
    assert naive.index[0] == strang_week.index[0].tz_convert("UTC").tz_localize(None)
