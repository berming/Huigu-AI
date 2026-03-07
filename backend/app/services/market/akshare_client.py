"""
AKShare market data client.
Wraps AKShare calls with error handling and data normalization.
Falls back to realistic mock data if AKShare is unavailable.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from app.models.market import (
    StockQuote, KLineBar, KLineData, IndexQuote,
    MarketOverview, StockSearchResult
)
from app.services.market.mock_data import (
    get_stock_quote_mock, get_batch_quotes_mock, get_market_overview_mock,
    get_kline_mock, search_stocks_mock
)

# AKShare is a synchronous library; we run it in a thread pool
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
    print("[Info] AKShare loaded — using real market data")
except ImportError:
    AKSHARE_AVAILABLE = False
    print("[Warning] AKShare not available — using mock data")


# ── AKShare helper functions (only used if AKSHARE_AVAILABLE) ────────────────

def _fetch_spot_em():
    return ak.stock_zh_a_spot_em()


def _fetch_index_spot(symbol: str) -> dict:
    try:
        df = ak.stock_zh_index_spot_em(symbol=symbol)
        if df is not None and not df.empty:
            row = df.iloc[0]
            return {
                "price": float(row.get("最新价", 0) or 0),
                "change": float(row.get("涨跌额", 0) or 0),
                "change_pct": float(row.get("涨跌幅", 0) or 0),
            }
    except Exception:
        pass
    return {"price": 0.0, "change": 0.0, "change_pct": 0.0}


def _fetch_kline(symbol: str, period: str, adjust: str):
    period_map = {"D": "daily", "W": "weekly", "M": "monthly"}
    ak_period = period_map.get(period, "daily")
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")
    return ak.stock_zh_a_hist(
        symbol=code, period=ak_period,
        start_date=start_date, end_date=end_date, adjust=adjust,
    )


def _search_stocks_ak(query: str):
    try:
        df = ak.stock_info_a_code_name()
        mask = df["code"].str.contains(query, na=False) | df["name"].str.contains(query, na=False)
        return df[mask].head(20).to_dict("records")
    except Exception:
        return []


# ── Public async API ─────────────────────────────────────────────────────────

async def get_stock_quote(symbol: str) -> Optional[StockQuote]:
    if not AKSHARE_AVAILABLE:
        return get_stock_quote_mock(symbol)
    loop = asyncio.get_event_loop()
    try:
        df = await loop.run_in_executor(None, _fetch_spot_em)
        code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")
        row = df[df["代码"] == code]
        if row.empty:
            return get_stock_quote_mock(symbol)
        r = row.iloc[0]
        return StockQuote(
            symbol=code, name=str(r.get("名称", "")),
            price=float(r.get("最新价", 0) or 0),
            change=float(r.get("涨跌额", 0) or 0),
            change_pct=float(r.get("涨跌幅", 0) or 0),
            open=float(r.get("今开", 0) or 0),
            high=float(r.get("最高", 0) or 0),
            low=float(r.get("最低", 0) or 0),
            prev_close=float(r.get("昨收", 0) or 0),
            volume=float(r.get("成交量", 0) or 0),
            amount=float(r.get("成交额", 0) or 0),
            turnover_rate=float(r.get("换手率", 0) or 0) if "换手率" in r else None,
            pe_ratio=float(r.get("市盈率-动态", 0) or 0) if "市盈率-动态" in r else None,
            market_cap=float(r.get("总市值", 0) or 0) if "总市值" in r else None,
        )
    except Exception as e:
        print(f"[AKShare] get_stock_quote error: {e}")
        return get_stock_quote_mock(symbol)


async def get_batch_quotes(symbols: list[str]) -> list[StockQuote]:
    if not AKSHARE_AVAILABLE:
        return get_batch_quotes_mock(symbols)
    loop = asyncio.get_event_loop()
    try:
        df = await loop.run_in_executor(None, _fetch_spot_em)
        codes = [s.replace("SH", "").replace("SZ", "").replace(".", "") for s in symbols]
        rows = df[df["代码"].isin(codes)]
        quotes = []
        for _, r in rows.iterrows():
            quotes.append(StockQuote(
                symbol=str(r.get("代码", "")), name=str(r.get("名称", "")),
                price=float(r.get("最新价", 0) or 0),
                change=float(r.get("涨跌额", 0) or 0),
                change_pct=float(r.get("涨跌幅", 0) or 0),
                open=float(r.get("今开", 0) or 0),
                high=float(r.get("最高", 0) or 0),
                low=float(r.get("最低", 0) or 0),
                prev_close=float(r.get("昨收", 0) or 0),
                volume=float(r.get("成交量", 0) or 0),
                amount=float(r.get("成交额", 0) or 0),
            ))
        return quotes
    except Exception as e:
        print(f"[AKShare] get_batch_quotes error: {e}")
        return get_batch_quotes_mock(symbols)


async def get_market_overview() -> MarketOverview:
    if not AKSHARE_AVAILABLE:
        return get_market_overview_mock()

    loop = asyncio.get_event_loop()
    try:
        df = await loop.run_in_executor(None, _fetch_spot_em)
        up = int((df["涨跌幅"] > 0).sum())
        down = int((df["涨跌幅"] < 0).sum())
        flat = int((df["涨跌幅"] == 0).sum())
    except Exception:
        return get_market_overview_mock()

    index_map = {
        "000001": ("sh000001", "上证指数"),
        "399001": ("sz399001", "深证成指"),
        "399006": ("sz399006", "创业板指"),
        "000300": ("sh000300", "沪深300"),
        "000688": ("sh000688", "科创50"),
    }

    async def fetch_one(code: str, ak_sym: str, name: str):
        data = await loop.run_in_executor(None, _fetch_index_spot, ak_sym)
        return IndexQuote(symbol=code, name=name, **data)

    results = await asyncio.gather(
        *[fetch_one(c, s, n) for c, (s, n) in index_map.items()],
        return_exceptions=True
    )
    indices = [i for i in results if isinstance(i, IndexQuote)]
    return MarketOverview(indices=indices, up_count=up, down_count=down, flat_count=flat)


async def get_kline(symbol: str, period: str = "D", adjust: str = "qfq") -> KLineData:
    if not AKSHARE_AVAILABLE:
        return get_kline_mock(symbol, period)

    loop = asyncio.get_event_loop()
    code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")
    name = symbol
    try:
        import akshare as ak
        df_info = await loop.run_in_executor(None, ak.stock_info_a_code_name)
        row = df_info[df_info["code"] == code]
        if not row.empty:
            name = str(row.iloc[0]["name"])
    except Exception:
        pass

    try:
        df = await loop.run_in_executor(None, _fetch_kline, symbol, period, adjust)
        bars = [
            KLineBar(
                date=str(r.get("日期", r.get("date", ""))),
                open=float(r.get("开盘", 0)),
                high=float(r.get("最高", 0)),
                low=float(r.get("最低", 0)),
                close=float(r.get("收盘", 0)),
                volume=float(r.get("成交量", 0)),
                amount=float(r.get("成交额", 0)),
            )
            for _, r in df.iterrows()
        ]
        return KLineData(symbol=symbol, name=name, period=period, bars=bars)
    except Exception as e:
        print(f"[AKShare] get_kline error: {e}")
        return get_kline_mock(symbol, period)


async def search_stocks(query: str) -> list[StockSearchResult]:
    if not AKSHARE_AVAILABLE:
        return search_stocks_mock(query)

    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, _search_stocks_ak, query)
        output = []
        for r in results:
            code = str(r.get("code", ""))
            output.append(StockSearchResult(
                symbol=code,
                name=str(r.get("name", "")),
                market="SH" if code.startswith(("6", "9", "5")) else "SZ",
            ))
        return output
    except Exception as e:
        print(f"[AKShare] search_stocks error: {e}")
        return search_stocks_mock(query)
