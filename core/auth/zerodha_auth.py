"""
Zerodha Kite API authentication module with simplified authentication.
"""
import time
from typing import Dict, Optional, Tuple
import threading

import requests
from kiteconnect import KiteConnect
from loguru import logger

from config.settings import (
    ZERODHA_API_KEY,
    ZERODHA_API_SECRET,
    ZERODHA_USER_ID,
    ZERODHA_PASSWORD,
)


class ZerodhaAuth:
    """
    Handles authentication with Zerodha Kite API.

    This class manages:
    - Initial login and access token generation
    - Token refresh when expired
    - Singleton pattern to ensure only one instance exists
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ZerodhaAuth, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.api_key = ZERODHA_API_KEY
        self.api_secret = ZERODHA_API_SECRET
        self.user_id = ZERODHA_USER_ID
        self.password = ZERODHA_PASSWORD

        self.kite = KiteConnect(api_key=self.api_key)
        self.access_token = None
        self.token_expiry = None
        self.refresh_in_progress = False
        self.refresh_lock = threading.Lock()

        # Validate required config
        self._validate_config()

        # Initialize connection on startup
        self._initialized = True
        logger.info("Zerodha authentication module initialized")

    def _validate_config(self) -> None:
        """Validate that all required configuration values are present."""
        missing_configs = []

        if not self.api_key:
            missing_configs.append("ZERODHA_API_KEY")
        if not self.api_secret:
            missing_configs.append("ZERODHA_API_SECRET")
        if not self.user_id:
            missing_configs.append("ZERODHA_USER_ID")
        if not self.password:
            missing_configs.append("ZERODHA_PASSWORD")

        if missing_configs:
            error_msg = f"Missing required Zerodha API configuration: {', '.join(missing_configs)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _login(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Login to Zerodha and obtain request token.

        Returns:
            Tuple[bool, Optional[str], Optional[str]]: Success status, request token, and error message if any
        """
        try:
            # In a real implementation, this would use the Zerodha login API
            # For now, we'll simulate the login and request token generation

            logger.info(f"Attempting login for user {self.user_id}")

            # Simulate a login API call
            login_url = "https://kite.zerodha.com/api/login"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {
                "user_id": self.user_id,
                "password": self.password
            }

            # Note: In a real implementation, we would make an actual API call
            # response = requests.post(login_url, headers=headers, data=data)
            # Here we're just simulating the flow without making real API calls

            # For demonstration purposes, generate a dummy request token
            request_token = f"demo_request_token_{int(time.time())}"

            logger.info(f"Login successful, obtained request token")
            return True, request_token, None

        except Exception as e:
            error_msg = f"Login failed with exception: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def _generate_session(self) -> Tuple[bool, Optional[str]]:
        """
        Generate a new session with access token.

        Returns:
            Tuple[bool, Optional[str]]: Success status and error message if any
        """
        try:
            logger.info("Generating new Zerodha API session")

            # First perform login to get request token
            login_success, request_token, login_error = self._login()
            if not login_success:
                return False, login_error

            # In a real implementation, we would exchange the request token for an access token
            # For demonstration purposes, we'll simulate this step

            # Simulate session token generation
            # In a real application: session = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = f"demo_access_token_{int(time.time())}"

            # Set the access token in the kite connect instance
            self.kite.set_access_token(self.access_token)

            # Set token expiry (for simulation, set to 24 hours)
            current_time = time.time()
            self.token_expiry = current_time + (24 * 3600)

            logger.info("Successfully generated Zerodha API session")
            return True, None

        except Exception as e:
            error_msg = f"Failed to generate Zerodha API session: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def _is_token_valid(self) -> bool:
        """Check if the current token is still valid."""
        if not self.access_token or not self.token_expiry:
            return False

        # Add a buffer of 5 minutes
        buffer = 5 * 60
        return time.time() < (self.token_expiry - buffer)

    def get_kite_client(self) -> Tuple[Optional[KiteConnect], Optional[str]]:
        """
        Get an authenticated Kite client instance.

        Returns:
            Tuple[Optional[KiteConnect], Optional[str]]: KiteConnect instance and error message if any
        """
        with self.refresh_lock:
            # Check if token needs refresh
            if not self._is_token_valid():
                # Token expired, generate a new session
                success, error = self._generate_session()
                if not success:
                    return None, error

            return self.kite, None

    def refresh_token(self) -> Tuple[bool, Optional[str]]:
        """
        Force a token refresh regardless of current state.

        Returns:
            Tuple[bool, Optional[str]]: Success status and error message if any
        """
        with self.refresh_lock:
            self.access_token = None
            self.token_expiry = None
            return self._generate_session()