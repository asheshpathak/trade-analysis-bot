"""
API routes for stock analysis application.
"""
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field
from loguru import logger

from api.controllers import StockAnalysisController
from config.settings import DEFAULT_SYMBOLS


# Pydantic models for request/response
class StockSymbol(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol")


class StockSymbolsList(BaseModel):
    symbols: List[str] = Field(DEFAULT_SYMBOLS, description="List of stock symbols to analyze")


class AnalysisResponse(BaseModel):
    status: str = Field(..., description="Response status")
    data: Dict = Field(..., description="Analysis data")
    timestamp: str = Field(..., description="Response timestamp")


# Create API router
router = APIRouter(prefix="/api/v1", tags=["stock-analysis"])


# Dependencies
async def get_controller():
    """Dependency to get controller instance."""
    return StockAnalysisController()


@router.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "stock-analysis-api"}


@router.get("/market/status", response_model=Dict)
async def get_market_status(controller: StockAnalysisController = Depends(get_controller)):
    """Get current market status."""
    try:
        return controller.get_market_status()
    except Exception as e:
        logger.error(f"Error getting market status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks", response_model=Dict)
async def get_available_stocks(controller: StockAnalysisController = Depends(get_controller)):
    """Get list of available stocks for analysis."""
    try:
        return {"symbols": controller.get_available_symbols()}
    except Exception as e:
        logger.error(f"Error getting available stocks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{symbol}", response_model=AnalysisResponse)
async def get_stock_analysis(
        symbol: str = Path(..., description="Stock symbol to analyze"),
        refresh: bool = Query(False, description="Force refresh analysis"),
        controller: StockAnalysisController = Depends(get_controller)
):
    """
    Get analysis for a single stock.

    Args:
        symbol: Stock symbol to analyze
        refresh: Force refresh analysis
        controller: StockAnalysisController instance

    Returns:
        Analysis results
    """
    try:
        result = controller.analyze_single_stock(symbol, refresh)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "status": "success",
            "data": result,
            "timestamp": controller.get_timestamp()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing stock {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analysis/batch", response_model=AnalysisResponse)
async def analyze_multiple_stocks(
        request: StockSymbolsList = Body(...),
        refresh: bool = Query(False, description="Force refresh analysis"),
        controller: StockAnalysisController = Depends(get_controller)
):
    """
    Analyze multiple stocks.

    Args:
        request: Request with list of symbols
        refresh: Force refresh analysis
        controller: StockAnalysisController instance

    Returns:
        Analysis results for all stocks
    """
    try:
        results = controller.analyze_multiple_stocks(request.symbols, refresh)

        return {
            "status": "success",
            "data": results,
            "timestamp": controller.get_timestamp()
        }
    except Exception as e:
        logger.error(f"Error in batch analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/latest", response_model=AnalysisResponse)
async def get_latest_analysis(controller: StockAnalysisController = Depends(get_controller)):
    """
    Get latest analysis results.

    Args:
        controller: StockAnalysisController instance

    Returns:
        Latest analysis results
    """
    try:
        result = controller.get_latest_analysis()

        if not result:
            raise HTTPException(status_code=404, detail="No analysis results available")

        return {
            "status": "success",
            "data": result,
            "timestamp": controller.get_timestamp()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators/{symbol}", response_model=Dict)
async def get_technical_indicators(
        symbol: str = Path(..., description="Stock symbol"),
        controller: StockAnalysisController = Depends(get_controller)
):
    """
    Get technical indicators for a stock.

    Args:
        symbol: Stock symbol
        controller: StockAnalysisController instance

    Returns:
        Technical indicators data
    """
    try:
        indicators = controller.get_technical_indicators(symbol)

        if not indicators:
            raise HTTPException(status_code=404, detail=f"No indicators available for {symbol}")

        return {
            "symbol": symbol,
            "indicators": indicators,
            "timestamp": controller.get_timestamp()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting indicators for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/{symbol}", response_model=Dict)
async def get_option_chain(
        symbol: str = Path(..., description="Stock symbol"),
        controller: StockAnalysisController = Depends(get_controller)
):
    """
    Get option chain for a stock.

    Args:
        symbol: Stock symbol
        controller: StockAnalysisController instance

    Returns:
        Option chain data
    """
    try:
        option_chain = controller.get_option_chain(symbol)

        if not option_chain:
            raise HTTPException(status_code=404, detail=f"No option chain available for {symbol}")

        return {
            "symbol": symbol,
            "option_chain": option_chain,
            "timestamp": controller.get_timestamp()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting option chain for {symbol}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))