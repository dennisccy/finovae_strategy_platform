"""
AI Insights Generator

Generates strategy summaries and improvement suggestions from backtest results
using Claude API.

- 10 suggestions covering all tactical categories
- In-memory cache keyed on backtest metrics + script code hash
- Prompt caching via cache_control on system prompt
- max_tokens=4000
"""

import hashlib
import json
import logging
import os
from typing import Optional

from anthropic import Anthropic
from openai import BadRequestError, OpenAI

from shared.model_catalog import (
    DEFAULT_MODEL,
    OPENAI_JSON_RESPONSE_FORMAT,
    OPENAI_MAX_COMPLETION_TOKENS,
    is_openai_model,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a quantitative trading strategy analyst specialising in return maximisation and risk/reward optimisation. Given backtest results, strategy code, and the user's original intent, you produce a concise analysis and 10 actionable improvement suggestions.

You MUST output ONLY valid JSON with this exact structure:
{
  "summary": "3-5 sentence analysis covering overall performance, key strengths, key weaknesses, and risk profile. Be specific with numbers.",
  "suggestions": [
    {
      "title": "Short title (3-6 words)",
      "description": "One sentence explaining the improvement and its expected impact on return or risk/reward.",
      "prompt": "A detailed modification instruction for a strategy code generator. Reference the existing strategy and specify exactly what to change."
    }
  ]
}

RULES:
1. Provide EXACTLY 10 suggestions, ordered from most to least impactful on total return or risk/reward ratio.
2. PRIMARY GOAL: Every suggestion must aim at increasing total return, improving risk/reward, or both.
3. Each prompt MUST be a MODIFICATION INSTRUCTION: "Modify the strategy to...", "Change the entry condition to...", etc.
4. Cover diverse tactical directions — cover all 10 categories, one suggestion each:
   - Entry timing / Exit strategy / Trend filter / Stop-loss or risk management / Take-profit or target
   - Parameter tuning / Trade frequency / Volatility adaptation / Market regime filter / Position sizing
5. TRADE-COUNT ADAPTIVE:
   - 0 trades:    All 10 suggestions MUST focus on producing trades first.
   - 1-20 trades: At least 8 suggestions must increase frequency.
   - 21-50 trades: At least 5 suggestions should increase frequency.
   - 51-200 trades: Balance frequency, risk, and return.
   - 200+ trades: Focus on tightening filters / reducing overtrading.
6. Be specific and actionable. Reference actual numbers from the backtest.
7. Output ONLY the JSON object, nothing else.
8. RESPECT USER CONFIGURATION: If "Allow Short: ENABLED" appears in the context, NEVER suggest disabling shorts, switching to long-only, reducing short exposure, or setting allow_short=False. The user explicitly enabled this mode — improve it, do not disable it.
9. If Walk-Forward Efficiency (WFE) data is provided, factor in OOS performance when ranking suggestions. WFE < 0.5 means robustness improvements (simpler parameters, regime filters) should rank higher. WFE < 0.3 is critical overfitting — at least 4 suggestions must address it."""


class InsightsGenerator:
    """
    Generates strategy analysis summaries and improvement suggestions
    from backtest results using Claude API.

    Includes an in-memory cache to avoid regenerating insights for
    identical backtest results + strategy code.
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
        self._cache: dict[str, tuple[str, list[dict]]] = {}

    def _get_client(self) -> Anthropic:
        if not self.api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Please set the environment variable."
            )
        if not self._client:
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def _get_openai_client(self) -> OpenAI:
        if not self.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Please set the environment variable."
            )
        if not self._openai_client:
            self._openai_client = OpenAI(api_key=self.openai_api_key)
        return self._openai_client

    @staticmethod
    def _cache_key(
        backtest_result: dict,
        script_code: str,
        allow_short: bool = False,
        previous_summary: str | None = None,
        previous_suggestions: list[str] | None = None,
        walk_forward_result: dict | None = None,
    ) -> str:
        """Hash backtest metrics + script code into a cache key."""
        # Use only the stable metric fields for the key
        key_data = json.dumps({
            "allow_short": allow_short,
            "total_return": backtest_result.get("total_return"),
            "max_drawdown": backtest_result.get("max_drawdown"),
            "num_trades": backtest_result.get("num_trades"),
            "win_rate": backtest_result.get("win_rate"),
            "sharpe_ratio": backtest_result.get("sharpe_ratio"),
            "profit_factor": backtest_result.get("profit_factor"),
            "script_code": script_code,
            "previous_summary": previous_summary or "",
            "previous_suggestions": previous_suggestions or [],
            "wfe": walk_forward_result.get("wfe") if walk_forward_result else None,
        }, sort_keys=True)
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def generate(
        self,
        backtest_result: dict,
        strategy_name: str = "",
        strategy_description: str = "",
        script_code: str = "",
        natural_language_prompt: str = "",
        symbol: str | None = None,
        timeframe: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        allow_short: bool = False,
        leverage: float = 1.0,
        initial_capital: float | None = None,
        previous_summary: str | None = None,
        previous_suggestions: list[str] | None = None,
        walk_forward_result: dict | None = None,
    ) -> tuple[str, list[dict], list[str]]:
        """
        Generate insights from backtest results.

        Returns cached results if the same backtest metrics + code were
        seen before.

        Returns:
            Tuple of (summary, suggestions, errors)
        """
        # --- Check cache ---
        cache_key = self._cache_key(backtest_result, script_code, allow_short, previous_summary, previous_suggestions, walk_forward_result)
        if cache_key in self._cache:
            logger.info("InsightsGenerator: cache hit (key=%s)", cache_key)
            summary, suggestions = self._cache[cache_key]
            return summary, suggestions, []

        try:

            num_trades = backtest_result.get('num_trades', 0)

            # Build a concise user message with the key metrics
            metrics_summary = (
                f"Strategy: {strategy_name or 'Unknown'}\n"
                f"Description: {strategy_description or 'N/A'}\n\n"
            )

            if natural_language_prompt:
                metrics_summary = f"Original User Prompt: {natural_language_prompt}\n\n" + metrics_summary

            if symbol or timeframe or start_date:
                metrics_summary += "Market Context:\n"
                if symbol:
                    metrics_summary += f"- Symbol: {symbol}\n"
                if timeframe:
                    metrics_summary += f"- Timeframe: {timeframe}\n"
                if start_date and end_date:
                    metrics_summary += f"- Date range: {start_date} to {end_date}\n"
                if initial_capital is not None:
                    metrics_summary += f"- Initial Capital: ${initial_capital:,.0f}\n"
                if allow_short:
                    metrics_summary += f"- Allow Short: ENABLED (user-configured — do not suggest disabling)\n"
                metrics_summary += "\n"

            metrics_summary += (
                f"Backtest Results:\n"
                f"- Total Return: {backtest_result.get('total_return', 0):.4f} ({backtest_result.get('total_return', 0) * 100:.2f}%)\n"
                f"- Max Drawdown: {backtest_result.get('max_drawdown', 0):.4f} ({backtest_result.get('max_drawdown', 0) * 100:.2f}%)\n"
                f"- Number of Trades: {num_trades}\n"
                f"- Win Rate: {backtest_result.get('win_rate', 0):.4f} ({backtest_result.get('win_rate', 0) * 100:.2f}%)\n"
                f"- Sharpe Ratio: {backtest_result.get('sharpe_ratio', 0):.4f}\n"
                f"- Profit Factor: {backtest_result.get('profit_factor', 0):.4f}\n"
            )

            if num_trades == 0:
                metrics_summary += "\nCRITICAL: Zero trades. All suggestions MUST focus on producing trades.\n"
            elif num_trades < 5:
                metrics_summary += f"\nCRITICAL: Only {num_trades} trades. At least 8/10 suggestions must increase frequency.\n"
            elif num_trades < 20:
                metrics_summary += f"\nWARNING: {num_trades} trades — too few. At least 6/10 suggestions should increase frequency.\n"
            elif num_trades < 50:
                metrics_summary += f"\nNOTE: {num_trades} trades — borderline. At least 4/10 suggestions should increase frequency.\n"
            elif num_trades > 300:
                metrics_summary += f"\nNOTE: {num_trades} trades — consider tightening filters to reduce noise.\n"

            if previous_summary:
                metrics_summary += (
                    f"\nPrevious Iteration Summary:\n{previous_summary}\n"
                    "(Note: suggestions should build on this — avoid repeating already-tried approaches.)\n"
                )

            if previous_suggestions:
                metrics_summary += (
                    f"\nAlready-tried suggestions (DO NOT repeat or produce suggestions "
                    f"that overlap in approach with these):\n"
                    + "\n".join(f"- {s}" for s in previous_suggestions)
                    + "\n"
                )

            if walk_forward_result:
                wfe = walk_forward_result.get("wfe", 0)
                wfe_label = (
                    "HEALTHY (≥0.5)" if wfe >= 0.5
                    else ("BORDERLINE (0.3–0.5)" if wfe >= 0.3
                    else "POOR (<0.3 — likely overfit)")
                )
                metrics_summary += (
                    f"\nWalk-Forward Validation ({walk_forward_result.get('num_windows', 0)} windows):\n"
                    f"- WFE: {wfe:.3f} — {wfe_label}\n"
                    f"- OOS Return: {walk_forward_result.get('combined_oos_return', 0) * 100:.2f}%\n"
                    f"- OOS Sharpe: {walk_forward_result.get('combined_oos_sharpe', 0):.3f}\n"
                    f"- OOS Win Rate: {walk_forward_result.get('combined_oos_win_rate', 0) * 100:.1f}%\n"
                    f"- OOS Max Drawdown: {walk_forward_result.get('combined_oos_max_drawdown', 0) * 100:.2f}%\n"
                )
                if wfe < 0.3:
                    metrics_summary += (
                        "CRITICAL: WFE < 0.3 — severe overfitting. "
                        "Suggestions MUST prioritise reducing parameter sensitivity and improving generalisability.\n"
                    )
                elif wfe < 0.5:
                    metrics_summary += (
                        "NOTE: Borderline WFE. At least 3 suggestions should address robustness "
                        "(simpler conditions, fewer parameters, regime filters).\n"
                    )

            # Direction breakdown analysis (when allow_short is enabled)
            if allow_short and "trades" in backtest_result:
                trades_list = backtest_result.get("trades", [])
                long_trades = [t for t in trades_list if t.get("direction", "long") == "long"]
                short_trades = [t for t in trades_list if t.get("direction", "short") == "short"]
                long_pnl = (
                    sum(t.get("pnl_percent", 0) for t in long_trades) / len(long_trades)
                    if long_trades else 0.0
                )
                short_pnl = (
                    sum(t.get("pnl_percent", 0) for t in short_trades) / len(short_trades)
                    if short_trades else 0.0
                )
                direction_section = (
                    f"\nDIRECTION ANALYSIS (Allow Shorts is ENABLED):\n"
                    f"- Long trades: {len(long_trades)} (avg return: {long_pnl * 100:.2f}%)\n"
                    f"- Short trades: {len(short_trades)} (avg return: {short_pnl * 100:.2f}%)\n"
                )
                if len(short_trades) == 0:
                    direction_section += (
                        "⚠ WARNING: 0 short trades — strategy never went short despite "
                        "allow_short=True. This is a critical issue.\n"
                    )
                if len(long_trades) == 0:
                    direction_section += "⚠ WARNING: 0 long trades — strategy only went short.\n"
                direction_section += (
                    "\nSUMMARY REQUIREMENT: Explicitly comment on the long/short breakdown "
                    "and which direction performed better.\n"
                    "SUGGESTION REQUIREMENT:\n"
                )
                if len(short_trades) == 0:
                    direction_section += (
                        "- FIRST suggestion MUST fix the short signal condition.\n"
                    )
                else:
                    direction_section += (
                        "- At least 1 suggestion must address improving the weaker direction.\n"
                    )
                metrics_summary += direction_section

            if script_code:
                metrics_summary += f"\nStrategy Code:\n```python\n{script_code}\n```"

            if is_openai_model(self.model):
                openai_client = self._get_openai_client()
                
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": metrics_summary}
                ]
                
                openai_kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "max_completion_tokens": OPENAI_MAX_COMPLETION_TOKENS["insights"],
                    "response_format": OPENAI_JSON_RESPONSE_FORMAT,
                }
                try:
                    response = openai_client.chat.completions.create(**openai_kwargs)
                except BadRequestError as e:
                    _m = str(e).lower()
                    _retry = dict(openai_kwargs)
                    if "max_completion_tokens" in _m or "max_tokens" in _m:
                        _retry.pop("max_completion_tokens", None)
                    if "response_format" in _m:
                        _retry.pop("response_format", None)
                    if _retry == openai_kwargs:
                        raise
                    logger.warning(
                        "InsightsGenerator: OpenAI rejected kwargs (%s); retrying without them",
                        e,
                    )
                    response = openai_client.chat.completions.create(**_retry)
                
                if hasattr(response, "usage") and response.usage:
                    u = response.usage
                    logger.info(
                        "InsightsGenerator tokens: model=%s input=%d output=%d",
                        self.model,
                        u.prompt_tokens,
                        u.completion_tokens,
                    )
                
                raw_text = response.choices[0].message.content.strip()

            else:
                client = self._get_client()

                # System prompt with cache_control for prompt caching
                system_blocks = [
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]

                response = client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system=system_blocks,
                    messages=[
                        {"role": "user", "content": metrics_summary}
                    ],
                )

                # Log token usage
                if hasattr(response, "usage"):
                    u = response.usage
                    cache_read = getattr(u, "cache_read_input_tokens", 0)
                    cache_creation = getattr(u, "cache_creation_input_tokens", 0)
                    logger.info(
                        "InsightsGenerator tokens: model=%s input=%d output=%d "
                        "cache_read=%d cache_creation=%d",
                        self.model,
                        u.input_tokens,
                        u.output_tokens,
                        cache_read,
                        cache_creation,
                    )

                raw_text = response.content[0].text.strip()

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw_text = "\n".join(lines).strip()

            parsed = json.loads(raw_text)

            summary = parsed.get("summary", "")
            suggestions = parsed.get("suggestions", [])

            # Validate suggestions structure (cap at 10)
            valid_suggestions = []
            for s in suggestions[:10]:
                if isinstance(s, dict) and "title" in s and "description" in s and "prompt" in s:
                    valid_suggestions.append({
                        "title": str(s["title"]),
                        "description": str(s["description"]),
                        "prompt": str(s["prompt"]),
                    })

            # Store in cache
            self._cache[cache_key] = (summary, valid_suggestions)

            return summary, valid_suggestions, []

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse insights JSON: %s", e)
            return "", [], [f"Failed to parse AI response: {e}"]
        except Exception as e:
            logger.error("Insights generation failed: %s", e)
            return "", [], [f"Insights generation failed: {str(e)}"]
