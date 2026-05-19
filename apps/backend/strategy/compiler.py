"""
Natural Language Strategy Compiler

Compiles natural language strategy descriptions into StrategySpec using Claude API.
"""

import json
import logging
import os
from typing import Optional

from anthropic import Anthropic
from openai import BadRequestError, OpenAI

from shared.llm_usage import capture_usage
from shared.model_catalog import (
    DEFAULT_MODEL,
    OPENAI_JSON_RESPONSE_FORMAT,
    OPENAI_MAX_COMPLETION_TOKENS,
    is_openai_model,
)

# Set up logging
logger = logging.getLogger(__name__)

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
        openai_api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ):
        """
        Initialize strategy compiler.

        Args:
            api_key: Anthropic API key (uses env var if None)
            openai_api_key: OpenAI API key (uses env var if None)
            model: Claude or OpenAI model to use for compilation
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._client: Optional[Anthropic] = None
        self._openai_client: Optional[OpenAI] = None

    def _get_client(self) -> Anthropic:
        """Get or create Anthropic client."""
        if not self.api_key:
            raise StrategyCompilerError(
                "ANTHROPIC_API_KEY not set. Please set the environment variable."
            )
        if not self._client:
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def _get_openai_client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if not self.openai_api_key:
            raise StrategyCompilerError(
                "OPENAI_API_KEY not set. Please set the environment variable."
            )
        if not self._openai_client:
            self._openai_client = OpenAI(api_key=self.openai_api_key)
        return self._openai_client

    def _build_system_prompt(self, constraints: CompileConstraints) -> str:
        """Build system prompt with available indicators."""
        indicator_list = ", ".join(constraints.allowed_indicators)
        return self.SYSTEM_PROMPT.replace("{indicators}", indicator_list)

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
        elif isinstance(right_operand, str):
            try:
                right_operand = float(right_operand)
            except ValueError:
                pass  # String reference to an indicator

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

    def compile(
        self,
        request: StrategyCompileRequest,
        usage_sink: Optional[list] = None,
    ) -> StrategyCompileResponse:
        """
        Compile natural language into StrategySpec.

        Args:
            request: Compilation request with NL description
            usage_sink: Optional list — when provided, the REAL SDK token
                usage for this call is appended (iter-3 cost tracking).

        Returns:
            StrategyCompileResponse with spec or errors
        """
        try:
            if is_openai_model(self.model):
                openai_client = self._get_openai_client()
                
                messages = [
                    {"role": "system", "content": self._build_system_prompt(request.constraints)},
                    {"role": "user", "content": request.natural_language}
                ]
                
                openai_kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "max_completion_tokens": OPENAI_MAX_COMPLETION_TOKENS["compiler"],
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
                        "StrategyCompiler: OpenAI rejected kwargs (%s); retrying without them",
                        e,
                    )
                    response = openai_client.chat.completions.create(**_retry)
                
                if hasattr(response, "usage") and response.usage:
                    u = response.usage
                    logger.info(
                        "StrategyCompiler tokens: model=%s input=%d output=%d",
                        self.model,
                        u.prompt_tokens,
                        u.completion_tokens,
                    )
                capture_usage(usage_sink, self.model, response, openai=True)

                response_text = response.choices[0].message.content.strip()

            else:
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

                capture_usage(usage_sink, self.model, response, openai=False)

                # Extract JSON from response
                response_text = response.content[0].text.strip()

            # Log the raw response for debugging
            logger.info(f"Raw Claude response: {response_text[:1000]}")

            # Try to parse JSON
            try:
                # Handle potential markdown code blocks
                if "```json" in response_text or "```" in response_text:
                    # Extract content between code fences
                    lines = response_text.split("\n")
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.strip().startswith("```"):
                            if in_json:
                                break
                            in_json = True
                            continue
                        elif in_json:
                            json_lines.append(line)
                    response_text = "\n".join(json_lines).strip()

                # Try to find JSON object boundaries if parsing fails
                if not response_text.startswith("{"):
                    # Find first { and last }
                    start_idx = response_text.find("{")
                    end_idx = response_text.rfind("}")
                    if start_idx != -1 and end_idx != -1:
                        response_text = response_text[start_idx:end_idx + 1]
                    else:
                        return StrategyCompileResponse(
                            success=False,
                            errors=[
                                "Could not find JSON object in Claude response",
                                f"Full response: {response_text[:1000]}"
                            ],
                        )

                logger.info(f"Extracted JSON text: {response_text[:500]}")
                data = json.loads(response_text)
                logger.info(f"Parsed JSON successfully: {list(data.keys())}")

            except json.JSONDecodeError as e:
                return StrategyCompileResponse(
                    success=False,
                    errors=[
                        f"Failed to parse Claude response as JSON: {e}",
                        f"Response text: {response_text[:1000]}"
                    ],
                )

            # Parse into StrategySpec
            try:
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
            except Exception as e:
                logger.error(f"Error parsing strategy spec: {e}")
                logger.error(f"Data keys: {list(data.keys())}")
                logger.error(f"Data content: {data}")
                return StrategyCompileResponse(
                    success=False,
                    errors=[
                        f"Error parsing strategy specification: {e}",
                        f"Received data keys: {list(data.keys())}",
                        f"Full response: {response_text[:1000]}"
                    ],
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
