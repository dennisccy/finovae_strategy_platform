"""
AI Script Generator

Generates Python Strategy class scripts directly from natural language
using Claude API. Produces scripts that conform to the Strategy class interface
for use in backtesting and (future) live execution.

Optimized for token efficiency:
- Single-turn generation with pre-filled tool results (no multi-turn overhead)
- Prompt caching via cache_control markers on system prompt
- Auto-downgrade to Haiku for refinement iterations
- Context-aware system prompt (first-gen vs refinement rules only)
"""

import json
import logging
import os
from typing import Any, Optional

from anthropic import Anthropic
from openai import BadRequestError, OpenAI

from shared.contracts import OHLCV
from shared.model_catalog import (
    DEFAULT_MODEL,
    HAIKU_MODEL,
    OPENAI_MAX_COMPLETION_TOKENS,
    SONNET_MODEL,
    is_openai_model,
)

logger = logging.getLogger(__name__)


class ScriptGeneratorError(Exception):
    """Exception raised for script generation errors."""
    pass


# ---------------------------------------------------------------------------
# System prompt — split into stable base + context-specific sections
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_BASE = """You are a trading strategy code generator. You write Python strategy classes for a backtesting engine.

Output ONLY a valid Python script (no markdown, no explanations, no code fences) that defines a Strategy class with this interface:

```
import numpy as np
import pandas as pd

class Strategy:
    name = "Strategy Name Here"
    description = "One-sentence description of what the strategy does"
    symbol = "BTC/USDT"       # REQUIRED: the trading pair this strategy was designed for

    # REQUIRED: Risk management parameters (used by the backtest engine)
    stop_loss_pct = 0.03      # e.g. 3% stop-loss (float, 0.01-0.15)
    take_profit_pct = 0.06    # e.g. 6% take-profit (float, must be >= 2x stop_loss_pct)
    position_size_pct = 0.01  # position size as fraction of account (float, 0.005-0.02)

    # REQUIRED: must match the trading timeframe this strategy was designed for
    timeframe = "1h"   # e.g. "1m", "5m", "15m", "1h", "4h", "1d"

    leverage = 1  # Used by trading client to set position leverage (REQUIRED, always emit)

    def setup(self, df: pd.DataFrame) -> pd.DataFrame:
        \"\"\"Compute indicators once. Add as columns to df. Called before backtest loop.\"\"\"
        return df

    def signal(self, df: pd.DataFrame, i: int) -> int:
        \"\"\"Per-bar signal. Return 1 (buy), -1 (sell), 0 (hold).\"\"\"
```

STOP-LOSS AND TAKE-PROFIT RULES:
- stop_loss_pct and take_profit_pct are MANDATORY class attributes.
- The engine enforces these automatically. take_profit_pct MUST be >= 2x stop_loss_pct.
- Calibrate to market: TRENDING → wider stops (1.5-2x ATR%), RANGING → tighter (1-2%).
- Typical ranges: stop_loss_pct 0.02-0.08, take_profit_pct 0.04-0.20.
- position_size_pct is MANDATORY. Valid range: 0.005 to 0.02 (0.5% to 2% of account per trade).
- leverage is MANDATORY (always emit). Default to 1 for non-leveraged strategies. When leverage > 1:
  • Set position_size_pct ≤ 1/leverage to avoid margin calls (e.g. leverage=2 → position_size_pct ≤ 0.5, use 0.4 for safety).
  • A losing trade must not exceed the margin posted. Keep position_size_pct conservative.

SIGNAL CONVENTION (v0.7):
  1  = go long  (open long; ignored if already long)
  -1 = go short if allow_short enabled and flat; else exit long if long
   0 = hold
   2 = flatten (close any open position regardless of direction)

Existing scripts using 1=buy, -1=sell, 0=hold are FULLY BACKWARD COMPATIBLE.

OPTIONAL CLASS ATTRIBUTES (v0.7):
  allow_short = True    # hint only — actual shorts require user to enable in UI

NOTE: leverage is now REQUIRED (always emit it). Default to 1 for non-leveraged strategies.

STRICT RULES:
1. Only use numpy and pandas. No other imports.
2. setup() adds indicator columns to df and returns it.
3. signal() returns 1 (buy), -1 (sell), 0 (hold), or 2 (flatten). ONLY access indices <= i.
4. Handle NaN from warmup — return 0 if indicators aren't ready.
5. No file I/O, network, exec, eval, __import__, os, sys, subprocess.
6. NEVER use names starting with underscore `_`. Sandbox rejects them.
7. NEVER use augmented assignment on attributes: `self.x += y` is BANNED. Write `self.x = self.x + y` instead. This applies to ALL operators (+=, -=, *=, /=, etc.) on any attribute.
8. NEVER use `nonlocal` statements. They are not allowed in the sandbox.

INDICATOR REFERENCE (use in setup()):
- SMA: df['sma_N'] = df['close'].rolling(window=N).mean()
- EMA: df['ema_N'] = df['close'].ewm(span=N, adjust=False).mean()
- RSI: delta→gain/loss rolling→rs→100-(100/(1+rs))
- MACD: EMA12 - EMA26, signal = EMA9 of MACD
- Bollinger: mid=SMA20, upper/lower = mid ± 2*std
- ATR: max(H-L, |H-prevC|, |L-prevC|) rolling
- Stochastic: %K = (C-lowN)/(highN-lowN)*100, %D = SMA3 of %K
- Crossover: if i>=1 and fast[i-1]<=slow[i-1] and fast[i]>slow[i]: return 1

TIMEFRAME PERIODS:
- 1m/5m: EMA 5/13 or RSI(7). 15m: EMA 9/21 or RSI(10). 1h/4h: EMA 9/21 or SMA 10/30. 1d: SMA 10/30 or EMA 12/26.
- NEVER use SMA 200 on 4h (needs 800+ bars). Default: EMA 9/21 crossover.

MARKET REGIME: TRENDING → trend-following (MA crossover, MACD, ADX). RANGING → mean-reversion (RSI, BB, Stochastic).

EXIT TRAP PREVENTION (CRITICAL):
- A strategy that enters a position and NEVER exits will wipe the account. This is the worst possible bug.
- BANNED exit patterns: "exit only when RSI > 70" (RSI may never reach 70 in a downtrend), "exit only when price > N-bar high" (may never occur if trend reverses), any single-sided threshold with no fallback.
- REQUIRED: Use exits that are GUARANTEED to eventually trigger. Best options:
  (a) Crossover exits — fast_ema crosses slow_ema ALWAYS eventually happens. Preferred.
  (b) Opposite signal — RSI enters overbought zone after being oversold. Only safe if the zone is reachable.
  (c) Price relative to EMA — price crossing EMA always eventually happens.
- FORBIDDEN: Writing an entry condition (e.g. RSI < 30) and an exit that requires the SAME indicator to reach the opposite extreme (RSI > 70) WITHOUT a secondary exit fallback.
- Mental test before writing: "If price trends against my position for 50 bars straight, will the exit condition ever fire?" If NO, the strategy is invalid."""

_FIRST_GEN_RULES = """
FIRST GENERATION RULES:
- MUST produce trades. Simplicity > sophistication.
- Use 1-2 indicators max. ONE entry + ONE exit condition.
- BANNED: multi-indicator AND conditions, SMA 200, complex multi-step logic.
- Goal: a trading BASELINE. Enhancements come in later iterations."""

_REFINEMENT_RULES = """
REFINEMENT RULES:
- You may add complexity: combine indicators, add filters.
- Aim for 50–300 trades over the backtest period. Below 50 = statistically unreliable.
- If previous had < 20 trades, relax conditions significantly before adding complexity.
- If previous had 0 trades, simplify drastically.
- Re-evaluate stop_loss_pct and take_profit_pct for market conditions."""

_SHORT_FIRST_GEN_RULES = """
SHORT-AWARE FIRST GENERATION RULES:
- Allow Shorts is ENABLED. You MUST generate a BIDIRECTIONAL strategy (both long AND short).
- MUST produce BOTH long AND short trades — do NOT generate a long-only strategy.
- signal 1  = "bullish state" → open LONG if flat
- signal -1 = "bearish state" → open SHORT if flat (allow_short=True); close LONG if long
- signal 0  = neutral / hold
- Use 1-2 indicators. Mirror entry conditions: bullish = inverse of bearish.
- BEST BIDIRECTIONAL INDICATORS: EMA crossover, MACD crossover, RSI vs midline (50).
- Example pattern: fast_ema > slow_ema → return 1 (bullish); fast_ema < slow_ema → return -1 (bearish)
- BANNED: long-only logic, SMA 200, complex multi-step filters that prevent short entries."""

_SHORT_REFINEMENT_RULES = """
SHORT-AWARE REFINEMENT RULES:
- Allow Shorts is ENABLED. MAINTAIN bidirectional trading — both 1 and -1 signals MUST fire trades.
- If previous backtest had 0 short trades: FIX the short entry condition — do not increase complexity until both directions trade.
- If previous backtest had 0 long trades: FIX the long entry condition.
- Add complexity (filters, confirmation) only after BOTH directions are producing trades."""


def _build_system_prompt(is_refinement: bool, allow_short: bool = False) -> str:
    """Build system prompt with only the relevant rules section."""
    if allow_short:
        rules = _SHORT_REFINEMENT_RULES if is_refinement else _SHORT_FIRST_GEN_RULES
    else:
        rules = _REFINEMENT_RULES if is_refinement else _FIRST_GEN_RULES
    return _SYSTEM_PROMPT_BASE + rules + "\n\nRemember: output ONLY the Python code, nothing else."


# ---------------------------------------------------------------------------
# Static tool content (risk rules + trading plan)
# ---------------------------------------------------------------------------

_RISK_RULES = """Risk Management Rules:
- Trade count inversely correlates with performance in flat markets (fewer = better)
- Adapt frequency to regime: choppy = 0-10 trades/24h max
- 2% equity risk per trade with 2:1 reward ratio = best performance
- Stop-losses on EVERY position (ATR-based 1.5-2x or percentage 2-5%)
- Position sizing: max 25% equity per trade, reduce in high volatility
- Trending: 5-30 trades/period. Ranging: 0-10. High frequency (100+) = losses."""

_TRADING_PLAN = """Trading Plan Guidelines:
- Stop-Loss: Percentage (2-5%), ATR-based (1.5-2x ATR), or support/resistance level
- Take-Profit: Fixed R multiple (2R min), trailing stop, or resistance target
- 2R Minimum Rule: take_profit_pct >= 2x stop_loss_pct. Profitable at 40% win rate.
- Position Sizing: Risk = Account * 0.02, Position = Risk / (Entry - Stop)
- Regime: Trending → wider stops, trailing. Ranging → tighter stops, fixed targets."""


class ScriptGenerator:
    """
    Generates Python Strategy class scripts from natural language descriptions.

    Token optimizations:
    - Single-turn: pre-fills all tool results into user message (no multi-turn)
    - Prompt caching: cache_control on system prompt for Anthropic cache hits
    - Model routing: auto-downgrades to Haiku for refinement iterations
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._client: Optional[Anthropic] = None
        self._openai_client: Optional[OpenAI] = None

    def _get_client(self) -> Anthropic:
        if not self.api_key:
            raise ScriptGeneratorError(
                "ANTHROPIC_API_KEY not set. Please set the environment variable."
            )
        if not self._client:
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def _get_openai_client(self) -> OpenAI:
        if not self.openai_api_key:
            raise ScriptGeneratorError(
                "OPENAI_API_KEY not set. Please set the environment variable for OpenAI models."
            )
        if not self._openai_client:
            self._openai_client = OpenAI(api_key=self.openai_api_key)
        return self._openai_client

    def generate(
        self,
        natural_language: str,
        previous_script_code: Optional[str] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        previous_backtest_metrics: Optional[dict] = None,
        ohlcv_data: Optional[list[OHLCV]] = None,
        allow_short: bool = False,
        leverage: float = 1.0,
    ) -> tuple[str, str, str, list[str]]:
        """
        Generate a Strategy class script from natural language.

        Single-turn call: pre-computes all tool results and injects them
        into the user message for maximum token efficiency.

        Args:
            natural_language: User's strategy description in plain English
            previous_script_code: If provided, refine this script (refinement mode)
            symbol: Trading symbol (e.g. "PEPE/USDT")
            timeframe: Candle timeframe (e.g. "4h")
            start_date: Backtest start date string
            end_date: Backtest end date string
            previous_backtest_metrics: Dict of metrics from previous backtest
            ohlcv_data: OHLCV data for market analysis

        Returns:
            Tuple of (script_code, strategy_name, strategy_description, errors)
        """
        try:
            is_refinement = previous_script_code is not None

            # --- Determine model ---
            # Auto-downgrade to Haiku for refinements unless user explicitly
            # selected a higher model (checked by whether self.model was
            # overridden from the default).
            effective_model = self.model
            if is_refinement and self.model == SONNET_MODEL:
                effective_model = HAIKU_MODEL
                logger.info("ScriptGenerator: auto-downgraded to Haiku for refinement")

            # --- Build user message with pre-filled tool results ---
            user_parts: list[str] = []

            # Leverage context injection (always when leverage > 1)
            if leverage > 1:
                safe_size = round(0.9 / leverage, 3)  # conservative: ~90% of 1/leverage
                lev_ctx = (
                    f"\n\nCRITICAL CONTEXT — Leverage is {leverage}x:\n"
                    f"- Set `leverage = {int(leverage) if leverage == int(leverage) else leverage}` in the class body.\n"
                    f"- With {leverage}x leverage, a price move of {100/leverage:.0f}% against you wipes your margin.\n"
                    f"- MANDATORY: set position_size_pct ≤ {safe_size} (conservative sizing to avoid margin calls).\n"
                    f"- Use tight stop-losses (stop_loss_pct ≤ {round(0.5/leverage, 3)}) to exit before margin call.\n"
                )
                user_parts.append(lev_ctx)

            # Short-aware context injection
            if allow_short:
                short_ctx = (
                    "\n\nCRITICAL CONTEXT — Allow Shorts is ENABLED:\n"
                    "The backtest engine will open SHORT positions when signal=-1 and the position is flat.\n"
                    "Your strategy MUST return -1 for bearish conditions AND 1 for bullish conditions.\n"
                    "A strategy that only returns 1 (buy) and -1 (sell/exit) is NOT acceptable — "
                    "ensure that when flat and bearish, -1 actually opens a short trade.\n"
                )
                user_parts.append(short_ctx)

            # Pre-fill market analysis
            if ohlcv_data is not None:
                try:
                    from strategy.market_analyzer import analyze_market
                    market_result = analyze_market(ohlcv_data)
                    user_parts.append(
                        f"MARKET ANALYSIS:\n{json.dumps(market_result, default=str, indent=None)}"
                    )
                except Exception as e:
                    logger.warning("analyze_market failed: %s", e)

            # Pre-fill static tool content
            user_parts.append(_RISK_RULES)
            user_parts.append(_TRADING_PLAN)

            # Market context
            if symbol or timeframe or start_date or end_date:
                ctx = "MARKET CONTEXT:\n"
                if symbol:
                    ctx += f"- Symbol: {symbol}\n"
                    ctx += f'  • Set class attribute `symbol = "{symbol}"` — MUST match the {symbol} symbol above.\n'
                if timeframe:
                    ctx += f"- Timeframe: {timeframe}\n"
                    ctx += f'  • Set class attribute `timeframe = "{timeframe}"` — MUST match the {timeframe} context above.\n'
                if start_date and end_date:
                    ctx += f"- Date range: {start_date} to {end_date}\n"
                    bar_count = self._estimate_bar_count(timeframe, start_date, end_date)
                    if bar_count:
                        ctx += f"- Approximate bars: {bar_count}\n"
                ctx += "\nCalibrate indicator periods for this timeframe and data window."
                user_parts.append(ctx)

            # Backtest feedback
            if previous_backtest_metrics:
                fb = "PREVIOUS BACKTEST RESULTS:\n"
                for key, val in previous_backtest_metrics.items():
                    fb += f"- {key}: {val}\n"
                num_trades = previous_backtest_metrics.get("num_trades", None)
                if num_trades is not None and num_trades == 0:
                    fb += "\nCRITICAL: Zero trades. Use much shorter periods and far less restrictive conditions.\n"
                elif num_trades is not None and num_trades < 5:
                    fb += f"\nCRITICAL: Only {num_trades} trades — statistically useless. Drastically relax all entry conditions.\n"
                elif num_trades is not None and num_trades < 20:
                    fb += f"\nWARNING: Only {num_trades} trades — too few to be reliable. Loosen entry filters, use faster indicators.\n"
                elif num_trades is not None and num_trades < 50:
                    fb += f"\nNOTE: {num_trades} trades — borderline. Consider relaxing one condition to increase frequency.\n"
                user_parts.append(fb)

            # Main request
            if is_refinement:
                user_parts.append(
                    f"CURRENT STRATEGY CODE:\n```python\n{previous_script_code}\n```\n\n"
                    f"Modify it according to: {natural_language}"
                )
            else:
                first_gen_note = (
                    "\n\nThis is the FIRST generation. Keep it SIMPLE:\n"
                    "- 1-2 indicators max, single entry + exit condition\n"
                    "- Prefer crossovers — they reliably produce trades\n"
                    "- MUST include stop_loss_pct, take_profit_pct, and position_size_pct"
                )
                user_parts.append(natural_language + first_gen_note)

            user_message = "\n\n".join(user_parts)

            system_prompt_text = _build_system_prompt(is_refinement, allow_short=allow_short)
            script_code = ""

            # --- Provider Routing ---
            if is_openai_model(effective_model):
                openai_client = self._get_openai_client()
                
                messages = [
                    {"role": "system", "content": system_prompt_text},
                    {"role": "user", "content": user_message}
                ]
                
                openai_kwargs = {
                    "model": effective_model,
                    "messages": messages,
                    "max_completion_tokens": OPENAI_MAX_COMPLETION_TOKENS["script"],
                }
                try:
                    response = openai_client.chat.completions.create(**openai_kwargs)
                except BadRequestError as e:
                    _m = str(e).lower()
                    _retry = dict(openai_kwargs)
                    if "max_completion_tokens" in _m or "max_tokens" in _m:
                        _retry.pop("max_completion_tokens", None)
                    if _retry == openai_kwargs:
                        raise
                    logger.warning(
                        "ScriptGenerator: OpenAI rejected kwargs (%s); retrying without them",
                        e,
                    )
                    response = openai_client.chat.completions.create(**_retry)
                
                if hasattr(response, "usage") and response.usage:
                    u = response.usage
                    logger.info(
                        "ScriptGenerator tokens: model=%s input=%d output=%d",
                        effective_model,
                        u.prompt_tokens,
                        u.completion_tokens,
                    )
                
                script_code = response.choices[0].message.content.strip()

            else:
                client = self._get_client()
                
                # --- Build system prompt with cache_control ---
                system_blocks = [
                    {
                        "type": "text",
                        "text": system_prompt_text,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]

                # --- Single-turn API call ---
                response = client.messages.create(
                    model=effective_model,
                    max_tokens=4000,
                    system=system_blocks,
                    messages=[{"role": "user", "content": user_message}],
                )

                # Log token usage
                if hasattr(response, "usage"):
                    u = response.usage
                    cache_read = getattr(u, "cache_read_input_tokens", 0)
                    cache_creation = getattr(u, "cache_creation_input_tokens", 0)
                    logger.info(
                        "ScriptGenerator tokens: model=%s input=%d output=%d "
                        "cache_read=%d cache_creation=%d",
                        effective_model,
                        u.input_tokens,
                        u.output_tokens,
                        cache_read,
                        cache_creation,
                    )

                # Extract text
                for block in response.content:
                    if hasattr(block, "text"):
                        script_code = block.text.strip()
                        break

            # Strip markdown code fences if present
            script_code = self._strip_code_fences(script_code)

            # Extract name and description from the class
            strategy_name, strategy_description = self._extract_metadata(script_code)

            return script_code, strategy_name, strategy_description, []

        except ScriptGeneratorError:
            raise
        except Exception as e:
            return "", "", "", [f"Script generation failed: {str(e)}"]

    def _strip_code_fences(self, code: str) -> str:
        """Remove markdown code fences and any preamble text if present."""
        # Extract content inside fences (ignore any text before/after)
        if "```python" in code or "```" in code:
            lines = code.split("\n")
            result_lines = []
            in_code = False
            for line in lines:
                if line.strip().startswith("```"):
                    if in_code:
                        break
                    in_code = True
                    continue
                elif in_code:
                    result_lines.append(line)
            if result_lines:
                return "\n".join(result_lines).strip()

        # No fences — strip any non-code preamble lines
        lines = code.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ", "class ", "def ")):
                return "\n".join(lines[i:]).strip()

        # Fallback: locate 'class Strategy' and walk back to imports
        if "class Strategy" in code:
            cls_idx = code.index("class Strategy")
            prefix_lines = code[:cls_idx].split("\n")
            first_import = next(
                (i for i, ln in enumerate(prefix_lines)
                 if ln.strip().startswith(("import ", "from "))),
                len(prefix_lines),
            )
            return "\n".join(prefix_lines[first_import:] + code[cls_idx:].split("\n")).strip()

        return code

    @staticmethod
    def _estimate_bar_count(
        timeframe: Optional[str], start_date: Optional[str], end_date: Optional[str]
    ) -> Optional[int]:
        """Estimate number of bars for the given timeframe and date range."""
        if not timeframe or not start_date or not end_date:
            return None
        try:
            from datetime import datetime as dt
            start = dt.strptime(start_date, "%Y-%m-%d")
            end = dt.strptime(end_date, "%Y-%m-%d")
            days = (end - start).days
            hours_per_bar = {
                "1m": 1 / 60, "5m": 5 / 60, "15m": 0.25,
                "1h": 1.0, "4h": 4.0, "1d": 24.0,
            }
            hpb = hours_per_bar.get(timeframe)
            if hpb and days > 0:
                return int(days * 24 / hpb)
        except Exception:
            pass
        return None

    def _extract_metadata(self, code: str) -> tuple[str, str]:
        """Extract strategy name and description from class attributes."""
        name = "Generated Strategy"
        description = ""

        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("name") and "=" in stripped:
                _, _, value = stripped.partition("=")
                name = value.strip().strip("'\"")
            elif stripped.startswith("description") and "=" in stripped:
                _, _, value = stripped.partition("=")
                description = value.strip().strip("'\"")

        return name, description
