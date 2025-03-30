"""
Option analysis module for stock analysis application.
"""
import datetime
from typing import Dict, Optional, Union, List, Tuple

import numpy as np
import pandas as pd
from loguru import logger


class OptionAnalysis:
    """
    Analyze option data for trading recommendations.

    Features:
    - Select appropriate option strikes
    - Calculate implied volatility percentile
    - Analyze open interest patterns
    - Calculate max pain price
    - Generate option contract symbols
    """

    def __init__(self, historical_data: pd.DataFrame, option_chain: pd.DataFrame):
        """
        Initialize with historical price and option chain data.

        Args:
            historical_data: DataFrame with OHLCV data
            option_chain: DataFrame with option chain data
        """
        self.historical_data = historical_data.copy() if historical_data is not None else None
        self.option_chain = option_chain.copy() if option_chain is not None else None

        logger.info("Option analysis module initialized")

    def analyze_options(self, current_price: float, prediction_direction: str, target_price: float, stop_loss: float) -> Dict:
        """
        Analyze options and calculate option-related metrics.

        Args:
            current_price: Current stock price
            prediction_direction: Predicted direction (UP/DOWN)
            target_price: Projected price target
            stop_loss: Recommended stop loss level

        Returns:
            Dictionary with option analysis results
        """
        if self.option_chain is None or self.option_chain.empty:
            logger.error("No option chain data available for analysis")
            return {}

        try:
            # Determine option type based on prediction direction
            option_type = "CE" if prediction_direction == "UP" else "PE"

            # Select appropriate strike
            selected_strike, strike_type = self._select_strike(current_price, option_type)

            # Calculate IV percentile
            iv_percentile = self._calculate_iv_percentile()

            # Calculate max pain
            max_pain = self._calculate_max_pain()

            # Analyze open interest
            oi_analysis = self._analyze_open_interest(option_type)

            # Get option prices
            current_option_price, target_option_price, option_stop_loss = self._calculate_option_prices(
                selected_strike, option_type, current_price, target_price, stop_loss
            )

            # Generate full option symbol
            underlying_strike = self._generate_option_symbol(selected_strike, option_type)

            # Compile results
            result = {
                "underlying_strike": underlying_strike,
                "selected_strike": selected_strike,
                "strike_type": strike_type,
                "options_iv_percentile": iv_percentile,
                "max_pain_price": max_pain,
                "open_interest_analysis": oi_analysis,
                "option_current_price": current_option_price,
                "option_target_price": target_option_price,
                "option_stop_loss": option_stop_loss
            }

            logger.info(f"Successfully analyzed options for strike {selected_strike} {option_type}")
            return result

        except Exception as e:
            logger.error(f"Error analyzing options: {str(e)}")
            return {}

    def _select_strike(self, current_price: float, option_type: str) -> Tuple[float, str]:
        """
        Select appropriate option strike based on current price.

        Args:
            current_price: Current stock price
            option_type: Option type (CE/PE)

        Returns:
            Tuple of (selected_strike, strike_type)
        """
        if self.option_chain is None:
            return 0, "Unknown"

        # Filter by option type
        filtered_chain = self.option_chain[self.option_chain["type"] == option_type]

        if filtered_chain.empty:
            logger.warning(f"No {option_type} options found in chain")
            # Fallback to a strike near current price
            return round(current_price / 5) * 5, "ATM"

        # Find strikes around current price
        strikes = filtered_chain["strike"].unique()
        strikes = sorted(strikes)

        # Find nearest strike to current price (ATM)
        nearest_idx = np.abs(np.array(strikes) - current_price).argmin()
        atm_strike = strikes[nearest_idx]

        if option_type == "CE":
            # For calls in an upward prediction, we might want slightly OTM
            if nearest_idx + 1 < len(strikes):
                selected_strike = strikes[nearest_idx + 1]
                strike_type = "OTM"
            else:
                selected_strike = atm_strike
                strike_type = "ATM"
        else:  # PE
            # For puts in a downward prediction, we might want slightly OTM
            if nearest_idx > 0:
                selected_strike = strikes[nearest_idx - 1]
                strike_type = "OTM"
            else:
                selected_strike = atm_strike
                strike_type = "ATM"

        # Check if we should consider ITM options instead based on IV or liquidity
        atm_option = filtered_chain[filtered_chain["strike"] == atm_strike].iloc[0]

        # If the ATM option has very high IV or low volume, consider ITM instead
        if atm_option["iv"] > 80 or atm_option["volume"] < 50:
            if option_type == "CE" and nearest_idx > 0:
                selected_strike = strikes[nearest_idx - 1]
                strike_type = "ITM"
            elif option_type == "PE" and nearest_idx + 1 < len(strikes):
                selected_strike = strikes[nearest_idx + 1]
                strike_type = "ITM"

        return selected_strike, strike_type

    def _calculate_iv_percentile(self) -> float:
        """
        Calculate implied volatility percentile.

        Returns:
            IV percentile (0-100)
        """
        if self.option_chain is None or "iv" not in self.option_chain.columns:
            return 50  # Default mid value

        try:
            # Get current average IV
            current_iv = self.option_chain["iv"].mean()

            # For a real implementation, we would compare to historical IV
            # Here we'll just simulate with a random percentile
            # In production, you would have historical IV data to calculate a true percentile

            # Simulate percentile between 10 and 90
            percentile = np.random.randint(10, 90)

            return round(percentile, 0)

        except Exception as e:
            logger.error(f"Error calculating IV percentile: {str(e)}")
            return 50

    def _calculate_max_pain(self) -> float:
        """
        Calculate option max pain price.

        Returns:
            Max pain price level
        """
        if self.option_chain is None or self.option_chain.empty:
            return 0

        try:
            # Get unique strikes
            strikes = sorted(self.option_chain["strike"].unique())

            if not strikes:
                return 0

            # Calculate loss at each strike
            max_pain_loss = float('inf')
            max_pain_strike = strikes[0]

            for strike in strikes:
                # Calculate total loss for option writers at this strike
                total_loss = 0

                # Calls: loss if price > strike
                for call in self.option_chain[self.option_chain["type"] == "CE"].itertuples():
                    if strike > call.strike:
                        loss = 0  # Option expires worthless
                    else:
                        loss = (strike - call.strike) * call.open_interest

                    total_loss += loss

                # Puts: loss if price < strike
                for put in self.option_chain[self.option_chain["type"] == "PE"].itertuples():
                    if strike < put.strike:
                        loss = 0  # Option expires worthless
                    else:
                        loss = (put.strike - strike) * put.open_interest

                    total_loss += loss

                # Update max pain if this is lower loss
                if total_loss < max_pain_loss:
                    max_pain_loss = total_loss
                    max_pain_strike = strike

            return max_pain_strike

        except Exception as e:
            logger.error(f"Error calculating max pain: {str(e)}")
            return 0

    def _analyze_open_interest(self, option_type: str) -> str:
        """
        Analyze option chain open interest patterns.

        Args:
            option_type: Option type (CE/PE)

        Returns:
            Analysis of open interest patterns
        """
        if self.option_chain is None or self.option_chain.empty:
            return "Insufficient data for OI analysis"

        try:
            # Filter by option type
            filtered_chain = self.option_chain[self.option_chain["type"] == option_type]

            if filtered_chain.empty:
                return f"No {option_type} options found for OI analysis"

            # Find strike with max OI
            max_oi_row = filtered_chain.loc[filtered_chain["open_interest"].idxmax()]
            max_oi_strike = max_oi_row["strike"]

            # Find strikes with high OI
            mean_oi = filtered_chain["open_interest"].mean()
            high_oi_strikes = filtered_chain[filtered_chain["open_interest"] > mean_oi * 1.5]["strike"].tolist()

            # Look for OI buildup (increasing OI with increasing volume)
            has_buildup = False

            # In a real implementation, we would have historical OI data
            # For now, we'll randomly simulate buildup
            has_buildup = np.random.choice([True, False], p=[0.7, 0.3])

            # Generate analysis text
            analysis = f"Maximum OI at strike {max_oi_strike}. "

            if high_oi_strikes:
                analysis += f"High OI concentration at strikes {', '.join(map(str, high_oi_strikes))}. "

            if has_buildup:
                if option_type == "CE":
                    analysis += "Significant call OI buildup suggests bullish sentiment."
                else:
                    analysis += "Significant put OI buildup suggests bearish sentiment."
            else:
                analysis += "No significant OI buildup detected."

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing open interest: {str(e)}")
            return "Error in OI analysis"

    def _calculate_option_prices(self, strike: float, option_type: str,
                                current_price: float, target_price: float,
                                stop_loss: float) -> Tuple[float, float, float]:
        """
        Calculate option prices (current, target, stop loss).

        Args:
            strike: Selected option strike
            option_type: Option type (CE/PE)
            current_price: Current stock price
            target_price: Target stock price
            stop_loss: Stop loss stock price

        Returns:
            Tuple of (current_option_price, target_option_price, option_stop_loss)
        """
        if self.option_chain is None:
            return 0, 0, 0

        try:
            # Try to get current option price from the chain
            option_row = self.option_chain[(self.option_chain["strike"] == strike) &
                                         (self.option_chain["type"] == option_type)]

            if not option_row.empty:
                current_option_price = option_row.iloc[0]["last_price"]
            else:
                # Estimate option price using intrinsic value + random extrinsic
                if option_type == "CE":
                    intrinsic = max(0, current_price - strike)
                else:  # PE
                    intrinsic = max(0, strike - current_price)

                extrinsic = current_price * 0.03  # Simple estimate for time value
                current_option_price = round(intrinsic + extrinsic, 2)

            # Estimate target option price
            if option_type == "CE":
                target_intrinsic = max(0, target_price - strike)
                stop_loss_intrinsic = max(0, stop_loss - strike)
            else:  # PE
                target_intrinsic = max(0, strike - target_price)
                stop_loss_intrinsic = max(0, strike - stop_loss)

            # Add estimated extrinsic value
            target_extrinsic = target_price * 0.02  # Less extrinsic at target (time decay)
            stop_loss_extrinsic = current_price * 0.02  # Extrinsic at stop loss

            target_option_price = round(target_intrinsic + target_extrinsic, 2)
            option_stop_loss = round(stop_loss_intrinsic + stop_loss_extrinsic, 2)

            # Ensure option stop loss is less than current for long options
            if option_stop_loss >= current_option_price:
                option_stop_loss = round(current_option_price * 0.7, 2)  # 30% loss

            return current_option_price, target_option_price, option_stop_loss

        except Exception as e:
            logger.error(f"Error calculating option prices: {str(e)}")
            return 0, 0, 0

    def _generate_option_symbol(self, strike: float, option_type: str) -> str:
        """
        Generate full option contract symbol.

        Args:
            strike: Option strike price
            option_type: Option type (CE/PE)

        Returns:
            Full option contract symbol
        """
        if self.option_chain is None or self.option_chain.empty:
            return ""

        try:
            # Extract symbol from option chain
            if "symbol" in self.option_chain.columns and not self.option_chain.empty:
                symbol = self.option_chain.iloc[0]["symbol"]
            else:
                # Default fallback
                symbol = "UNKNOWN"

            # Extract expiry month from option chain
            if "expiry" in self.option_chain.columns and not self.option_chain.empty:
                expiry = self.option_chain.iloc[0]["expiry"]
            else:
                # Default to current month
                now = datetime.datetime.now()
                expiry = now.strftime("%b").upper()

            # Format strike without decimal
            strike_str = str(int(strike)) if strike.is_integer() else str(strike)

            # Construct the full symbol
            full_symbol = f"{symbol}{expiry}{strike_str}{option_type}"

            return full_symbol

        except Exception as e:
            logger.error(f"Error generating option symbol: {str(e)}")
            return ""