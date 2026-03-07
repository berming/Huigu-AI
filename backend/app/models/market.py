from pydantic import BaseModel
from typing import Optional


class StockQuote(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    prev_close: float
    volume: float       # 手
    amount: float       # 元
    turnover_rate: Optional[float] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None


class KLineBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float


class KLineData(BaseModel):
    symbol: str
    name: str
    period: str
    bars: list[KLineBar]


class IndexQuote(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float


class MarketOverview(BaseModel):
    indices: list[IndexQuote]
    up_count: int
    down_count: int
    flat_count: int


class StockSearchResult(BaseModel):
    symbol: str
    name: str
    market: str   # SH / SZ / BJ
