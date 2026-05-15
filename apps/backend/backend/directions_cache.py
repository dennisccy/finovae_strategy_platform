"""File-based cache for initial direction backtest results.

Cache directory: /tmp/initial_directions/{cache_key}/

Cache key: {symbol}_{timeframe}_{startDate}_{endDate}_{exchange}_{allow_short}_{leverage}
  e.g. BTC_USDT_4h_2025-01-01_2025-12-31_binance_false_1

Per-direction storage (mirrors session_store iteration format):
  {cache_key}/
    {index:03d}_{direction_id}/
      prompt.txt, strategy.py, meta.json, insights.json
      timeframes/_primary/result.json, rating.json
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(os.environ.get("DIRECTIONS_CACHE_DIR", "/tmp/initial_directions"))

_MAX_EQUITY_PTS = 300
_MAX_TRADES = 200


# =============================================================================
# Helpers
# =============================================================================

def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json_safe(path: Path) -> Optional[object]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_dir(cache_key: str) -> Path:
    return BASE_DIR / cache_key


def _downsample(lst: list, max_pts: int) -> list:
    """Downsample a list to at most max_pts elements using uniform step."""
    if len(lst) <= max_pts:
        return lst
    step = len(lst) / max_pts
    return [lst[round(i * step)] for i in range(max_pts)]


def _trim_result(result: Optional[dict]) -> Optional[dict]:
    """Trim result dict: downsample equity_curve, cap trades."""
    if not isinstance(result, dict):
        return result
    out = dict(result)
    if isinstance(out.get("equity_curve"), list):
        out["equity_curve"] = _downsample(out["equity_curve"], _MAX_EQUITY_PTS)
    if isinstance(out.get("trades"), list):
        out["trades"] = out["trades"][:_MAX_TRADES]
    return out


def _trim_node(node_dict: dict) -> dict:
    """Return a trimmed copy of node_dict for storage."""
    out = dict(node_dict)
    out["result"] = _trim_result(out.get("result"))
    return out


def _find_iter_dir(cache_key: str, direction_id: str) -> Optional[Path]:
    cache_d = _cache_dir(cache_key)
    if not cache_d.exists():
        return None
    for d in cache_d.iterdir():
        if d.is_dir() and d.name.endswith(f"_{direction_id}"):
            return d
    return None


# =============================================================================
# Public API
# =============================================================================

def build_cache_key(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    exchange: str,
    allow_short: bool,
    leverage: int,
) -> str:
    """Build a filesystem-safe cache key from backtest parameters."""
    safe_symbol = symbol.replace("/", "_").replace("\\", "_")
    
    # Ensure leverage is represented as an integer string (e.g., '1' instead of '1.0')
    try:
        leverage_str = str(int(float(leverage)))
    except (ValueError, TypeError):
        leverage_str = str(leverage)
        
    return (
        f"{safe_symbol}_{timeframe}_{start_date}_{end_date}"
        f"_{exchange}_{str(allow_short).lower()}_{leverage_str}"
    )


def has_cache(cache_key: str) -> bool:
    """Return True if any cached data exists for this key."""
    return _cache_dir(cache_key).exists()


def write_direction_result(
    cache_key: str,
    index: int,
    direction_id: str,
    node_dict: dict,
) -> None:
    """Write (or overwrite) one direction result to the cache."""
    trimmed = _trim_node(node_dict)

    existing = _find_iter_dir(cache_key, direction_id)
    if existing:
        iter_dir = existing
    else:
        _ensure_dir(_cache_dir(cache_key))
        iter_dir = _cache_dir(cache_key) / f"{index:03d}_{direction_id}"
        iter_dir.mkdir(parents=True, exist_ok=True)

    (iter_dir / "prompt.txt").write_text(trimmed.get("prompt", ""), encoding="utf-8")
    (iter_dir / "strategy.py").write_text(trimmed.get("scriptCode", ""), encoding="utf-8")
    (iter_dir / "insights.json").write_text(
        json.dumps(trimmed.get("insights"), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _BULK_KEYS = {"prompt", "scriptCode", "insights", "result", "rating", "timeframeResults"}
    meta = {k: v for k, v in trimmed.items() if k not in _BULK_KEYS}
    (iter_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # result/rating — stored under the actual timeframe directory
    params = trimmed.get("params") or {}
    timeframe = params.get("timeframe") or (params.get("timeframes") or ["4h"])[0]
    primary_result = trimmed.get("result")
    primary_rating = trimmed.get("rating")
    if primary_result is not None or primary_rating is not None:
        tf_dir = iter_dir / "timeframes" / timeframe
        tf_dir.mkdir(parents=True, exist_ok=True)
        (tf_dir / "result.json").write_text(
            json.dumps(primary_result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (tf_dir / "rating.json").write_text(
            json.dumps(primary_rating, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def list_cached_directions(cache_key: str) -> list[dict]:
    """Return lightweight summaries for all cached directions (sorted by index)."""
    cache_d = _cache_dir(cache_key)
    if not cache_d.exists():
        return []

    summaries = []
    for iter_dir in sorted(cache_d.iterdir()):
        if not iter_dir.is_dir():
            continue
        meta = _read_json_safe(iter_dir / "meta.json")
        if not isinstance(meta, dict):
            continue

        tf_base = iter_dir / "timeframes"
        result = None
        if tf_base.exists():
            for tf_dir in sorted(tf_base.iterdir()):
                if not tf_dir.is_dir() or tf_dir.name == "_primary":
                    continue
                result = _read_json_safe(tf_dir / "result.json")
                if result is not None:
                    break
            if result is None:
                pdir = tf_base / "_primary"
                result = _read_json_safe(pdir / "result.json") if pdir.exists() else None
        if not isinstance(result, dict):
            result = None

        dir_parts = iter_dir.name.split("_", 1)
        direction_id = dir_parts[1] if len(dir_parts) > 1 else iter_dir.name
        summaries.append({
            "directionId": direction_id,
            "title": meta.get("strategyName", ""),
            "tagline": meta.get("changeSummary", ""),
            "totalReturn": (result.get("total_return") or 0) if result else 0,
            "winRate": (result.get("win_rate") or 0) if result else 0,
            "numTrades": (result.get("num_trades") or 0) if result else 0,
            "sharpe": (result.get("sharpe_ratio") or 0) if result else 0,
            "maxDrawdown": (result.get("max_drawdown") or 0) if result else 0,
            "status": meta.get("status", "complete"),
        })

    return summaries


def read_direction_full(cache_key: str, direction_id: str) -> Optional[dict]:
    """Reassemble all files for one cached direction into a complete node dict."""
    iter_dir = _find_iter_dir(cache_key, direction_id)
    if iter_dir is None:
        return None

    meta_raw = _read_json_safe(iter_dir / "meta.json")
    if not isinstance(meta_raw, dict):
        return None

    node: dict = dict(meta_raw)

    prompt_path = iter_dir / "prompt.txt"
    node["prompt"] = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

    script_path = iter_dir / "strategy.py"
    node["scriptCode"] = script_path.read_text(encoding="utf-8") if script_path.exists() else ""

    node["insights"] = _read_json_safe(iter_dir / "insights.json")

    tf_base = iter_dir / "timeframes"
    node["result"] = None
    node["rating"] = None
    if tf_base.exists():
        for tf_dir in sorted(tf_base.iterdir()):
            if not tf_dir.is_dir() or tf_dir.name == "_primary":
                continue
            result_data = _read_json_safe(tf_dir / "result.json")
            if result_data is not None:
                node["result"] = result_data
                node["rating"] = _read_json_safe(tf_dir / "rating.json")
                break
        if node["result"] is None:
            pdir = tf_base / "_primary"
            node["result"] = _read_json_safe(pdir / "result.json")
            node["rating"] = _read_json_safe(pdir / "rating.json")
    node["timeframeResults"] = []
    
    # Backfill missing properties required by the frontend IterationNode
    if "id" not in node:
        node["id"] = direction_id
    if "status" not in node:
        node["status"] = "complete"
    if "strategyName" not in node or node["strategyName"] == "Restored Strategy":
        node["strategyName"] = node.get("prompt", "Strategy")
    if "timestamp" not in node:
        import datetime
        mtime = (iter_dir / "meta.json").stat().st_mtime if (iter_dir / "meta.json").exists() else 0
        node["timestamp"] = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).isoformat() if mtime else datetime.datetime.now(datetime.timezone.utc).isoformat()
        
    res = node.get("result")
    if isinstance(res, dict):
        node["totalReturn"] = res.get("total_return", 0)
        node["winRate"] = res.get("win_rate", 0)
        node["numTrades"] = res.get("num_trades", 0)
        node["sharpe"] = res.get("sharpe_ratio", 0)
        node["maxDrawdown"] = res.get("max_drawdown", 0)

    return node
