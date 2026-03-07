from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.market.akshare_client import (
    get_stock_quote, get_batch_quotes, get_market_overview,
    get_kline, search_stocks
)

router = APIRouter(prefix="/api/market", tags=["market"])


# ── Alert types ───────────────────────────────────────────────────────────────

class AlertTarget(BaseModel):
    symbol: str
    name: str
    upper_target: float | None = None
    lower_target: float | None = None

class AlertResult(BaseModel):
    symbol: str
    name: str
    current_price: float
    upper_triggered: bool = False
    lower_triggered: bool = False
    upper_target: float | None = None
    lower_target: float | None = None


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


@router.post("/alerts/check", response_model=list[AlertResult])
async def check_alerts(targets: list[AlertTarget]):
    """
    Server-side alert check. Client POSTs its configured alerts;
    server fetches current prices and returns which ones are triggered.
    Useful for background refresh or push notification scheduling.
    """
    symbols = [t.symbol for t in targets]
    quotes = await get_batch_quotes(symbols)
    price_map = {q.symbol: q.price for q in quotes}

    results: list[AlertResult] = []
    for t in targets:
        price = price_map.get(t.symbol)
        if price is None:
            continue
        results.append(AlertResult(
            symbol=t.symbol,
            name=t.name,
            current_price=price,
            upper_target=t.upper_target,
            lower_target=t.lower_target,
            upper_triggered=bool(t.upper_target and price >= t.upper_target),
            lower_triggered=bool(t.lower_target and price <= t.lower_target),
        ))
    return results
