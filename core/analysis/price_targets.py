"""
Price targets calculation module for stock analysis.
"""
from typing import Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd
from loguru import logger

from core.analysis.technical_indicators import TechnicalIndicators


class PriceTargets:
    """
    Calculate price targets, stop loss levels, and risk/reward ratios.

    Features:
    - Calculate target prices based on technical analysis
    - Calculate stop loss levels
    - Calculate risk/reward ratio
    - Estimate days to target
    """

    def __init__(self, historical_data: pd.DataFrame, technical_indicators: TechnicalIndicators):
        """
        Initialize with historical price data and technical indicators.

        Args:
            historical_data: DataFrame with OHLCV data
            technical_indicators: Technical indicators instance
        """
        self.data = historical_data.copy() if historical_data is not None else None
        self.indicators = technical_indicators

        logger.info("Price targets module initialized")

    def calculate_price_targets(self, current_price: float, prediction_direction: str) -> Dict[str, Union[float, int]]:
        """
        Calculate price targets, stop loss, and related metrics.

        Args:
            current_price: Current stock price
            prediction_direction: Predicted direction ("UP" or "DOWN")

        Returns:
            Dictionary with target price, stop loss, risk/reward ratio, and days to target
        """
        if self.data is None or len(self.data) < 50:
            logger.error("Insufficient historical data for price target calculation")
            return {}

        try:
            # Get support and resistance levels
            supports, resistances = self.indicators.calculate_support_resistance()

            if not supports or not resistances:
                logger.warning("No support/resistance levels available, using percentage-based targets")
                # Fallback to percentage-based calculation
                if prediction_direction == "UP":
                    target_price = round(current_price * 1.05, 2)  # 5% up
                    stop_loss = round(current_price * 0.97, 2)  # 3% down
                else:  # "DOWN"
                    target_price = round(current_price * 0.95, 2)  # 5% down
                    stop_loss = round(current_price * 1.03, 2)  # 3% up
            else:
                # Use support/resistance levels
                if prediction_direction == "UP":
                    # Find first resistance above current price
                    potential_targets = [r for r in resistances if r > current_price]
                    target_price = min(potential_targets) if potential_targets else round(current_price * 1.05, 2)

                    # Find first support below current price
                    potential_stops = [s for s in supports if s < current_price]
                    stop_loss = max(potential_stops) if potential_stops else round(current_price * 0.97, 2)
                else:  # "DOWN"
                    # Find first support below current price
                    potential_targets = [s for s in supports if s < current_price]
                    target_price = max(potential_targets) if potential_targets else round(current_price * 0.95, 2)

                    # Find first resistance above current price
                    potential_stops = [r for r in resistances if r > current_price]
                    stop_loss = min(potential_stops) if potential_stops else round(current_price * 1.03, 2)

            # Calculate risk/reward ratio
            risk = abs(current_price - stop_loss)
            reward = abs(current_price - target_price)

            if risk == 0:
                risk_reward_ratio = 0  # Avoid division by zero
            else:
                risk_reward_ratio = round(reward / risk, 2)

            # Estimate days to target
            days_to_target = self._estimate_days_to_target(current_price, target_price)

            # Compile results
            result = {
                "target_price": target_price,
                "stop_loss_price": stop_loss,
                "risk_reward_ratio": risk_reward_ratio,
                "days_to_target": days_to_target
            }

            logger.info(f"Successfully calculated price targets: {result}")
            return result

        except Exception as e:
            logger.error(f"Error calculating price targets: {str(e)}")
            return {}

    def _estimate_days_to_target(self, current_price: float, target_price: float) -> int:
        """
        Estimate the number of days to reach the target price.

        Args:
            current_price: Current stock price
            target_price: Target price

        Returns:
            Estimated number of days to reach target
        """
        if self.data is None or len(self.data) < 30:
            return 10  # Default estimate

        try:
            # Calculate average daily price change (absolute value)
            price_changes = self.data["close"].pct_change().abs()
            avg_daily_change = price_changes.iloc[-30:].mean()  # Last 30 days

            # Calculate percentage difference to target
            pct_diff = abs(target_price - current_price) / current_price

            # Estimate days based on average movement
            if avg_daily_change == 0:
                return 30  # Fallback if no movement

            days = round(pct_diff / avg_daily_change)

            # Constrain the estimate to a reasonable range
            days = max(1, min(days, 60))

            return days

        except Exception as e:
            logger.error(f"Error estimating days to target: {str(e)}")
            return 10  # Default fallback