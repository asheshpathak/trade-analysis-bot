"""
API middleware for stock analysis application.
"""
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger


def setup_middlewares(app: FastAPI) -> None:
    """
    Setup FastAPI middleware.

    Args:
        app: FastAPI application instance
    """
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middlewares
    app.middleware("http")(logging_middleware)
    app.middleware("http")(error_handling_middleware)
    app.middleware("http")(response_time_middleware)

    logger.info("API middlewares configured")


async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware for request/response logging.

    Args:
        request: HTTP request
        call_next: Next middleware in chain

    Returns:
        HTTP response
    """
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response
    logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code}")

    return response


async def error_handling_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware for global error handling.

    Args:
        request: HTTP request
        call_next: Next middleware in chain

    Returns:
        HTTP response
    """
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # Log the error
        logger.error(f"Unhandled exception: {str(e)}")

        # Return error response
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )


async def response_time_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to measure and log response time.

    Args:
        request: HTTP request
        call_next: Next middleware in chain

    Returns:
        HTTP response
    """
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Log if response time is slow
    if process_time > 1.0:
        logger.warning(f"Slow response: {request.method} {request.url.path} - {process_time:.2f}s")

    return response