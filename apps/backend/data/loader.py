"""
OHLCV Data Loader with Caching

Provides a high-level interface for loading and caching OHLCV data.
"""

import asyncio
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from data.binance_client import BinanceClient
from shared.contracts import OHLCV

# Durable, CWD-independent default cache dir resolved from this file's location
# (apps/backend/data/loader.py -> parents[3] == repo root). The old default was
# the volatile "/tmp", which violated the single-Parquet storage anti-goal.
_DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[3] / ".data" / "market_data"

# Maps strategy timeframe → finer resolution timeframe used for sub-bar SL/TP accuracy.
# The resolution TF is chosen so its typical bar range is well below any practical SL value,
# eliminating bar-path ambiguity without fetching 1m data for every strategy.
_RESOLUTION_TF_MAP: dict[str, str] = {
    "1d": "1h",   # 24 sub-bars per daily candle
    "4h": "15m",  # 16 sub-bars per 4H candle
    "1h": "5m",   # 12 sub-bars per 1H candle
    "15m": "1m",  # 15 sub-bars per 15m candle
    "5m": "1m",   # 5 sub-bars per 5m candle
}


class OHLCVLoader:
    """
    High-level data loader with local file caching.

    Caches OHLCV data to disk to avoid repeated API calls.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        use_cache: bool = True,
    ):
        """
        Initialize OHLCV loader.

        Args:
            cache_dir: Directory for cached data files (defaults to
                MARKET_DATA_CACHE_DIR, else a durable in-repo .data/market_data)
            use_cache: Whether to use disk caching
        """
        if not cache_dir:
            cache_dir = os.getenv("MARKET_DATA_CACHE_DIR") or str(_DEFAULT_CACHE_DIR)

        self.cache_dir = Path(cache_dir)
        self.use_cache = use_cache

        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _parquet_path(self, symbol: str, timeframe: str) -> Path:
        """Single cache file per (symbol, timeframe) — no per-day fan-out."""
        safe_symbol = symbol.replace("/", "_").replace("-", "_")
        return self.cache_dir / safe_symbol / f"{timeframe}.parquet"

    def _dedupe_sort(self, data: list[OHLCV]) -> list[OHLCV]:
        """Dedupe by timestamp (first occurrence wins), then sort ascending."""
        seen: set = set()
        out: list[OHLCV] = []
        for candle in data:
            if candle.timestamp not in seen:
                seen.add(candle.timestamp)
                out.append(candle)
        out.sort(key=lambda c: c.timestamp)
        return out

    def _read_parquet_cache(self, cache_path: Path) -> list[OHLCV]:
        """Load the cached candles, or [] if the file is missing/corrupt.

        A corrupt, partial, or legacy-layout file is treated as a cache miss
        (return []) so the caller re-fetches instead of hard-crashing.
        """
        if not cache_path.exists():
            return []
        try:
            df = pd.read_parquet(cache_path)
            # Defensive: parquet preserves dtype, but normalise to UTC so a
            # legacy/foreign file still yields tz-aware timestamps.
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            return self._dedupe_sort(self._df_to_ohlcv_list(df))
        except Exception:
            return []

    def _write_parquet_atomic(self, cache_path: Path, data: list[OHLCV]) -> None:
        """Atomically rewrite the single Parquet file for this (symbol, tf).

        Writes to a temp file in the same directory then os.replace()s it onto
        the final path, so a partial or concurrent write is never observable
        (last complete writer wins; safe under overlapping resolution-TF loads
        and the asyncio.Semaphore(1) backtest gate).
        """
        if not data:
            return
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df = self._ohlcv_list_to_df(data)
        fd, tmp_name = tempfile.mkstemp(
            dir=cache_path.parent,
            prefix=f".{cache_path.stem}-",
            suffix=".parquet.tmp",
        )
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            df.to_parquet(tmp_path, index=False)
            os.replace(tmp_path, cache_path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise

    def _ohlcv_list_to_df(self, data: list[OHLCV]) -> pd.DataFrame:
        """Convert list of OHLCV to DataFrame."""
        return pd.DataFrame([
            {
                "timestamp": ohlcv.timestamp,
                "symbol": ohlcv.symbol,
                "timeframe": ohlcv.timeframe,
                "open": ohlcv.open,
                "high": ohlcv.high,
                "low": ohlcv.low,
                "close": ohlcv.close,
                "volume": ohlcv.volume,
                "quote_volume": ohlcv.quote_volume,
            }
            for ohlcv in data
        ])

    def _df_to_ohlcv_list(self, df: pd.DataFrame) -> list[OHLCV]:
        """Convert DataFrame to list of OHLCV."""
        return [
            OHLCV(
                timestamp=row["timestamp"].to_pydatetime().replace(tzinfo=timezone.utc)
                if hasattr(row["timestamp"], "to_pydatetime")
                else row["timestamp"],
                symbol=row["symbol"],
                timeframe=row["timeframe"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                quote_volume=float(row["quote_volume"]),
            )
            for _, row in df.iterrows()
        ]

    async def load(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[OHLCV]:
        """
        Load OHLCV data for a symbol and date range.

        Reads the single per-(symbol, timeframe) Parquet cache when present.
        If the cache fully covers [start_date, end_date] no Binance call is
        made; otherwise only the missing leading/trailing sub-range(s) are
        fetched, merged into the cached set, and the single Parquet is
        rewritten atomically. Liquid-pair Binance history is assumed
        contiguous (no interior gaps), so a covering [cache_min, cache_max]
        span is treated as fully populated.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            timeframe: Candle interval
            start_date: Start datetime (UTC)
            end_date: End datetime (UTC)

        Returns:
            List of OHLCV dataclasses sorted by timestamp. Byte-identical
            whether served cold or warm for the same inputs.
        """
        # use_cache=False: always fetch fresh; never read or write disk.
        if not self.use_cache:
            async with BinanceClient() as client:
                fetched = await self._fetch_with_retry(
                    client, symbol, timeframe, start_date, end_date
                )
            return self._postprocess(fetched, start_date, end_date)

        cache_path = self._parquet_path(symbol, timeframe)
        cached = self._read_parquet_cache(cache_path)

        # Only the shortfall vs the cached span needs fetching. Re-fetching the
        # boundary bar (inclusive sub-ranges) is harmless: it dedupes away and
        # keeps the single accumulating file contiguous.
        missing_ranges: list[tuple[datetime, datetime]] = []
        if cached:
            cache_min = cached[0].timestamp
            cache_max = cached[-1].timestamp
            if start_date < cache_min:
                missing_ranges.append((start_date, cache_min))
            if end_date > cache_max:
                missing_ranges.append((cache_max, end_date))
        else:
            missing_ranges.append((start_date, end_date))

        fetched: list[OHLCV] = []
        if missing_ranges:
            async with BinanceClient() as client:
                for sub_start, sub_end in missing_ranges:
                    fetched.extend(
                        await self._fetch_with_retry(
                            client, symbol, timeframe, sub_start, sub_end
                        )
                    )

        if fetched:
            merged = self._dedupe_sort(cached + fetched)
            self._write_parquet_atomic(cache_path, merged)
        else:
            merged = cached

        return self._postprocess(merged, start_date, end_date)

    def _postprocess(
        self, data: list[OHLCV], start_date: datetime, end_date: datetime
    ) -> list[OHLCV]:
        """Dedupe -> sort ascending -> filter strictly to the window.

        This is the determinism invariant: the returned list is identical
        whether ``data`` came from a cold fetch or a warm Parquet read.
        """
        deduped = self._dedupe_sort(data)
        return [c for c in deduped if start_date <= c.timestamp <= end_date]

    async def _fetch_with_retry(
        self,
        client: BinanceClient,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[OHLCV]:
        """Fetch one sub-range, retrying transient Binance errors (3 attempts)."""
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            try:
                return await client.fetch_ohlcv(
                    symbol, timeframe, start_date, end_date
                )
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    await asyncio.sleep(1 * (attempt + 1))
        raise RuntimeError(
            f"Failed to fetch data from Binance for "
            f"{start_date}..{end_date}: {last_exc}"
        )

    @staticmethod
    def get_resolution_timeframe(strategy_tf: str) -> Optional[str]:
        """
        Return the sub-bar resolution timeframe for a strategy timeframe.

        Returns None if no finer resolution is defined (e.g. "1m" strategies).
        """
        return _RESOLUTION_TF_MAP.get(strategy_tf)

    async def load_resolution(
        self,
        symbol: str,
        strategy_tf: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[OHLCV]:
        """
        Load sub-bar resolution data for improved SL/TP accuracy.

        Auto-derives the appropriate resolution timeframe from the strategy
        timeframe using _RESOLUTION_TF_MAP, then fetches that data via the
        normal load() path (with caching).

        Returns an empty list if no finer resolution is defined or on error.
        """
        resolution_tf = self.get_resolution_timeframe(strategy_tf)
        if not resolution_tf:
            return []
        return await self.load(symbol, resolution_tf, start_date, end_date)

    def load_sync(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[OHLCV]:
        """
        Synchronous wrapper for load().

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            timeframe: Candle interval
            start_date: Start datetime (UTC)
            end_date: End datetime (UTC)

        Returns:
            List of OHLCV dataclasses sorted by timestamp
        """
        import asyncio

        return asyncio.run(self.load(symbol, timeframe, start_date, end_date))

    def to_dataframe(self, data: list[OHLCV]) -> pd.DataFrame:
        """
        Convert OHLCV list to pandas DataFrame.

        Args:
            data: List of OHLCV dataclasses

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        df = self._ohlcv_list_to_df(data)
        df = df.set_index("timestamp")
        return df

    def clear_cache(self) -> int:
        """
        Clear all cached data.

        Returns:
            Number of cache files deleted
        """
        count = 0
        if self.cache_dir.exists():
            for f in self.cache_dir.rglob("*.parquet"):
                f.unlink()
                count += 1
        return count
