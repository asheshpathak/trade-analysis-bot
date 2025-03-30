"""
Main entry point for stock analysis application.
"""
import argparse
import sys
import os
import threading
import time
from typing import List, Optional

import uvicorn
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


def run_analysis(symbols: List[str], output_csv: bool = True, output_json: bool = True):
    """
    Run stock analysis for specified symbols.

    Args:
        symbols: List of stock symbols to analyze
        output_csv: Generate CSV output
        output_json: Generate JSON output
    """
    try:
        # Initialize analyzer
        analyzer = StockAnalyzer()

        # Analyze stocks
        logger.info(f"Analyzing {len(symbols)} stocks...")
        results = analyzer.analyze_multiple_stocks(symbols)

        # Generate outputs
        if output_csv:
            csv_generator = CSVGenerator()
            csv_file = csv_generator.generate_csv(results)
            logger.info(f"CSV output saved to: {csv_file}")

        if output_json:
            json_generator = JSONGenerator()
            json_file = json_generator.generate_json(results)
            logger.info(f"JSON output saved to: {json_file}")

        logger.info("Analysis completed successfully")

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
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help="Stock symbols to analyze"
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

    # Run in appropriate mode
    if args.api:
        run_api_server()
    elif args.analyze:
        run_analysis(
            args.symbols,
            not args.no_csv,
            not args.no_json
        )
    elif args.periodic:
        setup_periodic_analysis(
            args.symbols,
            args.interval
        )


if __name__ == "__main__":
    main()