"""
Backtest Pipeline Orchestration

Coordinates the full backtest workflow from NL input to results.
"""

import asyncio
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from backtest.engine import BacktestEngine
from backtest.rating import RatingCalculator
from backend.sandbox import SandboxExecutor, SandboxError
from data.loader import OHLCVLoader
from data.validation import DataValidator, DataValidationError
from shared.contracts import (
    BacktestRequest,
    BacktestResult,
    CompileConstraints,
    GenerateStrategyResult,
    OHLCV,
    RunRecord,
    StoredScript,
    StrategyCompileRequest,
    StrategyRating,
    StrategySpec,
    WalkForwardResult,
)
from strategy.codegen import CodeGenerator
from strategy.compiler import StrategyCompiler
from strategy.insights_generator import InsightsGenerator
from strategy.script_generator import ScriptGenerator

from shared.model_catalog import DEFAULT_MODEL


class PipelineError(Exception):
    """Exception raised for pipeline errors."""
    pass


class CancellationToken:
    """Thread-safe cancellation token for cooperative cancellation."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Signal cancellation."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def check(self) -> None:
        """Raise PipelineError if cancelled."""
        if self._event.is_set():
            raise PipelineError("Operation cancelled")


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
        cache_dir: Optional[str] = None,
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
        self.script_generator = ScriptGenerator(api_key=anthropic_api_key)
        self.insights_generator = InsightsGenerator(api_key=anthropic_api_key)

        self._run_history: list[RunRecord] = []
        self._script_store: dict[str, StoredScript] = {}

    async def run(
        self,
        natural_language: str,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        commission: float = 0.00075,
        slippage: float = 0.0005,
        model: str = DEFAULT_MODEL,
    ) -> tuple[Optional[BacktestResult], Optional[StrategySpec], list[str], Optional[StrategyRating]]:
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
            Tuple of (BacktestResult, StrategySpec, errors, StrategyRating)
            If errors, result and spec may be None
        """
        errors: list[str] = []
        run_id = str(uuid.uuid4())[:8]

        # Step 1: Compile NL to StrategySpec
        self.compiler.model = model
        compile_request = StrategyCompileRequest(
            natural_language=natural_language,
            constraints=CompileConstraints(),
        )

        compile_response = self.compiler.compile(compile_request)

        if not compile_response.success:
            return None, None, compile_response.errors, None

        strategy_spec = compile_response.strategy_spec

        # Step 2: Generate Python code
        code, code_errors = self.codegen.generate_and_validate(strategy_spec)
        if code_errors:
            return None, strategy_spec, code_errors, None

        # Step 3: Validate code in sandbox
        validation_errors = self.sandbox.validate_code(code)
        if validation_errors:
            return None, strategy_spec, validation_errors, None

        # Step 4: Fetch OHLCV data
        try:
            data = await self.loader.load(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            return None, strategy_spec, [f"Data fetch failed: {e}"], None

        if not data:
            return None, strategy_spec, ["No data available for the specified period"], None

        # Step 5: Validate data
        try:
            validation_result = self.validator.validate(data)
            if not validation_result.is_valid:
                errors.extend(validation_result.warnings)
        except DataValidationError as e:
            return None, strategy_spec, [f"Data validation failed: {e}"], None

        # Step 6: Get signal function from sandbox
        try:
            signal_func = self.sandbox.get_signal_function(code)
        except SandboxError as e:
            return None, strategy_spec, [f"Sandbox setup failed: {e}"], None

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
            return None, strategy_spec, [f"Backtest execution failed: {e}"], None

        # Step 8: Compute rating
        timeframe_hours = self._timeframe_to_hours(timeframe)
        rating, _rating_timings = RatingCalculator.calculate(
            result=result,
            ohlcv_data=data,
            initial_capital=initial_capital,
            timeframe_hours=timeframe_hours,
        )

        # Step 9: Save to history
        run_record = RunRecord(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            request=backtest_request,
            result=result,
            strategy_spec=strategy_spec,
            natural_language=natural_language,
        )
        self._run_history.append(run_record)

        return result, strategy_spec, errors, rating

    @staticmethod
    def _timeframe_to_hours(timeframe: str) -> float:
        """Convert timeframe string to hours."""
        mapping = {
            "1m": 1 / 60,
            "5m": 5 / 60,
            "15m": 0.25,
            "1h": 1.0,
            "4h": 4.0,
            "1d": 24.0,
        }
        return mapping.get(timeframe, 4.0)

    def run_sync(
        self,
        natural_language: str,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        commission: float = 0.00075,
        slippage: float = 0.0005,
    ) -> tuple[Optional[BacktestResult], Optional[StrategySpec], list[str], Optional[StrategyRating]]:
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

    async def generate_strategy(
        self,
        natural_language: str,
        model: str = DEFAULT_MODEL,
        previous_script_code: Optional[str] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        previous_backtest_metrics: Optional[dict] = None,
        allow_short: bool = False,
        leverage: float = 1.0,
        usage_sink: Optional[list] = None,
    ) -> GenerateStrategyResult:
        """
        Generate a Python Strategy class script from natural language.

        Args:
            natural_language: Strategy description in plain English
            model: Claude model to use
            previous_script_code: If provided, refine this script instead of
                generating from scratch.
            symbol: Trading symbol for market context
            timeframe: Candle timeframe for calibrating indicators
            start_date: Backtest start date string
            end_date: Backtest end date string
            previous_backtest_metrics: Metrics from previous backtest

        Returns:
            GenerateStrategyResult with script code and metadata
        """
        script_id = str(uuid.uuid4())[:8]

        # Fetch OHLCV data for market analysis tools (best-effort)
        ohlcv_data: Optional[list[OHLCV]] = None
        if symbol and timeframe and start_date and end_date:
            try:
                from datetime import datetime as _dt
                _start = _dt.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                _end = _dt.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                ohlcv_data = await self.loader.load(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=_start,
                    end_date=_end,
                )
            except Exception:
                pass  # Tools will gracefully degrade without data

        # Generate script via AI
        self.script_generator.model = model
        script_code, strategy_name, strategy_description, gen_errors = (
            self.script_generator.generate(
                natural_language,
                previous_script_code,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                previous_backtest_metrics=previous_backtest_metrics,
                ohlcv_data=ohlcv_data,
                allow_short=allow_short,
                leverage=leverage,
                usage_sink=usage_sink,
            )
        )

        # Determine the model that was actually used (may have been downgraded)
        is_refinement = previous_script_code is not None
        from strategy.script_generator import SONNET_MODEL, HAIKU_MODEL
        effective_model = model
        if is_refinement and model == SONNET_MODEL:
            effective_model = HAIKU_MODEL

        if gen_errors:
            return GenerateStrategyResult(
                script_id=script_id,
                script_code="",
                strategy_name="",
                strategy_description="",
                validation_errors=gen_errors,
                model_used=effective_model,
            )

        # Validate in sandbox
        validation_errors = self.sandbox.validate_code(script_code)

        # Also check that Strategy class can be instantiated
        if not validation_errors:
            try:
                self.sandbox.get_strategy_instance(script_code)
            except SandboxError as e:
                validation_errors.append(str(e))

        # Store script (even if validation errors, so user can edit and retry)
        self._script_store[script_id] = StoredScript(
            script_id=script_id,
            script_code=script_code,
            strategy_name=strategy_name,
            strategy_description=strategy_description,
            natural_language=natural_language,
            created_at=datetime.now(timezone.utc),
            model=model,
        )

        return GenerateStrategyResult(
            script_id=script_id,
            script_code=script_code,
            strategy_name=strategy_name,
            strategy_description=strategy_description,
            validation_errors=validation_errors,
            model_used=effective_model,
        )

    async def execute_backtest(
        self,
        script_id: str,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        commission: float = 0.00075,
        slippage: float = 0.0005,
        script_code: Optional[str] = None,
        strategy_name: Optional[str] = None,
        strategy_description: Optional[str] = None,
        cancel_token: Optional[CancellationToken] = None,
        status_callback: Optional[Callable] = None,
        allow_short: bool = False,
        leverage: float = 1.0,
        max_order_size_pct: Optional[float] = None,
        max_daily_loss_pct: Optional[float] = None,
        wfv_enabled: bool = False,
        wfv_is_months: int = 6,
        wfv_oos_months: int = 3,
        wfv_max_windows: Optional[int] = None,
    ) -> tuple[Optional[BacktestResult], list[str], Optional[StrategyRating], dict, Optional[WalkForwardResult]]:
        """
        Execute a backtest using a previously generated (or edited) script.

        Args:
            script_id: ID of the stored script
            symbol: Trading pair
            timeframe: Candle interval
            start_date: Backtest start
            end_date: Backtest end
            initial_capital: Starting capital
            commission: Commission rate
            slippage: Slippage rate
            script_code: If provided, overrides the stored script (user edited)

        Returns:
            Tuple of (BacktestResult, errors, StrategyRating, timings_dict)
        """
        t_total_start = time.perf_counter()
        timings: dict = {}

        stored = self._script_store.get(script_id)
        if not stored and script_code is None:
            timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000
            return None, [f"Script {script_id} not found"], None, timings, None
        if not stored and script_code is not None:
            stored = StoredScript(
                script_id=script_id,
                script_code=script_code,
                strategy_name=strategy_name or "Restored Strategy",
                strategy_description=strategy_description or "",
                natural_language="",
                created_at=datetime.now(timezone.utc),
                model="unknown",
            )
            self._script_store[script_id] = stored

        code = script_code if script_code is not None else stored.script_code

        try:
            return await self._execute_backtest_inner(
                code=code,
                stored=stored,
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                commission=commission,
                slippage=slippage,
                script_code=script_code,
                cancel_token=cancel_token,
                status_callback=status_callback,
                t_total_start=t_total_start,
                allow_short=allow_short,
                leverage=leverage,
                max_order_size_pct=max_order_size_pct,
                max_daily_loss_pct=max_daily_loss_pct,
                wfv_enabled=wfv_enabled,
                wfv_is_months=wfv_is_months,
                wfv_oos_months=wfv_oos_months,
                wfv_max_windows=wfv_max_windows,
            )
        except Exception:
            raise

    async def _execute_backtest_inner(
        self,
        code: str,
        stored,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
        commission: float,
        slippage: float,
        script_code: Optional[str],
        cancel_token: Optional[CancellationToken],
        status_callback: Optional[Callable],
        t_total_start: float,
        allow_short: bool = False,
        leverage: float = 1.0,
        max_order_size_pct: Optional[float] = None,
        max_daily_loss_pct: Optional[float] = None,
        wfv_enabled: bool = False,
        wfv_is_months: int = 6,
        wfv_oos_months: int = 3,
        wfv_max_windows: Optional[int] = None,
    ) -> tuple[Optional[BacktestResult], list[str], Optional[StrategyRating], dict, Optional[WalkForwardResult]]:
        timings: dict = {}
        loop = asyncio.get_running_loop()

        # --- Validate phase ---
        t0 = time.perf_counter()

        # Re-validate if code was edited
        if script_code is not None:
            if status_callback:
                await status_callback({"type": "status", "phase": "validate", "validate_step": "pattern_check"})
                await asyncio.sleep(0)
            validation_errors = await asyncio.to_thread(self.sandbox.validate_code, code)
            if validation_errors:
                timings["validate_ms"] = (time.perf_counter() - t0) * 1000
                timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000
                return None, validation_errors, None, timings, None
            if status_callback:
                await status_callback({"type": "status", "phase": "validate", "validate_step": "instantiate"})
                await asyncio.sleep(0)
            try:
                await asyncio.to_thread(self.sandbox.get_strategy_instance, code)
            except SandboxError as e:
                timings["validate_ms"] = (time.perf_counter() - t0) * 1000
                timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000
                return None, [str(e)], None, timings, None

        # Get setup_func and signal_func separately to avoid O(N²) setup re-invocation
        if status_callback:
            await status_callback({"type": "status", "phase": "validate", "validate_step": "setup_signal"})
            await asyncio.sleep(0)
        try:
            setup_func, signal_func = await asyncio.to_thread(self.sandbox.get_setup_and_signal_from_strategy, code)
        except SandboxError as e:
            timings["validate_ms"] = (time.perf_counter() - t0) * 1000
            timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000
            return None, [f"Sandbox setup failed: {e}"], None, timings, None

        # Extract stop-loss / take-profit / leverage params from strategy class
        strategy_params = self.sandbox.get_strategy_params(code)
        stop_loss_pct = strategy_params.get("stop_loss_pct")
        take_profit_pct = strategy_params.get("take_profit_pct")
        # UI request leverage always wins; script's leverage attr is for trading clients only
        effective_leverage = leverage

        timings["validate_ms"] = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()

        if cancel_token:
            cancel_token.check()

        # --- Fetch phase ---
        if status_callback:
            await status_callback({"type": "status", "phase": "fetch"})
            await asyncio.sleep(0)

        try:
            data = await self.loader.load(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            timings["fetch_ms"] = (time.perf_counter() - t0) * 1000
            timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000
            return None, [f"Data fetch failed: {e}"], None, timings, None

        if not data:
            timings["fetch_ms"] = (time.perf_counter() - t0) * 1000
            timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000
            return None, ["No data available for the specified period"], None, timings, None

        # Validate data
        try:
            validation_result = self.validator.validate(data)
            if not validation_result.is_valid:
                pass  # warnings only, continue
        except DataValidationError as e:
            timings["fetch_ms"] = (time.perf_counter() - t0) * 1000
            timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000
            return None, [f"Data validation failed: {e}"], None, timings, None

        # Fetch sub-bar resolution data for improved SL/TP accuracy (best-effort).
        # Only fetched when the strategy actually uses SL or TP to avoid unnecessary
        # API/cache hits for signal-exit-only strategies.
        resolution_data: list[OHLCV] = []
        if stop_loss_pct is not None or take_profit_pct is not None:
            try:
                resolution_data = await self.loader.load_resolution(
                    symbol=symbol,
                    strategy_tf=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception:
                pass  # Graceful degradation: engine falls back to OHLC path model

        timings["fetch_ms"] = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()

        if cancel_token:
            cancel_token.check()

        # --- Simulate phase ---
        if status_callback:
            await status_callback({"type": "status", "phase": "simulate"})
            await asyncio.sleep(0)

        run_id = str(uuid.uuid4())[:8]
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
            allow_short=allow_short,
            leverage=effective_leverage,
            max_order_size_pct=max_order_size_pct,
            max_daily_loss_pct=max_daily_loss_pct,
        )

        cancel_check = cancel_token.check if cancel_token else None

        def _sim_progress(bar: int, total: int) -> None:
            if status_callback:
                asyncio.run_coroutine_threadsafe(
                    status_callback({"type": "status", "phase": "simulate", "sim_bar": bar, "sim_total_bars": total}),
                    loop,
                )

        try:
            result = await asyncio.to_thread(
                self.engine.run,
                request=backtest_request,
                data=data,
                signal_func=signal_func,
                cancel_check=cancel_check,
                progress_callback=_sim_progress if status_callback else None,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                setup_func=setup_func,
                resolution_data=resolution_data or None,
            )
        except Exception as e:
            timings["simulate_ms"] = (time.perf_counter() - t0) * 1000
            timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000
            return None, [f"Backtest execution failed: {e}"], None, timings, None

        timings["simulate_ms"] = (time.perf_counter() - t0) * 1000
        t0 = time.perf_counter()

        if cancel_token:
            cancel_token.check()

        # --- Calculate phase ---
        if status_callback:
            await status_callback({"type": "status", "phase": "calculate"})
            await asyncio.sleep(0)

        def _calc_progress(step_key: str, step_index: int) -> None:
            if status_callback:
                asyncio.run_coroutine_threadsafe(
                    status_callback({"type": "status", "phase": "calculate", "calculate_step": step_key, "calculate_step_index": step_index}),
                    loop,
                )

        timeframe_hours = self._timeframe_to_hours(timeframe)
        rating, rating_timings = await asyncio.to_thread(
            RatingCalculator.calculate,
            result=result,
            ohlcv_data=data,
            initial_capital=initial_capital,
            timeframe_hours=timeframe_hours,
            step_callback=_calc_progress if status_callback else None,
        )

        timings["calculate_ms"] = (time.perf_counter() - t0) * 1000
        timings["calculate_steps"] = rating_timings

        # --- Walk-Forward phase (best-effort) ---
        wf_result: Optional[WalkForwardResult] = None
        if wfv_enabled:
            t0_wf = time.perf_counter()
            if cancel_token:
                cancel_token.check()
            if status_callback:
                await status_callback({"type": "status", "phase": "walk_forward", "wf_window": 0, "wf_total": 0})
                await asyncio.sleep(0)
            try:
                from backtest.walk_forward import run_walk_forward
                wf_result = await run_walk_forward(
                    engine=self.engine,
                    sandbox=self.sandbox,
                    code=code,
                    symbol=symbol,
                    timeframe=timeframe,
                    full_start=start_date.date(),
                    full_end=end_date.date(),
                    initial_capital=initial_capital,
                    commission=commission,
                    slippage=slippage,
                    allow_short=allow_short,
                    leverage=effective_leverage,
                    is_months=wfv_is_months,
                    oos_months=wfv_oos_months,
                    max_windows=wfv_max_windows,
                    full_data=data,
                    timeframe_hours=timeframe_hours,
                    status_callback=status_callback,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("WFV phase failed (best-effort): %s", e)
            timings["walk_forward_ms"] = (time.perf_counter() - t0_wf) * 1000

        # Save to history
        run_record = RunRecord(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            request=backtest_request,
            result=result,
            strategy_spec=None,
            natural_language=stored.natural_language,
        )
        self._run_history.append(run_record)

        timings["total_ms"] = (time.perf_counter() - t_total_start) * 1000

        return result, [], rating, timings, wf_result

    async def generate_insights(
        self,
        backtest_result: dict,
        strategy_name: str = "",
        strategy_description: str = "",
        script_code: str = "",
        natural_language_prompt: str = "",
        model: str = DEFAULT_MODEL,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        allow_short: bool = False,
        leverage: float = 1.0,
        initial_capital: Optional[float] = None,
        previous_summary: Optional[str] = None,
        previous_suggestions: Optional[list[str]] = None,
        walk_forward_result: Optional[dict] = None,
        usage_sink: Optional[list] = None,
    ) -> tuple[str, list[dict], list[str]]:
        """
        Generate AI insights (summary + suggestions) from backtest results.

        Returns:
            Tuple of (summary, suggestions, errors)
        """
        self.insights_generator.model = model
        return self.insights_generator.generate(
            backtest_result=backtest_result,
            strategy_name=strategy_name,
            strategy_description=strategy_description,
            script_code=script_code,
            natural_language_prompt=natural_language_prompt,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            allow_short=allow_short,
            leverage=leverage,
            initial_capital=initial_capital,
            previous_summary=previous_summary,
            previous_suggestions=previous_suggestions,
            walk_forward_result=walk_forward_result,
            usage_sink=usage_sink,
        )

    async def execute_walk_forward(
        self,
        script_id: str,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
        allow_short: bool = False,
        leverage: float = 1.0,
        is_months: int = 6,
        oos_months: int = 3,
        max_windows: Optional[int] = None,
        script_code: Optional[str] = None,
        strategy_name: Optional[str] = None,
        strategy_description: Optional[str] = None,
        cancel_token: Optional[CancellationToken] = None,
        status_callback: Optional[Callable] = None,
    ) -> tuple[Optional[WalkForwardResult], list[str]]:
        """
        Run walk-forward validation for a previously generated script.

        Returns:
            Tuple of (WalkForwardResult | None, errors)
        """
        from backtest.walk_forward import run_walk_forward

        # Resolve code from script store
        stored = self._script_store.get(script_id)
        if not stored and script_code is None:
            return None, [f"Script {script_id} not found"]
        if not stored and script_code is not None:
            stored = StoredScript(
                script_id=script_id,
                script_code=script_code,
                strategy_name=strategy_name or "Restored Strategy",
                strategy_description=strategy_description or "",
                natural_language="",
                created_at=datetime.now(timezone.utc),
                model="unknown",
            )
            self._script_store[script_id] = stored

        code = script_code if script_code is not None else stored.script_code  # type: ignore[union-attr]

        # Validate code (light check only — sandbox already validated during generate)
        validation_errors = self.sandbox.validate_code(code)
        if validation_errors:
            return None, validation_errors

        if cancel_token:
            cancel_token.check()

        # Fetch full date range data once
        if status_callback:
            await status_callback({"type": "status", "phase": "fetch"})
            await asyncio.sleep(0)

        try:
            full_data = await self.loader.load(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as e:
            return None, [f"Data fetch failed: {e}"]

        if not full_data:
            return None, ["No data available for the specified period"]

        if cancel_token:
            cancel_token.check()

        timeframe_hours = self._timeframe_to_hours(timeframe)

        if status_callback:
            await status_callback({"type": "status", "phase": "walk_forward", "wf_window": 0, "wf_total": 0})
            await asyncio.sleep(0)

        try:
            result = await run_walk_forward(
                engine=self.engine,
                sandbox=self.sandbox,
                code=code,
                symbol=symbol,
                timeframe=timeframe,
                full_start=start_date.date(),
                full_end=end_date.date(),
                initial_capital=initial_capital,
                commission=commission,
                slippage=slippage,
                allow_short=allow_short,
                leverage=leverage,
                is_months=is_months,
                oos_months=oos_months,
                max_windows=max_windows,
                full_data=full_data,
                timeframe_hours=timeframe_hours,
                status_callback=status_callback,
            )
        except Exception as e:
            return None, [f"Walk-forward failed: {e}"]

        return result, result.errors if result else []

    def get_stored_script(self, script_id: str) -> Optional[StoredScript]:
        """Get a stored script by ID."""
        return self._script_store.get(script_id)

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
    ) -> tuple[Optional[BacktestResult], Optional[StrategySpec], list[str], Optional[StrategyRating]]:
        """
        Rerun a previous backtest with optional modifications.

        Args:
            run_id: ID of the run to rerun
            modifications: Dict of parameters to modify

        Returns:
            Tuple of (BacktestResult, StrategySpec, errors, StrategyRating)
        """
        original = self.get_run_by_id(run_id)
        if not original:
            return None, None, [f"Run {run_id} not found"], None

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
