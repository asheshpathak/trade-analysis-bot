"""
Technical indicators calculation module for stock analysis.
"""
from typing import Dict, Optional, Union, List

import numpy as np
import pandas as pd
import pandas_ta as ta
from loguru import logger

from config.settings import (
    RSI_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    ADX_PERIOD,
    MOMENTUM_PERIOD,
)


class TechnicalIndicators:
    """
    Calculate technical indicators for stock analysis.

    Features:
    - Calculate RSI (Relative Strength Index)
    - Calculate MACD (Moving Average Convergence Divergence)
    - Calculate ADX (Average Directional Index)
    - Calculate momentum score
    - Calculate technical trend score
    - Calculate support and resistance levels
    """

    def __init__(self, historical_data: pd.DataFrame):
        """
        Initialize with historical price data.

        Args:
            historical_data: DataFrame with OHLCV data
        """
        self.data = historical_data.copy() if historical_data is not None else None

        if self.data is not None:
            # Ensure the expected columns exist
            required_columns = ["open", "high", "low", "close", "volume"]
            missing_columns = [col for col in required_columns if col not in self.data.columns]

            if missing_columns:
                logger.error(f"Historical data missing required columns: {missing_columns}")
                self.data = None

        logger.info("Technical indicators module initialized")

    def calculate_all_indicators(self) -> Dict[str, Union[float, int, List[float]]]:
        """
        Calculate all technical indicators.

        Returns:
            Dictionary with all calculated technical indicators
        """
        if self.data is None or len(self.data) < 50:  # Need enough data for reliable indicators
            logger.error("Insufficient historical data for technical analysis")
            return {}

        try:
            # Calculate all indicators
            rsi = self.calculate_rsi()
            macd, macd_signal, macd_hist = self.calculate_macd()
            adx = self.calculate_adx()
            momentum_score = self.calculate_momentum_score()
            trend_score = self.calculate_technical_trend_score()
            supports, resistances = self.calculate_support_resistance()
            volume_change = self.calculate_volume_change()

            # Compile results
            result = {
                "rsi": rsi,
                "macd": macd,
                "macd_signal": macd_signal,
                "macd_histogram": macd_hist,
                "adx": adx,
                "momentum_score": momentum_score,
                "technical_trend_score": trend_score,
                "volume_change_percent": volume_change,
                "support_levels": supports,
                "resistance_levels": resistances,
            }

            logger.info(f"Successfully calculated all technical indicators")
            return result

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            return {}

    def calculate_rsi(self, period: int = None) -> float:
        """
        Calculate Relative Strength Index.

        Args:
            period: Period for RSI calculation, defaults to setting in config

        Returns:
            Current RSI value
        """
        if self.data is None:
            return None

        period = period or RSI_PERIOD

        try:
            # Using pandas-ta for RSI calculation
            rsi = ta.rsi(self.data["close"], length=period)
            current_rsi = rsi.iloc[-1]
            return round(current_rsi, 2)
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            return None

    def calculate_macd(self, fast: int = None, slow: int = None, signal: int = None) -> tuple:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            fast: Fast period for MACD
            slow: Slow period for MACD
            signal: Signal period for MACD

        Returns:
            Tuple of (MACD, Signal, Histogram)
        """
        if self.data is None:
            return None, None, None

        fast = fast or MACD_FAST
        slow = slow or MACD_SLOW
        signal = signal or MACD_SIGNAL

        try:
            # Using pandas-ta for MACD calculation
            macd_result = ta.macd(self.data["close"], fast=fast, slow=slow, signal=signal)

            # Column names in pandas-ta are slightly different
            macd_col = f"MACD_{fast}_{slow}_{signal}"
            signal_col = f"MACDs_{fast}_{slow}_{signal}"
            hist_col = f"MACDh_{fast}_{slow}_{signal}"

            current_macd = round(macd_result[macd_col].iloc[-1], 2)
            current_signal = round(macd_result[signal_col].iloc[-1], 2)
            current_hist = round(macd_result[hist_col].iloc[-1], 2)

            return current_macd, current_signal, current_hist
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            return None, None, None

    def calculate_adx(self, period: int = None) -> float:
        """
        Calculate Average Directional Index.

        Args:
            period: Period for ADX calculation

        Returns:
            Current ADX value
        """
        if self.data is None:
            return None

        period = period or ADX_PERIOD

        try:
            # Using pandas-ta for ADX calculation
            adx_result = ta.adx(self.data["high"], self.data["low"], self.data["close"], length=period)

            # Get the ADX value (column name depends on period)
            adx_col = f"ADX_{period}"
            current_adx = adx_result[adx_col].iloc[-1]

            return round(current_adx, 2)
        except Exception as e:
            logger.error(f"Error calculating ADX: {str(e)}")
            return None

    def calculate_momentum_score(self, period: int = None) -> float:
        """
        Calculate momentum score based on multiple indicators.

        Args:
            period: Period for momentum calculation

        Returns:
            Momentum score between 0 and 1
        """
        if self.data is None:
            return None

        period = period or MOMENTUM_PERIOD

        try:
            # ROC (Rate of Change) using pandas-ta
            roc = ta.roc(self.data["close"], length=period)

            # Calculate SMAs using pandas-ta
            sma20 = ta.sma(self.data["close"], length=20)
            sma50 = ta.sma(self.data["close"], length=50)

            # RSI
            rsi = ta.rsi(self.data["close"], length=14)

            # Get most recent values
            current_roc = roc.iloc[-1]
            price_vs_sma20 = self.data["close"].iloc[-1] / sma20.iloc[-1] - 1
            price_vs_sma50 = self.data["close"].iloc[-1] / sma50.iloc[-1] - 1
            current_rsi = rsi.iloc[-1]

            # Normalize each component to [0, 1] range
            norm_roc = self._normalize(current_roc, -10, 10)
            norm_price_vs_sma20 = self._normalize(price_vs_sma20, -0.1, 0.1)
            norm_price_vs_sma50 = self._normalize(price_vs_sma50, -0.2, 0.2)
            norm_rsi = self._normalize(current_rsi, 30, 70)

            # Weighted average
            momentum_score = (
                0.3 * norm_roc +
                0.3 * norm_price_vs_sma20 +
                0.2 * norm_price_vs_sma50 +
                0.2 * norm_rsi
            )

            # Ensure score is in [0, 1]
            momentum_score = max(0, min(1, momentum_score))

            return round(momentum_score, 2)
        except Exception as e:
            logger.error(f"Error calculating momentum score: {str(e)}")
            return None

    def calculate_technical_trend_score(self) -> float:
        """
        Calculate composite technical trend score.

        Returns:
            Technical trend score between 0 and 100
        """
        if self.data is None:
            return None

        try:
            # RSI component
            rsi = self.calculate_rsi()
            rsi_score = self._normalize(rsi, 30, 70) * 100

            # MACD component
            macd, signal, hist = self.calculate_macd()
            macd_trending_up = 100 if hist > 0 else 0

            # ADX component (trend strength)
            adx = self.calculate_adx()
            adx_score = min(100, adx)

            # Moving average relationships using pandas-ta
            sma20 = ta.sma(self.data["close"], length=20).iloc[-1]
            sma50 = ta.sma(self.data["close"], length=50).iloc[-1]
            sma200 = ta.sma(self.data["close"], length=200).iloc[-1]

            price = self.data["close"].iloc[-1]
            ma_score = 0

            # Add this line to define the missing variable
            price_above_sma50 = price > sma50

            if price > sma20 > sma50 > sma200:
                # Strong uptrend
                ma_score = 100
            elif price > sma20 and price > sma50:
                # Moderate uptrend
                ma_score = 75
            elif price > sma20:
                # Weak uptrend
                ma_score = 60
            elif price < sma20 < sma50 < sma200:
                # Strong downtrend
                ma_score = 0
            elif price < sma20 and price < sma50:
                # Moderate downtrend
                ma_score = 25
            elif price < sma20:
                # Weak downtrend
                ma_score = 40
            else:
                # Neutral
                ma_score = 50

            # Volume trend
            volume_ma = ta.sma(self.data["volume"], length=20).iloc[-1]
            volume_score = 60
            if self.data["volume"].iloc[-1] > volume_ma and hist > 0:
                # High volume in direction of trend (bullish)
                volume_score = 100
            elif self.data["volume"].iloc[-1] > volume_ma and hist < 0:
                # High volume against trend (bearish)
                volume_score = 0

            # Weighted average for final score
            trend_score = (
                0.2 * rsi_score +
                0.2 * macd_trending_up +
                0.2 * adx_score +
                0.3 * ma_score +
                0.1 * volume_score
            )

            return round(trend_score, 0)
        except Exception as e:
            logger.error(f"Error calculating technical trend score: {str(e)}")
            return None

    def calculate_support_resistance(self, lookback: int = 30, window: int = 5) -> tuple:
        """
        Calculate support and resistance levels.

        Args:
            lookback: Number of periods to look back
            window: Window size for peak detection

        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        if self.data is None or len(self.data) < lookback:
            return [], []

        try:
            # Extract recent price data
            recent_data = self.data.iloc[-lookback:]

            # Find local minimums (supports)
            supports = []
            for i in range(window, len(recent_data) - window):
                if all(recent_data["low"].iloc[i] <= recent_data["low"].iloc[i-j] for j in range(1, window+1)) and \
                   all(recent_data["low"].iloc[i] <= recent_data["low"].iloc[i+j] for j in range(1, window+1)):
                    supports.append(round(recent_data["low"].iloc[i], 2))

            # Find local maximums (resistances)
            resistances = []
            for i in range(window, len(recent_data) - window):
                if all(recent_data["high"].iloc[i] >= recent_data["high"].iloc[i-j] for j in range(1, window+1)) and \
                   all(recent_data["high"].iloc[i] >= recent_data["high"].iloc[i+j] for j in range(1, window+1)):
                    resistances.append(round(recent_data["high"].iloc[i], 2))

            # Ensure we have at least 3 levels for each
            current_price = self.data["close"].iloc[-1]

            # If not enough support levels, add some based on percentage moves
            while len(supports) < 3:
                pct_move = 0.02 * (len(supports) + 1)
                new_support = round(current_price * (1 - pct_move), 2)
                if new_support not in supports:
                    supports.append(new_support)

            # If not enough resistance levels, add some based on percentage moves
            while len(resistances) < 3:
                pct_move = 0.02 * (len(resistances) + 1)
                new_resistance = round(current_price * (1 + pct_move), 2)
                if new_resistance not in resistances:
                    resistances.append(new_resistance)

            # Sort levels
            supports = sorted(supports)[:3]  # Take the 3 closest supports
            resistances = sorted(resistances)[-3:]  # Take the 3 closest resistances

            return supports, resistances
        except Exception as e:
            logger.error(f"Error calculating support and resistance levels: {str(e)}")
            return [], []

    def calculate_volume_change(self, days: int = 20) -> float:
        """
        Calculate volume change percentage compared to moving average.

        Args:
            days: Number of days for moving average

        Returns:
            Volume change percentage
        """
        if self.data is None or "volume" not in self.data.columns:
            return None

        try:
            # Use pandas-ta for SMA calculation
            volume_ma = ta.sma(self.data["volume"], length=days)
            current_volume = self.data["volume"].iloc[-1]
            avg_volume = volume_ma.iloc[-1]

            if avg_volume == 0:
                return 0

            volume_change = ((current_volume - avg_volume) / avg_volume) * 100
            return round(volume_change, 2)
        except Exception as e:
            logger.error(f"Error calculating volume change: {str(e)}")
            return None

    def _normalize(self, value, min_val, max_val):
        """Normalize a value to [0, 1] range."""
        if value is None:
            return 0.5  # Neutral if no value

        if value <= min_val:
            return 0
        if value >= max_val:
            return 1

        return (value - min_val) / (max_val - min_val)