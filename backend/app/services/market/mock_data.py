"""
Realistic mock data for A-share stocks when AKShare is unavailable.
Simulates real-time prices, K-line history, and market overview.
"""
import random
import math
from datetime import datetime, timedelta
from app.models.market import (
    StockQuote, KLineBar, KLineData, IndexQuote,
    MarketOverview, StockSearchResult
)

# Popular A-share stocks with realistic data
STOCK_DATABASE = {
    "000001": {"name": "平安银行", "base_price": 11.5, "market_cap": 2.23e11},
    "600519": {"name": "贵州茅台", "base_price": 1680.0, "market_cap": 2.12e12},
    "000858": {"name": "五粮液", "base_price": 148.5, "market_cap": 5.77e11},
    "601318": {"name": "中国平安", "base_price": 45.2, "market_cap": 8.22e11},
    "300750": {"name": "宁德时代", "base_price": 236.0, "market_cap": 5.53e11},
    "002594": {"name": "比亚迪", "base_price": 278.0, "market_cap": 8.07e11},
    "600036": {"name": "招商银行", "base_price": 35.8, "market_cap": 9.04e11},
    "601166": {"name": "兴业银行", "base_price": 18.2, "market_cap": 3.76e11},
    "000333": {"name": "美的集团", "base_price": 55.6, "market_cap": 4.00e11},
    "002415": {"name": "海康威视", "base_price": 27.3, "market_cap": 2.61e11},
    "688111": {"name": "金山办公", "base_price": 185.0, "market_cap": 7.43e10},
    "300999": {"name": "金龙鱼", "base_price": 22.5, "market_cap": 1.20e11},
    "601398": {"name": "工商银行", "base_price": 5.62, "market_cap": 2.00e12},
    "600900": {"name": "长江电力", "base_price": 26.8, "market_cap": 6.44e11},
    "000725": {"name": "京东方A", "base_price": 4.35, "market_cap": 1.83e11},
}

INDICES = {
    "000001": {"name": "上证指数", "base": 3280.0},
    "399001": {"name": "深证成指", "base": 10520.0},
    "399006": {"name": "创业板指", "base": 2085.0},
    "000300": {"name": "沪深300", "base": 3890.0},
    "000688": {"name": "科创50", "base": 960.0},
}

ALL_STOCKS = [
    {"code": k, "name": v["name"]}
    for k, v in STOCK_DATABASE.items()
]

# Add more stocks for search
EXTRA_STOCKS = [
    {"code": "601012", "name": "隆基绿能"},
    {"code": "600276", "name": "恒瑞医药"},
    {"code": "002475", "name": "立讯精密"},
    {"code": "300760", "name": "迈瑞医疗"},
    {"code": "601888", "name": "中国中免"},
    {"code": "688599", "name": "天合光能"},
    {"code": "600690", "name": "海尔智家"},
    {"code": "000568", "name": "泸州老窖"},
]
ALL_STOCKS.extend(EXTRA_STOCKS)


def _get_price(symbol: str, base: float) -> tuple[float, float, float, float, float]:
    """Generate realistic price fluctuation."""
    # Use symbol hash for consistent but random-looking variation
    seed = sum(ord(c) for c in symbol) + int(datetime.now().strftime("%Y%m%d%H"))
    r = random.Random(seed)

    change_pct = r.uniform(-0.035, 0.04)
    price = round(base * (1 + change_pct), 2)
    prev_close = base
    change = round(price - prev_close, 2)
    high = round(price * r.uniform(1.0, 1.02), 2)
    low = round(price * r.uniform(0.98, 1.0), 2)
    return price, change, change_pct * 100, high, low


def get_stock_quote_mock(symbol: str) -> StockQuote | None:
    code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")
    if code not in STOCK_DATABASE:
        return None

    stock = STOCK_DATABASE[code]
    price, change, change_pct, high, low = _get_price(code, stock["base_price"])
    prev_close = stock["base_price"]

    r = random.Random(sum(ord(c) for c in code))
    volume = r.randint(50000, 5000000)
    amount = volume * price * 100

    return StockQuote(
        symbol=code,
        name=stock["name"],
        price=price,
        change=change,
        change_pct=round(change_pct, 2),
        open=round(prev_close * r.uniform(0.995, 1.005), 2),
        high=high,
        low=low,
        prev_close=prev_close,
        volume=float(volume),
        amount=float(amount),
        turnover_rate=round(r.uniform(0.5, 8.0), 2),
        pe_ratio=round(r.uniform(8, 45), 1),
        market_cap=stock["market_cap"],
    )


def get_batch_quotes_mock(symbols: list[str]) -> list[StockQuote]:
    quotes = []
    for sym in symbols:
        q = get_stock_quote_mock(sym)
        if q:
            quotes.append(q)
    return quotes


def get_market_overview_mock() -> MarketOverview:
    indices = []
    for code, data in INDICES.items():
        _, change, change_pct, _, _ = _get_price(code, data["base"])
        price = round(data["base"] * (1 + change_pct / 100), 2)
        indices.append(IndexQuote(
            symbol=code,
            name=data["name"],
            price=price,
            change=round(price - data["base"], 2),
            change_pct=round(change_pct, 2),
        ))

    r = random.Random(int(datetime.now().strftime("%Y%m%d%H")))
    total = 5300
    up = r.randint(2000, 3500)
    down = r.randint(1500, total - up - 50)
    flat = total - up - down

    return MarketOverview(
        indices=indices,
        up_count=up,
        down_count=down,
        flat_count=flat,
    )


def get_kline_mock(symbol: str, period: str = "D") -> KLineData:
    code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")
    stock = STOCK_DATABASE.get(code, {"name": symbol, "base_price": 10.0})
    name = stock["name"]
    base_price = stock["base_price"]

    bars = []
    days_back = 250 if period == "D" else 52 if period == "W" else 24
    delta = timedelta(days=1 if period == "D" else 7 if period == "W" else 30)

    price = base_price * 0.7  # Start from lower price
    end_date = datetime.now()

    for i in range(days_back):
        date = end_date - delta * (days_back - i)
        # Skip weekends for daily
        if period == "D" and date.weekday() >= 5:
            continue

        # Random walk with slight upward drift
        change = random.gauss(0.001, 0.018)
        open_p = round(price, 2)
        close_p = round(price * (1 + change), 2)
        high_p = round(max(open_p, close_p) * random.uniform(1.0, 1.015), 2)
        low_p = round(min(open_p, close_p) * random.uniform(0.985, 1.0), 2)
        volume = random.randint(100000, 3000000)

        bars.append(KLineBar(
            date=date.strftime("%Y-%m-%d"),
            open=open_p,
            high=high_p,
            low=low_p,
            close=close_p,
            volume=float(volume),
            amount=float(volume * close_p * 100),
        ))
        price = close_p

    return KLineData(symbol=code, name=name, period=period, bars=bars)


def search_stocks_mock(query: str) -> list[StockSearchResult]:
    query = query.lower()
    results = []
    for stock in ALL_STOCKS:
        if query in stock["code"] or query in stock["name"]:
            code = stock["code"]
            market = "SH" if code.startswith(("6", "9")) else "SZ"
            results.append(StockSearchResult(
                symbol=code,
                name=stock["name"],
                market=market,
            ))
    return results[:20]
