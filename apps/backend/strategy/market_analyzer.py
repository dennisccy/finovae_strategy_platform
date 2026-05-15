"""
Market Analyzer Wrapper

Wraps the TechnicalAnalyzer skill for use as a tool_use response
in the ScriptGenerator's multi-turn conversation with Claude.
"""

import sys
import os
from typing import Any

import pandas as pd

from shared.contracts import OHLCV

# Add the skills directory to the path so we can import the analyzer
_SKILL_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", ".claude", "skills",
                 "crypto-ta-analyzer", "scripts")
)


def analyze_market(ohlcv_data: list[OHLCV]) -> dict[str, Any]:
    """
    Run full technical analysis on OHLCV data and return a structured
    result suitable for a tool_use response.

    Args:
        ohlcv_data: List of OHLCV contract objects from the data loader.

    Returns:
        Dict with regime, signal, key indicator values, divergences, etc.
    """
    # Convert contracts to DataFrame
    records = [
        {
            "timestamp": bar.timestamp,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in ohlcv_data
    ]
    df = pd.DataFrame(records)
    df = df.rename(columns={"timestamp": "time"})
    # Strip timezone from the time column — TechnicalAnalyzer uses np.issubdtype
    # which cannot handle tz-aware dtypes like datetime64[us, UTC]
    if pd.api.types.is_datetime64_any_dtype(df["time"]) and df["time"].dt.tz is not None:
        df["time"] = df["time"].dt.tz_convert("UTC").dt.tz_localize(None)

    # Import TechnicalAnalyzer (add skill dir to path temporarily)
    if _SKILL_DIR not in sys.path:
        sys.path.insert(0, _SKILL_DIR)
    from ta_analyzer import TechnicalAnalyzer  # type: ignore[import-untyped]

    analyzer = TechnicalAnalyzer(df)
    raw = analyzer.analyze_all()

    # Return a focused subset that's useful for strategy generation
    regime = raw.get("regime", {})
    return {
        "market_regime": regime.get("regime", "UNKNOWN"),
        "adx": regime.get("adx"),
        "atr_pct": regime.get("atr_pct"),
        "trend_direction": raw.get("tradeSignalV2", "NEUTRAL"),
        "signal_7tier": raw.get("tradeSignal7Tier", "NEUTRAL"),
        "normalized_score": raw.get("normalizedScore"),
        "confidence": raw.get("confidence"),
        "current_price": raw.get("currentPrice"),
        "price_change_24h": raw.get("priceChange24h"),
        "divergences": raw.get("divergences", {}),
        "squeeze_detected": raw.get("squeezeDetected", False),
        "volume_confirmation": raw.get("volumeConfirmation"),
        "key_indicators": {
            "rsi": raw.get("indicatorValues", {}).get("RSI"),
            "macd_hist": raw.get("indicatorValues", {}).get("MACD", {}).get("histogram")
                if isinstance(raw.get("indicatorValues", {}).get("MACD"), dict)
                else raw.get("indicatorValues", {}).get("MACD"),
            "bb_position": raw.get("indicatorValues", {}).get("BB"),
            "obv_signal": raw.get("individualSignals", {}).get("OBV"),
            "ichimoku_signal": raw.get("individualSignals", {}).get("ICHIMOKU"),
            "ema_signal": raw.get("individualSignals", {}).get("EMA"),
            "mfi": raw.get("indicatorValues", {}).get("MFI"),
        },
        "warnings": raw.get("warnings", []),
    }
