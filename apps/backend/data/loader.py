"""
OHLCV Data Loader with Caching

Provides a high-level interface for loading and caching OHLCV data.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from data.binance_client import BinanceClient
from shared.contracts import OHLCV

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
            cache_dir: Directory for cached data files (defaults to MARKET_DATA_CACHE_DIR or /tmp)
            use_cache: Whether to use disk caching
        """
        if not cache_dir:
            cache_dir = os.getenv("MARKET_DATA_CACHE_DIR", "/tmp")
            
        self.cache_dir = Path(cache_dir)
        self.use_cache = use_cache

        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_daily_cache_path(self, symbol: str, timeframe: str, date: datetime) -> Path:
        """Get file path for a daily cache file."""
        safe_symbol = symbol.replace("/", "_").replace("-", "_")
        date_str = date.strftime("%Y-%m-%d")
        return self.cache_dir / safe_symbol / timeframe / f"{date_str}.csv"

    def _load_from_csv(self, cache_path: Path) -> Optional[list[OHLCV]]:
        """Load OHLCV data from daily CSV cache if available."""
        if not cache_path.exists():
            return None

        try:
            df = pd.read_csv(cache_path)
            # Ensure timestamp is parsed as UTC datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            return self._df_to_ohlcv_list(df)
        except Exception:
            # If cache is corrupted or missing columns, return None to refetch
            return None

    def _save_to_csv(self, cache_path: Path, data: list[OHLCV]) -> None:
        """Save OHLCV data to daily CSV cache."""
        if not data:
            return

        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            df = self._ohlcv_list_to_df(data)
            df.to_csv(cache_path, index=False)
        except OSError:
            # Another concurrent backtest might be writing the exact same cache file.
            # Safe to ignore; this process already has the fetched data in memory.
            pass

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
        import asyncio
        
        all_data: list[OHLCV] = []
        missing_dates_to_fetch = []
        
        # Determine the exact bounds (normalized to midnight UTC for daily looping)
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with BinanceClient() as client:
            while current_date <= end_day:
                next_date = current_date + timedelta(days=1)
                cache_path = self._get_daily_cache_path(symbol, timeframe, current_date)
                
                daily_data = None
                
                # 1. Try Cache
                if self.use_cache:
                    daily_data = self._load_from_csv(cache_path)
                
                # 2. Mark for fetching if missing, else add to result
                if daily_data is None:
                    # Subtract 1 ms from next_date so we strictly bound fetching up to 23:59:59.999
                    query_end = next_date - timedelta(milliseconds=1)
                    missing_dates_to_fetch.append((current_date, query_end, cache_path))
                else:
                    all_data.extend(daily_data)
                
                current_date = next_date

            # Fetch missing dates concurrently but limit to 10 concurrent requests
            if missing_dates_to_fetch:
                semaphore = asyncio.Semaphore(10)
                
                async def fetch_and_cache(curr_dt, q_end, c_path):
                    async with semaphore:
                        try:
                            # Added a small retry loop to be robust against transient API errors
                            for attempt in range(3):
                                try:
                                    data = await client.fetch_ohlcv(symbol, timeframe, curr_dt, q_end)
                                    if self.use_cache and data is not None:
                                        self._save_to_csv(c_path, data)
                                    return data
                                except Exception as inner_e:
                                    if attempt == 2:
                                        raise inner_e
                                    await asyncio.sleep(1 * (attempt + 1))
                        except Exception as e:
                            raise RuntimeError(f"Failed to fetch data from Binance for {curr_dt}: {e}")
                
                tasks = [fetch_and_cache(c, q, p) for c, q, p in missing_dates_to_fetch]
                fetch_results = await asyncio.gather(*tasks)
                
                for result in fetch_results:
                    if result:
                        all_data.extend(result)

        # Deduplicate and sort, just in case
        unique_timestamps = set()
        deduped_data = []
        for candle in all_data:
            if candle.timestamp not in unique_timestamps:
                unique_timestamps.add(candle.timestamp)
                deduped_data.append(candle)
                
        deduped_data.sort(key=lambda x: x.timestamp)
        
        # Filter strictly to the requested time window
        filtered_data = [
            candle for candle in deduped_data 
            if start_date <= candle.timestamp <= end_date
        ]

        return filtered_data

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
            for f in self.cache_dir.rglob("*.csv"):
                f.unlink()
                count += 1
        return count
