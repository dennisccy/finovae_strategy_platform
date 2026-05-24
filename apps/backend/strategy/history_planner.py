"""Cached LLM history-planner for the open-universe warm start (J-15).

Given a read-only leaderboard mined from prior sessions (built by
``backend.auto_session.mine_history_families`` from the ONE canonical
``RobustScorer``) plus the bounded seed families of the current run, this planner
returns a prioritized ordering over those seed families and a one-line rationale
citing a concrete prior session / family / metric.  The open-universe controller
then screens + promotes the historically-strongest in-seed family first.

Structure mirrors :class:`strategy.insights_generator.InsightsGenerator`:
* a ``last_usage`` side channel carrying the real SDK token usage of the most
  recent call (threaded into the headless budget tracker — J-13);
* a system prompt that carries ``cache_control: {"type": "ephemeral"}`` on the
  Anthropic path so the (static) planner instructions are prompt-cached and the
  leaderboard/history is never re-sent uncached each round.

Best-effort by contract: any hard failure (no API key, SDK error, malformed
output) RAISES so the caller falls back to the deterministic mined-family
ordering — warm start still works without the LLM and the loop never crashes.
It is invoked at most once per run (before SCREEN).
"""

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
    TokenUsage,
    is_openai_model,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an allocation planner for an automated crypto strategy search. You \
decide the order in which a bounded set of candidate (symbol, timeframe) families should be \
explored, so the expensive evaluation budget is spent first on families most likely to pay off — \
using a read-only leaderboard of how each family performed in PRIOR sessions.

You MUST output ONLY valid JSON with this exact structure:
{
  "order": [["SYMBOL", "TIMEFRAME"], ...],
  "rationale": "One sentence citing the concrete prior session / family / robust score."
}

RULES:
1. "order" MUST be a permutation of EXACTLY the candidate seed families given to you — never \
invent, drop, or alter a symbol or timeframe. Reprioritize WITHIN the given set only.
2. Put the families with the strongest prior robust score FIRST. A higher historical robust \
score means a higher expected payoff.
3. A family with no prior history goes after families that do have history.
4. "rationale" MUST reference a real prior session and its robust score from the leaderboard \
(e.g. "Prior session X scored +0.42 on BTC/USDT 1h").
5. Output ONLY the JSON object, nothing else."""


class HistoryPlanner:
    """Plans the seed-family exploration order from a prior-session leaderboard."""

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
        # Side channel: real SDK token usage from the most recent plan() call
        # (None when no LLM call was made). Read by BacktestPipeline.plan_warmstart
        # and threaded into the headless cost tracker (J-13).
        self.last_usage: Optional[TokenUsage] = None

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
    def _build_user_message(
        seed_families: list[tuple[str, str]], history: list[dict[str, object]]
    ) -> str:
        lines = ["Candidate seed families to order (symbol, timeframe):"]
        for sym, tf in seed_families:
            lines.append(f"- {sym} {tf}")
        lines.append("")
        lines.append("Prior-session leaderboard (best robust score per family, strongest first):")
        if history:
            for h in history:
                raw_score = h.get("score", 0.0)
                score = float(raw_score) if isinstance(raw_score, (int, float)) else 0.0
                lines.append(
                    f"- {h.get('symbol')} {h.get('timeframe')}: robust score "
                    f"{score:+.4f} (prior session {h.get('session', 'unknown')})"
                )
        else:
            lines.append("- (no prior history)")
        lines.append("")
        lines.append("Return the prioritized order of the candidate seed families as JSON.")
        return "\n".join(lines)

    def plan(
        self,
        seed_families: list[tuple[str, str]],
        history: list[dict[str, object]],
        model: Optional[str] = None,
    ) -> tuple[list[tuple[str, str]], str]:
        """Return ``(ordered_families, rationale)``.

        ``ordered_families`` is a list of ``(symbol, timeframe)`` tuples drawn
        from ``seed_families``.  Raises on any hard failure (no key / SDK error /
        malformed output) so the caller can fall back deterministically.
        """
        self.last_usage = None
        active_model = model or self.model
        user_message = self._build_user_message(seed_families, history)

        if is_openai_model(active_model):
            openai_client = self._get_openai_client()
            openai_kwargs = {
                "model": active_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
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
                response = openai_client.chat.completions.create(**_retry)
            if hasattr(response, "usage") and response.usage:
                u = response.usage
                self.last_usage = TokenUsage(
                    input_tokens=u.prompt_tokens,
                    output_tokens=u.completion_tokens,
                    model=active_model,
                )
            raw_text = response.choices[0].message.content.strip()
        else:
            client = self._get_client()
            # System prompt with cache_control for prompt caching (match
            # insights_generator) — the static planner instructions are cached so
            # the per-run leaderboard is never re-sent uncached.
            system_blocks = [
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
            response = client.messages.create(
                model=active_model,
                max_tokens=1000,
                system=system_blocks,
                messages=[{"role": "user", "content": user_message}],
            )
            if hasattr(response, "usage"):
                u = response.usage
                self.last_usage = TokenUsage(
                    input_tokens=u.input_tokens,
                    output_tokens=u.output_tokens,
                    model=active_model,
                )
            raw_text = response.content[0].text.strip()

        # Strip markdown code fences if present.
        if raw_text.startswith("```"):
            lines = [ln for ln in raw_text.split("\n") if not ln.strip().startswith("```")]
            raw_text = "\n".join(lines).strip()

        parsed = json.loads(raw_text)
        raw_order = parsed.get("order", [])
        rationale = str(parsed.get("rationale", "")).strip()

        seed_set = set(seed_families)
        ordered: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in raw_order:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            fam = (str(item[0]), str(item[1]))
            if fam in seed_set and fam not in seen:
                ordered.append(fam)
                seen.add(fam)
        if not ordered:
            raise ValueError("planner returned no valid seed family ordering")
        # Append any seed family the planner omitted (stable) so the result is a
        # full permutation of the bounded seed — never drops a candidate.
        for fam in seed_families:
            if fam not in seen:
                ordered.append(fam)
                seen.add(fam)
        return ordered, rationale
