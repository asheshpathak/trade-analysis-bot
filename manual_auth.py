"""
Fallback manual authentication module for Zerodha.
"""
import time
import threading
import webbrowser
from typing import Dict, Optional, Tuple

from kiteconnect import KiteConnect
from loguru import logger

from config.settings import (
    ZERODHA_API_KEY,
    ZERODHA_API_SECRET,
)


class ZerodhaAuth:
    """
    Handles authentication with Zerodha Kite API using manual token entry.
    For use as a fallback when the token server fails.
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

        self.kite = KiteConnect(api_key=self.api_key)
        self.access_token = None
        self.token_expiry = None
        self.refresh_lock = threading.Lock()

        self._initialized = True
        logger.info("Manual Zerodha authentication module initialized")

    def manual_login(self) -> Tuple[bool, Optional[str]]:
        """
        Perform manual login process with user input for request token.

        Returns:
            Tuple[bool, Optional[str]]: Success status and error message if any
        """
        try:
            # Generate and print the login URL
            login_url = self.kite.login_url()

            print("\n==== MANUAL ZERODHA AUTHENTICATION ====")
            print(f"\nStep 1: Please visit this URL in your browser to log in to Zerodha:")
            print(f"\n{login_url}\n")

            # Try to open the browser automatically
            try:
                webbrowser.open(login_url)
                print("A browser window should have opened. If not, please copy and paste the URL manually.")
            except:
                pass

            print("\nStep 2: After successful login, you'll be redirected to a page that cannot be reached.")
            print("        That's expected! Look at the URL in your browser's address bar.")
            print("        It should look like: https://localhost:5000/redirect?request_token=XXXXXX&action=login")
            print("\nStep 3: Copy the request_token value from the URL (the part after request_token= and before &action)")

            # Prompt user for the request token
            request_token = input("\nEnter the request token: ").strip()

            if not request_token:
                return False, "No request token provided"

            # Generate session
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data["access_token"]

            # Set the access token in the kite connect instance
            self.kite.set_access_token(self.access_token)

            # Set token expiry (typically valid for a day)
            current_time = time.time()
            self.token_expiry = current_time + (24 * 3600)

            print(f"\nAuthentication successful! Access token will expire in 24 hours.")
            logger.info("Successfully generated Zerodha API session")

            return True, None

        except Exception as e:
            error_msg = f"Failed to generate Zerodha API session: {str(e)}"
            logger.error(error_msg)
            return False, error_msg