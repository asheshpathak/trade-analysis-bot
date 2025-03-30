"""
JSON output generator for stock analysis results.
"""
import json
import os
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any

from loguru import logger

from config.settings import OUTPUT_DIR, JSON_FILENAME


# Custom JSON encoder to handle numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)


class JSONGenerator:
    """
    Generate JSON output from stock analysis results.

    Features:
    - Convert analysis results to structured JSON format
    - Save JSON to file
    - Support for single or multiple stock analyses
    - Include metadata and organization by sections
    """

    def __init__(self, filename: Optional[str] = None):
        """
        Initialize JSON generator.

        Args:
            filename: Output filename (default from config)
        """
        self.filename = filename or os.path.join(OUTPUT_DIR, JSON_FILENAME)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)

        logger.info(f"JSON Generator initialized with output file: {self.filename}")

    def generate_json(self, analysis_results: Dict) -> str:
        """
        Generate JSON from analysis results.

        Args:
            analysis_results: Dictionary with analysis results for one or more stocks

        Returns:
            Path to generated JSON file
        """
        try:
            # Check if results is for a single stock or multiple stocks
            if "symbol" in analysis_results:
                # Single stock, structure it
                structured_results = {
                    "metadata": {
                        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "version": "1.0.0"
                    },
                    "stocks": [self._structure_stock_data(analysis_results)]
                }
            else:
                # Multiple stocks
                valid_results = [result for symbol, result in analysis_results.items()
                                 if "error" not in result]

                structured_results = {
                    "metadata": {
                        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "version": "1.0.0",
                        "stock_count": len(valid_results)
                    },
                    "stocks": [self._structure_stock_data(result) for result in valid_results]
                }

            # Write to JSON file with the custom encoder
            with open(self.filename, 'w') as f:
                json.dump(structured_results, f, indent=2, cls=NumpyEncoder)

            logger.info(f"Successfully generated JSON output: {self.filename}")
            return self.filename

        except Exception as e:
            logger.error(f"Error generating JSON: {str(e)}")
            return ""

    def _structure_stock_data(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structure stock data into organized sections.

        Args:
            stock_data: Dictionary with raw stock analysis data

        Returns:
            Dictionary with structured stock data
        """
        # Create structured output with sections as defined in requirements
        structured = {
            "basic_info": {
                "symbol": stock_data.get("symbol"),
                "previous_close": stock_data.get("previous_close"),
                "current_price": stock_data.get("current_price"),
                "volatility_percent": stock_data.get("volatility_percent")
            },
            "signal_info": {
                "signal": stock_data.get("signal"),
                "direction": stock_data.get("direction"),
                "confidence_percent": stock_data.get("confidence_percent"),
                "profit_probability_percent": stock_data.get("profit_probability_percent")
            },
            "price_targets": {
                "target_price": stock_data.get("target_price"),
                "stop_loss_price": stock_data.get("stop_loss_price"),
                "risk_reward_ratio": stock_data.get("risk_reward_ratio"),
                "days_to_target": stock_data.get("days_to_target")
            },
            "technical_indicators": {
                "technical_trend_score": stock_data.get("technical_trend_score"),
                "momentum_score": stock_data.get("momentum_score"),
                "rsi": stock_data.get("rsi"),
                "adx": stock_data.get("adx"),
                "macd": stock_data.get("macd"),
                "volume_change_percent": stock_data.get("volume_change_percent")
            },
            "support_resistance": {
                "support_levels": [
                    stock_data.get("major_support_1"),
                    stock_data.get("major_support_2"),
                    stock_data.get("major_support_3")
                ],
                "resistance_levels": [
                    stock_data.get("major_resistance_1"),
                    stock_data.get("major_resistance_2"),
                    stock_data.get("major_resistance_3")
                ]
            },
            "position_sizing": {
                "recommendation": stock_data.get("position_sizing_recommendation")
            },
            "option_info": {
                "underlying_strike": stock_data.get("underlying_strike"),
                "selected_strike": stock_data.get("selected_strike"),
                "strike_type": stock_data.get("strike_type"),
                "iv_percentile": stock_data.get("options_iv_percentile"),
                "max_pain_price": stock_data.get("max_pain_price"),
                "open_interest_analysis": stock_data.get("open_interest_analysis")
            },
            "option_prices": {
                "current_price": stock_data.get("option_current_price"),
                "target_price": stock_data.get("option_target_price"),
                "stop_loss": stock_data.get("option_stop_loss")
            },
            "risk_factors": {
                "earnings_impact_risk": stock_data.get("earnings_impact_risk"),
                "days_to_earnings": stock_data.get("days_to_earnings")
            },
            "metadata": {
                "model_accuracy": stock_data.get("model_accuracy"),
                "analysis_timestamp": stock_data.get("analysis_timestamp"),
                "market_status": stock_data.get("market_status")
            }
        }

        return structured