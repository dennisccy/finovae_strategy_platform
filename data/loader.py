"""
OHLCV Data Loader with Caching

Provides a high-level interface for loading and caching OHLCV data.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from data.binance_client import BinanceClient
from shared.contracts import OHLCV


class OHLCVLoader:
    """
    High-level data loader with local file caching.

    Caches OHLCV data to disk to avoid repeated API calls.
    """

    def __init__(
        self,
        cache_dir: str = ".cache/ohlcv",
        use_cache: bool = True,
    ):
        """
        Initialize OHLCV loader.

        Args:
            cache_dir: Directory for cached data files
            use_cache: Whether to use disk caching
        """
        self.cache_dir = Path(cache_dir)
        self.use_cache = use_cache

        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> str:
        """Generate a unique cache key for the request."""
        key_str = f"{symbol}_{timeframe}_{start_date.isoformat()}_{end_date.isoformat()}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get file path for cache key."""
        return self.cache_dir / f"{cache_key}.parquet"

    def _load_from_cache(self, cache_key: str) -> Optional[list[OHLCV]]:
        """Load OHLCV data from cache if available."""
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            df = pd.read_parquet(cache_path)
            return self._df_to_ohlcv_list(df)
        except Exception:
            # If cache is corrupted, return None to refetch
            return None

    def _save_to_cache(self, cache_key: str, data: list[OHLCV]) -> None:
        """Save OHLCV data to cache."""
        if not data:
            return

        df = self._ohlcv_list_to_df(data)
        cache_path = self._get_cache_path(cache_key)
        df.to_parquet(cache_path, index=False)

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

        Uses cached data if available, otherwise fetches from Binance API.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            timeframe: Candle interval
            start_date: Start datetime (UTC)
            end_date: End datetime (UTC)

        Returns:
            List of OHLCV dataclasses sorted by timestamp
        """
        cache_key = self._get_cache_key(symbol, timeframe, start_date, end_date)

        # Try cache first
        if self.use_cache:
            cached_data = self._load_from_cache(cache_key)
            if cached_data is not None:
                return cached_data

        # Fetch from Binance
        async with BinanceClient() as client:
            data = await client.fetch_ohlcv(symbol, timeframe, start_date, end_date)

        # Save to cache
        if self.use_cache and data:
            self._save_to_cache(cache_key, data)

        return data

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
            for f in self.cache_dir.glob("*.parquet"):
                f.unlink()
                count += 1
        return count
