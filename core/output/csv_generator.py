"""
CSV output generator for stock analysis results.
"""
import os
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from config.settings import OUTPUT_DIR, CSV_FILENAME


class CSVGenerator:
    """
    Generate CSV output from stock analysis results.

    Features:
    - Convert analysis results to CSV format
    - Save CSV to file
    - Support for single or multiple stock analyses
    - Combine results with previously saved data
    """

    def __init__(self, filename: Optional[str] = None):
        """
        Initialize CSV generator.

        Args:
            filename: Output filename (default from config)
        """
        self.filename = filename or os.path.join(OUTPUT_DIR, CSV_FILENAME)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)

        logger.info(f"CSV Generator initialized with output file: {self.filename}")

    def generate_csv(self, analysis_results: Dict) -> str:
        """
        Generate CSV from analysis results, preserving existing data.

        Args:
            analysis_results: Dictionary with analysis results for one or more stocks

        Returns:
            Path to generated CSV file
        """
        try:
            # First try to read existing CSV data if the file exists
            existing_df = None
            if os.path.exists(self.filename) and os.path.getsize(self.filename) > 0:
                try:
                    existing_df = pd.read_csv(self.filename)
                    logger.info(f"Loaded existing CSV data with {len(existing_df)} records")
                except Exception as e:
                    logger.warning(f"Could not read existing CSV file: {str(e)}")

            # Convert new results to DataFrame
            new_df = None
            if "symbol" in analysis_results:
                # Single stock
                new_df = pd.DataFrame([analysis_results])
            else:
                # Multiple stocks
                results_list = [result for result in analysis_results.values() if "error" not in result]
                if results_list:
                    new_df = pd.DataFrame(results_list)

            if new_df is None or new_df.empty:
                logger.error("No valid analysis results to write to CSV")
                return ""

            # Combine existing and new data
            if existing_df is not None and not existing_df.empty:
                # Remove duplicate symbols from existing data
                if 'symbol' in existing_df.columns and 'symbol' in new_df.columns:
                    new_symbols = new_df['symbol'].tolist()
                    existing_df = existing_df[~existing_df['symbol'].isin(new_symbols)]

                # Combine the DataFrames
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                logger.info(f"Combined existing and new data: {len(combined_df)} total records")
            else:
                combined_df = new_df
                logger.info(f"Using new data only: {len(combined_df)} records")

            # Reorder columns based on sections in requirements
            ordered_columns = self._get_ordered_columns()

            # Only include columns that exist in the data
            available_columns = [col for col in ordered_columns if col in combined_df.columns]

            # Reorder dataframe columns
            combined_df = combined_df[available_columns]

            # Write to CSV
            combined_df.to_csv(self.filename, index=False)

            logger.info(f"Successfully generated CSV with {len(combined_df)} records: {self.filename}")
            return self.filename

        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}")
            return ""

    def _get_ordered_columns(self) -> List[str]:
        """
        Get ordered list of columns for CSV output.

        Returns:
            List of column names in desired order
        """
        return [
            # Basic Stock Information
            "symbol",
            "previous_close",
            "current_price",
            "volatility_percent",

            # Signal Information
            "signal",
            "direction",
            "confidence_percent",
            "profit_probability_percent",

            # Price Targets
            "target_price",
            "stop_loss_price",
            "risk_reward_ratio",
            "days_to_target",

            # Technical Indicators
            "technical_trend_score",
            "momentum_score",
            "rsi",
            "adx",
            "macd",
            "volume_change_percent",

            # Support and Resistance Levels
            "major_support_1",
            "major_support_2",
            "major_support_3",
            "major_resistance_1",
            "major_resistance_2",
            "major_resistance_3",

            # Position Sizing
            "position_sizing_recommendation",

            # Option Information
            "underlying_strike",
            "selected_strike",
            "strike_type",
            "options_iv_percentile",
            "max_pain_price",
            "open_interest_analysis",

            # Option Prices
            "option_current_price",
            "option_target_price",
            "option_stop_loss",

            # Risk Factors
            "earnings_impact_risk",
            "days_to_earnings",

            # Model and Analysis Metadata
            "model_accuracy",
            "analysis_timestamp",
            "market_status"
        ]