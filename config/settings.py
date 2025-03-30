"""
Configuration settings for the Stock Analysis Application.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# API Keys and credentials
ZERODHA_API_KEY = os.getenv("ZERODHA_API_KEY")
ZERODHA_API_SECRET = os.getenv("ZERODHA_API_SECRET")
ZERODHA_USER_ID = os.getenv("ZERODHA_USER_ID")
ZERODHA_PASSWORD = os.getenv("ZERODHA_PASSWORD")

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() == "true"

# Output settings
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CSV_FILENAME = os.getenv("CSV_FILENAME", "stock_analysis.csv")
JSON_FILENAME = os.getenv("JSON_FILENAME", "stock_analysis.json")

# Market hours (IST)
MARKET_OPEN_HOUR = 9  # 9:00 AM
MARKET_OPEN_MINUTE = 15  # 9:15 AM
MARKET_CLOSE_HOUR = 15  # 3:00 PM
MARKET_CLOSE_MINUTE = 30  # 3:30 PM

# Data refresh settings
MARKET_OPEN_REFRESH_INTERVAL = int(os.getenv("MARKET_OPEN_REFRESH_INTERVAL", "60"))  # seconds
MARKET_CLOSED_REFRESH_INTERVAL = int(os.getenv("MARKET_CLOSED_REFRESH_INTERVAL", "3600"))  # seconds

# Analysis settings
VOLATILITY_WINDOW = 30  # days for volatility calculation
RSI_PERIOD = 14  # period for RSI calculation
MACD_FAST = 12  # fast period for MACD
MACD_SLOW = 26  # slow period for MACD
MACD_SIGNAL = 9  # signal period for MACD
ADX_PERIOD = 14  # period for ADX calculation
MOMENTUM_PERIOD = 10  # period for momentum calculation

# Position sizing settings
DEFAULT_RISK_PERCENTAGE = 2  # default risk percentage of account
MAX_POSITION_SIZE_PERCENTAGE = 10  # maximum position size as percentage of account

# Support and resistance calculations
SUPPORT_RESISTANCE_PERIODS = [30, 90, 180]  # periods for calculating support/resistance

# Parallel processing settings
MAX_THREADS = int(os.getenv("MAX_THREADS", "4"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

# Logging settings
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_ROTATION = "1 day"
LOG_RETENTION = "1 month"

# Default watchlist if none provided
DEFAULT_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "SBIN", "HDFC", "HINDUNILVR", "BHARTIARTL", "ITC"
]

# Create directories if they don't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)