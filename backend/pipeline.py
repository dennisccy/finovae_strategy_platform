"""
Backtest Pipeline Orchestration

Coordinates the full backtest workflow from NL input to results.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from backtest.engine import BacktestEngine
from backend.sandbox import SandboxExecutor, SandboxError
from data.loader import OHLCVLoader
from data.validation import DataValidator, DataValidationError
from shared.contracts import (
    BacktestRequest,
    BacktestResult,
    CompileConstraints,
    RunRecord,
    StrategyCompileRequest,
    StrategySpec,
)
from strategy.codegen import CodeGenerator
from strategy.compiler import StrategyCompiler


class PipelineError(Exception):
    """Exception raised for pipeline errors."""
    pass


class BacktestPipeline:
    """
    Orchestrates the complete backtest workflow:

    1. Compile NL → StrategySpec (Claude API)
    2. Generate Python code from StrategySpec
    3. Validate code in sandbox
    4. Fetch OHLCV data
    5. Run backtest
    6. Return results
    """

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        cache_dir: str = ".cache/ohlcv",
        random_seed: int = 42,
    ):
        """
        Initialize pipeline components.

        Args:
            anthropic_api_key: API key for Claude (uses env var if None)
            cache_dir: Directory for OHLCV data cache
            random_seed: Seed for deterministic backtest execution
        """
        self.compiler = StrategyCompiler(api_key=anthropic_api_key)
        self.codegen = CodeGenerator()
        self.sandbox = SandboxExecutor()
        self.loader = OHLCVLoader(cache_dir=cache_dir)
        self.validator = DataValidator()
        self.engine = BacktestEngine(random_seed=random_seed)

        self._run_history: list[RunRecord] = []

    async def run(
        self,
        natural_language: str,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ) -> tuple[Optional[BacktestResult], Optional[StrategySpec], list[str]]:
        """
        Run complete backtest pipeline.

        Args:
            natural_language: Strategy description in plain English
            symbol: Trading pair (e.g., "BTCUSDT")
            timeframe: Candle interval
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital in USDT
            commission: Commission rate
            slippage: Slippage rate

        Returns:
            Tuple of (BacktestResult, StrategySpec, errors)
            If errors, result and spec may be None
        """
        errors: list[str] = []
        run_id = str(uuid.uuid4())[:8]

        # Step 1: Compile NL to StrategySpec
        compile_request = StrategyCompileRequest(
            natural_language=natural_language,
            constraints=CompileConstraints(),
        )

        compile_response = self.compiler.compile(compile_request)

        if not compile_response.success:
            return None, None, compile_response.errors

        strategy_spec = compile_response.strategy_spec

        # Step 2: Generate Python code
        code, code_errors = self.codegen.generate_and_validate(strategy_spec)
        if code_errors:
            return None, strategy_spec, code_errors

        # Step 3: Validate code in sandbox
        validation_errors = self.sandbox.validate_code(code)
        if validation_errors:
            return None, strategy_spec, validation_errors

        # Step 4: Fetch OHLCV data
        try:
            data = await self.loader.load(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            return None, strategy_spec, [f"Data fetch failed: {e}"]

        if not data:
            return None, strategy_spec, ["No data available for the specified period"]

        # Step 5: Validate data
        try:
            validation_result = self.validator.validate(data)
            if not validation_result.is_valid:
                errors.extend(validation_result.warnings)
        except DataValidationError as e:
            return None, strategy_spec, [f"Data validation failed: {e}"]

        # Step 6: Get signal function from sandbox
        try:
            signal_func = self.sandbox.get_signal_function(code)
        except SandboxError as e:
            return None, strategy_spec, [f"Sandbox setup failed: {e}"]

        # Step 7: Run backtest
        backtest_request = BacktestRequest(
            run_id=run_id,
            strategy_code=code,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date.date(),
            end_date=end_date.date(),
            initial_capital=initial_capital,
            commission=commission,
            slippage=slippage,
        )

        try:
            result = self.engine.run(
                request=backtest_request,
                data=data,
                signal_func=signal_func,
            )
        except Exception as e:
            return None, strategy_spec, [f"Backtest execution failed: {e}"]

        # Step 8: Save to history
        run_record = RunRecord(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            request=backtest_request,
            result=result,
            strategy_spec=strategy_spec,
            natural_language=natural_language,
        )
        self._run_history.append(run_record)

        return result, strategy_spec, errors

    def run_sync(
        self,
        natural_language: str,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ) -> tuple[Optional[BacktestResult], Optional[StrategySpec], list[str]]:
        """
        Synchronous wrapper for run().

        Args:
            Same as run()

        Returns:
            Same as run()
        """
        import asyncio

        return asyncio.run(self.run(
            natural_language=natural_language,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission=commission,
            slippage=slippage,
        ))

    def get_run_history(self) -> list[RunRecord]:
        """Get all run records."""
        return self._run_history.copy()

    def get_run_by_id(self, run_id: str) -> Optional[RunRecord]:
        """Get a specific run by ID."""
        for run in self._run_history:
            if run.run_id == run_id:
                return run
        return None

    def rerun_with_modifications(
        self,
        run_id: str,
        modifications: Optional[dict] = None,
    ) -> tuple[Optional[BacktestResult], Optional[StrategySpec], list[str]]:
        """
        Rerun a previous backtest with optional modifications.

        Args:
            run_id: ID of the run to rerun
            modifications: Dict of parameters to modify

        Returns:
            Tuple of (BacktestResult, StrategySpec, errors)
        """
        original = self.get_run_by_id(run_id)
        if not original:
            return None, None, [f"Run {run_id} not found"]

        mods = modifications or {}

        return self.run_sync(
            natural_language=mods.get("natural_language", original.natural_language),
            symbol=mods.get("symbol", original.request.symbol),
            timeframe=mods.get("timeframe", original.request.timeframe),
            start_date=mods.get("start_date", datetime.combine(
                original.request.start_date, datetime.min.time()
            ).replace(tzinfo=timezone.utc)),
            end_date=mods.get("end_date", datetime.combine(
                original.request.end_date, datetime.min.time()
            ).replace(tzinfo=timezone.utc)),
            initial_capital=mods.get("initial_capital", original.request.initial_capital),
            commission=mods.get("commission", original.request.commission),
            slippage=mods.get("slippage", original.request.slippage),
        )
