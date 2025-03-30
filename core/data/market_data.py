"""
Market data fetching module for stock analysis application.
"""
import datetime
import time
import os
from typing import Dict, List, Optional, Tuple, Union, Any

import numpy as np
import pandas as pd
from kiteconnect import KiteConnect
from loguru import logger

from config.settings import (
    DEFAULT_SYMBOLS,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    VOLATILITY_WINDOW
)
from core.auth.zerodha_auth import ZerodhaAuth


class MarketData:
    """
    Responsible for fetching and processing market data from Zerodha Kite API.

    Features:
    - Check market status (open/closed)
    - Fetch historical data for analysis
    - Fetch live market data when market is open
    - Process and prepare data for analysis
    """

    # Class attribute to track last historical data request time
    _last_historical_request = 0

    def __init__(self, symbols: Optional[List[str]] = None):
        """
        Initialize the MarketData class.

        Args:
            symbols: List of stock symbols to analyze. If None, uses default list.
        """
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.zerodha_auth = ZerodhaAuth()
        self.historical_data_cache = {}
        self.live_data_cache = {}
        self.last_update_time = None

        logger.info(f"Market data module initialized with {len(self.symbols)} symbols")

    def is_market_open(self) -> bool:
        """
        Check if the market is currently open.

        Returns:
            bool: True if market is open, False otherwise
        """
        now = datetime.datetime.now()

        # Check if it's a weekday (0 = Monday, 6 = Sunday)
        if now.weekday() > 4:  # Saturday or Sunday
            logger.info("Market closed: Weekend")
            return False

        # Check if it's within market hours
        market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
        market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)

        if market_open <= now <= market_close:
            return True
        else:
            reason = "before opening" if now < market_open else "after closing"
            logger.info(f"Market closed: {reason}")
            return False

    def get_kite_client(self) -> Tuple[Optional[KiteConnect], Optional[str]]:
        """
        Get an authenticated Kite client.

        Returns:
            Tuple containing KiteConnect client and error message if any
        """
        return self.zerodha_auth.get_kite_client()

    def get_instrument_tokens(self) -> Dict[str, int]:
        """
        Get instrument tokens for the symbols.

        Returns:
            Dict mapping symbol to instrument token
        """
        kite, error = self.get_kite_client()
        if error:
            logger.error(f"Failed to get kite client: {error}")
            return {}

        try:
            instruments = kite.instruments("NSE")
            token_map = {}

            for symbol in self.symbols:
                for instrument in instruments:
                    if instrument["tradingsymbol"] == symbol:
                        token_map[symbol] = instrument["instrument_token"]
                        break

            if len(token_map) != len(self.symbols):
                missing = set(self.symbols) - set(token_map.keys())
                logger.warning(f"Could not find instrument tokens for symbols: {missing}")

            return token_map
        except Exception as e:
            logger.error(f"Error fetching instrument tokens: {str(e)}")
            return {}

    def fetch_historical_data(self, symbol: str, interval: str = "day", days: int = 365) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a symbol.

        Args:
            symbol: Stock symbol
            interval: Data interval (minute, day, etc.)
            days: Number of days of historical data

        Returns:
            DataFrame with historical data or None if fetch fails
        """
        kite, error = self.get_kite_client()
        if error:
            logger.error(f"Failed to get kite client: {error}")
            return None

        # Calculate from and to dates
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(days=days)

        try:
            # Get instrument token
            instruments = kite.instruments("NSE")
            instrument_token = None

            for instrument in instruments:
                if instrument["tradingsymbol"] == symbol:
                    instrument_token = instrument["instrument_token"]
                    break

            if not instrument_token:
                logger.error(f"Could not find instrument token for {symbol}")
                return None

            # Fetch historical data
            data = kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
                interval=interval
            )

            if not data:
                logger.error(f"No historical data returned for {symbol}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(data)
            df.set_index("date", inplace=True)

            # Cache the data
            self.historical_data_cache[symbol] = df

            logger.info(f"Successfully fetched historical data for {symbol}: {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return None

    # Update this method in market_data.py

    def fetch_historical_data_rate_limited(self, symbol: str, interval: str = "day", days: int = 365) -> Optional[
        pd.DataFrame]:
        """
        Fetch historical data with proper rate limiting.

        Zerodha restricts historical data API to 3 requests per minute.
        This implementation uses 1 request per minute to be more conservative.

        Args:
            symbol: Stock symbol
            interval: Data interval (minute, day, etc.)
            days: Number of days of historical data

        Returns:
            DataFrame with historical data or None if fetch fails
        """
        # Check cache first
        cache_dir = os.path.join("output", "historical_cache")
        os.makedirs(cache_dir, exist_ok=True)

        cache_file = os.path.join(cache_dir, f"{symbol.lower()}_historical.pkl")

        # Try to load from cache first
        if os.path.exists(cache_file):
            try:
                logger.info(f"Loading cached historical data for {symbol}")
                df = pd.read_pickle(cache_file)
                logger.info(f"Successfully loaded cached historical data for {symbol}: {len(df)} records")
                return df
            except Exception as e:
                logger.warning(f"Could not load cached data for {symbol}: {e}")

        # Get current time
        current_time = time.time()

        # Calculate time since last request - using class variable
        time_since_last_request = current_time - self.__class__._last_historical_request

        # Wait if needed to respect the rate limits - conservative approach: 1 request per minute
        if time_since_last_request < 60:  # 60 seconds = 1 minute
            wait_time = 60 - time_since_last_request
            logger.info(f"Rate limiting: Waiting {wait_time:.2f}s before historical data request")
            time.sleep(wait_time)

        # Update the last request time
        self.__class__._last_historical_request = time.time()

        # Make the request with retry logic
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Fetching historical data for {symbol} (attempt {attempt}/{max_retries})")

                # Fetch historical data
                kite, error = self.get_kite_client()
                if error:
                    logger.error(f"Failed to get kite client: {error}")
                    return None

                # Calculate from and to dates
                to_date = datetime.datetime.now()
                from_date = to_date - datetime.timedelta(days=days)

                # Get instrument token
                instruments = kite.instruments("NSE")
                instrument_token = None

                for instrument in instruments:
                    if instrument["tradingsymbol"] == symbol:
                        instrument_token = instrument["instrument_token"]
                        break

                if not instrument_token:
                    logger.error(f"Could not find instrument token for {symbol}")
                    return None

                # Fetch historical data
                data = kite.historical_data(
                    instrument_token=instrument_token,
                    from_date=from_date.strftime("%Y-%m-%d"),
                    to_date=to_date.strftime("%Y-%m-%d"),
                    interval=interval
                )

                if not data:
                    logger.error(f"No historical data returned for {symbol}")
                    return None

                # Convert to DataFrame
                df = pd.DataFrame(data)
                df.set_index("date", inplace=True)

                # Cache the data
                try:
                    df.to_pickle(cache_file)
                    logger.info(f"Cached historical data for {symbol}")
                except Exception as e:
                    logger.warning(f"Failed to cache historical data: {e}")

                # Also add to in-memory cache
                self.historical_data_cache[symbol] = df

                logger.info(f"Successfully fetched historical data for {symbol}: {len(df)} records")
                return df

            except Exception as e:
                error_message = str(e)
                logger.error(f"Error fetching historical data for {symbol}: {error_message}")

                # If rate limited, wait longer before retry
                if "too many requests" in error_message.lower() or "rate limit" in error_message.lower():
                    if attempt < max_retries:
                        # Exponential backoff - wait longer with each retry
                        wait_time = 60 * (2 ** attempt)  # 2min, 4min, 8min
                        logger.warning(f"Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")

                        # Update the class variable to prevent other requests during this wait
                        self.__class__._last_historical_request = time.time() + wait_time - 60

                        time.sleep(wait_time)
                        continue

                # For other errors or if we've exhausted retries
                return None

    def fetch_live_market_data(self) -> Dict[str, Dict]:
        """
        Fetch live market data for all symbols.

        Returns:
            Dictionary mapping symbols to their market data
        """
        kite, error = self.get_kite_client()
        if error:
            logger.error(f"Failed to get kite client: {error}")
            return {}

        # Get instrument tokens
        token_map = self.get_instrument_tokens()
        if not token_map:
            logger.error("No instrument tokens available")
            return {}

        try:
            # Fetch quotes for all symbols
            quotes = kite.quote(list(token_map.keys()))

            # Process and store the data
            result = {}
            for symbol, data in quotes.items():
                result[symbol] = {
                    "symbol": symbol,
                    "previous_close": data["ohlc"]["close"],
                    "current_price": data["last_price"],
                    "volume": data["volume"],
                    "timestamp": data["timestamp"]
                }

            self.live_data_cache = result
            self.last_update_time = datetime.datetime.now()

            logger.info(f"Successfully fetched live market data for {len(result)} symbols")
            return result

        except Exception as e:
            logger.error(f"Error fetching live market data: {str(e)}")
            return {}

    def fetch_option_chain(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch option chain data for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            DataFrame with option chain data or None if fetch fails
        """
        kite, error = self.get_kite_client()
        if error:
            logger.error(f"Failed to get kite client: {error}")
            return None

        try:
            # First get the instrument token for the symbol
            instruments = kite.instruments("NFO")

            # Filter instruments for the given symbol and current expiry
            now = datetime.datetime.now()
            current_month = now.strftime("%b").upper()
            next_month = (now + datetime.timedelta(days=32)).strftime("%b").upper()

            # Look for current month expiry options first, then next month
            option_instruments = []

            for expiry in [current_month, next_month]:
                filtered = [
                    inst for inst in instruments
                    if symbol in inst["tradingsymbol"] and expiry in inst["tradingsymbol"]
                ]

                if filtered:
                    option_instruments = filtered
                    break

            if not option_instruments:
                logger.error(f"No option instruments found for {symbol}")
                return None

            # Extract CE and PE options
            call_options = [inst for inst in option_instruments if inst["tradingsymbol"].endswith("CE")]
            put_options = [inst for inst in option_instruments if inst["tradingsymbol"].endswith("PE")]

            # Fetch quotes for all options
            call_tokens = [opt["instrument_token"] for opt in call_options]
            put_tokens = [opt["instrument_token"] for opt in put_options]

            call_quotes = kite.quote(call_tokens) if call_tokens else {}
            put_quotes = kite.quote(put_tokens) if put_tokens else {}

            # Prepare data for DataFrame
            option_data = []

            # Process call options
            for opt in call_options:
                strike_price = self._extract_strike_price(opt["tradingsymbol"])
                quote = call_quotes.get(str(opt["instrument_token"]), {})

                if quote:
                    option_data.append({
                        "symbol": symbol,
                        "expiry": self._extract_expiry(opt["tradingsymbol"]),
                        "strike": strike_price,
                        "type": "CE",
                        "last_price": quote.get("last_price", 0),
                        "volume": quote.get("volume", 0),
                        "open_interest": quote.get("oi", 0),
                        "iv": self._calculate_implied_volatility(quote, strike_price, "CE"),
                        "delta": None,  # Would need additional calculation
                        "full_symbol": opt["tradingsymbol"]
                    })

            # Process put options
            for opt in put_options:
                strike_price = self._extract_strike_price(opt["tradingsymbol"])
                quote = put_quotes.get(str(opt["instrument_token"]), {})

                if quote:
                    option_data.append({
                        "symbol": symbol,
                        "expiry": self._extract_expiry(opt["tradingsymbol"]),
                        "strike": strike_price,
                        "type": "PE",
                        "last_price": quote.get("last_price", 0),
                        "volume": quote.get("volume", 0),
                        "open_interest": quote.get("oi", 0),
                        "iv": self._calculate_implied_volatility(quote, strike_price, "PE"),
                        "delta": None,  # Would need additional calculation
                        "full_symbol": opt["tradingsymbol"]
                    })

            # Convert to DataFrame
            df = pd.DataFrame(option_data)

            if df.empty:
                logger.warning(f"Option chain for {symbol} is empty")
                return None

            logger.info(f"Successfully fetched option chain for {symbol}: {len(df)} options")
            return df

        except Exception as e:
            logger.error(f"Error fetching option chain for {symbol}: {str(e)}")
            return None

    def _extract_strike_price(self, tradingsymbol: str) -> float:
        """Extract strike price from trading symbol."""
        try:
            # Remove PE or CE suffix
            if tradingsymbol.endswith("PE") or tradingsymbol.endswith("CE"):
                tradingsymbol = tradingsymbol[:-2]

            # The last numeric part should be the strike price
            strike_part = ""
            for char in reversed(tradingsymbol):
                if char.isdigit():
                    strike_part = char + strike_part
                else:
                    break

            if strike_part:
                return float(strike_part)
            return 0
        except Exception:
            return 0

    def _extract_expiry(self, tradingsymbol: str) -> str:
        """Extract expiry date from trading symbol."""
        # This is a simplified version - actual extraction would depend on symbol format
        if tradingsymbol.endswith("PE") or tradingsymbol.endswith("CE"):
            # Remove the option type
            tradingsymbol = tradingsymbol[:-2]

        # Try to extract month code (e.g., APR, MAY, JUN)
        months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                 "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

        for month in months:
            if month in tradingsymbol:
                return month

        return "Unknown"

    def _calculate_implied_volatility(self, quote: Dict, strike_price: float, option_type: str) -> float:
        """
        Calculate implied volatility (simplified).

        This is a placeholder - real IV calculation requires option pricing models
        """
        # In a real implementation, this would use Black-Scholes or other models
        # For now, return a random value as a placeholder
        return round(np.random.uniform(15, 45), 2)

    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get comprehensive market data for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with market data for the symbol
        """
        # Check if we need to fetch live data or use historical
        is_market_open = self.is_market_open()
        logger.info(f"Market status: {'Open' if is_market_open else 'Closed'}")

        # Get historical data for analysis regardless of market status
        # Use rate-limited version
        historical_df = self.fetch_historical_data_rate_limited(symbol)

        # If historical data fetch/load failed
        if historical_df is None or historical_df.empty:
            logger.error(f"Failed to get historical data for {symbol}")
            return {}

        # If market is open, get live data, otherwise use the latest historical data
        if is_market_open:
            try:
                logger.info(f"Market is open, fetching minimal live data for {symbol}")
                current_price = self._get_current_price(symbol)

                if current_price is None:
                    logger.warning(f"Using historical close price for {symbol}")
                    current_price = historical_df.iloc[-1]["close"]

                volume = historical_df.iloc[-1]["volume"]
            except Exception as e:
                logger.warning(f"Error fetching live data, using historical: {e}")
                current_price = historical_df.iloc[-1]["close"]
                volume = historical_df.iloc[-1]["volume"]
        else:
            logger.info(f"Market is closed, using historical data for {symbol}")
            current_price = historical_df.iloc[-1]["close"]
            volume = historical_df.iloc[-1]["volume"]

        # Get previous close
        previous_close = historical_df.iloc[-2]["close"] if historical_df is not None and len(historical_df) > 1 else None

        # Calculate volatility
        volatility = self._calculate_volatility(historical_df) if historical_df is not None else None

        # Skip option chain to reduce API calls
        logger.info(f"Skipping option chain fetch for {symbol} to avoid rate limits")
        option_chain = None

        # Compile all data
        result = {
            "symbol": symbol,
            "previous_close": previous_close,
            "current_price": current_price,
            "volatility_percent": volatility,
            "market_status": "Open" if is_market_open else "Closed",
            "last_update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "historical_data": historical_df,
            "option_chain": option_chain,
            "volume": volume,
            "volume_change_percent": self._calculate_volume_change(historical_df) if historical_df is not None else None,
        }

        return result

    def get_market_data_with_rate_limits(self, symbol: str, historical_delay: float = 0.5, other_delay: float = 0.2) -> Dict[str, Any]:
        """
        Get comprehensive market data for a symbol with rate limiting.

        Args:
            symbol: Stock symbol
            historical_delay: Delay in seconds after historical data API calls
            other_delay: Delay in seconds after other API calls

        Returns:
            Dictionary with market data for the symbol
        """
        # Using the rate-limited fetch for historical data
        logger.info(f"Fetching market data with rate limits for {symbol}")

        # Check market status
        logger.info(f"Checking market status for {symbol}")
        is_market_open = self.is_market_open()
        logger.info(f"Market status: {'Open' if is_market_open else 'Closed'}")

        # Add delay after market status check
        time.sleep(other_delay)

        # Get historical data using rate-limited version
        logger.info(f"Fetching historical data for {symbol} (rate-limited)")
        historical_df = self.fetch_historical_data_rate_limited(symbol)

        # If historical data fetch/load failed
        if historical_df is None or historical_df.empty:
            logger.error(f"Failed to get historical data for {symbol}")
            return {}

        # If market is open, get minimal live data, otherwise use historical
        if is_market_open:
            time.sleep(other_delay)  # Add delay before API call

            try:
                logger.info(f"Market is open, fetching minimal live data for {symbol}")
                current_price = self._get_current_price(symbol)
                time.sleep(other_delay)  # Add delay after API call
            except Exception as e:
                logger.warning(f"Error fetching live data: {str(e)}")
                current_price = None

            if current_price is None:
                logger.warning(f"Using historical close price for {symbol}")
                current_price = historical_df.iloc[-1]["close"]

            volume = historical_df.iloc[-1]["volume"]
        else:
            logger.info(f"Market is closed, using historical data for {symbol}")
            current_price = historical_df.iloc[-1]["close"]
            volume = historical_df.iloc[-1]["volume"]

        # Get previous close
        previous_close = historical_df.iloc[-2]["close"] if historical_df is not None and len(historical_df) > 1 else None

        # Calculate volatility
        volatility = self._calculate_volatility(historical_df) if historical_df is not None else None

        # Skip option chain to reduce API calls
        logger.info(f"Skipping option chain fetch for {symbol} to avoid rate limits")
        option_chain = None

        # Compile all data
        result = {
            "symbol": symbol,
            "previous_close": previous_close,
            "current_price": current_price,
            "volatility_percent": volatility,
            "market_status": "Open" if is_market_open else "Closed",
            "last_update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "historical_data": historical_df,
            "option_chain": option_chain,
            "volume": volume,
            "volume_change_percent": self._calculate_volume_change(historical_df) if historical_df is not None else None,
        }

        logger.info(f"Market data fetch completed for {symbol}")
        return result

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch only the current price for a symbol to minimize API calls.

        Args:
            symbol: Stock symbol

        Returns:
            Current price or None if fetch fails
        """
        try:
            kite, error = self.get_kite_client()
            if error:
                logger.error(f"Failed to get kite client: {error}")
                return None

            # Get quote for single symbol
            quote = kite.quote([symbol])
            if not quote or symbol not in quote:
                return None

            return quote[symbol]["last_price"]
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {str(e)}")
            return None

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """
        Calculate historical volatility.

        Args:
            df: DataFrame with historical data

        Returns:
            Annualized volatility as a percentage
        """
        if df is None or len(df) < VOLATILITY_WINDOW:
            return None

        # Calculate daily returns
        df = df.copy()
        df["returns"] = df["close"].pct_change()

        # Calculate volatility (standard deviation of returns)
        volatility = df["returns"].iloc[-VOLATILITY_WINDOW:].std()

        # Annualize the volatility (multiply by sqrt of trading days in a year)
        annualized_volatility = volatility * (252 ** 0.5)

        # Return as percentage
        return round(annualized_volatility * 100, 2)

    def _calculate_volume_change(self, df: pd.DataFrame) -> float:
        """
        Calculate volume change percentage.

        Args:
            df: DataFrame with historical data

        Returns:
            Volume change percentage
        """
        if df is None or len(df) < 2:
            return None

        current_volume = df.iloc[-1]["volume"]
        previous_volume = df.iloc[-2]["volume"]

        if previous_volume == 0:
            return None

        return round(((current_volume - previous_volume) / previous_volume) * 100, 2)