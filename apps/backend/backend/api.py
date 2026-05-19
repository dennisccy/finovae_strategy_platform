"""
FastAPI Application and Endpoints

REST API for the backtesting platform.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from pathlib import Path

from dotenv import load_dotenv

# Load .env from the package root (finovae_strategy_platform_api/.env),
# regardless of the working directory the server is started from.
load_dotenv(Path(__file__).parent.parent / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

import asyncio
import json
import re

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.pipeline import BacktestPipeline, CancellationToken
from shared.contracts import StrategyRating
from shared.model_catalog import models_payload
from shared.schemas import (
    BacktestResultSchema,
    CapacityLevelSchema,
    CategoryRatingSchema,
    DrawdownPeriodSchema,
    EquityPointSchema,
    ExecuteBacktestRequest,
    ExecuteWalkForwardRequest,
    PhaseTimings,
    GenerateInsightsRequest,
    GenerateInsightsResponse,
    GenerateStrategyRequest,
    GenerateStrategyResponse,
    HistogramBinSchema,
    InsightsSuggestion,
    MonthlyReturnSchema,
    RollingMetricSchema,
    RunBacktestAPIRequest,
    RunBacktestAPIResponse,
    RunHistoryResponse,
    RunRecordSchema,
    SimulatedStopLevelSchema,
    StrategyRatingSchema,
    StrategySpecSchema,
    TradeExcursionSchema,
    TradeSchema,
    WalkForwardWindowSchema,
    WalkForwardResultSchema,
)

# Initialize FastAPI app
app = FastAPI(
    title="Finovae Strategy Platform API",
    description="""
## Crypto AI Backtesting Platform

Transform natural language trading strategies into actionable backtests using AI.

### Features
* **Natural Language Strategy Compilation**: Describe your strategy in plain English
* **Automated Code Generation**: AI converts your strategy to executable Python code
* **Historical Backtesting**: Test against real Binance OHLCV data
* **Performance Metrics**: Sharpe ratio, max drawdown, win rate, profit factor, and more
* **Sandboxed Execution**: Secure, isolated strategy execution environment

### Workflow
1. Submit a natural language strategy description
2. AI compiles it into a StrategySpec with indicators and conditions
3. Code generator creates executable signal function
4. Fetch historical data from Binance
5. Run backtest with realistic commission and slippage
6. Receive detailed performance metrics and trade history
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Finovae Platform",
        "url": "https://github.com/finovae",
    },
    license_info={
        "name": "MIT",
    },
)

# Configure CORS for frontend
_cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]
# Allow Vercel preview/production URLs via env var (comma-separated)
_extra_origins = os.environ.get("CORS_ORIGINS", "")
if _extra_origins:
    _cors_origins.extend(o.strip() for o in _extra_origins.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.session_routes import router as session_router  # noqa: E402
from backend.directions_routes import router as directions_router  # noqa: E402
from backend.auto_session import router as auto_session_router  # noqa: E402
app.include_router(session_router)
app.include_router(directions_router)
app.include_router(auto_session_router)

# Global pipeline instance
_pipeline: Optional[BacktestPipeline] = None


def get_pipeline() -> BacktestPipeline:
    """Get or create pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = BacktestPipeline()
    return _pipeline


import math


def _safe_float(v: float) -> float:
    """Replace inf/nan with JSON-safe values."""
    if math.isinf(v) or math.isnan(v):
        return 9999.99 if v > 0 else -9999.99
    return v


def _equity_point(ep) -> "EquityPointSchema":
    """Serialize an equity point, clamping values to schema-valid ranges.

    With leverage/shorts the account can go negative (equity < 0) or drawdown
    can slightly exceed 1.0 due to floating-point arithmetic.  We clamp rather
    than reject so the UI can still render the full curve.
    """
    return EquityPointSchema(
        timestamp=ep.timestamp,
        equity=max(1e-6, float(ep.equity)),   # floor at near-zero; schema requires gt=0
        drawdown=min(1.0, float(ep.drawdown)), # cap at 100%; schema requires le=1
    )


def _serialize_rating(rating: Optional[StrategyRating]) -> Optional[StrategyRatingSchema]:
    """Convert StrategyRating dataclass to Pydantic schema."""
    if rating is None:
        return None

    def _safe_metrics(metrics: dict) -> dict:
        return {
            k: (_safe_float(v) if isinstance(v, float) else v)
            for k, v in metrics.items()
        }

    def _cat(c):
        return CategoryRatingSchema(
            name=c.name,
            label=c.label,
            stars=c.stars,
            key_metrics=_safe_metrics(c.key_metrics),
            analyses=c.analyses,
        )

    return StrategyRatingSchema(
        profitability=_cat(rating.profitability),
        risk_resistance=_cat(rating.risk_resistance),
        risk_reward=_cat(rating.risk_reward),
        win_rate_ev=_cat(rating.win_rate_ev),
        liquidity=_cat(rating.liquidity),
        benchmark_equity=[
            _equity_point(ep)
            for ep in rating.benchmark_equity
        ],
        benchmark_total_return=rating.benchmark_total_return,
        monthly_returns=[
            MonthlyReturnSchema(year=m.year, month=m.month, return_pct=m.return_pct)
            for m in rating.monthly_returns
        ],
        trade_excursions=[
            TradeExcursionSchema(trade_id=te.trade_id, pnl_percent=te.pnl_percent, mae=te.mae, mfe=te.mfe)
            for te in rating.trade_excursions
        ],
        drawdown_periods=[
            DrawdownPeriodSchema(
                start_time=dp.start_time, end_time=dp.end_time,
                recovery_time=dp.recovery_time, depth=dp.depth,
                duration_days=dp.duration_days, recovery_days=dp.recovery_days,
            )
            for dp in rating.drawdown_periods
        ],
        rolling_sharpe=[
            RollingMetricSchema(timestamp=rm.timestamp, value=rm.value)
            for rm in rating.rolling_sharpe
        ],
        rolling_sharpe_benchmark=[
            RollingMetricSchema(timestamp=rm.timestamp, value=rm.value)
            for rm in rating.rolling_sharpe_benchmark
        ],
        return_distribution=[
            HistogramBinSchema(bin_start=b.bin_start, bin_end=b.bin_end, count=b.count)
            for b in rating.return_distribution
        ],
        simulated_stops=[
            SimulatedStopLevelSchema(
                level_pct=s.level_pct, adjusted_return=s.adjusted_return,
                adjusted_win_rate=s.adjusted_win_rate, trades_affected=s.trades_affected,
            )
            for s in rating.simulated_stops
        ],
        simulated_take_profits=[
            SimulatedStopLevelSchema(
                level_pct=s.level_pct, adjusted_return=s.adjusted_return,
                adjusted_win_rate=s.adjusted_win_rate, trades_affected=s.trades_affected,
            )
            for s in rating.simulated_take_profits
        ],
        capacity_levels=[
            CapacityLevelSchema(
                capital=cl.capital,
                volume_participation_pct=cl.volume_participation_pct,
                estimated_slippage_bps=cl.estimated_slippage_bps,
            )
            for cl in rating.capacity_levels
        ],
        annual_returns=rating.annual_returns,
        benchmark_annual_returns=rating.benchmark_annual_returns,
        annual_long_returns=rating.annual_long_returns,
        annual_short_returns=rating.annual_short_returns,
    )


# =============================================================================
# API ENDPOINTS
# =============================================================================


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - basic health check.

    Returns service status and version information.
    """
    return {
        "status": "ok",
        "service": "Finovae Strategy Platform",
        "version": "0.1.0",
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    Detailed health check with component status.

    Verifies that all system components (API, pipeline) are operational.
    """
    return {
        "status": "healthy",
        "components": {
            "api": "ok",
            "pipeline": "ok",
        },
    }


@app.get("/api/config", tags=["Reference Data"])
async def get_config():
    """Return server configuration (e.g. worker count for client-side concurrency control)."""
    return {"workers": getattr(app.state, "worker_count", 1)}


@app.post("/api/run-backtest", response_model=RunBacktestAPIResponse, tags=["Backtesting"],
           deprecated=True)
async def run_backtest(request: RunBacktestAPIRequest):
    """
    Run a complete backtest from natural language strategy description.

    ## Process Flow
    1. **Compile**: Natural language → StrategySpec JSON using Claude API
    2. **Generate**: StrategySpec → executable Python signal function
    3. **Validate**: Sandbox security check with RestrictedPython
    4. **Fetch**: Download OHLCV data from Binance (with caching)
    5. **Execute**: Run backtest with next-bar execution model
    6. **Analyze**: Calculate performance metrics (Sharpe, drawdown, etc.)

    ## Example Strategy
    ```
    Buy when RSI crosses below 30, sell when it crosses above 70
    ```

    ## Returns
    - **BacktestResult**: Performance metrics, equity curve, trade history
    - **StrategySpec**: Compiled strategy with indicators and conditions
    - **Errors**: Compilation or execution errors (if any)

    ## Notes
    - Execution is sandboxed for security
    - Data is cached to avoid redundant API calls
    - Realistic commission (0.075% Binance BNB taker) and slippage (0.05%) applied
    """
    pipeline = get_pipeline()

    # Convert dates to datetime with timezone
    start_datetime = datetime.combine(
        request.start_date,
        datetime.min.time(),
    ).replace(tzinfo=timezone.utc)

    end_datetime = datetime.combine(
        request.end_date,
        datetime.max.time(),
    ).replace(tzinfo=timezone.utc)

    # Run pipeline
    result, strategy_spec, errors, rating = await pipeline.run(
        natural_language=request.natural_language,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=start_datetime,
        end_date=end_datetime,
        initial_capital=request.initial_capital,
        model=request.model,
    )

    if errors and result is None:
        return RunBacktestAPIResponse(
            success=False,
            errors=errors,
        )

    # Convert to response schemas
    result_schema = None
    spec_schema = None

    if result:
        result_schema = BacktestResultSchema(
            run_id=result.run_id,
            total_return=result.total_return,
            max_drawdown=min(1.0, float(result.max_drawdown)),
            num_trades=result.num_trades,
            win_rate=result.win_rate,
            sharpe_ratio=_safe_float(result.sharpe_ratio),
            profit_factor=_safe_float(result.profit_factor),
            equity_curve=[
                _equity_point(ep)
                for ep in result.equity_curve
            ],
            trades=[
                TradeSchema(
                    trade_id=t.trade_id,
                    entry_time=t.entry_time,
                    exit_time=t.exit_time,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    quantity=t.quantity,
                    pnl=t.pnl,
                    pnl_percent=t.pnl_percent,
                    commission_paid=t.commission_paid,
                )
                for t in result.trades
            ],
            margin_called=getattr(result, "margin_called", False),
            unleveraged_return=getattr(result, "unleveraged_return", None),
        )

    if strategy_spec:
        spec_schema = StrategySpecSchema(
            name=strategy_spec.name,
            description=strategy_spec.description,
            entry_conditions=[
                {
                    "left_operand": c.left_operand,
                    "operator": c.operator.value,
                    "right_operand": c.right_operand,
                }
                for c in strategy_spec.entry_conditions
            ],
            exit_conditions=[
                {
                    "left_operand": c.left_operand,
                    "operator": c.operator.value,
                    "right_operand": c.right_operand,
                }
                for c in strategy_spec.exit_conditions
            ],
            position_size={
                "type": strategy_spec.position_size.type.value,
                "value": strategy_spec.position_size.value,
            },
            indicators=[
                {
                    "name": i.name,
                    "params": i.params,
                    "output_name": i.output_name,
                }
                for i in strategy_spec.indicators
            ],
        )

    return RunBacktestAPIResponse(
        success=True,
        run_id=result.run_id if result else None,
        result=result_schema,
        rating=_serialize_rating(rating),
        strategy_spec=spec_schema,
        errors=errors,
    )


@app.post("/api/generate-strategy", response_model=GenerateStrategyResponse, tags=["AI Script Proxy"])
async def generate_strategy(request: GenerateStrategyRequest):
    """
    Generate a Python strategy script from natural language description.

    ## Step 1 of the two-step backtest flow

    AI generates a Strategy class with setup() and signal() methods.
    The script is validated in the sandbox and stored for later execution.

    Returns the script for user review before backtesting.
    """
    pipeline = get_pipeline()

    gen_result = await pipeline.generate_strategy(
        natural_language=request.natural_language,
        model=request.model,
        previous_script_code=request.previous_script_code,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        previous_backtest_metrics=request.previous_backtest_metrics,
        allow_short=request.allow_short,
        leverage=request.leverage,
    )

    if gen_result.validation_errors and not gen_result.script_code:
        return GenerateStrategyResponse(
            success=False,
            errors=gen_result.validation_errors,
        )

    return GenerateStrategyResponse(
        success=True,
        script_id=gen_result.script_id,
        script_code=gen_result.script_code,
        strategy_name=gen_result.strategy_name,
        strategy_description=gen_result.strategy_description,
        model_used=gen_result.model_used or None,
        validation_errors=gen_result.validation_errors,
    )


@app.post("/api/execute-backtest", tags=["AI Script Proxy"])
async def execute_backtest(request: ExecuteBacktestRequest, raw_request: Request):
    """
    Execute a backtest using a previously generated (or edited) strategy script.

    ## Step 2 of the two-step backtest flow

    Streams real-time progress as Server-Sent Events (SSE). Each event is a JSON
    object with a ``type`` field:

    - ``{"type":"status","phase":"validate","validate_step":"pattern_check"}``
    - ``{"type":"status","phase":"simulate","sim_bar":500,"sim_total_bars":5000}``
    - ``{"type":"result","success":true,"result":{...},"rating":{...},"timings":{...}}``
    - ``{"type":"error","errors":["..."],"timings":null}``

    Supports cooperative cancellation: if the client disconnects the backend
    cancels the running pipeline within ~0.5 s.
    """
    pipeline = get_pipeline()

    start_datetime = datetime.combine(
        request.start_date,
        datetime.min.time(),
    ).replace(tzinfo=timezone.utc)

    end_datetime = datetime.combine(
        request.end_date,
        datetime.max.time(),
    ).replace(tzinfo=timezone.utc)

    queue: asyncio.Queue = asyncio.Queue()
    cancel_token = CancellationToken()

    async def status_cb(event: dict) -> None:
        await queue.put(event)

    async def run() -> None:
        async with app.state.backtest_semaphore:
            try:
                result, errors, rating, timings_dict, wf_result = await pipeline.execute_backtest(
                    script_id=request.script_id,
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    start_date=start_datetime,
                    end_date=end_datetime,
                    initial_capital=request.initial_capital,
                    commission=request.commission,
                    script_code=request.script_code,
                    strategy_name=request.strategy_name,
                    strategy_description=request.strategy_description,
                    cancel_token=cancel_token,
                    status_callback=status_cb,
                    allow_short=request.allow_short,
                    leverage=request.leverage,
                    max_order_size_pct=request.max_order_size_pct,
                    max_daily_loss_pct=request.max_daily_loss_pct,
                    wfv_enabled=request.wfv_enabled,
                    wfv_is_months=request.wfv_is_months,
                    wfv_oos_months=request.wfv_oos_months,
                    wfv_max_windows=request.wfv_max_windows,
                )

                phase_timings = PhaseTimings(**timings_dict) if timings_dict else None

                if errors and result is None:
                    await queue.put({
                        "type": "error",
                        "errors": errors,
                        "timings": jsonable_encoder(phase_timings),
                    })
                else:
                    result_schema = None
                    if result:
                        result_schema = BacktestResultSchema(
                            run_id=result.run_id,
                            total_return=result.total_return,
                            max_drawdown=min(1.0, float(result.max_drawdown)),
                            num_trades=result.num_trades,
                            win_rate=result.win_rate,
                            sharpe_ratio=_safe_float(result.sharpe_ratio),
                            profit_factor=_safe_float(result.profit_factor),
                            equity_curve=[
                                _equity_point(ep)
                                for ep in result.equity_curve
                            ],
                            trades=[
                                TradeSchema(
                                    trade_id=t.trade_id,
                                    entry_time=t.entry_time,
                                    exit_time=t.exit_time,
                                    entry_price=t.entry_price,
                                    exit_price=t.exit_price,
                                    quantity=t.quantity,
                                    pnl=t.pnl,
                                    pnl_percent=t.pnl_percent,
                                    commission_paid=t.commission_paid,
                                    direction=t.direction,
                                    leverage=t.leverage,
                                    margin=getattr(t, "margin", 0.0),
                                )
                                for t in result.trades
                            ],
                            margin_called=getattr(result, "margin_called", False),
                            unleveraged_return=getattr(result, "unleveraged_return", None),
                        )

                    stored = pipeline.get_stored_script(request.script_id)
                    rating_schema = _serialize_rating(rating)

                    # Save to directions cache if this is a direction run
                    if request.direction_id is not None and result is not None and request.exchange:
                        try:
                            from backend.directions_cache import build_cache_key, write_direction_result
                            cache_key = build_cache_key(
                                request.symbol,
                                request.timeframe,
                                str(request.start_date),
                                str(request.end_date),
                                request.exchange,
                                request.allow_short,
                                int(request.leverage),
                            )
                            node_dict = {
                                "prompt": request.direction_prompt or "",
                                "scriptCode": request.script_code or (stored.script_code if stored else ""),
                                "strategyName": stored.strategy_name if stored else "",
                                "status": "complete",
                                "result": jsonable_encoder(result_schema),
                                "rating": jsonable_encoder(rating_schema),
                                "insights": None,
                                "params": {
                                    "symbol": request.symbol,
                                    "timeframe": request.timeframe,
                                    "start_date": str(request.start_date),
                                    "end_date": str(request.end_date),
                                    "initial_capital": request.initial_capital,
                                    "exchange": request.exchange,
                                    "allow_short": request.allow_short,
                                    "leverage": request.leverage,
                                },
                            }
                            write_direction_result(
                                cache_key,
                                request.direction_index if request.direction_index is not None else 0,
                                request.direction_id,
                                node_dict,
                            )
                        except Exception as _cache_err:
                            logger.warning("Failed to write direction cache: %s", _cache_err)

                    await queue.put({
                        "type": "result",
                        "success": True,
                        "run_id": result.run_id if result else None,
                        "result": jsonable_encoder(result_schema),
                        "rating": jsonable_encoder(rating_schema),
                        "timings": jsonable_encoder(phase_timings),
                        "script_code": request.script_code or (stored.script_code if stored else None),
                        "strategy_name": stored.strategy_name if stored else None,
                        "strategy_description": stored.strategy_description if stored else None,
                        "errors": errors,
                        "walk_forward_result": jsonable_encoder(_serialize_walk_forward(wf_result)) if wf_result else None,
                    })
            except Exception as e:
                await queue.put({
                    "type": "error",
                    "errors": [str(e)],
                    "timings": None,
                })
            finally:
                await queue.put(None)  # sentinel

    task = asyncio.create_task(run())

    async def event_stream():
        try:
            while True:
                if await raw_request.is_disconnected():
                    cancel_token.cancel()
                    task.cancel()
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                if event is None:
                    return
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            cancel_token.cancel()
            task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/generate-insights", response_model=GenerateInsightsResponse, tags=["AI Script Proxy"])
async def generate_insights(request: GenerateInsightsRequest):
    """
    Generate AI-powered strategy insights from backtest results.

    Produces a summary analysis and 3-4 actionable improvement suggestions.
    Each suggestion includes a prompt that can be fed back to generate-strategy
    for iterative refinement.
    """
    pipeline = get_pipeline()

    backtest_dict = request.backtest_result.model_dump()

    summary, suggestions, errors = await pipeline.generate_insights(
        backtest_result=backtest_dict,
        strategy_name=request.strategy_name,
        strategy_description=request.strategy_description,
        script_code=request.script_code,
        natural_language_prompt=request.natural_language_prompt,
        model=request.model,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=request.start_date,
        end_date=request.end_date,
        allow_short=request.allow_short,
        leverage=request.leverage,
        initial_capital=request.initial_capital,
        previous_summary=request.previous_summary,
        previous_suggestions=request.previous_suggestions,
        walk_forward_result=request.walk_forward_result,
    )

    if errors and not summary:
        return GenerateInsightsResponse(
            success=False,
            errors=errors,
        )

    return GenerateInsightsResponse(
        success=True,
        summary=summary,
        suggestions=[
            InsightsSuggestion(
                title=s["title"],
                description=s["description"],
                prompt=s["prompt"],
            )
            for s in suggestions
        ],
        errors=errors,
    )


@app.get("/api/runs", response_model=RunHistoryResponse, tags=["Run History"])
async def get_run_history():
    """
    Get history of all backtest runs.

    Returns a list of all previous backtest executions with summarized results.
    Useful for tracking strategy iterations and comparing performance over time.

    ## Response
    - List of run records with timestamps
    - Strategy specs and performance summaries
    - Last 10 equity curve points per run (for preview)
    """
    pipeline = get_pipeline()
    runs = pipeline.get_run_history()

    run_schemas = []
    for run in runs:
        run_schemas.append(RunRecordSchema(
            run_id=run.run_id,
            timestamp=run.timestamp,
            request={
                "run_id": run.request.run_id,
                "strategy_code": run.request.strategy_code[:100] + "...",
                "symbol": run.request.symbol,
                "timeframe": run.request.timeframe,
                "start_date": run.request.start_date,
                "end_date": run.request.end_date,
                "initial_capital": run.request.initial_capital,
                "commission": run.request.commission,
                "slippage": run.request.slippage,
            },
            result={
                "run_id": run.result.run_id,
                "total_return": run.result.total_return,
                "max_drawdown": run.result.max_drawdown,
                "num_trades": run.result.num_trades,
                "win_rate": run.result.win_rate,
                "sharpe_ratio": run.result.sharpe_ratio,
                "profit_factor": run.result.profit_factor,
                "equity_curve": [
                    {"timestamp": ep.timestamp, "equity": ep.equity, "drawdown": ep.drawdown}
                    for ep in run.result.equity_curve[-10:]  # Last 10 points only
                ],
                "trades": [
                    {
                        "trade_id": t.trade_id,
                        "entry_time": t.entry_time,
                        "exit_time": t.exit_time,
                        "entry_price": t.entry_price,
                        "exit_price": t.exit_price,
                        "quantity": t.quantity,
                        "pnl": t.pnl,
                        "pnl_percent": t.pnl_percent,
                        "commission_paid": t.commission_paid,
                    }
                    for t in run.result.trades
                ],
            },
            strategy_spec={
                "name": run.strategy_spec.name,
                "description": run.strategy_spec.description,
                "entry_conditions": [
                    {
                        "left_operand": c.left_operand,
                        "operator": c.operator.value,
                        "right_operand": c.right_operand,
                    }
                    for c in run.strategy_spec.entry_conditions
                ],
                "exit_conditions": [
                    {
                        "left_operand": c.left_operand,
                        "operator": c.operator.value,
                        "right_operand": c.right_operand,
                    }
                    for c in run.strategy_spec.exit_conditions
                ],
                "position_size": {
                    "type": run.strategy_spec.position_size.type.value,
                    "value": run.strategy_spec.position_size.value,
                },
                "indicators": [
                    {
                        "name": i.name,
                        "params": i.params,
                        "output_name": i.output_name,
                    }
                    for i in run.strategy_spec.indicators
                ],
            } if run.strategy_spec else None,
            natural_language=run.natural_language,
        ))

    return RunHistoryResponse(
        runs=run_schemas,
        total_count=len(run_schemas),
    )


@app.get("/api/runs/{run_id}", tags=["Run History"])
async def get_run(run_id: str):
    """
    Get detailed information for a specific backtest run.

    Retrieves complete run details including strategy specification and performance metrics.

    ## Parameters
    - **run_id**: Unique identifier for the backtest run

    ## Returns
    - Full run record with all metrics
    - 404 error if run not found

    ## Example
    ```
    GET /api/runs/123e4567-e89b-12d3-a456-426614174000
    ```
    """
    pipeline = get_pipeline()
    run = pipeline.get_run_by_id(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return {
        "run_id": run.run_id,
        "timestamp": run.timestamp.isoformat(),
        "natural_language": run.natural_language,
        "strategy_spec": {
            "name": run.strategy_spec.name,
            "description": run.strategy_spec.description,
        } if run.strategy_spec else None,
        "result": {
            "total_return": run.result.total_return,
            "max_drawdown": run.result.max_drawdown,
            "num_trades": run.result.num_trades,
            "win_rate": run.result.win_rate,
            "sharpe_ratio": run.result.sharpe_ratio,
            "profit_factor": run.result.profit_factor,
        },
    }


@app.get("/api/symbols", tags=["Reference Data"])
async def get_available_symbols():
    """
    Get list of available trading symbols for backtesting.

    Returns supported USDT trading pairs from Binance.
    Use these symbols in backtest requests.

    ## Returns
    List of available symbols (e.g., BTCUSDT, ETHUSDT)
    """
    # Common USDT pairs - in production, fetch from Binance
    return {
        "symbols": [
            "BTC/USDT",
            "ETH/USDT",
            "BNB/USDT",
            "SOL/USDT",
            "XRP/USDT",
            "ADA/USDT",
            "DOGE/USDT",
            "AVAX/USDT",
            "DOT/USDT",
            "LINK/USDT",
            "MATIC/USDT",
            "UNI/USDT",
            "LTC/USDT",
            "ATOM/USDT",
            "NEAR/USDT",
            "ARB/USDT",
            "OP/USDT",
            "SUI/USDT",
            "APT/USDT",
            "INJ/USDT",
            "TIA/USDT",
            "SEI/USDT",
            "FET/USDT",
            "RENDER/USDT",
            "WLD/USDT",
            "PEPE/USDT",
        ],
    }


@app.get("/api/validate-symbol", tags=["Reference Data"])
async def validate_symbol(symbol: str = Query(..., description="Symbol to validate, e.g. PEPE/USDT")):
    """Check if a trading symbol exists on Binance. Accepts BASE/USDT or BASEUSDT format."""
    normalized = symbol.upper().replace('/', '')
    if not re.match(r'^[A-Z]+USDT$', normalized):
        return {"valid": False, "error": f"Symbol must be in BASE/USDT format (e.g. PEPE/USDT)"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.binance.com/api/v3/exchangeInfo",
                params={"symbol": normalized},
            )
        if resp.status_code == 200:
            return {"valid": True}
        return {"valid": False, "error": f"{symbol} not found on Binance"}
    except Exception as e:
        return {"valid": False, "error": f"Could not verify symbol: {str(e)}"}


@app.get("/api/models", tags=["Reference Data"])
async def get_available_models():
    """
    Get the list of supported models (OpenAI + Claude) for the model picker.

    The list is the single source of truth in ``shared.model_catalog``; the
    entry flagged default is the project-wide default. Use these values in
    backtest / generate requests.
    """
    return {"models": models_payload()}


@app.get("/api/timeframes", tags=["Reference Data"])
async def get_available_timeframes():
    """
    Get list of supported candle timeframes for backtesting.

    Returns available intervals (1m, 5m, 15m, 1h, 4h, 1d) with display labels.
    Use these timeframe values in backtest requests.

    ## Returns
    List of timeframe objects with:
    - **value**: API value (e.g., "1h")
    - **label**: Human-readable label (e.g., "1 Hour")
    """
    return {
        "timeframes": [
            {"value": "1m", "label": "1 Minute"},
            {"value": "5m", "label": "5 Minutes"},
            {"value": "15m", "label": "15 Minutes"},
            {"value": "1h", "label": "1 Hour"},
            {"value": "4h", "label": "4 Hours"},
            {"value": "1d", "label": "1 Day"},
        ],
    }


def _serialize_walk_forward(result) -> WalkForwardResultSchema:
    """Convert WalkForwardResult dataclass to Pydantic schema."""
    return WalkForwardResultSchema(
        windows=[
            WalkForwardWindowSchema(
                window_index=w.window_index,
                is_start=w.is_start,
                is_end=w.is_end,
                oos_start=w.oos_start,
                oos_end=w.oos_end,
                is_total_return=_safe_float(w.is_total_return),
                oos_total_return=_safe_float(w.oos_total_return),
                is_sharpe=_safe_float(w.is_sharpe),
                oos_sharpe=_safe_float(w.oos_sharpe),
                is_num_trades=w.is_num_trades,
                oos_num_trades=w.oos_num_trades,
                oos_equity_curve=[_equity_point(ep) for ep in w.oos_equity_curve],
            )
            for w in result.windows
        ],
        num_windows=result.num_windows,
        is_months=result.is_months,
        oos_months=result.oos_months,
        combined_oos_return=_safe_float(result.combined_oos_return),
        combined_oos_sharpe=_safe_float(result.combined_oos_sharpe),
        combined_oos_win_rate=float(result.combined_oos_win_rate),
        combined_oos_max_drawdown=min(1.0, float(result.combined_oos_max_drawdown)),
        wfe=_safe_float(result.wfe),
        combined_oos_equity=[_equity_point(ep) for ep in result.combined_oos_equity],
        errors=result.errors,
    )


@app.post("/api/execute-walk-forward", tags=["AI Script Proxy"])
async def execute_walk_forward(request: ExecuteWalkForwardRequest, raw_request: Request):
    """
    Run walk-forward validation on a previously generated strategy script.

    Streams real-time progress as Server-Sent Events (SSE). Each event is a JSON
    object with a ``type`` field:

    - ``{"type":"status","phase":"fetch"}``
    - ``{"type":"status","phase":"walk_forward","wf_window":K,"wf_total":N}``
    - ``{"type":"result","success":true,"result":{WalkForwardResult}}``
    - ``{"type":"error","errors":["..."]}``
    """
    pipeline = get_pipeline()

    start_datetime = datetime.combine(
        request.start_date,
        datetime.min.time(),
    ).replace(tzinfo=timezone.utc)

    end_datetime = datetime.combine(
        request.end_date,
        datetime.max.time(),
    ).replace(tzinfo=timezone.utc)

    queue: asyncio.Queue = asyncio.Queue()
    cancel_token = CancellationToken()

    async def status_cb(event: dict) -> None:
        await queue.put(event)

    async def run() -> None:
        async with app.state.backtest_semaphore:
            try:
                result, errors = await pipeline.execute_walk_forward(
                    script_id=request.script_id,
                    symbol=request.symbol,
                    timeframe=request.timeframe,
                    start_date=start_datetime,
                    end_date=end_datetime,
                    initial_capital=request.initial_capital,
                    commission=request.commission,
                    allow_short=request.allow_short,
                    leverage=request.leverage,
                    is_months=request.is_months,
                    oos_months=request.oos_months,
                    max_windows=request.max_windows,
                    script_code=request.script_code,
                    strategy_name=request.strategy_name,
                    strategy_description=request.strategy_description,
                    cancel_token=cancel_token,
                    status_callback=status_cb,
                )

                if result is None:
                    await queue.put({
                        "type": "error",
                        "errors": errors,
                    })
                else:
                    result_schema = _serialize_walk_forward(result)
                    await queue.put({
                        "type": "result",
                        "success": True,
                        "result": jsonable_encoder(result_schema),
                        "errors": errors,
                    })
            except Exception as e:
                await queue.put({
                    "type": "error",
                    "errors": [str(e)],
                })
            finally:
                await queue.put(None)

    task = asyncio.create_task(run())

    async def event_stream():
        try:
            while True:
                if await raw_request.is_disconnected():
                    cancel_token.cancel()
                    task.cancel()
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                if event is None:
                    return
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            cancel_token.cancel()
            task.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    from backend.session_store import initialize as init_session_store
    init_session_store()
    # Pre-initialize pipeline
    get_pipeline()
    # One backtest at a time per worker process; total capacity = WEB_CONCURRENCY workers
    app.state.worker_count = int(os.environ.get("WEB_CONCURRENCY", "1"))
    app.state.backtest_semaphore = asyncio.Semaphore(1)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _pipeline
    _pipeline = None
