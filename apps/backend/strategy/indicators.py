"""
Indicator Registry and Implementations

Whitelisted technical indicators for strategy execution.
All indicators are implemented using pandas/numpy for sandbox safety.
"""

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd


@dataclass
class IndicatorFunction:
    """Registered indicator function."""
    name: str
    func: Callable[[pd.DataFrame, dict], pd.Series]
    params: dict[str, tuple[type, any]]  # param_name: (type, default)
    description: str


def _sma(df: pd.DataFrame, params: dict) -> pd.Series:
    """Simple Moving Average."""
    period = params.get("period", 20)
    return df["close"].rolling(window=period).mean()


def _ema(df: pd.DataFrame, params: dict) -> pd.Series:
    """Exponential Moving Average."""
    period = params.get("period", 20)
    return df["close"].ewm(span=period, adjust=False).mean()


def _rsi(df: pd.DataFrame, params: dict) -> pd.Series:
    """Relative Strength Index."""
    period = params.get("period", 14)
    delta = df["close"].diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def _macd(df: pd.DataFrame, params: dict) -> pd.Series:
    """MACD Line."""
    fast = params.get("fast_period", 12)
    slow = params.get("slow_period", 26)

    fast_ema = df["close"].ewm(span=fast, adjust=False).mean()
    slow_ema = df["close"].ewm(span=slow, adjust=False).mean()

    return fast_ema - slow_ema


def _macd_signal(df: pd.DataFrame, params: dict) -> pd.Series:
    """MACD Signal Line."""
    fast = params.get("fast_period", 12)
    slow = params.get("slow_period", 26)
    signal = params.get("signal_period", 9)

    macd = _macd(df, {"fast_period": fast, "slow_period": slow})
    return macd.ewm(span=signal, adjust=False).mean()


def _macd_hist(df: pd.DataFrame, params: dict) -> pd.Series:
    """MACD Histogram."""
    fast = params.get("fast_period", 12)
    slow = params.get("slow_period", 26)
    signal = params.get("signal_period", 9)

    macd = _macd(df, {"fast_period": fast, "slow_period": slow})
    macd_sig = _macd_signal(df, {"fast_period": fast, "slow_period": slow, "signal_period": signal})

    return macd - macd_sig


def _bollinger_upper(df: pd.DataFrame, params: dict) -> pd.Series:
    """Bollinger Band Upper."""
    period = params.get("period", 20)
    std_dev = params.get("std_dev", 2.0)

    middle = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()

    return middle + (std * std_dev)


def _bollinger_middle(df: pd.DataFrame, params: dict) -> pd.Series:
    """Bollinger Band Middle (SMA)."""
    period = params.get("period", 20)
    return df["close"].rolling(window=period).mean()


def _bollinger_lower(df: pd.DataFrame, params: dict) -> pd.Series:
    """Bollinger Band Lower."""
    period = params.get("period", 20)
    std_dev = params.get("std_dev", 2.0)

    middle = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()

    return middle - (std * std_dev)


def _atr(df: pd.DataFrame, params: dict) -> pd.Series:
    """Average True Range."""
    period = params.get("period", 14)

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    return tr.rolling(window=period).mean()


def _adx(df: pd.DataFrame, params: dict) -> pd.Series:
    """Average Directional Index."""
    period = params.get("period", 14)

    # Calculate +DM and -DM
    up_move = df["high"].diff()
    down_move = -df["low"].diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    # Calculate ATR
    atr = _atr(df, {"period": period})

    # Smooth +DM and -DM
    plus_dm_smooth = pd.Series(plus_dm, index=df.index).rolling(window=period).mean()
    minus_dm_smooth = pd.Series(minus_dm, index=df.index).rolling(window=period).mean()

    # Calculate +DI and -DI
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)

    # Calculate DX and ADX
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))

    return dx.rolling(window=period).mean()


def _stoch_k(df: pd.DataFrame, params: dict) -> pd.Series:
    """Stochastic %K."""
    period = params.get("period", 14)

    lowest_low = df["low"].rolling(window=period).min()
    highest_high = df["high"].rolling(window=period).max()

    return 100 * (df["close"] - lowest_low) / (highest_high - lowest_low)


def _stoch_d(df: pd.DataFrame, params: dict) -> pd.Series:
    """Stochastic %D (smoothed %K)."""
    period = params.get("period", 14)
    smooth = params.get("smooth", 3)

    stoch_k = _stoch_k(df, {"period": period})
    return stoch_k.rolling(window=smooth).mean()


def _cci(df: pd.DataFrame, params: dict) -> pd.Series:
    """Commodity Channel Index."""
    period = params.get("period", 20)

    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

    return (tp - sma) / (0.015 * mad)


def _williams_r(df: pd.DataFrame, params: dict) -> pd.Series:
    """Williams %R."""
    period = params.get("period", 14)

    highest_high = df["high"].rolling(window=period).max()
    lowest_low = df["low"].rolling(window=period).min()

    return -100 * (highest_high - df["close"]) / (highest_high - lowest_low)


def _obv(df: pd.DataFrame, params: dict) -> pd.Series:
    """On-Balance Volume."""
    direction = np.where(df["close"] > df["close"].shift(), 1,
                        np.where(df["close"] < df["close"].shift(), -1, 0))
    return (direction * df["volume"]).cumsum()


def _vwap(df: pd.DataFrame, params: dict) -> pd.Series:
    """Volume Weighted Average Price (rolling)."""
    period = params.get("period", 20)

    tp = (df["high"] + df["low"] + df["close"]) / 3
    tp_vol = tp * df["volume"]

    return tp_vol.rolling(window=period).sum() / df["volume"].rolling(window=period).sum()


def _mfi(df: pd.DataFrame, params: dict) -> pd.Series:
    """Money Flow Index."""
    period = params.get("period", 14)

    tp = (df["high"] + df["low"] + df["close"]) / 3
    mf = tp * df["volume"]

    positive_mf = np.where(tp > tp.shift(), mf, 0.0)
    negative_mf = np.where(tp < tp.shift(), mf, 0.0)

    positive_mf_sum = pd.Series(positive_mf, index=df.index).rolling(window=period).sum()
    negative_mf_sum = pd.Series(negative_mf, index=df.index).rolling(window=period).sum()

    mfr = positive_mf_sum / negative_mf_sum

    return 100 - (100 / (1 + mfr))


def _roc(df: pd.DataFrame, params: dict) -> pd.Series:
    """Rate of Change."""
    period = params.get("period", 12)
    return 100 * (df["close"] - df["close"].shift(period)) / df["close"].shift(period)


def _momentum(df: pd.DataFrame, params: dict) -> pd.Series:
    """Momentum."""
    period = params.get("period", 10)
    return df["close"] - df["close"].shift(period)


# Indicator Registry - WHITELIST
INDICATOR_REGISTRY: dict[str, IndicatorFunction] = {
    "sma": IndicatorFunction(
        name="sma",
        func=_sma,
        params={"period": (int, 20)},
        description="Simple Moving Average",
    ),
    "ema": IndicatorFunction(
        name="ema",
        func=_ema,
        params={"period": (int, 20)},
        description="Exponential Moving Average",
    ),
    "rsi": IndicatorFunction(
        name="rsi",
        func=_rsi,
        params={"period": (int, 14)},
        description="Relative Strength Index (0-100)",
    ),
    "macd": IndicatorFunction(
        name="macd",
        func=_macd,
        params={"fast_period": (int, 12), "slow_period": (int, 26)},
        description="MACD Line",
    ),
    "macd_signal": IndicatorFunction(
        name="macd_signal",
        func=_macd_signal,
        params={"fast_period": (int, 12), "slow_period": (int, 26), "signal_period": (int, 9)},
        description="MACD Signal Line",
    ),
    "macd_hist": IndicatorFunction(
        name="macd_hist",
        func=_macd_hist,
        params={"fast_period": (int, 12), "slow_period": (int, 26), "signal_period": (int, 9)},
        description="MACD Histogram",
    ),
    "bollinger_upper": IndicatorFunction(
        name="bollinger_upper",
        func=_bollinger_upper,
        params={"period": (int, 20), "std_dev": (float, 2.0)},
        description="Bollinger Band Upper",
    ),
    "bollinger_middle": IndicatorFunction(
        name="bollinger_middle",
        func=_bollinger_middle,
        params={"period": (int, 20)},
        description="Bollinger Band Middle",
    ),
    "bollinger_lower": IndicatorFunction(
        name="bollinger_lower",
        func=_bollinger_lower,
        params={"period": (int, 20), "std_dev": (float, 2.0)},
        description="Bollinger Band Lower",
    ),
    "atr": IndicatorFunction(
        name="atr",
        func=_atr,
        params={"period": (int, 14)},
        description="Average True Range",
    ),
    "adx": IndicatorFunction(
        name="adx",
        func=_adx,
        params={"period": (int, 14)},
        description="Average Directional Index",
    ),
    "stoch_k": IndicatorFunction(
        name="stoch_k",
        func=_stoch_k,
        params={"period": (int, 14)},
        description="Stochastic %K",
    ),
    "stoch_d": IndicatorFunction(
        name="stoch_d",
        func=_stoch_d,
        params={"period": (int, 14), "smooth": (int, 3)},
        description="Stochastic %D",
    ),
    "cci": IndicatorFunction(
        name="cci",
        func=_cci,
        params={"period": (int, 20)},
        description="Commodity Channel Index",
    ),
    "williams_r": IndicatorFunction(
        name="williams_r",
        func=_williams_r,
        params={"period": (int, 14)},
        description="Williams %R (-100 to 0)",
    ),
    "obv": IndicatorFunction(
        name="obv",
        func=_obv,
        params={},
        description="On-Balance Volume",
    ),
    "vwap": IndicatorFunction(
        name="vwap",
        func=_vwap,
        params={"period": (int, 20)},
        description="Volume Weighted Average Price",
    ),
    "mfi": IndicatorFunction(
        name="mfi",
        func=_mfi,
        params={"period": (int, 14)},
        description="Money Flow Index (0-100)",
    ),
    "roc": IndicatorFunction(
        name="roc",
        func=_roc,
        params={"period": (int, 12)},
        description="Rate of Change (%)",
    ),
    "momentum": IndicatorFunction(
        name="momentum",
        func=_momentum,
        params={"period": (int, 10)},
        description="Momentum (price difference)",
    ),
}


def compute_indicator(
    df: pd.DataFrame,
    indicator_name: str,
    params: Optional[dict] = None,
) -> pd.Series:
    """
    Compute an indicator value.

    Args:
        df: DataFrame with OHLCV data
        indicator_name: Name of indicator from registry
        params: Indicator parameters (uses defaults if None)

    Returns:
        Series of indicator values

    Raises:
        ValueError: If indicator not in whitelist
    """
    if indicator_name not in INDICATOR_REGISTRY:
        raise ValueError(
            f"Unknown indicator: {indicator_name}. "
            f"Available: {list(INDICATOR_REGISTRY.keys())}"
        )

    indicator = INDICATOR_REGISTRY[indicator_name]
    final_params = {}

    # Apply defaults
    for param_name, (param_type, default) in indicator.params.items():
        if params and param_name in params:
            final_params[param_name] = param_type(params[param_name])
        else:
            final_params[param_name] = default

    return indicator.func(df, final_params)


def get_indicator_names() -> list[str]:
    """Get list of available indicator names."""
    return list(INDICATOR_REGISTRY.keys())


def get_indicator_info(name: str) -> Optional[IndicatorFunction]:
    """Get indicator info by name."""
    return INDICATOR_REGISTRY.get(name)
