"""
Binance API Client for OHLCV Data

Fetches klines (candlestick) data from Binance spot market API.
Supports USDT pairs only with configurable timeframes.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

import httpx

from shared.contracts import OHLCV


class BinanceClientError(Exception):
    """Exception raised for Binance API errors."""
    pass


class BinanceClient:
    """
    Asynchronous client for Binance spot market klines API.

    Supports fetching OHLCV data for USDT pairs with rate limiting
    and automatic pagination for large date ranges.
    """

    BASE_URL = "https://api.binance.com"
    KLINES_ENDPOINT = "/api/v3/klines"

    # Binance klines limit per request
    MAX_KLINES_PER_REQUEST = 1000

    # Valid timeframes
    VALID_TIMEFRAMES = {"1m", "5m", "15m", "1h", "4h", "1d"}

    # Timeframe to milliseconds mapping
    TIMEFRAME_MS = {
        "1m": 60 * 1000,
        "5m": 5 * 60 * 1000,
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
        "1d": 24 * 60 * 60 * 1000,
    }

    def __init__(
        self,
        timeout: float = 30.0,
        rate_limit_delay: float = 0.1,
    ):
        """
        Initialize Binance client.

        Args:
            timeout: HTTP request timeout in seconds
            rate_limit_delay: Delay between requests to avoid rate limiting
        """
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "BinanceClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _validate_symbol(self, symbol: str) -> None:
        """Validate that symbol is a USDT pair (accepts both BTC/USDT and BTCUSDT)."""
        normalized = symbol.replace('/', '')
        if not normalized.endswith("USDT"):
            raise BinanceClientError(f"Only USDT pairs supported, got: {symbol}")
        if not normalized[:-4].isalpha():
            raise BinanceClientError(f"Invalid symbol format: {symbol}")

    def _validate_timeframe(self, timeframe: str) -> None:
        """Validate timeframe is supported."""
        if timeframe not in self.VALID_TIMEFRAMES:
            raise BinanceClientError(
                f"Invalid timeframe: {timeframe}. "
                f"Valid options: {self.VALID_TIMEFRAMES}"
            )

    def _parse_kline(self, kline: list, symbol: str, timeframe: str) -> OHLCV:
        """
        Parse Binance kline response into OHLCV dataclass.

        Binance kline format:
        [
            0: Open time (ms),
            1: Open,
            2: High,
            3: Low,
            4: Close,
            5: Volume,
            6: Close time (ms),
            7: Quote asset volume,
            8: Number of trades,
            9: Taker buy base volume,
            10: Taker buy quote volume,
            11: Ignore
        ]
        """
        return OHLCV(
            timestamp=datetime.fromtimestamp(kline[0] / 1000, tz=timezone.utc),
            symbol=symbol,
            timeframe=timeframe,
            open=float(kline[1]),
            high=float(kline[2]),
            low=float(kline[3]),
            close=float(kline[4]),
            volume=float(kline[5]),
            quote_volume=float(kline[7]),
        )

    async def _fetch_klines_batch(
        self,
        symbol: str,
        timeframe: str,
        start_time: int,
        end_time: int,
        limit: int = MAX_KLINES_PER_REQUEST,
    ) -> list[list]:
        """
        Fetch a single batch of klines from Binance.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            timeframe: Candle interval
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            limit: Maximum klines to fetch

        Returns:
            List of raw kline arrays
        """
        if not self._client:
            raise BinanceClientError("Client not initialized. Use async context manager.")

        params = {
            "symbol": symbol.replace('/', ''),  # Binance requires BTCUSDT format
            "interval": timeframe,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit,
        }

        response = await self._client.get(self.KLINES_ENDPOINT, params=params)

        if response.status_code != 200:
            raise BinanceClientError(
                f"Binance API error: {response.status_code} - {response.text}"
            )

        return response.json()

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[OHLCV]:
        """
        Fetch OHLCV data for a symbol and date range.

        Automatically paginates for large date ranges.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            timeframe: Candle interval (1m, 5m, 15m, 1h, 4h, 1d)
            start_date: Start datetime (UTC)
            end_date: End datetime (UTC)

        Returns:
            List of OHLCV dataclasses sorted by timestamp
        """
        self._validate_symbol(symbol)
        self._validate_timeframe(timeframe)

        # Convert to UTC timestamps in milliseconds
        start_ms = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)

        if start_ms >= end_ms:
            raise BinanceClientError("start_date must be before end_date")

        all_klines: list[OHLCV] = []
        current_start = start_ms
        timeframe_ms = self.TIMEFRAME_MS[timeframe]

        while current_start < end_ms:
            batch = await self._fetch_klines_batch(
                symbol=symbol,
                timeframe=timeframe,
                start_time=current_start,
                end_time=end_ms,
            )

            if not batch:
                break

            for kline in batch:
                ohlcv = self._parse_kline(kline, symbol, timeframe)
                all_klines.append(ohlcv)

            # Move start to after last candle
            last_candle_time = batch[-1][0]
            current_start = last_candle_time + timeframe_ms

            # Rate limiting delay
            if current_start < end_ms:
                await asyncio.sleep(self.rate_limit_delay)

        return sorted(all_klines, key=lambda x: x.timestamp)

    async def get_available_symbols(self) -> list[str]:
        """
        Get list of available USDT trading pairs.

        Returns:
            List of symbol strings (e.g., ["BTCUSDT", "ETHUSDT", ...])
        """
        if not self._client:
            raise BinanceClientError("Client not initialized. Use async context manager.")

        response = await self._client.get("/api/v3/exchangeInfo")

        if response.status_code != 200:
            raise BinanceClientError(
                f"Binance API error: {response.status_code} - {response.text}"
            )

        data = response.json()
        symbols = [
            s["symbol"]
            for s in data["symbols"]
            if s["symbol"].endswith("USDT")
            and s["status"] == "TRADING"
            and s["isSpotTradingAllowed"]
        ]

        return sorted(symbols)
