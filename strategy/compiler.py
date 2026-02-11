"""
Natural Language Strategy Compiler

Compiles natural language strategy descriptions into StrategySpec using Claude API.
"""

import json
import os
from typing import Optional

from anthropic import Anthropic

from shared.contracts import (
    CompileConstraints,
    Condition,
    ConditionOperator,
    IndicatorConfig,
    PositionSizing,
    PositionSizingType,
    StrategyCompileRequest,
    StrategyCompileResponse,
    StrategySpec,
)
from strategy.indicators import INDICATOR_REGISTRY


class StrategyCompilerError(Exception):
    """Exception raised for compilation errors."""
    pass


class StrategyCompiler:
    """
    Compiles natural language strategy descriptions into executable StrategySpec.

    Uses Claude API to parse and structure the strategy, then validates
    against the indicator whitelist and constraint limits.
    """

    SYSTEM_PROMPT = """You are a trading strategy compiler. Your job is to convert natural language trading strategy descriptions into a structured JSON format.

You must output ONLY valid JSON with the following structure:
{
    "name": "Short descriptive name for the strategy",
    "description": "One-sentence description of what the strategy does",
    "indicators": [
        {
            "name": "indicator_name",
            "params": {"period": 14},
            "output_name": "unique_name_to_reference_this"
        }
    ],
    "entry_conditions": [
        {
            "left_operand": "indicator_output_name or 'price'",
            "operator": "< | > | <= | >= | == | cross_above | cross_below",
            "right_operand": "indicator_output_name or number"
        }
    ],
    "exit_conditions": [
        {
            "left_operand": "indicator_output_name or 'price'",
            "operator": "< | > | <= | >= | == | cross_above | cross_below",
            "right_operand": "indicator_output_name or number"
        }
    ],
    "position_size": {
        "type": "fixed_percent | fixed_amount | all_in",
        "value": 100
    }
}

Rules:
1. Available indicators: {indicators}
2. For entry_conditions: ALL conditions must be true to enter (AND logic)
3. For exit_conditions: ANY condition being true triggers exit (OR logic)
4. Use "price" to reference the current close price
5. Use cross_above/cross_below for crossover signals
6. Default position_size to all_in (type: "all_in", value: 100) if not specified
7. Each indicator must have a unique output_name
8. Conditions reference indicators by their output_name

Examples:
- "RSI < 30" -> entry_condition with rsi_14 < 30
- "Price crosses above SMA(50)" -> cross_above between price and sma_50
- "MACD crosses below signal line" -> cross_below between macd and macd_signal

Output ONLY the JSON, no explanations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize strategy compiler.

        Args:
            api_key: Anthropic API key (uses env var if None)
            model: Claude model to use for compilation
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self._client: Optional[Anthropic] = None

    def _get_client(self) -> Anthropic:
        """Get or create Anthropic client."""
        if not self.api_key:
            raise StrategyCompilerError(
                "ANTHROPIC_API_KEY not set. Please set the environment variable."
            )
        if not self._client:
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def _build_system_prompt(self, constraints: CompileConstraints) -> str:
        """Build system prompt with available indicators."""
        indicator_list = ", ".join(constraints.allowed_indicators)
        return self.SYSTEM_PROMPT.format(indicators=indicator_list)

    def _parse_condition(self, cond_data: dict) -> Condition:
        """Parse condition from JSON data."""
        operator_map = {
            ">": ConditionOperator.GREATER_THAN,
            "<": ConditionOperator.LESS_THAN,
            ">=": ConditionOperator.GREATER_EQUAL,
            "<=": ConditionOperator.LESS_EQUAL,
            "==": ConditionOperator.EQUAL,
            "cross_above": ConditionOperator.CROSS_ABOVE,
            "cross_below": ConditionOperator.CROSS_BELOW,
        }

        operator_str = cond_data.get("operator", "")
        if operator_str not in operator_map:
            raise StrategyCompilerError(f"Unknown operator: {operator_str}")

        right_operand = cond_data.get("right_operand")
        if isinstance(right_operand, (int, float)):
            right_operand = float(right_operand)

        return Condition(
            left_operand=str(cond_data.get("left_operand", "")),
            operator=operator_map[operator_str],
            right_operand=right_operand,
        )

    def _parse_indicator(self, ind_data: dict) -> IndicatorConfig:
        """Parse indicator config from JSON data."""
        params = ind_data.get("params", {})
        # Ensure params are int/float
        parsed_params = {}
        for k, v in params.items():
            if isinstance(v, (int, float)):
                parsed_params[k] = v
            else:
                try:
                    parsed_params[k] = float(v)
                except (ValueError, TypeError):
                    parsed_params[k] = v

        return IndicatorConfig(
            name=ind_data.get("name", ""),
            params=parsed_params,
            output_name=ind_data.get("output_name", ""),
        )

    def _parse_position_sizing(self, sizing_data: dict) -> PositionSizing:
        """Parse position sizing from JSON data."""
        type_map = {
            "fixed_amount": PositionSizingType.FIXED_AMOUNT,
            "fixed_percent": PositionSizingType.FIXED_PERCENT,
            "all_in": PositionSizingType.ALL_IN,
        }

        type_str = sizing_data.get("type", "all_in")
        if type_str not in type_map:
            raise StrategyCompilerError(f"Unknown position sizing type: {type_str}")

        return PositionSizing(
            type=type_map[type_str],
            value=float(sizing_data.get("value", 100)),
        )

    def _validate_strategy(
        self,
        spec: StrategySpec,
        constraints: CompileConstraints,
    ) -> list[str]:
        """Validate strategy against constraints. Returns list of errors."""
        errors = []

        # Check indicator count
        if len(spec.indicators) > constraints.max_indicators:
            errors.append(
                f"Too many indicators: {len(spec.indicators)} > {constraints.max_indicators}"
            )

        # Check indicator whitelist
        for ind in spec.indicators:
            if ind.name not in constraints.allowed_indicators:
                errors.append(f"Indicator not allowed: {ind.name}")

        # Check condition counts
        if len(spec.entry_conditions) > constraints.max_conditions:
            errors.append(
                f"Too many entry conditions: {len(spec.entry_conditions)} > {constraints.max_conditions}"
            )

        if len(spec.exit_conditions) > constraints.max_conditions:
            errors.append(
                f"Too many exit conditions: {len(spec.exit_conditions)} > {constraints.max_conditions}"
            )

        # Validate indicator output_names are unique
        output_names = [ind.output_name for ind in spec.indicators]
        if len(output_names) != len(set(output_names)):
            errors.append("Duplicate indicator output_names found")

        # Validate condition operands reference valid indicators or 'price'
        valid_operands = set(output_names) | {"price"}

        for cond in spec.entry_conditions + spec.exit_conditions:
            if cond.left_operand not in valid_operands:
                errors.append(f"Unknown operand in condition: {cond.left_operand}")
            if isinstance(cond.right_operand, str) and cond.right_operand not in valid_operands:
                errors.append(f"Unknown operand in condition: {cond.right_operand}")

        return errors

    def compile(self, request: StrategyCompileRequest) -> StrategyCompileResponse:
        """
        Compile natural language into StrategySpec.

        Args:
            request: Compilation request with NL description

        Returns:
            StrategyCompileResponse with spec or errors
        """
        try:
            client = self._get_client()

            # Call Claude API
            response = client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=self._build_system_prompt(request.constraints),
                messages=[
                    {"role": "user", "content": request.natural_language}
                ],
            )

            # Extract JSON from response
            response_text = response.content[0].text.strip()

            # Try to parse JSON
            try:
                # Handle potential markdown code blocks
                if response_text.startswith("```"):
                    lines = response_text.split("\n")
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.startswith("```") and not in_json:
                            in_json = True
                            continue
                        elif line.startswith("```") and in_json:
                            break
                        elif in_json:
                            json_lines.append(line)
                    response_text = "\n".join(json_lines)

                data = json.loads(response_text)
            except json.JSONDecodeError as e:
                return StrategyCompileResponse(
                    success=False,
                    errors=[f"Failed to parse Claude response as JSON: {e}"],
                )

            # Parse into StrategySpec
            indicators = [self._parse_indicator(ind) for ind in data.get("indicators", [])]
            entry_conditions = [self._parse_condition(c) for c in data.get("entry_conditions", [])]
            exit_conditions = [self._parse_condition(c) for c in data.get("exit_conditions", [])]
            position_size = self._parse_position_sizing(
                data.get("position_size", {"type": "all_in", "value": 100})
            )

            spec = StrategySpec(
                name=data.get("name", "Unnamed Strategy"),
                description=data.get("description", ""),
                entry_conditions=entry_conditions,
                exit_conditions=exit_conditions,
                position_size=position_size,
                indicators=indicators,
            )

            # Validate
            validation_errors = self._validate_strategy(spec, request.constraints)
            if validation_errors:
                return StrategyCompileResponse(
                    success=False,
                    strategy_spec=spec,
                    errors=validation_errors,
                )

            return StrategyCompileResponse(
                success=True,
                strategy_spec=spec,
                errors=[],
            )

        except StrategyCompilerError as e:
            return StrategyCompileResponse(
                success=False,
                errors=[str(e)],
            )
        except Exception as e:
            return StrategyCompileResponse(
                success=False,
                errors=[f"Compilation failed: {str(e)}"],
            )

    def compile_sync(self, natural_language: str) -> StrategyCompileResponse:
        """
        Synchronous compilation with default constraints.

        Args:
            natural_language: Strategy description

        Returns:
            StrategyCompileResponse
        """
        request = StrategyCompileRequest(
            natural_language=natural_language,
            constraints=CompileConstraints(),
        )
        return self.compile(request)
