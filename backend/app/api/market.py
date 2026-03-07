from fastapi import APIRouter, HTTPException, Query
from app.services.market.akshare_client import (
    get_stock_quote, get_batch_quotes, get_market_overview,
    get_kline, search_stocks
)

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/overview")
async def market_overview():
    return await get_market_overview()


@router.get("/quote/{symbol}")
async def stock_quote(symbol: str):
    quote = await get_stock_quote(symbol)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return quote


@router.get("/kline/{symbol}")
async def kline(
    symbol: str,
    period: str = Query("D", description="D=日K, W=周K, M=月K"),
    adjust: str = Query("qfq", description="qfq=前复权, hfq=后复权, none=不复权"),
):
    return await get_kline(symbol, period, adjust)


@router.get("/search")
async def search(q: str = Query(..., min_length=1)):
    return await search_stocks(q)


@router.post("/watchlist/quotes")
async def watchlist_quotes(symbols: list[str]):
    return await get_batch_quotes(symbols)
