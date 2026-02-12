"""
FastAPI Application and Endpoints

REST API for the backtesting platform.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.pipeline import BacktestPipeline
from shared.schemas import (
    BacktestResultSchema,
    EquityPointSchema,
    RunBacktestAPIRequest,
    RunBacktestAPIResponse,
    RunHistoryResponse,
    RunRecordSchema,
    StrategySpecSchema,
    TradeSchema,
)

# Initialize FastAPI app
app = FastAPI(
    title="Finovae Strategy Platform",
    description="Crypto AI Backtesting Platform with NL Strategy Compilation",
    version="0.1.0",
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

# Global pipeline instance
_pipeline: Optional[BacktestPipeline] = None


def get_pipeline() -> BacktestPipeline:
    """Get or create pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = BacktestPipeline()
    return _pipeline


# =============================================================================
# API ENDPOINTS
# =============================================================================


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Finovae Strategy Platform",
        "version": "0.1.0",
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "api": "ok",
            "pipeline": "ok",
        },
    }


@app.post("/api/run-backtest", response_model=RunBacktestAPIResponse)
async def run_backtest(request: RunBacktestAPIRequest):
    """
    Run a complete backtest from natural language strategy description.

    This endpoint:
    1. Compiles NL to StrategySpec using Claude API
    2. Generates executable Python code
    3. Fetches OHLCV data from Binance
    4. Runs the backtest in a sandbox
    5. Returns results with metrics and trades

    Args:
        request: Backtest request with NL strategy description

    Returns:
        RunBacktestAPIResponse with results or errors
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
    result, strategy_spec, errors = await pipeline.run(
        natural_language=request.natural_language,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=start_datetime,
        end_date=end_datetime,
        initial_capital=request.initial_capital,
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
            max_drawdown=result.max_drawdown,
            num_trades=result.num_trades,
            win_rate=result.win_rate,
            sharpe_ratio=result.sharpe_ratio,
            profit_factor=result.profit_factor,
            equity_curve=[
                EquityPointSchema(
                    timestamp=ep.timestamp,
                    equity=ep.equity,
                    drawdown=ep.drawdown,
                )
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
        strategy_spec=spec_schema,
        errors=errors,
    )


@app.get("/api/runs", response_model=RunHistoryResponse)
async def get_run_history():
    """
    Get history of all backtest runs.

    Returns:
        RunHistoryResponse with list of run records
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
            },
            natural_language=run.natural_language,
        ))

    return RunHistoryResponse(
        runs=run_schemas,
        total_count=len(run_schemas),
    )


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    """
    Get a specific run by ID.

    Args:
        run_id: Run identifier

    Returns:
        Full run record or 404
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
        },
        "result": {
            "total_return": run.result.total_return,
            "max_drawdown": run.result.max_drawdown,
            "num_trades": run.result.num_trades,
            "win_rate": run.result.win_rate,
            "sharpe_ratio": run.result.sharpe_ratio,
            "profit_factor": run.result.profit_factor,
        },
    }


@app.get("/api/symbols")
async def get_available_symbols():
    """
    Get list of available trading symbols.

    Returns:
        List of USDT trading pairs
    """
    # Common USDT pairs - in production, fetch from Binance
    return {
        "symbols": [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "ADAUSDT",
            "DOGEUSDT",
            "AVAXUSDT",
            "DOTUSDT",
            "LINKUSDT",
        ],
    }


@app.get("/api/timeframes")
async def get_available_timeframes():
    """
    Get list of supported timeframes.

    Returns:
        List of supported candle intervals
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


# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    # Pre-initialize pipeline
    get_pipeline()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _pipeline
    _pipeline = None
