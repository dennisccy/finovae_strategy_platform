"""
Data Validation and Gap Detection

Validates OHLCV data quality and detects gaps in the time series.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from shared.contracts import OHLCV


class DataValidationError(Exception):
    """Exception raised for data validation failures."""
    pass


@dataclass
class DataGap:
    """Represents a gap in the OHLCV time series."""
    start_time: datetime
    end_time: datetime
    expected_candles: int
    gap_duration: timedelta


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    total_candles: int
    gaps: list[DataGap]
    invalid_candles: list[tuple[int, str]]  # (index, reason)
    warnings: list[str]


class DataValidator:
    """
    Validates OHLCV data for quality and completeness.

    Checks for:
    - Data gaps (missing candles)
    - Invalid OHLCV values
    - Timestamp ordering
    - Price anomalies
    """

    # Timeframe to expected interval in seconds
    TIMEFRAME_SECONDS = {
        "1m": 60,
        "5m": 5 * 60,
        "15m": 15 * 60,
        "1h": 60 * 60,
        "4h": 4 * 60 * 60,
        "1d": 24 * 60 * 60,
    }

    # Maximum allowed price change percentage per candle
    MAX_PRICE_CHANGE_PCT = 0.50  # 50%

    def __init__(
        self,
        max_gap_tolerance: int = 1,
        check_price_anomalies: bool = True,
    ):
        """
        Initialize validator.

        Args:
            max_gap_tolerance: Maximum allowed consecutive missing candles
            check_price_anomalies: Whether to check for price anomalies
        """
        self.max_gap_tolerance = max_gap_tolerance
        self.check_price_anomalies = check_price_anomalies

    def _validate_single_candle(
        self,
        candle: OHLCV,
        index: int,
        prev_candle: Optional[OHLCV] = None,
    ) -> list[str]:
        """
        Validate a single OHLCV candle.

        Returns list of validation error messages.
        """
        errors = []

        # Check for non-positive prices
        if candle.open <= 0:
            errors.append(f"Candle {index}: non-positive open price ({candle.open})")
        if candle.high <= 0:
            errors.append(f"Candle {index}: non-positive high price ({candle.high})")
        if candle.low <= 0:
            errors.append(f"Candle {index}: non-positive low price ({candle.low})")
        if candle.close <= 0:
            errors.append(f"Candle {index}: non-positive close price ({candle.close})")

        # Check high >= low
        if candle.high < candle.low:
            errors.append(
                f"Candle {index}: high ({candle.high}) < low ({candle.low})"
            )

        # Check high >= open and high >= close
        if candle.high < candle.open or candle.high < candle.close:
            errors.append(
                f"Candle {index}: high ({candle.high}) is not the maximum"
            )

        # Check low <= open and low <= close
        if candle.low > candle.open or candle.low > candle.close:
            errors.append(
                f"Candle {index}: low ({candle.low}) is not the minimum"
            )

        # Check for negative volume
        if candle.volume < 0:
            errors.append(f"Candle {index}: negative volume ({candle.volume})")

        # Check for price anomalies (large jumps)
        if self.check_price_anomalies and prev_candle:
            price_change = abs(candle.open - prev_candle.close) / prev_candle.close
            if price_change > self.MAX_PRICE_CHANGE_PCT:
                errors.append(
                    f"Candle {index}: suspicious price jump "
                    f"({price_change:.1%} from previous close)"
                )

        return errors

    def _detect_gaps(
        self,
        data: list[OHLCV],
        timeframe: str,
    ) -> list[DataGap]:
        """
        Detect gaps in the time series.

        Args:
            data: List of OHLCV candles (must be sorted)
            timeframe: Expected candle interval

        Returns:
            List of detected gaps
        """
        if len(data) < 2:
            return []

        expected_interval = timedelta(seconds=self.TIMEFRAME_SECONDS[timeframe])
        gaps = []

        for i in range(1, len(data)):
            actual_diff = data[i].timestamp - data[i - 1].timestamp
            expected_candles = int(actual_diff / expected_interval) - 1

            if expected_candles > 0:
                gaps.append(DataGap(
                    start_time=data[i - 1].timestamp + expected_interval,
                    end_time=data[i].timestamp,
                    expected_candles=expected_candles,
                    gap_duration=actual_diff - expected_interval,
                ))

        return gaps

    def validate(self, data: list[OHLCV]) -> ValidationResult:
        """
        Validate a list of OHLCV data.

        Args:
            data: List of OHLCV candles

        Returns:
            ValidationResult with details of any issues found

        Raises:
            DataValidationError: If critical validation fails
        """
        if not data:
            raise DataValidationError("Empty data list")

        # Check all same symbol and timeframe
        symbols = set(c.symbol for c in data)
        timeframes = set(c.timeframe for c in data)

        if len(symbols) > 1:
            raise DataValidationError(f"Mixed symbols in data: {symbols}")
        if len(timeframes) > 1:
            raise DataValidationError(f"Mixed timeframes in data: {timeframes}")

        timeframe = data[0].timeframe
        if timeframe not in self.TIMEFRAME_SECONDS:
            raise DataValidationError(f"Unknown timeframe: {timeframe}")

        # Sort by timestamp
        sorted_data = sorted(data, key=lambda x: x.timestamp)

        # Check for timestamp ordering issues
        warnings = []
        if data != sorted_data:
            warnings.append("Data was not sorted by timestamp")

        # Validate each candle
        invalid_candles = []
        for i, candle in enumerate(sorted_data):
            prev_candle = sorted_data[i - 1] if i > 0 else None
            errors = self._validate_single_candle(candle, i, prev_candle)
            for error in errors:
                invalid_candles.append((i, error))

        # Detect gaps
        gaps = self._detect_gaps(sorted_data, timeframe)

        # Check gap tolerance
        critical_gaps = [g for g in gaps if g.expected_candles > self.max_gap_tolerance]
        if critical_gaps:
            gap_info = ", ".join(
                f"{g.start_time.isoformat()} ({g.expected_candles} candles)"
                for g in critical_gaps
            )
            warnings.append(f"Data has significant gaps: {gap_info}")

        is_valid = len(invalid_candles) == 0 and len(critical_gaps) == 0

        return ValidationResult(
            is_valid=is_valid,
            total_candles=len(data),
            gaps=gaps,
            invalid_candles=invalid_candles,
            warnings=warnings,
        )

    def fill_gaps(
        self,
        data: list[OHLCV],
        method: str = "forward",
    ) -> list[OHLCV]:
        """
        Fill gaps in OHLCV data.

        Args:
            data: List of OHLCV candles
            method: Fill method ("forward" uses previous close for all OHLC)

        Returns:
            List of OHLCV with gaps filled
        """
        if not data or len(data) < 2:
            return data

        sorted_data = sorted(data, key=lambda x: x.timestamp)
        timeframe = sorted_data[0].timeframe
        symbol = sorted_data[0].symbol
        expected_interval = timedelta(seconds=self.TIMEFRAME_SECONDS[timeframe])

        filled_data = [sorted_data[0]]

        for i in range(1, len(sorted_data)):
            prev_candle = sorted_data[i - 1]
            curr_candle = sorted_data[i]

            # Fill any gaps
            gap_time = prev_candle.timestamp + expected_interval
            while gap_time < curr_candle.timestamp:
                if method == "forward":
                    fill_price = prev_candle.close
                    filled_candle = OHLCV(
                        timestamp=gap_time,
                        symbol=symbol,
                        timeframe=timeframe,
                        open=fill_price,
                        high=fill_price,
                        low=fill_price,
                        close=fill_price,
                        volume=0.0,
                        quote_volume=0.0,
                    )
                    filled_data.append(filled_candle)
                gap_time += expected_interval

            filled_data.append(curr_candle)

        return filled_data
