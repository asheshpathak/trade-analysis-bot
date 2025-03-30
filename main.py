"""
Main entry point for stock analysis application with rate limit compliance.
"""
import argparse
import sys
import os
import threading
import time
from typing import List, Optional
import random
from tqdm import tqdm

import uvicorn
import json
import datetime
from fastapi import FastAPI
from loguru import logger

from config.logging_config import setup_logging
from config.settings import (
    API_HOST,
    API_PORT,
    API_DEBUG,
    DEFAULT_SYMBOLS
)
from core.analysis.stock_analyzer import StockAnalyzer
from core.output.csv_generator import CSVGenerator
from core.output.json_generator import JSONGenerator
from api.middleware import setup_middlewares
from api.routes import router as api_router
from utils.concurrency import PeriodicTask


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="Stock Analysis API",
        description="API for stock analysis and technical indicators",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # Setup middlewares
    setup_middlewares(app)

    # Include API routes
    app.include_router(api_router)

    return app


def run_api_server():
    """Run the API server."""
    app = create_app()

    logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info")


def run_analysis(
        symbols: List[str],
        output_csv: bool = True,
        output_json: bool = True,
        historical_delay: float = 0.5,  # Delay for historical data API
        other_delay: float = 0.2,  # Delay for other API calls
        retry_delay: float = 60.0,  # Delay when rate limit is hit
        max_retries: int = 3  # Maximum number of retries
):
    """
    Run stock analysis for specified symbols sequentially to respect API rate limits.

    Args:
        symbols: List of stock symbols to analyze
        output_csv: Generate CSV output
        output_json: Generate JSON output
        historical_delay: Delay in seconds after historical data API calls
        other_delay: Delay in seconds after other API calls
        retry_delay: Delay in seconds when rate limit is hit
        max_retries: Maximum number of retries for rate-limited requests
    """
    try:
        # Initialize analyzer
        analyzer = StockAnalyzer()

        # Prepare for results
        all_results = {}
        total_symbols = len(symbols)
        successful_count = 0
        rate_limited_count = 0
        other_error_count = 0

        logger.info(f"Analyzing {total_symbols} stocks sequentially with rate limiting...")
        logger.info(
            f"Using historical_delay={historical_delay}s, other_delay={other_delay}s, retry_delay={retry_delay}s")

        # Create cache directory if it doesn't exist
        os.makedirs(os.path.join("output", "cache"), exist_ok=True)
        os.makedirs(os.path.join("output", "historical_cache"), exist_ok=True)

        # Sequential processing with progress bar
        with tqdm(total=total_symbols, desc="Analyzing stocks") as pbar:
            for i, symbol in enumerate(symbols):
                logger.info(f"Starting analysis for {symbol} ({i + 1}/{total_symbols})")

                # Add delay before each symbol
                if i > 0:
                    pause_time = 5  # 5 seconds between symbols
                    logger.info(f"Waiting {pause_time}s before starting next symbol...")
                    time.sleep(pause_time)

                # Check if we already have results for this symbol from a previous run
                result_cache_file = os.path.join("output", "cache", f"{symbol.lower()}.json")
                if os.path.exists(result_cache_file):
                    try:
                        with open(result_cache_file, 'r') as f:
                            cached_result = json.load(f)

                        # Check if result is from today
                        if "analysis_timestamp" in cached_result:
                            timestamp = cached_result["analysis_timestamp"]
                            try:
                                analysis_date = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").date()
                                today = datetime.datetime.now().date()

                                if analysis_date == today:
                                    logger.info(f"Using cached analysis for {symbol} from today")
                                    all_results[symbol] = cached_result
                                    successful_count += 1
                                    pbar.update(1)
                                    logger.info(
                                        f"Completed {i + 1}/{total_symbols} symbols. {total_symbols - (i + 1)} remaining.")
                                    continue
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning(f"Could not load cached result for {symbol}: {e}")

                # Attempt analysis with retries
                retry_count = 0
                current_retry_delay = retry_delay

                while retry_count <= max_retries:
                    try:
                        # Analyze the stock with specified delays
                        result = analyzer.analyze_stock_with_rate_limits(
                            symbol,
                            historical_delay=historical_delay,
                            other_delay=other_delay
                        )

                        # Store result
                        all_results[symbol] = result

                        # Check if successful
                        if "error" not in result:
                            successful_count += 1
                            logger.info(f"Successfully analyzed {symbol}")
                            break  # Break retry loop on success
                        else:
                            if "rate limit" in result["error"].lower() or "too many requests" in result[
                                "error"].lower():
                                rate_limited_count += 1
                                logger.warning(
                                    f"Rate limit hit for {symbol}, retrying after delay of {current_retry_delay}s")
                                time.sleep(current_retry_delay)
                                # Increase delay for next retry
                                current_retry_delay *= 2  # Exponential backoff
                                retry_count += 1
                                continue
                            else:
                                other_error_count += 1
                                logger.error(f"Error analyzing {symbol}: {result['error']}")
                                break  # Break on non-rate-limit error

                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error analyzing {symbol}: {error_msg}")

                        # Check if it's a rate limit error
                        if "too many requests" in error_msg.lower() or "rate limit" in error_msg.lower():
                            rate_limited_count += 1
                            if retry_count < max_retries:
                                logger.warning(
                                    f"Rate limit hit for {symbol}, retrying after delay of {current_retry_delay}s ({retry_count + 1}/{max_retries})")
                                time.sleep(current_retry_delay)
                                current_retry_delay *= 2  # Exponential backoff
                                retry_count += 1
                                continue

                        # Non-rate limit error or max retries reached
                        all_results[symbol] = {"error": error_msg}
                        other_error_count += 1
                        break

                # Update progress
                pbar.update(1)

                # Log progress
                remaining = total_symbols - (i + 1)
                if remaining > 0:
                    logger.info(f"Completed {i + 1}/{total_symbols} symbols. {remaining} remaining.")

        # Show summary
        logger.info(f"Analysis summary:")
        logger.info(f"  Total symbols: {total_symbols}")
        logger.info(f"  Successfully analyzed: {successful_count}")
        logger.info(f"  Rate limit errors: {rate_limited_count}")
        logger.info(f"  Other errors: {other_error_count}")

        # Generate outputs
        if output_csv:
            csv_generator = CSVGenerator()
            csv_file = csv_generator.generate_csv(all_results)
            logger.info(f"CSV output saved to: {csv_file}")

        if output_json:
            json_generator = JSONGenerator()
            json_file = json_generator.generate_json(all_results)
            logger.info(f"JSON output saved to: {json_file}")

        logger.info("Analysis completed")

    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        sys.exit(1)


def setup_periodic_analysis(symbols: List[str], interval: int):
    """
    Setup periodic analysis.

    Args:
        symbols: List of stock symbols to analyze
        interval: Update interval in seconds
    """

    # Define update task
    def update_task():
        run_analysis(symbols)

    # Create and start periodic task
    periodic_task = PeriodicTask(update_task, interval)
    periodic_task.start()

    logger.info(f"Periodic analysis setup with interval {interval}s")

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping periodic analysis")
        periodic_task.stop()


def load_symbols_from_file(file_path: str) -> List[str]:
    """
    Load stock symbols from a file.

    Args:
        file_path: Path to the file containing symbols

    Returns:
        List of stock symbols
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read().strip()

            # Handle different possible formats
            if ',' in content:
                # Comma-separated format
                symbols_with_prefixes = content.split(',')
            else:
                # Line-by-line format
                symbols_with_prefixes = content.splitlines()

            # Process the symbols
            symbols = []
            for sym in symbols_with_prefixes:
                sym = sym.strip()
                if not sym:
                    continue

                # Handle exchange prefixes
                if ':' in sym:
                    sym = sym.split(':')[1]

                # Handle suffixes like -EQ
                if '-' in sym:
                    sym = sym.split('-')[0]

                symbols.append(sym)

            logger.info(f"Loaded {len(symbols)} symbols from {file_path}")
            return symbols

    except Exception as e:
        logger.error(f"Error reading symbols file {file_path}: {str(e)}")
        return []


def parse_arguments():
    """
    Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Stock Analysis Application")

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--api",
        action="store_true",
        help="Run as API server"
    )
    mode_group.add_argument(
        "--analyze",
        action="store_true",
        help="Run analysis once"
    )
    mode_group.add_argument(
        "--periodic",
        action="store_true",
        help="Run periodic analysis"
    )

    # Symbols to analyze
    symbols_group = parser.add_mutually_exclusive_group()
    symbols_group.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help="Stock symbols to analyze"
    )
    symbols_group.add_argument(
        "--symbols-file",
        type=str,
        help="Path to file containing list of stock symbols"
    )

    # Output options
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Disable CSV output"
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Disable JSON output"
    )

    # Analysis options
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of symbols to analyze"
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Skip the first N symbols"
    )
    parser.add_argument(
        "--historical-delay",
        type=float,
        default=0.5,
        help="Delay after historical data API calls in seconds"
    )
    parser.add_argument(
        "--other-delay",
        type=float,
        default=0.2,
        help="Delay after other API calls in seconds"
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=60.0,
        help="Delay when rate limit is hit in seconds"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for rate-limited requests"
    )

    # Periodic analysis interval
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Update interval in seconds for periodic analysis"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    # Setup logging
    setup_logging()

    # Parse command line arguments
    args = parse_arguments()

    # Determine the symbols to analyze
    symbols = args.symbols
    if args.symbols_file:
        symbols = load_symbols_from_file(args.symbols_file)
        if not symbols:
            logger.error("No valid symbols found in the provided file")
            sys.exit(1)

    # Apply skip and limit if specified
    if args.skip > 0:
        if args.skip >= len(symbols):
            logger.error(f"Skip value ({args.skip}) is greater than or equal to the number of symbols ({len(symbols)})")
            sys.exit(1)
        logger.info(f"Skipping first {args.skip} symbols")
        symbols = symbols[args.skip:]

    # Apply limit if specified
    if args.limit and args.limit > 0 and args.limit < len(symbols):
        logger.info(f"Limiting analysis to {args.limit} symbols out of {len(symbols)}")
        symbols = symbols[:args.limit]

    # Run in appropriate mode
    if args.api:
        run_api_server()
    elif args.analyze:
        run_analysis(
            symbols,
            not args.no_csv,
            not args.no_json,
            args.historical_delay,
            args.other_delay,
            args.retry_delay,
            args.max_retries
        )
    elif args.periodic:
        setup_periodic_analysis(
            symbols,
            args.interval
        )


if __name__ == "__main__":
    main()