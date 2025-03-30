"""
API controllers for stock analysis application.
"""
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any

from loguru import logger

from config.settings import DEFAULT_SYMBOLS, OUTPUT_DIR
from core.analysis.stock_analyzer import StockAnalyzer
from core.data.market_data import MarketData
from utils.concurrency import PeriodicTask
from utils.helpers import read_json_file, write_json_file, get_timestamp
from utils.validators import validate_symbol, validate_symbols_list


class StockAnalysisController:
    """
    Controller for stock analysis API.

    Features:
    - Handle API requests
    - Coordinate analysis operations
    - Manage data caching and persistence
    - Schedule periodic analysis updates
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(StockAnalysisController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize controller if not already initialized."""
        if self._initialized:
            return

        self.analyzer = StockAnalyzer()
        self.market_data = MarketData()
        self.cache_dir = os.path.join(OUTPUT_DIR, "cache")
        self.cache = {}
        self.last_update = None

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

        # Setup periodic updates
        self.periodic_task = None
        self._setup_periodic_updates()

        self._initialized = True
        logger.info("Stock analysis controller initialized")

    def _setup_periodic_updates(self):
        """Setup periodic updates based on market status."""
        from config.settings import (
            MARKET_OPEN_REFRESH_INTERVAL,
            MARKET_CLOSED_REFRESH_INTERVAL
        )

        # Determine refresh interval based on market status
        refresh_interval = (
            MARKET_OPEN_REFRESH_INTERVAL if self.market_data.is_market_open()
            else MARKET_CLOSED_REFRESH_INTERVAL
        )

        # Create and start periodic task
        self.periodic_task = PeriodicTask(
            self._update_analysis,
            refresh_interval,
            DEFAULT_SYMBOLS
        )
        self.periodic_task.start()

        logger.info(f"Periodic updates setup with interval {refresh_interval}s")

    def _update_analysis(self, symbols: List[str]):
        """
        Update analysis for specified symbols.

        Args:
            symbols: List of symbols to analyze
        """
        if not symbols:
            logger.warning("No symbols provided for update")
            return

        try:
            # Check if market status has changed
            is_market_open = self.market_data.is_market_open()

            # Adjust refresh interval if market status changed
            if hasattr(self, 'last_market_status') and self.last_market_status != is_market_open:
                from config.settings import (
                    MARKET_OPEN_REFRESH_INTERVAL,
                    MARKET_CLOSED_REFRESH_INTERVAL
                )

                refresh_interval = (
                    MARKET_OPEN_REFRESH_INTERVAL if is_market_open
                    else MARKET_CLOSED_REFRESH_INTERVAL
                )

                self.periodic_task.set_interval(refresh_interval)
                logger.info(f"Market status changed, adjusted refresh interval to {refresh_interval}s")

            self.last_market_status = is_market_open

            # Analyze stocks
            logger.info(f"Updating analysis for {len(symbols)} symbols")
            results = self.analyzer.analyze_multiple_stocks(symbols)

            # Update cache
            for symbol, result in results.items():
                if "error" not in result:
                    cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}.json")
                    write_json_file(result, cache_file)
                    self.cache[symbol] = result

            self.last_update = datetime.now()
            logger.info(f"Analysis update completed at {self.last_update}")

        except Exception as e:
            logger.error(f"Error updating analysis: {str(e)}")

    def get_market_status(self) -> Dict[str, Any]:
        """
        Get current market status.

        Returns:
            Dictionary with market status information
        """
        is_open = self.market_data.is_market_open()

        return {
            "is_open": is_open,
            "status": "Open" if is_open else "Closed",
            "timestamp": get_timestamp()
        }

    def get_available_symbols(self) -> List[str]:
        """
        Get list of available symbols.

        Returns:
            List of available stock symbols
        """
        return DEFAULT_SYMBOLS

    def analyze_single_stock(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Analyze a single stock.

        Args:
            symbol: Stock symbol to analyze
            force_refresh: Force refresh analysis

        Returns:
            Analysis results
        """
        # Validate symbol
        if not validate_symbol(symbol):
            return {"error": f"Invalid symbol: {symbol}"}

        # Check cache if refresh not forced
        if not force_refresh:
            # Try memory cache first
            if symbol in self.cache:
                return self.cache[symbol]

            # Try file cache
            cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}.json")
            if os.path.exists(cache_file):
                result = read_json_file(cache_file)
                if result:
                    self.cache[symbol] = result
                    return result

        # Perform fresh analysis
        try:
            logger.info(f"Analyzing stock: {symbol}")
            result = self.analyzer.analyze_stock(symbol)

            # Update cache
            if "error" not in result:
                cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}.json")
                write_json_file(result, cache_file)
                self.cache[symbol] = result

            return result
        except Exception as e:
            logger.error(f"Error analyzing stock {symbol}: {str(e)}")
            return {"error": str(e)}

    def analyze_multiple_stocks(self, symbols: List[str], force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Analyze multiple stocks.

        Args:
            symbols: List of stock symbols to analyze
            force_refresh: Force refresh analysis

        Returns:
            Dictionary mapping symbols to their analysis results
        """
        # Validate symbols
        valid_symbols = validate_symbols_list(symbols)

        if not valid_symbols:
            return {"error": "No valid symbols provided"}

        results = {}

        for symbol in valid_symbols:
            results[symbol] = self.analyze_single_stock(symbol, force_refresh)

        return results

    def get_latest_analysis(self) -> Dict[str, Any]:
        """
        Get latest analysis results.

        Returns:
            Dictionary with latest analysis results
        """
        if not self.cache:
            # Try to load from cache files
            for symbol in DEFAULT_SYMBOLS:
                cache_file = os.path.join(self.cache_dir, f"{symbol.lower()}.json")
                if os.path.exists(cache_file):
                    result = read_json_file(cache_file)
                    if result:
                        self.cache[symbol] = result

        if not self.cache:
            return None

        return {
            "stocks": self.cache,
            "last_update": self.last_update.strftime("%Y-%m-%d %H:%M:%S") if self.last_update else None,
            "market_status": "Open" if self.market_data.is_market_open() else "Closed"
        }

    def get_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Get technical indicators for a stock.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with technical indicators
        """
        # Validate symbol
        if not validate_symbol(symbol):
            return None

        try:
            # Get market data
            market_data = self.market_data.get_market_data(symbol)

            if not market_data or "historical_data" not in market_data:
                return None

            # Calculate indicators
            from core.analysis.technical_indicators import TechnicalIndicators
            indicators = TechnicalIndicators(market_data["historical_data"])
            result = indicators.calculate_all_indicators()

            return result
        except Exception as e:
            logger.error(f"Error getting indicators for {symbol}: {str(e)}")
            return None

    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Get option chain for a stock.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with option chain data
        """
        # Validate symbol
        if not validate_symbol(symbol):
            return None

        try:
            # Fetch option chain
            option_chain = self.market_data.fetch_option_chain(symbol)

            if option_chain is None:
                return None

            # Convert to dictionary for API response
            result = option_chain.to_dict(orient="records")

            return result
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {str(e)}")
            return None

    def get_timestamp(self) -> str:
        """
        Get current timestamp.

        Returns:
            Formatted timestamp string
        """
        return get_timestamp()