"""
Fill Model for Order Execution

Handles slippage and commission calculations for simulated order fills.
"""

from dataclasses import dataclass


@dataclass
class BuyFillResult:
    """Result of a buy order fill."""
    fill_price: float      # Price after slippage
    quantity: float        # Quantity purchased
    commission: float      # Commission paid
    total_cost: float      # Total cost including commission


@dataclass
class SellFillResult:
    """Result of a sell order fill."""
    fill_price: float      # Price after slippage
    quantity: float        # Quantity sold
    commission: float      # Commission paid
    gross_proceeds: float  # Proceeds before commission
    net_proceeds: float    # Proceeds after commission


class FillModel:
    """
    Simulates order fills with slippage and commission.

    Models realistic execution by applying:
    - Slippage: Price impact from market orders
    - Commission: Binance spot trading fees
    """

    # Binance minimum order values
    MIN_NOTIONAL = 10.0  # Minimum order value in USDT

    def __init__(
        self,
        default_commission: float = 0.001,  # 0.1% Binance spot
        default_slippage: float = 0.0005,   # 0.05%
    ):
        """
        Initialize fill model.

        Args:
            default_commission: Default commission rate
            default_slippage: Default slippage rate
        """
        self.default_commission = default_commission
        self.default_slippage = default_slippage

    def calculate_buy_fill(
        self,
        price: float,
        available_cash: float,
        commission_rate: float | None = None,
        slippage_rate: float | None = None,
    ) -> BuyFillResult:
        """
        Calculate fill for a buy order.

        Slippage increases the price for buys (unfavorable).

        Args:
            price: Base execution price
            available_cash: Available cash in USDT
            commission_rate: Commission rate (uses default if None)
            slippage_rate: Slippage rate (uses default if None)

        Returns:
            BuyFillResult with fill details
        """
        commission_rate = self.default_commission if commission_rate is None else commission_rate
        slippage_rate = self.default_slippage if slippage_rate is None else slippage_rate

        # Apply slippage (buy at higher price)
        fill_price = price * (1 + slippage_rate)

        # Calculate maximum quantity we can buy
        # cash = quantity * fill_price + commission
        # cash = quantity * fill_price * (1 + commission_rate)
        # quantity = cash / (fill_price * (1 + commission_rate))
        max_quantity = available_cash / (fill_price * (1 + commission_rate))

        # Check minimum notional
        if max_quantity * fill_price < self.MIN_NOTIONAL:
            return BuyFillResult(
                fill_price=fill_price,
                quantity=0.0,
                commission=0.0,
                total_cost=0.0,
            )

        # Calculate costs
        gross_cost = max_quantity * fill_price
        commission = gross_cost * commission_rate
        total_cost = gross_cost + commission

        return BuyFillResult(
            fill_price=fill_price,
            quantity=max_quantity,
            commission=commission,
            total_cost=total_cost,
        )

    def calculate_sell_fill(
        self,
        price: float,
        quantity: float,
        commission_rate: float | None = None,
        slippage_rate: float | None = None,
    ) -> SellFillResult:
        """
        Calculate fill for a sell order.

        Slippage decreases the price for sells (unfavorable).

        Args:
            price: Base execution price
            quantity: Quantity to sell
            commission_rate: Commission rate (uses default if None)
            slippage_rate: Slippage rate (uses default if None)

        Returns:
            SellFillResult with fill details
        """
        commission_rate = self.default_commission if commission_rate is None else commission_rate
        slippage_rate = self.default_slippage if slippage_rate is None else slippage_rate

        # Apply slippage (sell at lower price)
        fill_price = price * (1 - slippage_rate)

        # Calculate proceeds
        gross_proceeds = quantity * fill_price
        commission = gross_proceeds * commission_rate
        net_proceeds = gross_proceeds - commission

        return SellFillResult(
            fill_price=fill_price,
            quantity=quantity,
            commission=commission,
            gross_proceeds=gross_proceeds,
            net_proceeds=net_proceeds,
        )

    def calculate_round_trip_cost(
        self,
        entry_price: float,
        exit_price: float,
        quantity: float,
        commission_rate: float | None = None,
        slippage_rate: float | None = None,
    ) -> float:
        """
        Calculate total cost for a round-trip trade.

        Useful for estimating break-even price targets.

        Args:
            entry_price: Entry price
            exit_price: Exit price
            quantity: Position size
            commission_rate: Commission rate
            slippage_rate: Slippage rate

        Returns:
            Total cost in quote currency (USDT)
        """
        commission_rate = self.default_commission if commission_rate is None else commission_rate
        slippage_rate = self.default_slippage if slippage_rate is None else slippage_rate

        # Entry slippage + commission
        entry_fill = entry_price * (1 + slippage_rate)
        entry_cost = entry_fill * quantity * commission_rate + entry_fill * quantity * slippage_rate

        # Exit slippage + commission
        exit_fill = exit_price * (1 - slippage_rate)
        exit_cost = exit_fill * quantity * commission_rate + exit_price * quantity * slippage_rate

        return entry_cost + exit_cost

    def break_even_return(
        self,
        commission_rate: float | None = None,
        slippage_rate: float | None = None,
    ) -> float:
        """
        Calculate minimum return needed to break even.

        Args:
            commission_rate: Commission rate
            slippage_rate: Slippage rate

        Returns:
            Break-even return as decimal (e.g., 0.003 = 0.3%)
        """
        commission_rate = self.default_commission if commission_rate is None else commission_rate
        slippage_rate = self.default_slippage if slippage_rate is None else slippage_rate

        # Buy at higher price, sell at lower price, pay commission both ways
        total_drag = 2 * commission_rate + 2 * slippage_rate

        return total_drag
