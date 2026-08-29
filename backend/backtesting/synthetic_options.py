"""
Synthetic options pricing using Black-Scholes model.

When historical options data is not available or insufficient,
we can generate synthetic option prices and Greeks using the
Black-Scholes model for backtesting purposes.
"""

from __future__ import annotations

import math
import numpy as np
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from scipy import stats

from backend.app.data.models import (
    OptionContract,
    OptionRight,
    OptionSnapshot,
    Quote,
    Greeks,
)


@dataclass
class BlackScholesModel:
    """
    Black-Scholes options pricing model.

    Calculates theoretical option prices and Greeks assuming:
    - European options
    - No dividends
    - Constant volatility and interest rates
    - Lognormal distribution of stock returns
    """

    def __init__(
        self,
        risk_free_rate: float = 0.05,  # 5% annual risk-free rate
        dividend_yield: float = 0.0
    ):
        self.risk_free_rate = risk_free_rate
        self.dividend_yield = dividend_yield

    def _d1(
        self,
        S: float,  # Current stock price
        K: float,  # Strike price
        T: float,  # Time to expiration (in years)
        sigma: float  # Volatility
    ) -> float:
        """Calculate d1 parameter."""
        return (math.log(S / K) + (self.risk_free_rate - self.dividend_yield + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))

    def _d2(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float
    ) -> float:
        """Calculate d2 parameter."""
        return self._d1(S, K, T, sigma) - sigma * math.sqrt(T)

    def call_price(
        self,
        S: float,  # Current stock price
        K: float,  # Strike price
        T: float,  # Time to expiration (in years)
        sigma: float  # Volatility
    ) -> float:
        """Calculate European call option price."""
        if T <= 0:
            return max(0, S - K)

        d1 = self._d1(S, K, T, sigma)
        d2 = self._d2(S, K, T, sigma)

        call_price = (
            S * math.exp(-self.dividend_yield * T) * stats.norm.cdf(d1) -
            K * math.exp(-self.risk_free_rate * T) * stats.norm.cdf(d2)
        )
        return max(0, call_price)

    def put_price(
        self,
        S: float,  # Current stock price
        K: float,  # Strike price
        T: float,  # Time to expiration (in years)
        sigma: float  # Volatility
    ) -> float:
        """Calculate European put option price."""
        if T <= 0:
            return max(0, K - S)

        d1 = self._d1(S, K, T, sigma)
        d2 = self._d2(S, K, T, sigma)

        put_price = (
            K * math.exp(-self.risk_free_rate * T) * stats.norm.cdf(-d2) -
            S * math.exp(-self.dividend_yield * T) * stats.norm.cdf(-d1)
        )
        return max(0, put_price)

    def delta(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float,
        option_type: OptionRight
    ) -> float:
        """Calculate option delta."""
        if T <= 0:
            if option_type == OptionRight.CALL:
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0

        d1 = self._d1(S, K, T, sigma)

        if option_type == OptionRight.CALL:
            return math.exp(-self.dividend_yield * T) * stats.norm.cdf(d1)
        else:
            return -math.exp(-self.dividend_yield * T) * stats.norm.cdf(-d1)

    def gamma(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float
    ) -> float:
        """Calculate option gamma."""
        if T <= 0:
            return 0.0

        d1 = self._d1(S, K, T, sigma)
        return (math.exp(-self.dividend_yield * T) * stats.norm.pdf(d1)) / (S * sigma * math.sqrt(T))

    def theta(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float,
        option_type: OptionRight
    ) -> float:
        """Calculate option theta (per day)."""
        if T <= 0:
            return 0.0

        d1 = self._d1(S, K, T, sigma)
        d2 = self._d2(S, K, T, sigma)

        if option_type == OptionRight.CALL:
            theta = (
                -(S * sigma * math.exp(-self.dividend_yield * T) * stats.norm.pdf(d1)) / (2 * math.sqrt(T))
                - self.risk_free_rate * K * math.exp(-self.risk_free_rate * T) * stats.norm.cdf(d2)
                + self.dividend_yield * S * math.exp(-self.dividend_yield * T) * stats.norm.cdf(d1)
            )
        else:
            theta = (
                -(S * sigma * math.exp(-self.dividend_yield * T) * stats.norm.pdf(d1)) / (2 * math.sqrt(T))
                + self.risk_free_rate * K * math.exp(-self.risk_free_rate * T) * stats.norm.cdf(-d2)
                - self.dividend_yield * S * math.exp(-self.dividend_yield * T) * stats.norm.cdf(-d1)
            )

        # Convert to per-day theta
        return theta / 365.0

    def vega(
        self,
        S: float,
        K: float,
        T: float,
        sigma: float
    ) -> float:
        """Calculate option vega (per 1% change in volatility)."""
        if T <= 0:
            return 0.0

        d1 = self._d1(S, K, T, sigma)
        return S * math.exp(-self.dividend_yield * T) * stats.norm.pdf(d1) * math.sqrt(T) / 100.0


class SyntheticOptionChain:
    """
    Generates synthetic option chains for a given underlying price and volatility.

    Creates a range of strikes and expirations with theoretical prices
    using the Black-Scholes model.
    """

    def __init__(self, model: Optional[BlackScholesModel] = None):
        self.model = model or BlackScholesModel()

    def generate_option_chain(
        self,
        underlying: str,
        underlying_price: float,
        volatility: float,
        current_date: date,
        min_dte: int = 0,
        max_dte: int = 365,
        strike_count: int = 20,
        price_range: float = 0.3  # ±30% of underlying price for strike range
    ) -> List[OptionContract]:
        """
        Generate a synthetic option chain.

        Args:
            underlying: The underlying symbol (e.g., "SPY")
            underlying_price: Current price of the underlying
            volatility: Implied volatility to use for pricing
            current_date: Current date for DTE calculation
            min_dte: Minimum days to expiration
            max_dte: Maximum days to expiration
            strike_count: Number of different strikes to generate
            price_range: Range around underlying price for strikes (as fraction)

        Returns:
            List of OptionContract objects for both calls and puts
        """
        contracts = []

        # Generate expiration dates
        exp_dates = []
        for dte in range(min_dte, max_dte + 1, max(1, (max_dte - min_dte) // 10)):  # ~10 expiration dates
            exp_date = current_date + timedelta(days=dte)
            exp_dates.append(exp_date)

        # Ensure we have at least the min and max DTE
        if min_dte not in [ (d - current_date).days for d in exp_dates ]:
            exp_dates.append(current_date + timedelta(days=min_dte))
        if max_dte not in [ (d - current_date).days for d in exp_dates ]:
            exp_dates.append(current_date + timedelta(days=max_dte))

        # Generate strike prices
        min_strike = underlying_price * (1 - price_range)
        max_strike = underlying_price * (1 + price_range)
        strikes = np.linspace(min_strike, max_strike, strike_count)

        # Generate contracts for each expiration and strike
        for exp_date in exp_dates:
            days_to_exp = (exp_date - current_date).days
            T = days_to_exp / 365.0  # Convert to years

            for strike in strikes:
                # Call option
                call_contract = OptionContract(
                    symbol=self._generate_option_symbol(underlying, exp_date, strike, OptionRight.CALL),
                    underlying=underlying,
                    expiration=exp_date,
                    strike=strike,
                    right=OptionRight.CALL,
                )
                contracts.append(call_contract)

                # Put option
                put_contract = OptionContract(
                    symbol=self._generate_option_symbol(underlying, exp_date, strike, OptionRight.PUT),
                    underlying=underlying,
                    expiration=exp_date,
                    strike=strike,
                    right=OptionRight.PUT,
                )
                contracts.append(put_contract)

        return contracts

    def _generate_option_symbol(
        self,
        underlying: str,
        expiration: date,
        strike: float,
        right: OptionRight
    ) -> str:
        """Generate an option symbol in the format O:UNDERLYINGYYMMDD[C/P]STRIKE"""
        # Format: O:SPY 240920C00500000 (for SPY call expiring 2024-09-20 at $500 strike)
        # Note: Actual OCC format is more complex, this is simplified for backtesting
        yy_mm_dd = expiration.strftime("%y%m%d")
        call_put = "C" if right == OptionRight.CALL else "P"
        # Strike price formatted as 8 digits with 3 decimal places (e.g., 500.000 -> 00500000)
        strike_str = f"{int(strike * 1000):08d}"
        return f"O:{underlying}{yy_mm_dd}{call_put}{strike_str}"

    def price_option_chain(
        self,
        option_contracts: List[OptionContract],
        underlying_price: float,
        volatility: float,
        current_date: date
    ) -> List[OptionSnapshot]:
        """
        Generate option snapshots with theoretical prices for a list of contracts.

        Args:
            option_contracts: List of OptionContract objects to price
            underlying_price: Current price of the underlying
            volatility: Volatility to use for pricing
            current_date: Current date for DTE calculation

        Returns:
            List of OptionSnapshot objects with theoretical prices and Greeks
        """
        snapshots = []

        for contract in option_contracts:
            # Calculate time to expiration
            days_to_exp = (contract.expiration - current_date).days
            if days_to_exp < 0:
                # Expired option
                continue

            T = days_to_exp / 365.0  # Years

            # Calculate theoretical price
            if contract.right == OptionRight.CALL:
                theoretical_price = self.model.call_price(
                    underlying_price, contract.strike, T, volatility
                )
            else:
                theoretical_price = self.model.put_price(
                    underlying_price, contract.strike, T, volatility
                )

            # Calculate Greeks
            delta = self.model.delta(
                underlying_price, contract.strike, T, volatility, contract.right
            )
            gamma = self.model.gamma(
                underlying_price, contract.strike, T, volatility
            )
            theta = self.model.theta(
                underlying_price, contract.strike, T, volatility, contract.right
            )
            vega = self.model.vega(
                underlying_price, contract.strike, T, volatility
            )

            # For synthetic data, we'll set bid/ask around the theoretical price
            # with a small spread
            spread_pct = 0.02  # 2% bid/ask spread
            half_spread = theoretical_price * spread_pct / 2
            bid = max(0.01, theoretical_price - half_spread)
            ask = theoretical_price + half_spread

            # Create quote
            quote = Quote(
                symbol=contract.symbol,
                bid=bid,
                ask=ask,
                last=theoretical_price,
                timestamp=datetime.now()
            )

            # Create Greeks
            greeks = Greeks(
                delta=delta,
                gamma=gamma,
                theta=theta,
                vega=vega
            )

            # Create snapshot
            snapshot = OptionSnapshot(
                contract=contract,
                quote=quote,
                implied_volatility=volatility,
                greeks=greeks,
                underlying_price=underlying_price
            )

            snapshots.append(snapshot)

        return snapshots


def create_synthetic_option_data(
    underlying: str,
    underlying_price: float,
    historical_volatility: float,
    current_date: date,
    min_dte: int = 0,
    max_dte: int = 365
) -> Tuple[List[OptionContract], List[OptionSnapshot]]:
    """
    Convenience function to generate synthetic option data.

    Args:
        underlying: The underlying symbol (e.g., "SPY")
        underlying_price: Current price of the underlying
        historical_volatility: Historical volatility of the underlying
        current_date: Current date
        min_dte: Minimum days to expiration
        max_dte: Maximum days to expiration

    Returns:
        Tuple of (option_contracts, option_snapshots)
    """
    chain_generator = SyntheticOptionChain()

    # Generate option contracts
    contracts = chain_generator.generate_option_chain(
        underlying=underlying,
        underlying_price=underlying_price,
        volatility=historical_volatility,
        current_date=current_date,
        min_dte=min_dte,
        max_dte=max_dte
    )

    # Price the options
    snapshots = chain_generator.price_option_chain(
        option_contracts=contracts,
        underlying_price=underlying_price,
        volatility=historical_volatility,
        current_date=current_date
    )

    return contracts, snapshots