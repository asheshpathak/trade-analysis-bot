"""
Main stock analyzer module that coordinates the analysis process.
"""
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from core.analysis.technical_indicators import TechnicalIndicators
from core.analysis.price_targets import PriceTargets
from core.analysis.option_analysis import OptionAnalysis
from core.analysis.risk_factors import RiskFactors
from core.analysis.model import StockPredictionModel
from core.data.market_data import MarketData


class StockAnalyzer:
    """
    Coordinate the stock analysis process.

    This class orchestrates the entire analysis workflow:
    1. Fetch market data
    2. Calculate technical indicators
    3. Generate predictions
    4. Calculate price targets
    5. Analyze options
    6. Assess risk factors
    7. Compile final results
    """

    def __init__(self):
        """Initialize the stock analyzer."""
        self.market_data = MarketData()
        logger.info("Stock analyzer initialized")

    def analyze_stock(self, symbol: str) -> Dict:
        """
        Perform comprehensive analysis on a stock.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Dictionary with complete analysis results
        """
        try:
            logger.info(f"Starting analysis for {symbol}")

            # Step 1: Fetch market data
            market_data = self.market_data.get_market_data(symbol)
            if not market_data:
                error_msg = f"Failed to fetch market data for {symbol}"
                logger.error(error_msg)
                return {"error": error_msg}

            current_price = market_data.get("current_price")
            previous_close = market_data.get("previous_close")
            historical_data = market_data.get("historical_data")
            option_chain = market_data.get("option_chain")
            volatility = market_data.get("volatility_percent")
            volume_change = market_data.get("volume_change_percent")

            if not current_price or not historical_data.any():
                error_msg = f"Insufficient market data for {symbol}"
                logger.error(error_msg)
                return {"error": error_msg}

            # Step 2: Calculate technical indicators
            indicators = TechnicalIndicators(historical_data)
            technical_indicators = indicators.calculate_all_indicators()

            # Step 3: Generate prediction
            model = StockPredictionModel(historical_data, indicators)
            prediction = model.generate_prediction()

            if not prediction:
                error_msg = f"Failed to generate prediction for {symbol}"
                logger.error(error_msg)
                return {"error": error_msg}

            direction = prediction.get("direction")

            # Step 4: Calculate price targets
            price_targets = PriceTargets(historical_data, indicators)
            targets = price_targets.calculate_price_targets(current_price, direction)

            if not targets:
                error_msg = f"Failed to calculate price targets for {symbol}"
                logger.error(error_msg)
                return {"error": error_msg}

            target_price = targets.get("target_price")
            stop_loss = targets.get("stop_loss_price")

            # Step 5: Analyze options
            option_analyzer = OptionAnalysis(historical_data, option_chain)
            option_analysis = option_analyzer.analyze_options(
                current_price, direction, target_price, stop_loss
            )

            # Step 6: Assess risk factors
            risk_analyzer = RiskFactors(symbol, current_price)
            risk_analysis = risk_analyzer.analyze_risk_factors(stop_loss)

            # Step 7: Compile final results
            results = {
                # Basic Stock Information
                "symbol": symbol,
                "previous_close": previous_close,
                "current_price": current_price,
                "volatility_percent": volatility,

                # Signal Information
                "signal": prediction.get("signal"),
                "direction": direction,
                "confidence_percent": prediction.get("confidence_percent"),
                "profit_probability_percent": prediction.get("profit_probability_percent"),

                # Price Targets
                "target_price": target_price,
                "stop_loss_price": stop_loss,
                "risk_reward_ratio": targets.get("risk_reward_ratio"),
                "days_to_target": targets.get("days_to_target"),

                # Technical Indicators
                "technical_trend_score": technical_indicators.get("technical_trend_score"),
                "momentum_score": technical_indicators.get("momentum_score"),
                "rsi": technical_indicators.get("rsi"),
                "adx": technical_indicators.get("adx"),
                "macd": technical_indicators.get("macd"),
                "volume_change_percent": volume_change,

                # Support and Resistance Levels
                "major_support_1": technical_indicators.get("support_levels")[0] if technical_indicators.get("support_levels") else None,
                "major_support_2": technical_indicators.get("support_levels")[1] if technical_indicators.get("support_levels") and len(technical_indicators.get("support_levels")) > 1 else None,
                "major_support_3": technical_indicators.get("support_levels")[2] if technical_indicators.get("support_levels") and len(technical_indicators.get("support_levels")) > 2 else None,
                "major_resistance_1": technical_indicators.get("resistance_levels")[0] if technical_indicators.get("resistance_levels") else None,
                "major_resistance_2": technical_indicators.get("resistance_levels")[1] if technical_indicators.get("resistance_levels") and len(technical_indicators.get("resistance_levels")) > 1 else None,
                "major_resistance_3": technical_indicators.get("resistance_levels")[2] if technical_indicators.get("resistance_levels") and len(technical_indicators.get("resistance_levels")) > 2 else None,

                # Position Sizing
                "position_sizing_recommendation": risk_analysis.get("position_sizing_recommendation"),

                # Option Information
                "underlying_strike": option_analysis.get("underlying_strike"),
                "selected_strike": option_analysis.get("selected_strike"),
                "strike_type": option_analysis.get("strike_type"),
                "options_iv_percentile": option_analysis.get("options_iv_percentile"),
                "max_pain_price": option_analysis.get("max_pain_price"),
                "open_interest_analysis": option_analysis.get("open_interest_analysis"),

                # Option Prices
                "option_current_price": option_analysis.get("option_current_price"),
                "option_target_price": option_analysis.get("option_target_price"),
                "option_stop_loss": option_analysis.get("option_stop_loss"),

                # Risk Factors
                "earnings_impact_risk": risk_analysis.get("earnings_impact_risk"),
                "days_to_earnings": risk_analysis.get("days_to_earnings"),

                # Model and Analysis Metadata
                "model_accuracy": prediction.get("model_accuracy"),
                "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "market_status": market_data.get("market_status")
            }

            logger.info(f"Analysis completed for {symbol}")
            return results

        except Exception as e:
            error_msg = f"Error analyzing {symbol}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def analyze_multiple_stocks(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Analyze multiple stocks.

        Args:
            symbols: List of stock symbols to analyze

        Returns:
            Dictionary mapping symbols to their analysis results
        """
        results = {}

        for symbol in symbols:
            try:
                results[symbol] = self.analyze_stock(symbol)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {str(e)}")
                results[symbol] = {"error": str(e)}

        return results