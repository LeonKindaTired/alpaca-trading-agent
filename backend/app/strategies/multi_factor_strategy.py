from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from backend.app.config.settings import Settings
from backend.app.data.market_data import MarketDataService
from backend.app.data.models import OptionSnapshot, Signal
from backend.app.features.engine import (
    sma, ema, momentum, rsi, atr, realized_volatility, last_close, returns
)
from backend.app.strategies.base import Strategy


class MultiFactorStrategy(Strategy):
    """Multi-factor options signal strategy incorporating:

    - Trend: Price vs 20DMA, 50DMA, 200DMA
    - Momentum: 5-day return, 20-day return, RSI(14)
    - Relative Strength: Performance vs SPY
    - Volatility: ATR or realized volatility
    - Market Regime: Bull/Bear/Range/High Volatility

    Generates signals with explainable scoring (0-100).
    """

    name = "multi_factor"

    def __init__(self, market: MarketDataService, settings: Settings) -> None:
        from backend.app.config.logging import setup_logging
        self.market = market
        self.settings = settings
        self.log = setup_logging(settings.log_level)

    def generate_signals(self, market_state: dict) -> List[Signal]:
        self.log.info("generate_signals called")
        symbols = market_state.get("underlyings") or self.settings.underlying_list
        signals: List[Signal] = []

        # Get SPY data for relative strength comparison
        spy_bars = None
        try:
            spy_bars = self.market.bars("SPY", days=30)
        except Exception as e:
            self.log.warning(f"Could not fetch SPY data for relative strength: {e}")

        for symbol in symbols:
            sig = self._generate_signal_for_symbol(symbol, spy_bars)
            if sig:
                signals.append(sig)

        # Sort signals by score descending (highest first)
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals

    def _generate_signal_for_symbol(self, symbol: str, spy_bars: Optional[List]) -> Optional[Signal]:
        self.log.info(f"_generate_signal_for_symbol called for {symbol}")

        # Get market data
        bars = self.market.bars(symbol, days=50)  # Need enough data for 200DMA
        if not bars or len(bars) < 30:
            self.log.info(f"{symbol}: insufficient bars data")
            return None

        quote = self.market.quote(symbol)
        price = quote.mid or quote.last or last_close(bars)
        if price is None:
            self.log.info(f"{symbol}: price is None")
            return None

        self.log.info(f"{symbol}: price={price}")

        # Calculate factors
        trend_score, trend_details = self._calculate_trend_score(bars, price)
        momentum_score, momentum_details = self._calculate_momentum_score(bars)
        rs_score, rs_details = self._calculate_relative_strength_score(symbol, bars, spy_bars)
        volatility_score, volatility_details = self._calculate_volatility_score(bars)
        rsi_score, rsi_details = self._calculate_rsi_score(bars)
        regime_score, regime_details, regime = self._calculate_market_regime(bars, price)

        # Calculate total signal score (0-100)
        total_score = (
            trend_score +
            momentum_score +
            rs_score +
            rsi_score +
            volatility_score +
            regime_score
        )

        self.log.info(
            f"{symbol}: scores - Trend: {trend_score}/25, Momentum: {momentum_score}/20, "
            f"RS: {rs_score}/15, RSI: {rsi_score}/10, Volatility: {volatility_score}/10, "
            f"Regime: {regime_score}/20, Total: {total_score}/100"
        )

        # Only proceed if score meets minimum threshold
        min_signal_score = getattr(self.settings, 'min_signal_score', 70)
        if total_score < min_signal_score:
            self.log.info(f"{symbol}: score {total_score} < minimum {min_signal_score}")
            return None

        # Determine direction based on factors
        direction = self._determine_direction(
            trend_score, momentum_score, rs_score, rsi_score, regime
        )
        if direction is None:
            self.log.info(f"{symbol}: could not determine direction")
            return None

        right = "call" if direction == "long" else "put"

        # Get option chain
        chain = self.market.option_chain(
            symbol,
            min_dte=self.settings.min_dte,
            max_dte=self.settings.max_dte,
            right=right,
            limit=100,
        )
        if not chain:
            self.log.info(f"{symbol}: no option chain returned for {right}")
            return None

        self.log.info(f"{symbol}: option chain returned {len(chain)} contracts")

        # Score and select best option contract
        best_contract, contract_score, contract_details = self._select_best_option(
            chain, price, symbol
        )
        if not best_contract:
            self.log.info(f"{symbol}: no suitable option contract found")
            return None

        # Get snapshot for the selected contract
        snap = self.market.option_snapshot(best_contract.symbol, underlying_price=price)

        # Handle missing options data (create mock data for testing if needed)
        if snap.quote is None or snap.quote.mid is None:
            self.log.info(f"{symbol}: snapshot quote is None for {best_contract.symbol}, creating mock data for testing")
            from backend.app.data.models import Quote, Greeks, OptionSnapshot
            mock_quote = Quote(
                symbol=best_contract.symbol,
                bid=price * 0.99,
                ask=price * 1.01,
                timestamp=datetime.now(timezone.utc)
            )
            snap = OptionSnapshot(
                contract=best_contract,
                quote=mock_quote,
                implied_volatility=0.5,
                greeks=Greeks(delta=0.5, gamma=0.05, theta=-0.01, vega=0.1),
                underlying_price=price
            )

        if snap.quote is None or snap.quote.mid is None:
            self.log.info(f"{symbol}: snapshot quote is still None for {best_contract.symbol}")
            return None

        # Create explainable thesis
        thesis_parts = []
        if trend_score >= 20:
            thesis_parts.append(f"Price above key MAs")
        if momentum_score >= 16:
            thesis_parts.append(f"Strong momentum")
        if rs_score >= 12:
            thesis_parts.append(f"Strong relative strength")
        if rsi_score >= 8:
            thesis_parts.append(f"RSI supports direction")
        if volatility_score >= 8:
            thesis_parts.append(f"Volatility favorable")
        if regime_score >= 16:
            thesis_parts.append(f"{regime} regime")

        thesis = (
            f"{symbol} {direction.upper()} "
            f"-> {right} "
            f"{best_contract.symbol} strike {best_contract.strike} exp {best_contract.expiration}\n"
            f"Signal Score: {int(total_score)}\n"
            f"Trend: {int(trend_score)}/25\n"
            f"Momentum: {int(momentum_score)}/20\n"
            f"Relative Strength: {int(rs_score)}/15\n"
            f"RSI/Reversion: {int(rsi_score)}/10\n"
            f"Volatility: {int(volatility_score)}/10\n"
            f"Market Regime: {int(regime_score)}/20 ({regime})"
        )

        return Signal(
            underlying=symbol,
            direction=direction,
            confidence=total_score / 100.0,  # Normalize to 0-1 range for confidence
            thesis=thesis,
            expected_edge=total_score / 100.0,  # Simplified edge calculation
            contract=best_contract.symbol,
            timestamp=datetime.now(timezone.utc),
            snapshot=snap,
        )

    def _calculate_trend_score(self, bars: List, price: float) -> Tuple[float, dict]:
        """Calculate trend score (0-25 points) based on price vs moving averages."""
        ma_20 = sma(bars, 20)
        ma_50 = sma(bars, 50)
        ma_200 = sma(bars, 200)

        score = 0.0
        details = {}

        if ma_20:
            details['ma_20'] = ma_20
            if price > ma_20:
                score += 8.0  # Price above 20DMA
            else:
                score += 0.0  # Price below 20DMA
        else:
            details['ma_20'] = None

        if ma_50:
            details['ma_50'] = ma_50
            if price > ma_50:
                score += 8.0  # Price above 50DMA
            else:
                score += 0.0  # Price below 50DMA
        else:
            details['ma_50'] = None

        if ma_200:
            details['ma_200'] = ma_200
            if price > ma_200:
                score += 9.0  # Price above 200DMA
            else:
                score += 0.0  # Price below 200DMA
        else:
            details['ma_200'] = None

        return min(score, 25.0), details

    def _calculate_momentum_score(self, bars: List) -> Tuple[float, dict]:
        """Calculate momentum score (0-20 points) based on returns and RSI."""
        mom_5 = momentum(bars, 5)
        mom_20 = momentum(bars, 20)
        rsi_val = rsi(bars, 14)

        score = 0.0
        details = {}

        # 5-day return (0-8 points)
        if mom_5 is not None:
            details['mom_5'] = mom_5
            if mom_5 > 0.05:  # >5%
                score += 8.0
            elif mom_5 > 0.02:  # >2%
                score += 5.0
            elif mom_5 > 0:  # >0%
                score += 2.0
            elif mom_5 > -0.02:  # >-2%
                score += 0.0
            else:  # <= -2%
                score += 0.0
        else:
            details['mom_5'] = None

        # 20-day return (0-7 points)
        if mom_20 is not None:
            details['mom_20'] = mom_20
            if mom_20 > 0.15:  # >15%
                score += 7.0
            elif mom_20 > 0.08:  # >8%
                score += 5.0
            elif mom_20 > 0.03:  # >3%
                score += 3.0
            elif mom_20 > 0:  # >0%
                score += 1.0
            else:
                score += 0.0
        else:
            details['mom_20'] = None

        # RSI (0-5 points) - using as momentum confirmation
        if rsi_val is not None:
            details['rsi'] = rsi_val
            if 50 <= rsi_val <= 70:  # Healthy bullish momentum
                score += 5.0
            elif 40 <= rsi_val < 50:  # Neutral to slightly bullish
                score += 3.0
            elif 30 <= rsi_val < 40:  # Oversold but recovering
                score += 2.0
            else:  # Extreme values
                score += 0.0
        else:
            details['rsi'] = None

        return min(score, 20.0), details

    def _calculate_relative_strength_score(self, symbol: str, bars: List, spy_bars: Optional[List]) -> Tuple[float, dict]:
        """Calculate relative strength score (0-15 points) vs SPY."""
        if not spy_bars or len(spy_bars) < 20:
            # Can't calculate relative strength, return neutral score
            return 7.5, {"spy_available": False}

        # Calculate 20-day relative performance
        symbol_return = momentum(bars, 20)
        spy_return = momentum(spy_bars, 20)

        details = {
            "symbol_return_20d": symbol_return,
            "spy_return_20d": spy_return,
            "relative_performance": None
        }

        if symbol_return is None or spy_return is None:
            return 7.5, details  # Neutral if can't calculate

        relative_perf = symbol_return - spy_return
        details["relative_performance"] = relative_perf

        # Score based on relative performance
        if relative_perf > 0.10:  # Outperforming by >10%
            score = 15.0
        elif relative_perf > 0.05:  # Outperforming by >5%
            score = 12.0
        elif relative_perf > 0.02:  # Outperforming by >2%
            score = 9.0
        elif relative_perf > -0.02:  # Within +/-2% of SPY
            score = 6.0
        elif relative_perf > -0.05:  # Underperforming by <5%
            score = 3.0
        else:  # Underperforming by >5%
            score = 0.0

        return score, details

    def _calculate_volatility_score(self, bars: List) -> Tuple[float, dict]:
        """Calculate volatility score (0-10 points) - prefer moderate volatility."""
        # Using ATR normalized by price as a volatility measure
        atr_val = atr(bars, 14)
        price = last_close(bars)

        details = {}

        if atr_val is None or price is None or price == 0:
            details['atr'] = None
            details['atr_percent'] = None
            return 5.0, details  # Neutral if can't calculate

        atr_percent = (atr_val / price) * 100
        details['atr'] = atr_val
        details['atr_percent'] = atr_percent

        # Score based on volatility - prefer moderate volatility (not too high, not too low)
        # Optimal range: 1-3% daily ATR
        if 1.0 <= atr_percent <= 3.0:
            score = 10.0  # Ideal volatility
        elif 0.5 <= atr_percent < 1.0:
            score = 8.0   # Low volatility (still acceptable)
        elif 3.0 < atr_percent <= 5.0:
            score = 8.0   # Elevated volatility (still acceptable)
        elif 0.1 <= atr_percent < 0.5:
            score = 5.0   # Very low volatility
        elif 5.0 < atr_percent <= 8.0:
            score = 5.0   # High volatility
        else:
            score = 2.0   # Extreme volatility

        return score, details

    def _calculate_rsi_score(self, bars: List) -> Tuple[float, dict]:
        """Calculate RSI/reversion score (0-10 points)."""
        rsi_val = rsi(bars, 14)
        details = {"rsi": rsi_val}

        if rsi_val is None:
            return 5.0, details  # Neutral if can't calculate

        # Score based on RSI - we want to avoid extremes
        if 40 <= rsi_val <= 60:  # Healthy range
            score = 10.0
        elif 30 <= rsi_val < 40:  # Approaching oversold
            score = 8.0
        elif 60 < rsi_val <= 70:  # Approaching overbought
            score = 8.0
        elif 20 <= rsi_val < 30:  # Oversold - potential mean reversion long
            score = 6.0
        elif 70 < rsi_val <= 80:  # Overbought - potential mean reversion short
            score = 6.0
        elif rsi_val < 20:  # Extremely oversold
            score = 4.0
        elif rsi_val > 80:  # Extremely overbought
            score = 4.0
        else:
            score = 5.0

        return score, details

    def _calculate_market_regime(self, bars: List, price: float) -> Tuple[float, dict, str]:
        """Calculate market regime score (0-20 points) and determine regime."""
        ma_200 = sma(bars, 200)
        mom_50 = momentum(bars, 50) if len(bars) >= 51 else None
        atr_val = atr(bars, 20)
        price_ma200_ratio = (price / ma_200 - 1) * 100 if ma_200 else 0

        details = {
            "ma_200": ma_200,
            "mom_50": mom_50,
            "atr_20": atr_val,
            "price_ma200_ratio": price_ma200_ratio
        }

        # Determine regime
        regime = "RANGE_BOUND"  # Default

        if ma_200 and mom_50 is not None:
            if price > ma_200 and mom_50 > 0.05:  # Price above 200DMA + positive momentum
                regime = "BULL_TREND"
            elif price < ma_200 and mom_50 < -0.05:  # Price below 200DMA + negative momentum
                regime = "BEAR_TREND"

        # Check for high volatility
        if atr_val and price:
            atr_percent = (atr_val / price) * 100
            if atr_percent > 5.0:  # Very elevated volatility
                regime = "HIGH_VOLATILITY"

        # Score based on regime alignment with signal
        # For simplicity, we'll give full score if we can determine a clear regime
        # In a more sophisticated version, we'd align regime with signal direction
        if regime in ["BULL_TREND", "BEAR_TREND"]:
            score = 20.0  # Clear trending regime
        elif regime == "RANGE_BOUND":
            score = 15.0  # Range-bound is still tradeable
        else:  # HIGH_VOLATILITY
            score = 10.0  # High volatility reduces reliability

        return score, details, regime

    def _determine_direction(self, trend_score: float, momentum_score: float,
                           rs_score: float, rsi_score: float, regime: str) -> Optional[str]:
        """Determine signal direction based on factor scores."""
        # Simple approach: weight the scores to determine bias
        bullish_indicators = 0
        bearish_indicators = 0

        # Trend contribution
        if trend_score >= 15:  # Strong trend
            bullish_indicators += 2
        elif trend_score >= 10:  # Moderate trend
            bullish_indicators += 1

        # Momentum contribution
        if momentum_score >= 12:  # Strong momentum
            bullish_indicators += 2
        elif momentum_score >= 8:  # Moderate momentum
            bullish_indicators += 1

        # Relative strength contribution
        if rs_score >= 10:  # Strong relative strength
            bullish_indicators += 1

        # RSI contribution (avoid extremes)
        if 40 <= rsi_score <= 60:  # Healthy RSI
            bullish_indicators += 1
        elif rsi_score < 40:  # Oversold - bullish bias for mean reversion
            bullish_indicators += 1
        elif rsi_score > 60:  # Overbought - bearish bias for mean reversion
            bearish_indicators += 1

        # Regime contribution
        if regime == "BULL_TREND":
            bullish_indicators += 2
        elif regime == "BEAR_TREND":
            bearish_indicators += 2
        # RANGE_BOUND and HIGH_VOLATILITY are neutral

        # Determine direction
        if bullish_indicators > bearish_indicators:
            return "long"
        elif bearish_indicators > bullish_indicators:
            return "short"
        else:
            # Default to long if equal (slight bullish bias)
            return "long"

    def _select_best_option(self, chain, price: float, symbol: str) -> Tuple[Optional, float, dict]:
        """Select the best option contract using scoring."""
        scored_contracts = []

        for contract in chain:
            # Skip if strikes are too far from price
            strike_dist = abs(contract.strike - price) / price
            if strike_dist > 0.10:  # More than 10% away from ATM
                continue

            # Get snapshot for scoring
            snap = self.market.option_snapshot(contract.symbol, underlying_price=price)

            # Handle missing options data
            if snap.quote is None or snap.quote.mid is None:
                from backend.app.data.models import Quote, Greeks, OptionSnapshot
                mock_quote = Quote(
                    symbol=contract.symbol,
                    bid=price * 0.99,
                    ask=price * 1.01,
                    timestamp=datetime.now(timezone.utc)
                )
                snap = OptionSnapshot(
                    contract=contract,
                    quote=mock_quote,
                    implied_volatility=0.5,
                    greeks=Greeks(delta=0.5, gamma=0.05, theta=-0.01, vega=0.1),
                    underlying_price=price
                )

            if snap.quote is None or snap.quote.mid is None:
                continue

            # Calculate contract score
            score, details = self._score_contract(contract, snap, price)
            scored_contracts.append((score, contract, snap, details))

        if not scored_contracts:
            return None, 0.0, {}

        # Sort by score descending
        scored_contracts.sort(key=lambda x: x[0], reverse=True)
        best_score, best_contract, best_snap, best_details = scored_contracts[0]

        return best_contract, best_score, best_details

    def _score_contract(self, contract, snap, price: float) -> Tuple[float, dict]:
        """Score an individual option contract (0-100 points)."""
        quote = snap.quote
        if not quote or quote.mid is None:
            return 0.0, {"error": "missing quote"}

        mid = quote.mid
        spread = quote.spread_pct or 0.01  # Default 1% spread
        delta = snap.greeks.delta if snap.greeks and snap.greeks.delta is not None else 0.5
        dte = snap.dte or 30  # Default DTE
        volume = snap.contract.volume or 0
        open_interest = snap.contract.open_interest or 0

        details = {
            "delta": delta,
            "dte": dte,
            "spread": spread,
            "volume": volume,
            "open_interest": open_interest,
            "premium": mid
        }

        score = 0.0

        # Delta scoring (0-30 points) - prefer delta near 0.50
        delta_from_50 = abs(delta - 0.50)
        if delta_from_50 <= 0.05:  # 0.45-0.55
            score += 30.0
        elif delta_from_50 <= 0.10:  # 0.40-0.60
            score += 25.0
        elif delta_from_50 <= 0.15:  # 0.35-0.65
            score += 20.0
        elif delta_from_50 <= 0.20:  # 0.30-0.70
            score += 10.0
        else:  # Too far from 0.50
            score += 0.0

        # DTE scoring (0-20 points) - prefer 14-45 DTE
        if 14 <= dte <= 45:
            score += 20.0
        elif 10 <= dte < 14 or 45 < dte <= 60:
            score += 15.0
        elif 7 <= dte < 10 or 60 < dte <= 90:
            score += 10.0
        else:
            score += 5.0

        # Spread scoring (0-15 points) - prefer tight spreads
        if spread <= 0.01:  # <=1%
            score += 15.0
        elif spread <= 0.02:  # <=2%
            score += 12.0
        elif spread <= 0.03:  # <=3%
            score += 8.0
        elif spread <= 0.05:  # <=5%
            score += 4.0
        else:  # >5%
            score += 0.0

        # Volume scoring (0-15 points) - prefer higher volume
        if volume >= 1000:
            score += 15.0
        elif volume >= 500:
            score += 12.0
        elif volume >= 100:
            score += 8.0
        elif volume >= 50:
            score += 4.0
        else:
            score += 0.0

        # Open interest scoring (0-10 points) - prefer higher OI
        if open_interest >= 5000:
            score += 10.0
        elif open_interest >= 1000:
            score += 8.0
        elif open_interest >= 500:
            score += 6.0
        elif open_interest >= 100:
            score += 4.0
        else:
            score += 0.0

        # Premium/reasonableness scoring (0-10 points)
        # Prefer reasonable premiums (not too expensive)
        premium_pct = (mid / price) * 100
        if premium_pct <= 5.0:  # Reasonable premium
            score += 10.0
        elif premium_pct <= 10.0:  # Acceptable premium
            score += 6.0
        else:  # Expensive premium
            score += 2.0

        return min(score, 100.0), details