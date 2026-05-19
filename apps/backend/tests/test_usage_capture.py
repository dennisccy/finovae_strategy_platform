"""Real AI-token usage capture (iter-3 / J-13).

The cost tracker MUST accumulate the REAL SDK ``.usage`` token counts — not
an estimate, not a hardcoded constant. These tests stub the OpenAI /
Anthropic SDK client at each production call site (compiler,
script_generator, insights_generator) and assert the exact token counts the
fake SDK returned flowed into the caller-supplied ``usage_sink``. If the
capture is ever bypassed or hardcoded, these fail.
"""

from __future__ import annotations

import types

from shared.contracts import CompileConstraints, StrategyCompileRequest
from strategy.compiler import StrategyCompiler
from strategy.insights_generator import InsightsGenerator
from strategy.script_generator import ScriptGenerator

_STRATEGY_SRC = (
    "import pandas as pd\n"
    "class Strategy:\n"
    "    name = 'Cap Test'\n"
    "    description = 'd'\n"
    "    symbol = 'BTC/USDT'\n"
    "    timeframe = '1h'\n"
    "    stop_loss_pct = 0.03\n"
    "    take_profit_pct = 0.06\n"
    "    position_size_pct = 0.01\n"
    "    leverage = 1\n"
    "    def setup(self, df):\n"
    "        return df\n"
    "    def signal(self, df, i):\n"
    "        return 0\n"
)
_INSIGHTS_JSON = '{"summary": "ok", "suggestions": [{"title": "t", ' \
                 '"description": "d", "prompt": "p"}]}'
_SPEC_JSON = (
    '{"name": "S", "description": "d", "indicators": [], '
    '"entry_conditions": [], "exit_conditions": [], '
    '"position_size": {"type": "all_in", "value": 100}}'
)


def _ns(**kw):
    return types.SimpleNamespace(**kw)


class _FakeOpenAI:
    def __init__(self, content: str, prompt_tokens: int, completion_tokens: int):
        usage = _ns(prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens)
        resp = _ns(
            choices=[_ns(message=_ns(content=content))],
            usage=usage,
        )

        def _create(**kwargs):
            return resp

        self.chat = _ns(completions=_ns(create=_create))


class _FakeAnthropic:
    def __init__(self, text: str, input_tokens: int, output_tokens: int):
        usage = _ns(input_tokens=input_tokens, output_tokens=output_tokens,
                    cache_read_input_tokens=0, cache_creation_input_tokens=0)
        resp = _ns(content=[_ns(text=text)], usage=usage)

        def _create(**kwargs):
            return resp

        self.messages = _ns(create=_create)


# --- ScriptGenerator ---------------------------------------------------------

def test_script_generator_openai_captures_real_usage():
    g = ScriptGenerator()
    g.openai_api_key = "x"
    g.model = "gpt-5.4-mini"
    g._openai_client = _FakeOpenAI(_STRATEGY_SRC, 321, 654)

    sink: list[dict] = []
    code, name, _desc, errs = g.generate("buy low", usage_sink=sink)

    assert "class Strategy" in code and not errs
    assert sink == [
        {"model": "gpt-5.4-mini", "input_tokens": 321, "output_tokens": 654}
    ]


def test_script_generator_anthropic_captures_real_usage():
    g = ScriptGenerator()
    g.api_key = "x"
    g.model = "claude-haiku-4-5"
    g._client = _FakeAnthropic(_STRATEGY_SRC, 111, 222)

    sink: list[dict] = []
    g.generate("buy low", usage_sink=sink)

    assert sink == [
        {"model": "claude-haiku-4-5", "input_tokens": 111, "output_tokens": 222}
    ]


def test_script_generator_without_sink_is_unchanged():
    g = ScriptGenerator()
    g.openai_api_key = "x"
    g.model = "gpt-5.4-mini"
    g._openai_client = _FakeOpenAI(_STRATEGY_SRC, 10, 20)
    # No usage_sink → no crash, normal return (default behaviour preserved).
    code, _n, _d, errs = g.generate("buy low")
    assert "class Strategy" in code and not errs


# --- InsightsGenerator -------------------------------------------------------

def test_insights_generator_openai_captures_real_usage():
    g = InsightsGenerator()
    g.openai_api_key = "x"
    g.model = "gpt-5.4-mini"
    g._openai_client = _FakeOpenAI(_INSIGHTS_JSON, 900, 80)

    sink: list[dict] = []
    summary, suggestions, errs = g.generate(
        {"total_return": 0.1, "num_trades": 10}, script_code="x",
        usage_sink=sink,
    )

    assert summary == "ok" and suggestions and not errs
    assert sink == [
        {"model": "gpt-5.4-mini", "input_tokens": 900, "output_tokens": 80}
    ]


# --- StrategyCompiler --------------------------------------------------------

def test_compiler_openai_captures_real_usage():
    c = StrategyCompiler()
    c.openai_api_key = "x"
    c.model = "gpt-5.4-mini"
    c._openai_client = _FakeOpenAI(_SPEC_JSON, 42, 7)

    sink: list[dict] = []
    resp = c.compile(
        StrategyCompileRequest(natural_language="rsi",
                               constraints=CompileConstraints()),
        usage_sink=sink,
    )

    assert resp.success
    assert sink == [
        {"model": "gpt-5.4-mini", "input_tokens": 42, "output_tokens": 7}
    ]


# --- Pipeline forwarding -----------------------------------------------------

async def test_pipeline_generate_strategy_forwards_usage_sink():
    from backend.pipeline import BacktestPipeline

    pipe = BacktestPipeline()
    pipe.script_generator.openai_api_key = "x"
    pipe.script_generator.model = "gpt-5.4-mini"
    pipe.script_generator._openai_client = _FakeOpenAI(_STRATEGY_SRC, 55, 66)

    sink: list[dict] = []
    res = await pipe.generate_strategy(
        natural_language="buy", model="gpt-5.4-mini", usage_sink=sink
    )

    assert res.script_code
    assert sink == [
        {"model": "gpt-5.4-mini", "input_tokens": 55, "output_tokens": 66}
    ]


async def test_pipeline_generate_insights_forwards_usage_sink():
    from backend.pipeline import BacktestPipeline

    pipe = BacktestPipeline()
    pipe.insights_generator.openai_api_key = "x"
    pipe.insights_generator.model = "gpt-5.4-mini"
    pipe.insights_generator._openai_client = _FakeOpenAI(_INSIGHTS_JSON, 12, 34)

    sink: list[dict] = []
    summary, suggestions, errs = await pipe.generate_insights(
        backtest_result={"total_return": 0.2, "num_trades": 5},
        script_code="x", model="gpt-5.4-mini", usage_sink=sink,
    )

    assert summary == "ok" and not errs
    assert sink == [
        {"model": "gpt-5.4-mini", "input_tokens": 12, "output_tokens": 34}
    ]
