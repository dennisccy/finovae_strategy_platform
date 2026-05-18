"""Unit/integration tests for data/loader.py — single-file Parquet OHLCV cache.

Covers the iter-1 storage anti-goal:
  * single Parquet file per (symbol, timeframe); zero per-day .csv
  * warm covering-cache load makes ZERO Binance fetches
  * cold == warm equivalence (determinism invariant survives Parquet round-trip)
  * partial coverage fetches only the missing sub-range(s)
  * corrupt/partial Parquet -> treated as a cache miss, not a hard crash
  * clear_cache() removes the Parquet file(s) and returns the correct count
  * durable default cache dir is absolute and not under /tmp

Binance is mocked as an async spy that records every fetch_ohlcv call and
serves only the candles inside the requested window from a deterministic
synthetic dataset (asyncio_mode=auto -> no decorator needed).
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import data.loader as loader_mod
from data.loader import OHLCVLoader
from shared.contracts import OHLCV

START = datetime(2024, 1, 1, tzinfo=timezone.utc)
STEP = timedelta(hours=1)


def _series(symbol: str, timeframe: str, n: int) -> list[OHLCV]:
    """Deterministic contiguous hourly candle series."""
    return [
        OHLCV(
            timestamp=START + i * STEP,
            symbol=symbol,
            timeframe=timeframe,
            open=100.0 + i,
            high=105.0 + i,
            low=95.0 + i,
            close=100.0 + i * 0.5,
            volume=1000.0 + i,
            quote_volume=50000.0 + i,
        )
        for i in range(n)
    ]


def _make_fake_binance(master: list[OHLCV], calls: list[dict]):
    """Build a fake BinanceClient class serving from `master`, recording calls."""

    class _FakeBinanceClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def fetch_ohlcv(self, symbol, timeframe, start_date, end_date):
            calls.append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "start": start_date,
                    "end": end_date,
                }
            )
            return [
                c
                for c in master
                if c.symbol == symbol
                and c.timeframe == timeframe
                and start_date <= c.timestamp <= end_date
            ]

    return _FakeBinanceClient


@pytest.fixture
def binance_spy(monkeypatch):
    """Returns (calls_list, install(master)) — install patches loader.BinanceClient."""
    calls: list[dict] = []

    def install(master: list[OHLCV]):
        monkeypatch.setattr(
            loader_mod, "BinanceClient", _make_fake_binance(master, calls)
        )
        return calls

    return calls, install


async def test_warm_load_makes_zero_binance_fetches(tmp_path, binance_spy):
    calls, install = binance_spy
    install(_series("BTCUSDT", "1h", 48))
    ld = OHLCVLoader(cache_dir=str(tmp_path))
    s, e = START, START + 47 * STEP

    cold = await ld.load("BTCUSDT", "1h", s, e)
    assert len(calls) >= 1
    assert len(cold) == 48

    calls.clear()
    warm = await ld.load("BTCUSDT", "1h", s, e)

    assert calls == []  # covering cache -> ZERO Binance calls on the warm path
    assert len(warm) == 48


async def test_cold_equals_warm_equivalence(tmp_path, binance_spy):
    calls, install = binance_spy
    install(_series("ETHUSDT", "1h", 30))
    ld = OHLCVLoader(cache_dir=str(tmp_path))
    s, e = START, START + 29 * STEP

    cold = await ld.load("ETHUSDT", "1h", s, e)
    calls.clear()
    warm = await ld.load("ETHUSDT", "1h", s, e)

    assert calls == []
    assert cold == warm  # frozen dataclass field-wise equality
    # tz-aware UTC timestamps survive the Parquet round-trip exactly
    assert cold[0].timestamp == warm[0].timestamp
    assert warm[0].timestamp.utcoffset() == timedelta(0)
    assert [c.timestamp for c in cold] == [c.timestamp for c in warm]
    assert [c.close for c in cold] == [c.close for c in warm]


async def test_on_disk_single_parquet_zero_csv(tmp_path, binance_spy):
    _calls, install = binance_spy
    install(_series("BTCUSDT", "1h", 24))
    ld = OHLCVLoader(cache_dir=str(tmp_path))
    s, e = START, START + 23 * STEP

    await ld.load("BTCUSDT", "1h", s, e)

    parquets = sorted(Path(tmp_path).rglob("*.parquet"))
    csvs = sorted(Path(tmp_path).rglob("*.csv"))
    assert len(parquets) == 1
    assert csvs == []
    assert parquets[0].name == "1h.parquet"
    assert parquets[0].parent.name == "BTCUSDT"


async def test_partial_leading_coverage_fetches_only_missing(tmp_path, binance_spy):
    calls, install = binance_spy
    install(_series("BTCUSDT", "1h", 100))
    ld = OHLCVLoader(cache_dir=str(tmp_path))

    # Warm the cache with the middle/tail window [ts40, ts99].
    await ld.load("BTCUSDT", "1h", START + 40 * STEP, START + 99 * STEP)
    calls.clear()

    # Request the full window [ts0, ts99] — only the leading gap is missing.
    res = await ld.load("BTCUSDT", "1h", START, START + 99 * STEP)

    assert len(calls) == 1  # exactly one sub-range fetched, NOT the whole window
    assert calls[0]["start"] == START
    assert calls[0]["end"] == START + 40 * STEP
    assert len(res) == 100
    assert res[0].timestamp == START
    assert res[-1].timestamp == START + 99 * STEP


async def test_partial_trailing_coverage_fetches_only_missing(tmp_path, binance_spy):
    calls, install = binance_spy
    install(_series("BTCUSDT", "1h", 100))
    ld = OHLCVLoader(cache_dir=str(tmp_path))

    # Warm the cache with the leading window [ts0, ts60].
    await ld.load("BTCUSDT", "1h", START, START + 60 * STEP)
    calls.clear()

    # Request [ts0, ts99] — only the trailing gap is missing.
    res = await ld.load("BTCUSDT", "1h", START, START + 99 * STEP)

    assert len(calls) == 1
    assert calls[0]["start"] == START + 60 * STEP
    assert calls[0]["end"] == START + 99 * STEP
    assert len(res) == 100


async def test_corrupt_parquet_is_treated_as_cache_miss(tmp_path, binance_spy):
    calls, install = binance_spy
    install(_series("BTCUSDT", "1h", 24))
    ld = OHLCVLoader(cache_dir=str(tmp_path))
    s, e = START, START + 23 * STEP

    await ld.load("BTCUSDT", "1h", s, e)
    pq = next(Path(tmp_path).rglob("*.parquet"))
    pq.write_bytes(b"this is not a valid parquet file")
    calls.clear()

    res = await ld.load("BTCUSDT", "1h", s, e)  # must not raise

    assert len(calls) >= 1  # corrupt cache -> re-fetched
    assert len(res) == 24
    assert res[0].timestamp == START


async def test_clear_cache_deletes_parquet_and_returns_count(tmp_path, binance_spy):
    _calls, install = binance_spy
    master = _series("BTCUSDT", "1h", 12) + _series("ETHUSDT", "1h", 12)
    install(master)
    ld = OHLCVLoader(cache_dir=str(tmp_path))
    s, e = START, START + 11 * STEP

    await ld.load("BTCUSDT", "1h", s, e)
    await ld.load("ETHUSDT", "1h", s, e)
    assert len(list(Path(tmp_path).rglob("*.parquet"))) == 2

    deleted = ld.clear_cache()

    assert deleted == 2
    assert list(Path(tmp_path).rglob("*.parquet")) == []


async def test_use_cache_false_always_fetches_and_writes_nothing(tmp_path, binance_spy):
    calls, install = binance_spy
    install(_series("BTCUSDT", "1h", 24))
    ld = OHLCVLoader(cache_dir=str(tmp_path), use_cache=False)
    s, e = START, START + 23 * STEP

    r1 = await ld.load("BTCUSDT", "1h", s, e)
    n1 = len(calls)
    r2 = await ld.load("BTCUSDT", "1h", s, e)

    assert n1 >= 1
    assert len(calls) > n1  # cache bypassed -> fetched again
    assert r1 == r2
    assert list(Path(tmp_path).rglob("*.parquet")) == []  # nothing persisted


def test_default_cache_dir_is_durable_not_tmp(monkeypatch):
    monkeypatch.delenv("MARKET_DATA_CACHE_DIR", raising=False)
    ld = OHLCVLoader(use_cache=False)  # use_cache=False -> no dir is created
    repo_root = Path(loader_mod.__file__).resolve().parents[3]

    assert ld.cache_dir.is_absolute()
    assert not str(ld.cache_dir).startswith("/tmp")
    assert ld.cache_dir == repo_root / ".data" / "market_data"
