#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A-Stock-Analysis 统一报告生成器
A股市场行情分析报告
早市（盘前参考）08:30 / 午市（午盘总结）12:30 / 晚市（收盘复盘）19:30
融合 StockAnalysis 与 daily-reporter 两个模块功能
数据来源: Baostock（主要指数/自选股）+ 新浪财经（实时行情/图表快照）+ 东方财富（主力资金）
"""

import baostock as bs
import pandas as pd
from tech_charts import render_tech_charts
import base64
import json
import re
import sys
import os
import time
import datetime
import urllib.request
import urllib.error
import logging
from pathlib import Path
from datetime import timedelta

# ─────────────────────────────────────────────
# 日志配置
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # A-Stock-Analysis/
SCRIPT_DIR = BASE_DIR / "scripts"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"
LOG_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"astock_{datetime.date.today()}.log", encoding="utf-8"),
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────
INDICES = [
    ('sh.000001', '上证指数'),
    ('sz.399001', '深证成指'),
    ('sz.399006', '创业板指'),
    ('sh.000300', '沪深300'),
    ('sh.000016', '上证50'),
    ('sh.000688', '科创50'),
    ('sz.399005', '中小100'),
    ('sh.000905', '中证500'),
]

WATCH_STOCKS = [
    ('sz.002594', '比亚迪',     '新能源汽车龙头'),
    ('sz.002185', '华天科技',   '半导体封装测试'),
    ('sh.601360', '三六零',     '网络安全/AI'),
    ('sz.002179', '中航光电',   '军工连接器龙头'),
    ('sz.002230', '科大讯飞',   'AI语音龙头'),
    ('sh.600410', '华胜天成',   '云计算/算力'),
    ('sz.002475', '立讯精密',   '消费电子/连接器'),
    ('sz.000977', '浪潮信息',   'AI服务器/算力'),
    ('sh.600438', '通威股份',   '光伏/硅料'),
]

BREADTH_INDICES = [
    ('sh.000001', '上证指数'),
    ('sz.399001', '深证成指'),
    ('sz.399006', '创业板指'),
]

STOCK_COLORS = {
    "002594": "#16a34a", "002185": "#2563eb", "601360": "#d97706",
    "002179": "#7c3aed", "002230": "#dc2626", "600410": "#0891b2",
    "002475": "#db2777", "000977": "#475569", "600438": "#ca8a04",
}
STOCK_TAGS_BG = {
    "002594": ("#dcfce7","#15803d"), "002185": ("#dbeafe","#1d4ed8"),
    "601360": ("#fef9c3","#a16207"), "002179": ("#ede9fe","#5b21b6"),
    "002230": ("#fee2e2","#b91c1c"), "600410": ("#cffafe","#0e7490"),
    "002475": ("#fce7f3","#9d174d"), "000977": ("#e2e8f0","#1e293b"),
    "600438": ("#fef3c7","#854d0e"),
}

SESSIONS = {
    "morning": {"title":"A股早报","slot":"早市（盘前参考）","period":"盘前快照","window":(0,12)},
    "noon":    {"title":"A股午报","slot":"午市（午盘总结）","period":"午盘快照","window":(12,15)},
    "evening": {"title":"A股日报","slot":"晚市（收盘复盘）","period":"收盘快照","window":(15,24)},
}

SSE_HOLIDAYS_2026 = {
    (2026,1,1),(2026,1,2),(2026,1,3),
    (2026,2,15),(2026,2,16),(2026,2,17),(2026,2,18),(2026,2,19),(2026,2,20),(2026,2,21),(2026,2,22),(2026,2,23),
    (2026,4,4),(2026,4,5),(2026,4,6),
    (2026,5,1),(2026,5,2),(2026,5,3),(2026,5,4),(2026,5,5),
    (2026,6,19),(2026,6,20),(2026,6,21),
    (2026,9,25),(2026,9,26),(2026,9,27),
    (2026,10,1),(2026,10,2),(2026,10,3),(2026,10,4),(2026,10,5),(2026,10,6),(2026,10,7),
}

PLACEHOLDER_SVG = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(
        b'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="180">'
        b'<rect width="600" height="180" fill="#f8fafc" rx="6"/>'
        b'<text x="300" y="96" text-anchor="middle" font-size="13" '
        b'fill="#94a3b8" font-family="sans-serif">Chart unavailable</text>'
        b'</svg>'
    ).decode()
)

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def get_bj_now():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)

def today_str():
    return get_bj_now().strftime('%Y-%m-%d')

def week_ago_str(days=7):
    return (get_bj_now() - timedelta(days=days)).strftime('%Y-%m-%d')

def is_trading_day(d):
    if d.weekday() >= 5: return False
    if (d.year, d.month, d.day) in SSE_HOLIDAYS_2026: return False
    return True

def get_t_day():
    d = get_bj_now().date()
    for _ in range(10):
        if is_trading_day(d): return d
        d -= timedelta(days=1)
    raise RuntimeError("无法确定最近交易日")

def fmt_vol(v):
    if pd.isna(v): return 'N/A'
    v = float(v)
    if abs(v) >= 1e8: return f"{v/1e8:.2f}亿"
    if abs(v) >= 1e4: return f"{v/1e4:.0f}万"
    return f"{v:.0f}"

def fmt_amt(v):
    if pd.isna(v): return 'N/A'
    v = float(v)
    if abs(v) >= 1e8: return f"{v/1e8:.2f}亿"
    if abs(v) >= 1e4: return f"{v/1e4:.0f}万"
    return f"{v:.0f}"

def fmt_amount_cn(v):
    try:
        v = float(v)
    except Exception:
        return "—"
    if v == 0: return "0"
    sign = "+" if v > 0 else "-"
    a = abs(v)
    if a >= 1e8: return f"{sign}{a/1e8:.2f}亿"
    if a >= 1e4: return f"{sign}{a/1e4:.0f}万"
    return f"{sign}{int(round(a))}"

def query_k(code, fields, start, end, freq='d'):
    rs = bs.query_history_k_data_plus(code, fields, start_date=start, end_date=end, frequency=freq, adjustflag='3')
    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    if not data: return pd.DataFrame()
    cols = [c.strip() for c in fields.split(',')]
    df = pd.DataFrame(data, columns=cols)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df.dropna(subset=['close'])

def sleep_short():
    time.sleep(0.3)

def fetch(url, timeout=12, referer=""):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    if referer: headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def fetch_text(url, timeout=12, referer="", encoding="utf-8"):
    return fetch(url, timeout, referer).decode(encoding, errors="replace")

def download_chart_b64(url, label):
    try:
        data = fetch(url, timeout=15, referer="http://finance.sina.com.cn/")
        if len(data) < 1000: raise ValueError(f"响应过小({len(data)}B)")
        b64 = base64.b64encode(data).decode()
        return f"data:image/gif;base64,{b64}"
    except Exception as e:
        log.info(f"  ⚠ {label} 图表下载失败: {e}")
        return PLACEHOLDER_SVG

# ─────────────────────────────────────────────
# 1. 主要指数（Baostock）
# ─────────────────────────────────────────────
def get_index_data():
    start, end = week_ago_str(10), today_str()
    results = []
    for code, name in INDICES:
        df = query_k(code, 'date,open,high,low,close,volume,amount,pctChg', start, end)
        sleep_short()
        if df.empty or len(df) < 1: continue
        cur = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else cur
        results.append({
            'name': name, 'code': code, 'date': cur['date'],
            'close': float(cur['close']), 'pctChg': float(cur['pctChg']),
            'open': float(cur['open']), 'high': float(cur['high']), 'low': float(cur['low']),
            'volume': float(cur['volume']), 'amount': float(cur['amount']),
            'prev_close': float(prev['close']),
            'change': float(cur['close']) - float(prev['close']),
        })
    return results

# ─────────────────────────────────────────────
# 2. 全市场统计
# ─────────────────────────────────────────────
def get_market_breadth():
    start, end = week_ago_str(20), today_str()
    results = {}
    for code, name in BREADTH_INDICES:
        df = query_k(code, 'date,close,pctChg', start, end)
        sleep_short()
        if df.empty or len(df) < 3: continue
        recent = df.tail(5)['pctChg'].tolist()
        up_days = sum(1 for x in recent if x > 0)
        results[name] = {
            'up_days': up_days, 'total_days': len(recent),
            'recent_avg': sum(recent) / len(recent),
            'latest_pct': float(df.iloc[-1]['pctChg']),
        }
    return results

def get_market_stats(indices):
    if not indices: return {}
    rising = sum(1 for i in indices if i['pctChg'] > 0)
    falling = sum(1 for i in indices if i['pctChg'] < 0)
    avg_pct = sum(i['pctChg'] for i in indices) / len(indices)
    total_vol = sum(i['volume'] for i in indices)
    total_amt = sum(i['amount'] for i in indices)
    return {
        'rising': rising, 'falling': falling,
        'avg_pct': avg_pct,
        'total_vol': total_vol, 'total_amt': total_amt,
    }

# ─────────────────────────────────────────────
# 3. 自选股详细行情（Baostock）
# ─────────────────────────────────────────────
def get_watch_stocks():
    start, end = week_ago_str(20), today_str()
    results = []
    for code, name, tag in WATCH_STOCKS:
        df = query_k(code, 'date,open,high,low,close,volume,amount,pctChg', start, end)
        sleep_short()
        if df.empty or len(df) < 1:
            results.append({'name': name, 'code': code, 'tag': tag, 'error': True})
            continue
        cur = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else cur
        prev2 = df.iloc[-3] if len(df) > 2 else prev
        ma5 = df.tail(5)['close'].mean() if len(df) >= 5 else float(cur['close'])
        ma10 = df.tail(10)['close'].mean() if len(df) >= 10 else ma5
        recent5 = df.tail(5)['pctChg'].tolist()
        high20 = df['high'].tail(20).max()
        low20 = df['low'].tail(20).min()
        current_close = float(cur['close'])
        pct_from_high = (current_close - high20) / high20 * 100 if high20 else 0
        pct_from_low = (current_close - low20) / low20 * 100 if low20 else 0
        results.append({
            'name': name, 'code': code, 'tag': tag,
            'date': cur['date'], 'close': current_close,
            'pctChg': float(cur['pctChg']),
            'open': float(cur['open']), 'high': float(cur['high']), 'low': float(cur['low']),
            'volume': float(cur['volume']), 'amount': float(cur['amount']),
            'prev_close': float(prev['close']),
            'change': current_close - float(prev['close']),
            'prev2_close': float(prev2['close']),
            'ma5': ma5, 'ma10': ma10,
            'up5': sum(1 for x in recent5 if x > 0),
            'high20': high20, 'low20': low20,
            'pct_from_high': pct_from_high, 'pct_from_low': pct_from_low,
        })
    return results

# ─────────────────────────────────────────────
# 4. 新浪实时行情
# ─────────────────────────────────────────────
def fetch_sina_index():
    codes = "s_sh000001,s_sz399001,s_sz399006,s_sh000688,s_sh000016"
    url = f"http://hq.sinajs.cn/list={codes}"
    result = {}
    try:
        text = fetch_text(url, referer="http://finance.sina.com.cn/")
        for line in text.strip().splitlines():
            m = re.search(r'var hq_str_(s_\w+)="([^"]*)"', line)
            if not m: continue
            fields = m.group(2).split(",")
            if len(fields) < 5: continue
            result[m.group(1)] = {
                "name": fields[0], "price": fields[1],
                "chg_amt": fields[2], "chg_pct": fields[3], "vol": fields[4],
            }
    except Exception as e:
        log.info(f"⚠ 新浪指数行情失败: {e}")
    return result

def fetch_sina_stock(stock):
    code, market = stock['code'], stock['market']
    result = {"code": code, "market": market, "name": stock['name'], "tag": stock['tag']}
    try:
        url = f"http://hq.sinajs.cn/list={market}{code}"
        text = fetch_text(url, referer="http://finance.sina.com.cn/")
        m = re.search(r'"([^"]+)"', text)
        if m:
            fields = m.group(1).split(",")
            if len(fields) >= 32:
                result["open"] = fields[1]; result["prev"] = fields[2]
                result["price"] = fields[3]; result["high"] = fields[4]
                result["low"] = fields[5]; result["vol"] = fields[8]
                result["amt"] = fields[9]; result["date"] = fields[30]
                result["time"] = fields[31]
                try:
                    prev = float(fields[2]); cur = float(fields[3])
                    result["chg_pct"] = round((cur - prev) / prev * 100, 2) if prev else 0
                    result["chg_amt"] = round(cur - prev, 2)
                except Exception: pass
    except Exception as e:
        log.info(f"  新浪行情 {code} 失败: {e}")
    # 同花顺校验
    try:
        url = f"http://stockpage.10jqka.com.cn/{code}/"
        text = fetch_text(url, referer="http://stockpage.10jqka.com.cn/")
        start = re.search(r'\[\{"date":"\d+"', text)
        if start:
            try:
                arr, _ = json.JSONDecoder().raw_decode(text[start.start():])
            except Exception: arr = None
            if arr:
                latest = arr[-1]
                result["ths_stk_pct"] = latest.get("item1", "")
    except Exception: pass
    return result

# ─────────────────────────────────────────────
# 5. 主力资金流向（东方财富）
# ─────────────────────────────────────────────
def fetch_capital_flow(stock, lmt=10):
    code = stock['code']
    market = stock['market']
    secid = ("1" if market == "sh" else "0") + "." + code
    ts_ms = int(time.time() * 1000)
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/fflow/kline/get"
        f"?lmt={lmt}&klt=101&fields1=f1,f2,f3,f7"
        "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
        "&ut=b2884a393a59ad64002292a3e90d46a5"
        f"&secid={secid}&_={ts_ms}"
    )
    result = {"ok": False, "name": stock['name'], "days": [], "error": ""}
    try:
        raw = fetch_text(url, timeout=15, referer="https://data.eastmoney.com/")
        data = json.loads(raw)
        if data.get("rc") not in (0, None):
            raise ValueError(f"rc={data.get('rc')}")
        payload = data.get("data") or {}
        if payload.get("name"): result["name"] = payload["name"]
        klines = payload.get("klines") or []
        if not klines:
            raise ValueError("klines 为空")
        days = []
        for line in klines:
            parts = line.split(",")
            if len(parts) < 6: continue
            def _num(i, default=0.0):
                if i >= len(parts): return default
                try: return float(parts[i])
                except Exception: return default
            def _opt(i):
                if i >= len(parts): return None
                try: return float(parts[i])
                except Exception: return None
            days.append({
                "date": parts[0], "main": _num(1), "small": _num(2),
                "medium": _num(3), "large": _num(4), "xlarge": _num(5),
                "main_pct": _opt(6), "small_pct": _opt(7),
                "medium_pct": _opt(8), "large_pct": _opt(9), "xlarge_pct": _opt(10),
                "close": _opt(11), "chg_pct": _opt(12),
            })
        if not days: raise ValueError("所有 klines 条目字段数不足 6")
        result["days"] = days
        result["today"] = days[-1]
        def _sum(n, key): return sum(d[key] for d in days[-n:]) if len(days) >= 1 else 0.0
        result["sum5"] = {k: _sum(5, k) for k in ("main","small","medium","large","xlarge")}
        result["sum10"] = {k: _sum(10, k) for k in ("main","small","medium","large","xlarge")}
        result["ok"] = True
    except Exception as e:
        result["error"] = str(e)
        log.info(f"  ⚠ 主力资金 {code} 失败: {e}")
    return result

# ─────────────────────────────────────────────
# 6. 当日要闻
# ─────────────────────────────────────────────
def fetch_market_news(t_day):
    headlines = []
    try:
        date_str = t_day.strftime("%Y-%m-%d")
        url = f"https://finance.sina.com.cn/roll/index.d.html?cids=&date={date_str}&num=20"
        text = fetch_text(url, referer="https://finance.sina.com.cn/")
        titles = re.findall(r'<a[^>]*target="_blank"[^>]*>([^<]{10,60})</a>', text)
        for t in titles:
            t = t.strip()
            if t and any(kw in t for kw in ["股","市","A股","行情","指数","板块","券","基金"]):
                headlines.append(t)
                if len(headlines) >= 8: break
    except Exception as e:
        log.info(f"⚠ 快讯抓取失败: {e}")
    return headlines

# ─────────────────────────────────────────────
# 7. 趋势与规律分析
# ─────────────────────────────────────────────
def analyze_trends(indices, watch_stocks, breadth):
    analyses = []
    if indices:
        avg_pct = sum(i['pctChg'] for i in indices) / len(indices)
        up_count = sum(1 for i in indices if i['pctChg'] > 0)
        if avg_pct > 1.5:
            trend = "强势上攻"
            desc = f"主要指数全线飘红，平均涨幅 {avg_pct:.2f}%，{up_count}/{len(indices)} 个指数上涨，做多动能充沛。"
        elif avg_pct > 0.3:
            trend = "震荡偏强"
            desc = f"指数平均涨幅 {avg_pct:.2f}%，{up_count}/{len(indices)} 上涨，沪指在均线系统上方运行，结构分化。"
        elif avg_pct < -1.5:
            trend = "显著回调"
            desc = f"主要指数平均下跌 {abs(avg_pct):.2f}%，市场承压，量能需观察是否进一步萎缩。"
        elif avg_pct < -0.3:
            trend = "震荡偏弱"
            desc = f"指数平均跌幅 {abs(avg_pct):.2f}%，{up_count}/{len(indices)} 上涨，短线资金偏谨慎。"
        else:
            trend = "横盘整理"
            desc = f"主要指数几乎走平（{avg_pct:.2f}%），多空平衡，市场等待方向指引。"
        analyses.append({'title': '大盘趋势', 'trend': trend, 'desc': desc})

    if indices:
        total_amt = sum(i['amount'] for i in indices)
        if total_amt > 1e12:
            vol_desc = "成交活跃（单市场成交超万亿），资金参与度高。"
        elif total_amt > 8e11:
            vol_desc = "量能处于中等水平，存量资金博弈特征明显。"
        else:
            vol_desc = "量能萎缩，市场观望情绪浓厚。"
        analyses.append({'title': '量价特征', 'trend': '', 'desc': vol_desc})

    if indices:
        sorted_idx = sorted(indices, key=lambda x: x['pctChg'], reverse=True)
        strongest = sorted_idx[0]
        weakest = sorted_idx[-1]
        style_desc = f"{strongest['name']}({strongest['pctChg']:+.2f}%)领跑，{weakest['name']}({weakest['pctChg']:+.2f}%)偏弱。"
        analyses.append({'title': '风格特征', 'trend': '', 'desc': style_desc})

    valid = [s for s in watch_stocks if not s.get('error')]
    if valid:
        up_stocks = [s for s in valid if s['pctChg'] > 0]
        down_stocks = [s for s in valid if s['pctChg'] < 0]
        strong_stock = max(valid, key=lambda x: x['pctChg'])
        weak_stock = min(valid, key=lambda x: x['pctChg'])
        avg_pct_stock = sum(s['pctChg'] for s in valid) / len(valid)
        above_ma5 = sum(1 for s in valid if s['close'] > s['ma5'])
        below_ma5 = len(valid) - above_ma5
        stock_desc = (
            f"自选股今日平均涨跌 {avg_pct_stock:+.2f}%，"
            f"{len(up_stocks)}只上涨 / {len(down_stocks)}只下跌。"
            f"{strong_stock['name']}({strong_stock['pctChg']:+.2f}%)最强，"
            f"{weak_stock['name']}({weak_stock['pctChg']:+.2f}%)最弱。"
            f"均线看，{above_ma5}只高于MA5，{below_ma5}只低于MA5，"
            f"整体 {'偏强' if above_ma5 > below_ma5 else '偏弱'}。"
        )
        analyses.append({'title': '自选股动向', 'trend': '', 'desc': stock_desc})

    if breadth:
        rhythm = []
        for name, info in breadth.items():
            up = info['up_days']
            rhythm.append(f"{name}近5日{up}涨{info['total_days']-up}跌")
        analyses.append({'title': '近期节奏', 'trend': '', 'desc': '；'.join(rhythm)})

    return analyses

# ─────────────────────────────────────────────
# 8. 综合评述
# ─────────────────────────────────────────────
def make_summary(indices, watch_stocks, stats):
    if not indices: return "暂无数据，请稍后重试。"
    avg_pct = stats.get('avg_pct', 0)
    rising = stats.get('rising', 0)
    falling = stats.get('falling', 0)
    if avg_pct > 2.0:
        overall = "**今日市场强势上攻**，三大指数全线飘红，量能配合良好，做多情绪高涨。"
    elif avg_pct > 0.5:
        overall = "**今日市场稳中有升**，主要指数收涨，结构性机会为主，热点板块有所表现。"
    elif avg_pct < -2.0:
        overall = "**今日市场显著回调**，主要指数承压，空头情绪较重，短线需控制风险。"
    elif avg_pct < -0.5:
        overall = "**今日市场小幅回落**，主要指数收跌，整体仍在震荡区间，建议谨慎观望。"
    else:
        overall = "**今日市场基本走平**，多空双方博弈激烈，指数波澜不惊。"
    valid = [s for s in watch_stocks if not s.get('error')]
    if valid:
        strong = max(valid, key=lambda x: x['pctChg'])
        weak = min(valid, key=lambda x: x['pctChg'])
        overall += f" 个股方面，{strong['name']}({strong['pctChg']:+.2f}%)表现最强，{weak['name']}({weak['pctChg']:+.2f}%)偏弱。"
    return overall

# ─────────────────────────────────────────────
# 9. Markdown 报告生成
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 10. HTML 报告生成（主力资金图表 + 分时/K线快照）
# ─────────────────────────────────────────────
def fmt_pct(val):
    try:
        v = float(val)
        sign = "▲" if v >= 0 else "▼"
        cls = "up" if v >= 0 else "dn"
        return f'<span class="{cls}">{sign} {abs(v):.2f}%</span>'
    except Exception:
        return '<span class="nt">—</span>'

def _cf_cls(v):
    try:
        vv = float(v)
        if vv > 0: return "up"
        if vv < 0: return "dn"
        return "nt"
    except Exception:
        return "nt"

def _cf_amount_span(v):
    try:
        vv = float(v)
        if vv > 0: return f'<span class="up">{fmt_amount_cn(vv)}</span>'
        if vv < 0: return f'<span class="dn">{fmt_amount_cn(vv)}</span>'
        return f'<span class="nt">0</span>'
    except Exception:
        return '<span class="nt">—</span>'

def compute_indicators(s, w, cf):
    """Compute RSI, MACD, MA, support/resistance from available data."""
    ind = {}
    close = w.get("close") or (s.get("price") and float(s.get("price"))) or 0
    # RSI from capital flow days chg_pct
    if cf and cf.get("ok") and len(cf["days"]) >= 5:
        n = min(len(cf["days"]), 14)
        chgs = [cf["days"][i].get("chg_pct") or 0 for i in range(-n, 0)]
        gains = [max(c, 0) for c in chgs]
        losses = [abs(min(c, 0)) for c in chgs]
        ag = sum(gains) / n
        al = sum(losses) / n
        ind["rsi"] = round(100 - 100 / (1 + ag / al), 1) if al > 0 else 100
    # MACD from close in cf days
    if cf and cf.get("ok") and len(cf["days"]) >= 26:
        closes = [d.get("close", 0) for d in cf["days"]]
        def _ema(data, p):
            k = 2.0 / (p + 1)
            r = [data[0]]
            for v in data[1:]: r.append(v * k + r[-1] * (1 - k))
            return r
        e12 = _ema(closes[-12:] if len(closes) >= 12 else closes, 12)[-1]
        e26 = _ema(closes[-26:] if len(closes) >= 26 else closes, 26)[-1]
        macd = e12 - e26
        macd_hist_vals = [_ema(closes[-12:] if len(closes) >= 12 else closes, 12)[i] -
                          _ema(closes[-26:] if len(closes) >= 26 else closes, 26)[i]
                          for i in range(len(_ema(closes[-26:] if len(closes) >= 26 else closes, 26)))]
        sig = sum(macd_hist_vals[-9:]) / min(9, len(macd_hist_vals)) if len(macd_hist_vals) >= 9 else macd
        ind["macd"] = round(macd, 3)
        ind["macd_signal"] = round(sig, 3)
        ind["macd_hist"] = round(macd - sig, 3)
    # MA from Baostock watch data
    ind["ma5"] = w.get("ma5")
    ind["ma10"] = w.get("ma10")
    if ind["ma5"] and ind["ma10"]:
        ind["ma_cross"] = "金叉" if ind["ma5"] > ind["ma10"] else "死叉"
    # Support / Resistance
    ind["resistance"] = w.get("high20")
    ind["support"] = w.get("low20")
    ind["pct_from_high"] = w.get("pct_from_high")
    ind["pct_from_low"] = w.get("pct_from_low")
    # Range position
    h20, l20 = w.get("high20", 0), w.get("low20", 0)
    if h20 and l20 and h20 != l20:
        ind["range_pos"] = round((close - l20) / (h20 - l20) * 100, 1)
    else:
        ind["range_pos"] = 50
    # 5-day momentum
    ind["up5"] = w.get("up5", 0)
    ind["up5_pct"] = round(w.get("pctChg") or 0, 2)
    # Volume ratio proxy (from amount)
    if cf and cf.get("ok") and len(cf["days"]) >= 5:
        today_amt = abs(cf["days"][-1].get("main", 0) + cf["days"][-1].get("small", 0))
        prev_amts = [abs(cf["days"][i].get("main", 0) + cf["days"][i].get("small", 0))
                     for i in range(-5, -1)]
        avg_amt = sum(prev_amts) / max(len(prev_amts), 1) if prev_amts else 1
        ind["vol_ratio"] = round(today_amt / avg_amt, 1) if avg_amt > 0 else 1
    return ind

def _tag(cls, text):
    return "<div class=\'da-tag " + cls + "\'>" + text + "</div>"

def render_depth_analysis(s, w, cf, tech, news_latest=None):
    """Render depth analysis HTML for a single stock."""
    name = s.get("name", "")
    close = w.get("close") or (s.get("price") and float(s.get("price"))) or 0
    tag = s.get("tag", "")

    # ── RSI ──
    rsi = tech.get("rsi")
    if rsi is not None:
        if rsi >= 70:   rc, rt = "ovb", "超买"
        elif rsi <= 30: rc, rt = "ovs", "超卖"
        elif rsi >= 60: rc, rt = "str", "偏强"
        elif rsi <= 40: rc, rt = "wkr", "偏弱"
        else:           rc, rt = "neu", "中性"
        rsi_html = "<div class=\'da-row\'><div class=\'da-cell\'>" + _tag(rc, "RSI(14) " + str(rsi) + " · " + rt) + "</div>"
    else:
        rsi_html = "<div class=\'da-row\'><div class=\'da-cell\'>" + _tag("neu", "RSI(14) —") + "</div>"

    # ── MACD ──
    macd = tech.get("macd"); macd_sig = tech.get("macd_signal")
    if macd is not None and macd_sig is not None:
        mc = "up" if macd > 0 else "dn"
        mi = "▲" if macd >= 0 else "▼"
        hc = "up" if tech.get("macd_hist", 0) >= 0 else "dn"
        hi = "▲" if tech.get("macd_hist", 0) >= 0 else "▼"
        macd_html = ("<div class=\'da-cell\'>" +
            _tag(mc, mi + " " + str(abs(macd)) +
                 " &nbsp;<span class=\'cf-pct " + hc + "\'>" + hi + str(abs(tech.get("macd_hist", 0))) + "</span>") +
            "</div></div>")
    else:
        macd_html = "<div class=\'da-cell\'>" + _tag("neu", "MACD —") + "</div></div>"

    # ── MA ──
    ma5 = tech.get("ma5"); ma10 = tech.get("ma10")
    if ma5 and ma10:
        xc = "up" if close > ma5 else "dn"
        xn = tech.get("ma_cross", "")
        ma_txt = "MA5 " + ("%.2f" % ma5) + " / MA10 " + ("%.2f" % ma10) + " · <span class=\'" + xc + "\'>" + xn + "</span>"
    elif ma5:
        ma_txt = "MA5 " + ("%.2f" % ma5)
    else:
        ma_txt = "MA 数据不可用"
    ma_html = "<div class=\'da-row\'><div class=\'da-cell\'>" + _tag("neu", ma_txt) + "</div>"

    # ── Range / Support ──
    res = tech.get("resistance"); sup = tech.get("support"); pos = tech.get("range_pos", 50)
    if res and sup:
        pc = "up" if pos > 50 else "dn"
        range_txt = ("区间 " + ("%.2f" % sup) + "~" + ("%.2f" % res) +
                     " · <span class=\'" + pc + "\'>当前位置 " + str(pos) + "%</span>")
    else:
        range_txt = "—"
    range_html = "<div class=\'da-cell\'>" + _tag("neu", range_txt) + "</div></div>"

    # ── Momentum ──
    up5 = tech.get("up5", 0); up5pct = tech.get("up5_pct", 0)
    mc = "up" if up5 >= 3 else ("dn" if up5 <= 1 else "neu")
    mom_html = ("<div class=\'da-row\'><div class=\'da-cell\'>" +
                _tag(mc, "近5日 " + str(up5) + "涨 · 今日 " + ("%+0.2f" % up5pct) + "%") + "</div>")

    # ── Volume ──
    vr = tech.get("vol_ratio")
    if vr is not None:
        vc = "up" if vr > 1 else "dn"
        vol_html = "<div class=\'da-cell\'>" + _tag(vc, "量比 " + str(vr) + "x") + "</div></div>"
    else:
        vol_html = "<div class=\'da-cell\'>" + _tag("neu", "量比 —") + "</div></div>"

    tech_section = ("<div class=\'tech-grid\'>" + rsi_html + macd_html +
                    ma_html + range_html + mom_html + vol_html + "</div>")

    # ── Sentiment ──
    sent_parts = []
    if cf and cf.get("ok"):
        today = cf.get("today", {})
        main_net = today.get("main", 0)
        small_net = today.get("small", 0)
        main5 = cf.get("sum5", {}).get("main", 0)
        if main_net > 50000000:
            sent_parts.append(_tag("up", "主力净流入 +" + ("%.1f" % (main_net / 100000000)) + "亿 · 强势"))
        elif main_net < -50000000:
            sent_parts.append(_tag("dn", "主力净流出 " + ("%.1f" % (abs(main_net) / 100000000)) + "亿 · 偏弱"))
        else:
            sent_parts.append(_tag("neu", "主力净流入 " + ("%.1f" % (main_net / 100000000)) + "亿 · 中性"))
        if small_net > 0:
            sent_parts.append(_tag("neu", "散户跟入 +" + ("%.1f" % (small_net / 100000000)) + "亿"))
        elif small_net < 0:
            sent_parts.append(_tag("neu", "散户减仓 " + ("%.1f" % (abs(small_net) / 100000000)) + "亿"))
        if main5 > 0:
            sent_parts.append(_tag("up", "5日主力净流入 +" + ("%.1f" % (main5 / 100000000)) + "亿"))
        elif main5 < 0:
            sent_parts.append(_tag("dn", "5日主力净流出 " + ("%.1f" % (abs(main5) / 100000000)) + "亿"))
        total_f = abs(main_net) + abs(small_net)
        main_ratio = abs(main_net) / total_f * 100 if total_f > 0 else 0
        if main_ratio > 70:
            sent_parts.append(_tag("ovb", "主力控盘度 " + ("%.0f" % main_ratio) + "% · 高度控盘"))
        elif main_ratio > 50:
            sent_parts.append(_tag("str", "主力占比 " + ("%.0f" % main_ratio) + "% · 持续流入"))
    else:
        sent_parts.append(_tag("neu", "资金数据暂不可用"))

    sentiment_section = ("<div class=\'sentiment-items\'>" + "".join(sent_parts) + "</div>")

    # ── Key events ──
    events_html = ""
    if news_latest:
        matched = []
        for h in news_latest:
            if name and name in h:
                matched.append(h)
            elif tag:
                for tk in tag.split("/"):
                    tk = tk.strip()
                    if len(tk) > 1 and tk in h:
                        matched.append(h); break
            if len(matched) >= 2: break
        if matched:
            ev_items = "".join("<li>" + ev + "</li>" for ev in matched)
            events_html = "<div class=\'ev-title\'>📌 关联事件</div><ul class=\'ev-list\'>" + ev_items + "</ul>"

    # ── Verdict ──
    score = 0
    if rsi:
        if 40 <= rsi <= 60: score += 1
        elif rsi < 30: score += 2
        elif rsi > 70: score -= 1
    if tech.get("ma_cross") == "金叉": score += 2
    if main_net > 0: score += 1
    if up5 >= 4: score += 1
    if up5 <= 1: score -= 1
    if score >= 3:   vc, vt = "up", "偏多"
    elif score <= -1: vc, vt = "dn", "偏空"
    else:            vc, vt = "neu", "中性"

    verdict_html = ("<div class=\'da-verdict\'>"
                    "<span class=\'verdict-label\'>综合研判</span>"
                    "<span class=\'da-tag " + vc + " verdict-score\'>" + vt + "（评分 " + str(score) + "）</span>"
                    "</div>")

    return ("<div class=\'depth-section\'>"
            "<div class=\'depth-toggle rotated\' onclick=\'this.nextElementSibling.classList.toggle(\"hidden\");this.classList.toggle(\"rotated\")\'>"
            "<span class=\'depth-toggle-icon\'>▸</span>📊 深度分析"
            "</div>"
            "<div class=\'depth-body\'>"
            "<div class=\'depth-cols\'>"
            "<div class=\'depth-col\'><div class=\'depth-sub-title\'>🧠 技术面</div>" + tech_section + "</div>"
            "<div class=\'depth-col\'><div class=\'depth-sub-title\'>💰 资金面</div>" + sentiment_section + events_html + "</div>"
            "</div>"
            + verdict_html
            + "</div></div>")

def render_capital_flow(cf):
    if not cf or not cf.get("ok"):
        err = (cf or {}).get("error", "")
        return (
            '<div class="cf-wrap cf-empty">'
            '<div class="cf-title">💰 主力资金追踪</div>'
            f'<div class="cf-note">数据暂不可用{("：" + err) if err else ""}</div>'
            '</div>'
        )
    days = cf["days"]
    today = cf["today"]
    sum5 = cf["sum5"]
    sum10 = cf["sum10"]

    main_pct = today.get("main_pct")
    pct_html = f'<span class="cf-pct">{main_pct:+.2f}%</span>' if main_pct is not None else ""

    breakdown = [
        ("超大单", today["xlarge"]), ("大单", today["large"]),
        ("中单", today["medium"]), ("小单", today["small"]),
    ]
    breakdown_html = "".join(
        f'<div class="cf-item"><span class="cf-k">{k}</span>{_cf_amount_span(v)}</div>'
        for k, v in breakdown
    )

    W, H = 560, 150
    PAD_L, PAD_R, PAD_T, PAD_B = 6, 6, 14, 22
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    n = len(days)
    gap = 4
    bar_w = max(4, (plot_w - gap * (n - 1)) / max(n, 1))
    max_abs = max((abs(d["main"]) for d in days), default=1.0) or 1.0
    mid_y = PAD_T + plot_h / 2
    bars, labels = [], []
    for i, d in enumerate(days):
        x = PAD_L + i * (bar_w + gap)
        v = d["main"]
        h = (abs(v) / max_abs) * (plot_h / 2)
        color = "#dc2626" if v > 0 else ("#16a34a" if v < 0 else "#cbd5e1")
        if v >= 0:
            y, rect_h = mid_y - h, h
        else:
            y, rect_h = mid_y, h
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(rect_h,0.5):.1f}" fill="{color}" rx="1"/>')
        if n <= 6 or i == 0 or i == n - 1 or i % max(1, n // 5) == 0:
            mmdd = d["date"][5:] if len(d["date"]) >= 10 else d["date"]
            lx = x + bar_w / 2
            labels.append(f'<text x="{lx:.1f}" y="{H - 6}" font-size="9" fill="#94a3b8" text-anchor="middle">{mmdd}</text>')
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" class="cf-svg" preserveAspectRatio="xMidYMid meet">'
        f'<rect width="{W}" height="{H}" fill="#fafbfc" rx="4"/>'
        f'<line x1="{PAD_L}" y1="{mid_y:.1f}" x2="{W-PAD_R}" y2="{mid_y:.1f}" stroke="#e2e8f0" stroke-dasharray="2,2"/>'
        + "".join(bars) + "".join(labels) + '</svg>'
    )

    return f"""
      <div class="cf-wrap">
        <div class="cf-header">
          <div class="cf-title">💰 主力资金追踪 · 近 {len(days)} 交易日</div>
          <div class="cf-hint">数据：东方财富 fflow · 单位 元</div>
        </div>
        <div class="cf-kpis">
          <div class="cf-kpi"><div class="cf-label">今日主力净流入</div><div class="cf-value">{_cf_amount_span(today['main'])}{pct_html}</div></div>
          <div class="cf-kpi"><div class="cf-label">近 5 日合计</div><div class="cf-value">{_cf_amount_span(sum5['main'])}</div></div>
          <div class="cf-kpi"><div class="cf-label">近 {len(days)} 日合计</div><div class="cf-value">{_cf_amount_span(sum10['main'])}</div></div>
        </div>
        <div class="cf-breakdown">
          <div class="cf-bd-title">今日 5 档资金拆解</div>
          <div class="cf-bd-row">{breakdown_html}</div>
        </div>
        {svg}
      </div>"""

def compute_deep_indicators(s, w, cf):
    """
    Compute comprehensive technical indicators.
    KDJ(9,3,3), Bollinger Bands(20,2), ATR(14), ADX(14), OBV, MA system, score/verdict.
    """
    import statistics
    ind = {}
    close = w.get("close") or (s.get("price") and float(s.get("price"))) or 0
    high20 = w.get("high20") or close
    low20 = w.get("low20") or close

    # OHLCV from Baostock (extra history for KDJ)
    code = w.get("code", s.get("code", ""))
    # Build full 9-char Baostock code
    numeric = code.split(".")[-1] if "." in code else code
    full_code = numeric if len(numeric) == 9 else code  # use as-is if already 9-char
    df_kl = None
    try:
        import baostock as bs
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=8)))
        end_d = now.strftime("%Y-%m-%d")
        start_d = (now - timedelta(days=50)).strftime("%Y-%m-%d")
        rs = bs.query_history_k_data_plus(full_code,
            fields="date,open,high,low,close,volume,amount,pctChg",
            start_date=start_d, end_date=end_d, frequency="d", adjustflag="2")
        data = []
        while rs.error_code == '0' and rs.next():
            data.append(rs.get_row_data())
        if data:
            import pandas as pd
            cols = ["date","open","high","low","close","volume","amount","pctChg"]
            df_kl = pd.DataFrame(data, columns=cols)
            for c in ["open","high","low","close","volume","amount","pctChg"]:
                df_kl[c] = pd.to_numeric(df_kl[c], errors="coerce")
    except Exception:
        pass

    kl  = df_kl.tail(30)["close"].tolist() if df_kl is not None and len(df_kl) > 9 else []
    kl_h = df_kl.tail(30)["high"].tolist() if df_kl is not None and len(df_kl) > 9 else []
    kl_l = df_kl.tail(30)["low"].tolist()  if df_kl is not None and len(df_kl) > 9 else []
    kl_v = df_kl.tail(30)["volume"].tolist() if df_kl is not None and len(df_kl) > 9 else []

    # KDJ (9,3,3)
    n = 9
    if len(kl_l) >= n:
        kvals, dvals = [50.0], [50.0]
        for i in range(n, len(kl_l) + 1):
            wl = min(kl_l[i-n:i]); wh = max(kl_h[i-n:i])
            rsv = (kl[i-1] - wl) / (wh - wl) * 100.0 if wh != wl else 50.0
            kvals.append(kvals[-1] * 2.0/3.0 + rsv / 3.0)
        for kv in kvals[1:]:
            dvals.append(dvals[-1] * 2.0/3.0 + kv / 3.0)
        j = 3.0 * kvals[-1] - 2.0 * dvals[-1]
        ind["kdj_k"] = round(kvals[-1], 1)
        ind["kdj_d"] = round(dvals[-1], 1)
        ind["kdj_j"] = round(j, 1)
        if j > 80:                  ind["kdj_signal"] = "超买"
        elif j < 20:               ind["kdj_signal"] = "超卖"
        elif kvals[-1] > dvals[-1] and kvals[-1] < 30:  ind["kdj_signal"] = "低位金叉"
        elif kvals[-1] > dvals[-1]: ind["kdj_signal"] = "金叉"
        elif kvals[-1] < dvals[-1] and kvals[-1] > 70:  ind["kdj_signal"] = "高位死叉"
        elif kvals[-1] < dvals[-1]: ind["kdj_signal"] = "死叉"
        else:                       ind["kdj_signal"] = "中性"
    else:
        ind["kdj_k"] = ind["kdj_d"] = ind["kdj_j"] = None
        ind["kdj_signal"] = "数据不足"

    # Bollinger Bands (20,2)
    if len(kl) >= 20:
        ma20 = statistics.mean(kl[-20:])
        std = statistics.pstdev(kl[-20:])
        upper = ma20 + 2.0 * std; lower = ma20 - 2.0 * std
        ind["boll_mid"]   = round(ma20, 2)
        ind["boll_upper"] = round(upper, 2)
        ind["boll_lower"] = round(lower, 2)
        pos = (close - lower) / (upper - lower) * 100.0 if upper != lower else 50.0
        ind["boll_pos"] = round(pos, 1)
        if close < lower:            ind["boll_signal"] = "下轨下方（超卖）"
        elif close > upper:           ind["boll_signal"] = "上轨上方（超买）"
        elif pos > 80:                ind["boll_signal"] = "上轨附近（偏强）"
        elif pos < 20:                ind["boll_signal"] = "下轨附近（偏弱）"
        else:                         ind["boll_signal"] = "布林带内运行"
    else:
        ind["boll_signal"] = "数据不足"

    # ATR (14)
    if len(kl) >= 15 and len(kl_h) >= 15:
        trs = []
        for i in range(-15, 0):
            hl = kl_h[i] - kl_l[i]
            trs.append(max(hl, abs(kl_h[i] - kl[i-1]), abs(kl_l[i] - kl[i-1])))
        ind["atr"] = round(sum(trs[-14:]) / 14.0, 3) if len(trs) >= 14 else None

    # ADX (14) - simplified
    # MACD (12,26,9)
    if len(kl) >= 26:
        def _ema3(data, period):
            k = 2.0 / (period + 1)
            ema = [data[0]]
            for v in data[1:]:
                ema.append(v * k + ema[-1] * (1 - k))
            return ema
        e12 = _ema3(kl, 12)
        e26 = _ema3(kl, 26)
        dif = e12[-1] - e26[-1]
        dif_s = [e12[i] - e26[i] for i in range(len(e26))]
        sig = sum(dif_s[-9:]) / min(9, len(dif_s)) if len(dif_s) >= 9 else dif_s[-1]
        hist = dif - sig
        ind["macd_dif"] = round(dif, 3)
        ind["macd_dea"] = round(sig, 3)
        ind["macd_hist"] = round(hist, 3)
        if dif > sig and hist > 0:     ind["macd_signal"] = "MACD 金叉（偏多）"
        elif dif < sig and hist < 0: ind["macd_signal"] = "MACD 死叉（偏空）"
        elif dif > sig:              ind["macd_signal"] = "MACD 零轴上方"
        elif dif < sig:              ind["macd_signal"] = "MACD 零轴下方"
        else:                         ind["macd_signal"] = "MACD 中性"
    else:
        ind["macd_signal"] = "数据不足"

    # 20/60/250 day MA
    for period, name in [(20,"ma20"), (60,"ma60"), (250,"ma250")]:
        if len(kl) >= period:
            ind[name] = round(sum(kl[-period:]) / period, 2)
        else:
            ind[name] = None

    if len(kl) >= 15 and len(kl_h) >= 15:
        pdm = [max(kl_h[i]-kl_h[i-1], 0) if (kl_h[i]-kl_h[i-1]) > (kl_l[i-1]-kl_l[i]) else 0 for i in range(-14, 0)]
        ndm = [max(kl_l[i-1]-kl_l[i], 0) if (kl_l[i-1]-kl_l[i]) > (kl_h[i]-kl_h[i-1]) else 0 for i in range(-14, 0)]
        sp, sn = sum(pdm), sum(ndm)
        adx = min(abs(sp - sn) / (sp + sn + 0.001) * 100.0, 100.0)
        ind["adx"] = round(adx, 1)
        ind["adx_signal"] = "强趋势" if adx > 30 else ("趋势运行" if adx > 20 else ("震荡市" if adx > 15 else "趋势不明"))
    else:
        ind["adx"] = None; ind["adx_signal"] = "数据不足"

    # OBV
    if len(kl) >= 2 and len(kl_v) >= 2:
        obv = sum((kl_v[i] if kl[i] > kl[i-1] else -kl_v[i] if kl[i] < kl[i-1] else 0)
                  for i in range(1, min(len(kl), len(kl_v))))
        obv_p = sum((kl_v[i] if kl[i] > kl[i-1] else -kl_v[i] if kl[i] < kl[i-1] else 0)
                  for i in range(1, min(len(kl)-1, len(kl_v)-1)))
        ind["obv"] = round(obv / 100000000.0, 2)
        ind["obv_trend"] = "上升" if obv > obv_p else "下降"

    # MA system
    ma5 = w.get("ma5"); ma10 = w.get("ma10")
    if ma5 and ma10:
        if close > ma5 > ma10:       ind["ma_signal"] = "多头排列（强势）"
        elif close < ma5 < ma10:    ind["ma_signal"] = "空头排列（弱势）"
        elif close > ma5:           ind["ma_signal"] = "MA5上方"
        else:                        ind["ma_signal"] = "MA5下方"
    else:
        ind["ma_signal"] = "数据不足"

    # Support / Resistance
    if high20 and low20 and high20 != low20:
        rng = high20 - low20
        ind["resistance1"] = round(high20, 2)
        ind["resistance2"] = round(high20 + rng * 0.5, 2)
        ind["support1"] = round(low20, 2)
        ind["support2"] = round(low20 - rng * 0.5, 2)
    else:
        ind["resistance1"] = round(close * 1.02, 2)
        ind["resistance2"] = round(close * 1.05, 2)
        ind["support1"] = round(close * 0.98, 2)
        ind["support2"] = round(close * 0.95, 2)

    # Volume ratio
    if df_kl is not None and len(df_kl) >= 5:
        avg5 = df_kl.tail(5)["volume"].mean()
        tv   = df_kl.iloc[-1]["volume"] if len(df_kl) >= 1 else 0
        ind["vol_ratio"] = round(tv / avg5, 2) if avg5 else 1.0

    # ROE, PE, PB from Baostock
    try:
        import baostock as bs
        rs_p = bs.query_profit_data(code=full_code, year=2025, quarter=4)
        prof_data = []
        while rs_p.error_code == '0' and rs_p.next():
            prof_data.append(rs_p.get_row_data())
        if prof_data and len(prof_data) > 0:
            # fields: code,pubDate,statDate,roeAvg,npMargin,gpMargin,netProfit,epsTTM,MBRevenue,totalShare,liqaShare
            roe_val = prof_data[0][3]  # roeAvg is index 3
            if roe_val:
                ind["roe"] = round(float(roe_val) * 100, 2)  # as percentage
            np_margin = prof_data[0][4]  # net profit margin
            if np_margin:
                ind["net_margin"] = round(float(np_margin) * 100, 2)
    except Exception:
        pass

    # Market PE percentile
    try:
        import warnings as _w; _w.filterwarnings("ignore")
        import os as _os; _os.environ["SSL_CERT_FILE"] = "/etc/ssl/cert.pem"
        import akshare as ak
        df_pe = ak.stock_a_ttm_lyr()
        if df_pe is not None and len(df_pe) > 0:
            lv = df_pe.iloc[-1]
            ind["market_pe"]    = round(float(lv.get("middlePETTM") or 0), 1)
            ind["market_pe_pct"]  = round(float(lv.get("quantileInAllHistoryMiddlePeTtm") or 0) * 100, 1)
            ind["market_pe_10y"]  = round(float(lv.get("quantileInRecent10YearsMiddlePeTtm") or 0) * 100, 1)
    except Exception:
        pass

    # Score synthesis
    score = 0; sigs = []
    ks = ind.get("kdj_signal", "")
    if ks in ("超卖", "低位金叉"):     score += 2; sigs.append("KDJ低位")
    if "超买" in ks:                  score -= 1; sigs.append("KDJ超买")
    if "金叉" in ks and "低位" not in ks: score += 1; sigs.append("KDJ金叉")
    if "死叉" in ks and "高位" not in ks: score -= 1; sigs.append("KDJ死叉")
    if ind.get("boll_signal", "").startswith("下轨"):  score += 1; sigs.append("BOLL下轨")
    if ind.get("boll_signal", "").startswith("上轨"):  score -= 1; sigs.append("BOLL上轨")
    if ind.get("ma_signal", "").startswith("多头"):    score += 2; sigs.append("MA多头")
    if ind.get("ma_signal", "").startswith("空头"):   score -= 2; sigs.append("MA空头")
    if ind.get("adx_signal") == "强趋势":
        score += (1 if (ind.get("kdj_k") or 50) > 50 else -1); sigs.append("强趋势")
    if ind.get("obv_trend") == "上升": score += 1; sigs.append("OBV上升")
    ms = ind.get("macd_signal", "")
    if "金叉" in ms: score += 2; sigs.append("MACD金叉")
    if "死叉" in ms: score -= 2; sigs.append("MACD死叉")
    if "零轴上方" in ms: score += 1; sigs.append("MACD零轴上")
    if "零轴下方" in ms: score -= 1; sigs.append("MACD零轴下")

    if score >= 3:       verdict, v_cls = "偏多", "up"
    elif score <= -2:    verdict, v_cls = "偏空", "dn"
    elif score >= 1:     verdict, v_cls = "震荡偏多", "up"
    elif score <= -1:    verdict, v_cls = "震荡偏空", "dn"
    else:                verdict, v_cls = "中性震荡", "neu"
    ind["score"] = score; ind["signals"] = sigs
    ind["verdict"] = verdict; ind["verdict_cls"] = v_cls
    return ind

def _sc(cl, txt):
    return "<span class='" + cl + "'>" + txt + "</span>"

def render_deep_analysis(s, w, cf, tech):
    """Render enhanced deep analysis HTML for a single stock."""
    name = s.get("name", ""); tag = s.get("tag", "")
    close = w.get("close") or (s.get("price") and float(s.get("price"))) or 0

    # KDJ
    kk = tech.get("kdj_k"); kd = tech.get("kdj_d"); kj = tech.get("kdj_j")
    ks = tech.get("kdj_signal", "")
    if kk is not None:
        kc = "ovb" if kk > 80 else ("ovs" if kk < 20 else ("str" if kk > 50 else "wkr"))
        kdj_html = ("<div class='da-tag " + kc + "'>KDJ K:" + ("%.1f" % kk) +
                    " D:" + ("%.1f" % kd) + " J:" + ("%.1f" % kj) + " · " + ks + "</div>")
    else:
        kdj_html = "<div class='da-tag neu'>KDJ — " + ks + "</div>"

    # MACD
    ms = tech.get("macd_signal", "")
    dif = tech.get("macd_dif"); dea = tech.get("macd_dea"); hist = tech.get("macd_hist")
    if ms != "数据不足" and dif is not None:
        mc = "up" if dif > 0 else "dn"
        hc = "up" if (hist or 0) > 0 else "dn"
        macd_html = ("<div class='da-tag " + mc + "'>MACD DIF:" + ("%.3f" % dif) +
                     " DEA:" + ("%.3f" % dea) + " · " + ms +
                     " <span class='" + hc + "'>柱:" + ("%.3f" % (hist or 0)) + "</span></div>")
    else:
        macd_html = "<div class='da-tag neu'>MACD — " + ms + "</div>"

    # Bollinger
    bs = tech.get("boll_signal", ""); bp = tech.get("boll_pos")
    if bs != "数据不足" and bp is not None:
        pc = "up" if bp > 50 else "dn"
        boll_html = "<div class='da-tag neu'>BOLL " + bs + " · 位置" + _sc(pc, " %.0f%%" % bp) + "</div>"
    else:
        boll_html = "<div class='da-tag neu'>BOLL —</div>"

    # ADX
    ax = tech.get("adx"); adxs = tech.get("adx_signal", "")
    if ax is not None:
        ac = "up" if ax > 25 else ("dn" if ax < 15 else "neu")
        adx_html = "<div class='da-tag " + ac + "'>ADX " + ("%.1f" % ax) + " · " + adxs + "</div>"
    else:
        adx_html = "<div class='da-tag neu'>ADX —</div>"

    # OBV
    obv = tech.get("obv"); obt = tech.get("obv_trend", "")
    if obv is not None:
        oc = "up" if obt == "上升" else "dn"
        obv_html = "<div class='da-tag " + oc + "'>OBV " + ("%.2f亿" % obv) + " · " + obt + "</div>"
    else:
        obv_html = "<div class='da-tag neu'>OBV —</div>"

    # MA20/60/250 system
    ma20 = tech.get("ma20"); ma60 = tech.get("ma60"); ma250 = tech.get("ma250")
    ma5 = tech.get("ma5") or w.get("ma5"); ma10 = tech.get("ma10") or w.get("ma10")
    ms = tech.get("ma_signal", "")
    if ma20 and ma60 and ma250:
        cnt = sum([close > ma20, close > ma60, close > ma250])
        if cnt == 3:    ma_long = "多头排列（强势）"; mlc = "up"
        elif cnt == 0: ma_long = "空头排列（弱势）"; mlc = "dn"
        elif cnt >= 2: ma_long = "偏多"; mlc = "up"
        else:           ma_long = "偏弱"; mlc = "dn"
        ma_txt = ("MA20:" + ("%.1f" % ma20) + " MA60:" + ("%.1f" % ma60) +
                  " MA250:" + ("%.1f" % ma250) + " · " + ma_long)
        ma_html = "<div class='da-tag " + mlc + "'>" + ma_txt + "</div>"
    elif ma5 and ma10:
        mtxt = ("MA5:" + ("%.2f" % ma5) + " MA10:" + ("%.2f" % ma10) + " · " + ms)
        ma_html = "<div class='da-tag neu'>" + mtxt + "</div>"
    else:
        ma_html = "<div class='da-tag neu'>均线数据不足</div>"

    # S/R
    r1 = tech.get("resistance1"); r2 = tech.get("resistance2")
    s1 = tech.get("support1"); s2 = tech.get("support2")
    sr_html = ("<div class='da-tag neu'>" +
               "阻力 " + ("%.2f" % r1 if r1 else "—") + " / " + ("%.2f" % r2 if r2 else "—") +
               " · 支承 " + ("%.2f" % s1 if s1 else "—") + " / " + ("%.2f" % s2 if s2 else "—") + "</div>")

    # ATR
    atr = tech.get("atr")
    if atr is not None and close:
        ap = atr / close * 100.0
        atr_html = "<div class='da-tag neu'>ATR " + ("%.3f" % atr) + "（波动 " + ("%.1f%%" % ap) + "）</div>"
    else:
        atr_html = "<div class='da-tag neu'>ATR —</div>"

    # Volume
    vr = tech.get("vol_ratio")
    vc = "up" if (vr or 1) > 1.2 else ("dn" if (vr or 1) < 0.8 else "neu")
    vr_html = "<div class='da-tag " + vc + "'>量比 " + ("%.2fx" % vr if vr else "—") + "</div>"

    tech_rows = (
        "<div class='da-row'><div class='da-cell'>" + kdj_html + "</div><div class='da-cell'>" + macd_html + "</div></div>"
        "<div class='da-row'><div class='da-cell'>" + adx_html + "</div><div class='da-cell'>" + obv_html + "</div></div>"
        "<div class='da-row' style='flex-wrap:wrap'><div class='da-cell' style='min-width:100%'>" + ma_html + "</div></div>"
        "<div class='da-row'><div class='da-cell'>" + sr_html + "</div><div class='da-cell'>" + atr_html + "</div></div>"
        "<div class='da-row'><div class='da-cell'>" + vr_html + "</div></div>"
    )

    # Sentiment
    sp = []
    if cf and cf.get("ok"):
        mn  = cf.get("today", {}).get("main") or 0
        sn_ = cf.get("today", {}).get("small") or 0
        m5  = cf.get("sum5", {}).get("main") or 0
        m10 = cf.get("sum10", {}).get("main") or 0
        if mn > 100000000:    sc, st = "up", "主力强势净流入"
        elif mn < -100000000: sc, st = "dn", "主力净流出"
        elif mn > 30000000:   sc, st = "up", "主力温和净流入"
        elif mn < -30000000:  sc, st = "dn", "主力温和净流出"
        else:                 sc, st = "neu", "主力进出平衡"
        sp.append("<div class='da-tag " + sc + "'>" + st + " " + ("%+0.1f亿" % (mn/100000000)) + "</div>")
        sc5 = "up" if m5 > 50000000 else ("dn" if m5 < -50000000 else "neu")
        st5 = "5日净流入" if m5 > 50000000 else ("5日净流出" if m5 < -50000000 else "5日平衡")
        sp.append("<div class='da-tag " + sc5 + "'>" + st5 + " " + ("%+0.1f亿" % (m5/100000000)) + "</div>")
        sc10 = "up" if m10 > 100000000 else ("dn" if m10 < -100000000 else "neu")
        st10 = "10日强势" if m10 > 100000000 else ("10日偏弱" if m10 < -100000000 else "10日中性")
        sp.append("<div class='da-tag " + sc10 + "'>" + st10 + " " + ("%+0.1f亿" % (m10/100000000)) + "</div>")
        tr = abs(mn) + abs(sn_)
        mr = abs(mn) / tr * 100.0 if tr > 0 else 0
        rc2 = "ovb" if mr > 70 else ("str" if mr > 50 else ("wkr" if mr < 30 else "neu"))
        rt2 = "高度控盘" if mr > 70 else ("主力主导" if mr > 50 else ("资金分散" if mr < 30 else "散户主导"))
        sp.append("<div class='da-tag " + rc2 + "'>" + rt2 + "（" + ("%.0f%%" % mr) + "）</div>")
    else:
        sp.append("<div class='da-tag neu'>资金数据不可用</div>")

    # Verdict
    score = tech.get("score", 0); sigs = tech.get("signals", [])
    vt = tech.get("verdict", "中性"); vc = tech.get("verdict_cls", "neu")
    vhtml = ("<div class='da-verdict'>"
             "<span class='verdict-label'>综合研判</span>"
             "<span class='da-tag " + vc + " verdict-score'>" + vt + "（" + str(score) + "分）</span>"
             + ("<span class='sig-tag'>" + " · ".join(sigs) + "</span>" if sigs else "")
             + "</div>")

    # Market PE + ROE
    mhtml = ""
    mpe = tech.get("market_pe"); mpct = tech.get("market_pe_pct"); m10y = tech.get("market_pe_10y")
    if mpe and mpct:
        mpc = "up" if mpct > 70 else ("dn" if mpct < 30 else "neu")
        m10y_c = "up" if (m10y or 0) > 50 else "dn"
        mhtml = ("<div class='mkt-context'>"
                 "<span class='mkt-label'>大盘估值</span>"
                 "<span class='da-tag " + mpc + "'>全市场PE " + ("%.1f" % mpe) +
                 " · 历史分位 " + ("%.0f%%" % mpct) + "</span>"
                 "<span class='da-tag " + m10y_c + "'>10年分位 " + ("%.0f%%" % (m10y or 0)) + "</span></div>")
    roe = tech.get("roe")
    if roe:
        rcls = "up" if roe > 15 else ("str" if roe > 8 else "neu")
        mhtml += ("<div class='mkt-context'>"
                  "<span class='mkt-label'>基本面</span>"
                  "<span class='da-tag " + rcls + "'>ROE " + ("%.1f" % roe) + "%</span>"
                  + ("<span class='da-tag str'>净利润率 " + ("%.1f" % tech.get("net_margin", 0)) + "%</span>" if tech.get("net_margin") else "") + "</div>")

    toggle_onclick = "this.nextElementSibling.classList.toggle(&quot;hidden&quot;);this.classList.toggle(&quot;rotated&quot;)"

    return (
        "<div class='depth-section'>"
        "<div class='depth-toggle rotated' onclick='" + toggle_onclick + "'>"
        "<span class='depth-toggle-icon'>▸</span>📊 深度分析"
        "</div>"
        "<div class='depth-body'>"
        + mhtml
        + "<div class='depth-cols'>"
        "<div class='depth-col'><div class='depth-sub-title'>🧠 技术面</div><div class='tech-grid'>" + tech_rows + "</div></div>"
        "<div class='depth-col'><div class='depth-sub-title'>💰 资金面</div><div class='sentiment-items'>" + "".join(sp) + "</div></div>"
        + "</div>"
        + vhtml
        + "</div></div>"
    )


def _render_stock_tech_charts(code, w):
    """Fetch 90-day OHLCV from Baostock and render MACD/BOLL/KDJ charts."""
    # Ensure baostock is logged in
    try:
        bs.login()
    except Exception:
        pass
    raw = code.split(".")[-1] if "." in code else code
    # Determine market prefix from w or code pattern
    mkt = (w.get("market") or "").lower()
    if mkt == "sz" or (not mkt and len(code) == 6 and code.startswith(("0", "3"))):
        prefix = "sz."
    elif mkt == "sh" or (not mkt and len(code) == 6 and code.startswith(("6", "9"))):
        prefix = "sh."
    else:
        prefix = ""
    full = (prefix + raw) if prefix else (raw if len(raw) == 9 else code)
    try:
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone(timedelta(hours=8)))
        end_d = now.strftime("%Y-%m-%d")
        start_d = (now - timedelta(days=90)).strftime("%Y-%m-%d")
        rs = bs.query_history_k_data_plus(full,
            fields="date,open,high,low,close,volume,amount,pctChg",
            start_date=start_d, end_date=end_d, frequency="d", adjustflag="2")
        data = []
        while rs.error_code == "0" and rs.next():
            data.append(rs.get_row_data())
        if not data:
            return ""
        import pandas as pd
        cols = ["date","open","high","low","close","volume","amount","pctChg"]
        df = pd.DataFrame(data, columns=cols)
        for c in ["open","high","low","close","volume","amount","pctChg"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        charts = render_tech_charts(df)
        if not charts:
            return ""
        items = []
        for key, label in [("macd","MACD(12,26,9)"),("boll","BOLL(20,2)"),("kdj","KDJ(9,3,3)")]:
            if key in charts:
                items.append(
                    "<div class=\'tc\'>"
                    "<div class=\'tc-label\'>" + label + "</div>"
                    "<img src=\'data:image/png;base64," + charts[key] + "\' class=\'tc-img\' alt=\'" + label + "\'>"
                    "</div>")
        return "<div class=\'tc-row\'>" + "".join(items) + "</div>"
    except Exception as e:
        return ""


def generate_html(t_day, sina_indices, stock_data, news, session, gen_dt, indices, watch, breadth, stats, analyses, summary):
    meta = SESSIONS[session]
    title_name = meta["title"]
    period_txt = meta["period"]
    hhmm_now = gen_dt.strftime("%H%M")
    date_str = t_day.strftime("%Y年%-m月%-d日")
    weekday = ["周一","周二","周三","周四","周五","周六","周日"][t_day.weekday()]
    gen_time = gen_dt.strftime("%H:%M")
    file_date = t_day.strftime("%Y%m%d")
    file_badge = f"{file_date}_{hhmm_now}"

    idx_map = [
        ("s_sh000001", "上证指数"), ("s_sz399001", "深证成指"),
        ("s_sz399006", "创业板指"), ("s_sh000688", "科创50"), ("s_sh000016", "上证50"),
    ]
    # ── Define data variables ──
    rising = stats.get("rising", 0)
    falling = stats.get("falling", 0)
    sentiment = "偏多" if rising > falling else ("偏空" if falling > rising else "中性")
    avg_pct = stats.get("avg_pct", 0)
    total_amt = stats.get("total_amt", 0)
    date_str_md = t_day.strftime("%Y-%m-%d")
    period_map = {"morning": "早市（盘前参考）", "noon": "午市（午盘总结）", "evening": "晚市（收盘复盘）"}
    period_cn = period_map.get(session, "日常")
    md_gen_time = gen_dt.strftime("%H:%M:%S")

    # ── Build merged HTML report sections from all data ──
    icon_map = {"大盘趋势": "📈", "量价特征": "📊", "风格特征": "🎯", "自选股动向": "🔍", "近期节奏": "🔄"}
    valid = [s for s in watch if not s.get("error")]

    # Section 1: Header + Market Summary
    sentiment_html = "偏多" if rising > falling else ("偏空" if falling > rising else "中性")
    sentiment_cls = "up" if rising > falling else ("dn" if falling > rising else "nt")
    report_html = ("<div class='rpt-card rpt-header'>"
                  "<div class='rpt-title'>📈 A股市场行情日报</div>"
                  "<div class='rpt-meta'>"
                  "<span>报告日期：<strong>" + date_str_md + "</strong> " + period_cn + "</span>"
                  "<span>生成时间：" + md_gen_time + " BJ</span>"
                  "<span>市场情绪：<strong class='" + sentiment_cls + "'>" + sentiment_html + "</strong>（" + str(rising) + "涨 / " + str(falling) + "跌）</span>"
                  "<span>平均涨跌幅：<strong>" + ("{:+.2f}".format(avg_pct)) + "%</strong></span>"
                  "<span>合计成交额：<strong>" + fmt_amt(total_amt) + "</strong></span>"
                  "</div></div>")

    # Section 2: Main Indices Table
    idx_rows_html = ""
    for idx in indices:
        a = "▲" if idx["pctChg"] > 0 else "▼" if idx["pctChg"] < 0 else "―"
        pct_cls = "up" if idx["pctChg"] > 0 else ("dn" if idx["pctChg"] < 0 else "nt")
        idx_rows_html += ("<tr><td>" + idx["name"] + "</td><td>" + idx["code"] + "</td>"
                         "<td>" + ("{:,.2f}".format(idx["close"])) + "</td>"
                         "<td class='" + pct_cls + "'>" + a + " " + ("{:+.2f}".format(idx["pctChg"])) + "%</td>"
                         "<td>" + ("{:+.2f}".format(idx["change"])) + "</td>"
                         "<td>" + ("{:,.2f}".format(idx["high"])) + "</td>"
                         "<td>" + ("{:,.2f}".format(idx["low"])) + "</td>"
                         "<td>" + fmt_vol(idx["volume"]) + "</td>"
                         "<td>" + fmt_amt(idx["amount"]) + "</td></tr>")

    report_html += ("<div class='rpt-card'>"
                    "<div class='rpt-sec'>一、主要指数</div>"
                    "<div class='rpt-tbl-wrap'>"
                    "<table class='rpt-tbl'>"
                    "<thead><tr><th>指数</th><th>代码</th><th>收盘点位</th><th>涨跌幅</th><th>涨跌额</th><th>最高</th><th>最低</th><th>成交量</th><th>成交额</th></tr></thead>"
                    "<tbody>" + idx_rows_html + "</tbody></table></div>"
                    "<div class='rpt-src'>数据来源：Baostock · 仅供参考，不构成投资建议</div></div>")

    # Section 3: Market Breadth
    if breadth:
        br_items = []
        for name, info in breadth.items():
            up = info["up_days"]; dn = info["total_days"] - up
            bars = "🟢" * up + "🔴" * dn
            br_items.append("<div class='br-item'><strong>" + name + "</strong>：" + bars + "（" + str(up) + "涨/" + str(dn) + "跌 · 均幅 " + ("{:+.2f}".format(info["recent_avg"])) + "%）</div>")
        report_html += ("<div class='rpt-card'>"
                       "<div class='rpt-sec'>二、市场节奏（近5日涨跌）</div>"
                       "<div class='rpt-breadth'>" + "".join(br_items) + "</div></div>")

    # Section 4: Watch Stocks Table
    stock_rows_html = ""
    if valid:
        for s in valid:
            a = "▲" if s["pctChg"] > 0 else "▼" if s["pctChg"] < 0 else "―"
            pct_cls = "up" if s["pctChg"] > 0 else ("dn" if s["pctChg"] < 0 else "nt")
            stock_rows_html += ("<tr>"
                               "<td>" + s["name"] + "</td><td>" + s["code"] + "</td><td>" + s["tag"] + "</td>"
                               "<td>" + ("%.2f" % s["close"]) + "</td>"
                               "<td class='" + pct_cls + "'>" + a + " " + ("{:+.2f}".format(s["pctChg"])) + "%</td>"
                               "<td>" + ("{:+.2f}".format(s["change"])) + "</td>"
                               "<td>" + ("%.2f" % s.get("ma5", 0)) + "</td>"
                               "<td>" + ("%.2f" % s.get("ma10", 0)) + "</td>"
                               "<td>" + ("%.1f" % s["pct_from_high"]) + "%</td>"
                               "<td>" + ("{:+.1f}".format(s["pct_from_low"])) + "%</td>"
                               "</tr>")
        strong = max(valid, key=lambda x: x["pctChg"])
        weak = min(valid, key=lambda x: x["pctChg"])
        avg_pct_s = sum(s["pctChg"] for s in valid) / len(valid)
        stock_note = ("自选股小结：平均 " + ("{:+.2f}".format(avg_pct_s)) + "%，"
                      + strong["name"] + "(" + ("{:+.2f}".format(strong["pctChg"])) + "%)最强，"
                      + weak["name"] + "(" + ("{:+.2f}".format(weak["pctChg"])) + "%)最弱。")
    else:
        stock_note = "暂无数据"

    report_html += ("<div class='rpt-card'>"
                    "<div class='rpt-sec'>三、自选个股</div>"
                    "<div class='rpt-tbl-wrap'>"
                    "<table class='rpt-tbl'>"
                    "<thead><tr><th>股票</th><th>代码</th><th>业务</th><th>收盘价</th><th>涨跌幅</th><th>涨跌额</th><th>MA5</th><th>MA10</th><th>距高点</th><th>距低点</th></tr></thead>"
                    "<tbody>" + stock_rows_html + "</tbody></table></div>"
                    "<div class='rpt-note'>" + stock_note + "</div></div>")

    # Section 5: Trends Analysis
    if analyses:
        ana_items = []
        for a in analyses:
            icon = icon_map.get(a["title"], "•")
            trend = ("（" + a["trend"] + "）") if a["trend"] else ""
            ana_items.append("<li><strong>" + icon + " " + a["title"] + trend + "</strong>：" + a["desc"] + "</li>")
        if ana_items:
            report_html += ("<div class='rpt-card'>"
                           "<div class='rpt-sec'>四、趋势分析</div>"
                           "<ul class='rpt-ana'>" + "".join(ana_items) + "</ul></div>")

    # Section 6: Summary
    if summary:
        report_html += ("<div class='rpt-card'>"
                       "<div class='rpt-sec'>五、综合评述</div>"
                       "<div class='rpt-summary'>" + summary + "</div>"
                       "<div class='rpt-src'>🤖 本报告由 Huigu-AI 自动生成 · 数据来源 Baostock · 仅供参考，不构成投资建议</div></div>")

    report_html += "<div class='rpt-card rpt-chart-sec'><div class='rpt-sec'>六、个股行情（实时数据）</div></div>"

    idx_cells = ""
    for key, label in idx_map:
        d = sina_indices.get(key, {})
        price = d.get("price", "—")
        chg_pct = d.get("chg_pct", "")
        idx_cells += f"""
      <div class="idx">
        <div class="n">{label}</div>
        <div class="v">{price}</div>
        <div class="c">{fmt_pct(chg_pct) if chg_pct else '<span class="nt">—</span>'}</div>
      </div>"""

    stock_cards = ""
    # Build watch lookup by code for depth analysis
    # Build watch lookup - handle both "002594" and "sz.002594" formats
    watch_map = {}
    for sw in watch:
        watch_map[sw["code"]] = sw
        # Also add with market prefix if missing
        code = sw["code"]
        if "." not in code:
            for prefix in ("sz.", "sh."):
                watch_map[prefix + code] = sw

    for s in stock_data:
        code = s.get("code") or ""
        w = watch_map.get(code, {})
        if not w:
            # Try to find by matching the numeric part
            for k, v in watch_map.items():
                if code.lstrip("0") in k.lstrip("sz.").lstrip("sh."):
                    w = v; break

        code = s["code"]
        color = STOCK_COLORS.get(code, "#64748b")
        bg, fg = STOCK_TAGS_BG.get(code, ("#f1f5f9", "#475569"))
        price = s.get("price", "—")
        chg = s.get("chg_pct", "")
        chg_html = fmt_pct(chg) if chg != "" else '<span class="nt">待更新</span>'
        mkt = s["market"]
        ths_note = f'<span class="ths-badge">同花顺 {s["ths_stk_pct"]}%</span>' if s.get("ths_stk_pct") else ""

        min_url = f"http://image.sinajs.cn/newchart/min/n/{mkt}{code}.gif"
        daily_url = f"http://image.sinajs.cn/newchart/daily/n/{mkt}{code}.gif"
        log.info(f"  下载图表: {s['name']} 分时图...")
        min_b64 = download_chart_b64(min_url, f"{s['name']} 分时图")
        log.info(f"  下载图表: {s['name']} 日K线...")
        daily_b64 = download_chart_b64(daily_url, f"{s['name']} 日K线")
        tech_charts_html = _render_stock_tech_charts(code, w)

        stock_cards += f"""
    <div class="sc" style="border-top:3px solid {color}">
      <div class="sc-header">
        <div>
          <div class="sn">{s["name"]}</div>
          <div class="sk">{code} · {mkt.upper()} · {s["tag"]}</div>
        </div>
        <span class="stag" style="background:{bg};color:{fg}">{s["tag"]}</span>
        <div class="sc-price">
          <div class="price-val">{price}</div>
          <div class="price-chg">{chg_html}{ths_note}</div>
        </div>
      </div>
      <div class="charts-row">
        <div class="chart-cell">
          <div class="chart-label">📈 分时图（{t_day.month}/{t_day.day} 快照）<span>来源：新浪财经 · 已离线存档</span></div>
          <img src="{min_b64}" alt="{s["name"]}分时图" class="chart-img">
        </div>
        <div class="chart-cell">
          <div class="chart-label">🕯 日K线（近期快照）<span>来源：新浪财经 · 已离线存档</span></div>
          <img src="{daily_b64}" alt="{s["name"]}日K线" class="chart-img">
        </div>
      </div>
      {render_capital_flow(s.get("cf"))}
      {render_deep_analysis(s, w, s.get('cf'), compute_deep_indicators(s, w, s.get('cf')))}
      {tech_charts_html}
    </div>"""

    news_items = "".join(f"<li>{n}</li>" for n in news) if news else "<li>当日要闻抓取失败</li>"

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_name} · {date_str}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'PingFang SC','Noto Sans SC',-apple-system,sans-serif;background:#f1f5f9;color:#0f172a;padding:16px 12px;line-height:1.5}}
.w{{max-width:980px;margin:0 auto}}

/* ── 页头 ─────────────────────────────────── */
.hd{{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px}}
.ht{{font-size:20px;font-weight:700}}
.hs{{font-size:11px;color:#94a3b8;margin-top:4px}}
.bdg{{font-size:10px;padding:4px 13px;border-radius:20px;font-weight:600;background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe;white-space:nowrap}}

/* ── 章节标题 ─────────────────────────────── */
.sec{{font-size:10px;font-weight:700;letter-spacing:3px;color:#94a3b8;margin:20px 0 10px;padding-bottom:6px;border-bottom:1px solid #e2e8f0}}

/* ── A股配色 红涨绿跌 ─────────────────────── */
.up{{color:#dc2626}}.dn{{color:#16a34a}}.nt{{color:#64748b}}

/* ── 报告卡片（.rpt-card）通用容器 ─────────── */
.rpt-card{{background:#fff;border-radius:12px;border:1px solid #e2e8f0;box-shadow:0 1px 4px rgba(0,0,0,.04);margin-bottom:14px;padding:16px 18px;overflow:hidden}}
.rpt-card.rpt-header{{background:linear-gradient(135deg,#fafbfc,#fff);border-left:4px solid #3b82f6}}
.rpt-card.rpt-chart-sec{{padding:10px 18px;background:#fafbfc}}

.rpt-title{{font-size:16px;font-weight:700;color:#0f172a;margin-bottom:10px}}
.rpt-sec{{font-size:12px;font-weight:700;color:#475569;letter-spacing:1px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #f1f5f9}}
.rpt-meta{{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:11px;color:#64748b;line-height:1.8}}
.rpt-meta span{{display:inline-flex;align-items:center;gap:3px}}
.rpt-meta strong{{color:#0f172a;font-weight:700}}
.rpt-src{{font-size:10px;color:#94a3b8;margin-top:10px;padding-top:8px;border-top:1px dashed #f1f5f9;text-align:right}}
.rpt-note{{font-size:12px;color:#475569;margin-top:10px;padding:8px 12px;background:#f8fafc;border-radius:6px;line-height:1.6}}
.rpt-summary{{font-size:13px;color:#334155;line-height:1.8}}

/* ── 报告表格 ─────────────────────────────── */
.rpt-tbl-wrap{{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -18px;padding:0 18px}}
.rpt-tbl{{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}}
.rpt-tbl th{{text-align:left;padding:6px 8px;color:#94a3b8;font-weight:600;font-size:10px;border-bottom:2px solid #e2e8f0;letter-spacing:.5px}}
.rpt-tbl td{{padding:8px 8px;border-bottom:1px solid #f1f5f9;color:#334155}}
.rpt-tbl td:nth-child(n+3){{text-align:right;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}}
.rpt-tbl tbody tr:hover{{background:#fafbfc}}

/* ── 趋势分析列表 ─────────────────────────── */
.rpt-ana{{list-style:none;padding:0;margin:0}}
.rpt-ana li{{font-size:12px;color:#475569;line-height:1.8;padding:6px 0;border-bottom:1px solid #f8fafc}}
.rpt-ana li:last-child{{border-bottom:none}}

/* ── 市场节奏（breadth） ──────────────────── */
.rpt-breadth{{display:flex;flex-direction:column;gap:8px}}
.br-item{{font-size:12px;color:#475569;line-height:1.6;padding:6px 10px;background:#f8fafc;border-radius:6px}}
.br-item strong{{color:#0f172a}}

/* ── 情绪 / 信号标签 ─────────────────────── */
.sentiment-items{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}}
.sig-tag{{display:inline-block;font-size:10px;padding:3px 8px;border-radius:10px;font-weight:500;background:#f1f5f9;color:#475569}}
.mkt-context{{font-size:12px;color:#64748b;margin-top:8px;line-height:1.6}}
.mkt-label{{font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:1px;margin-bottom:4px}}

/* ── 新浪实时指数格 ──────────────────────── */
.idx-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:8px}}
.idx{{background:#fff;border-radius:8px;padding:10px 12px;border:1px solid #e2e8f0;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.idx .n{{font-size:10px;color:#94a3b8;margin-bottom:3px;font-weight:500}}
.idx .v{{font-size:15px;font-weight:700}}
.idx .c{{font-size:11px;margin-top:2px;font-weight:600}}

/* ── 个股卡片 ─────────────────────────────── */
.sc{{background:#fff;border-radius:12px;border:1px solid #e2e8f0;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:16px;overflow:hidden}}
.sc-header{{display:flex;align-items:center;gap:12px;padding:14px 18px 12px;flex-wrap:wrap}}
.sn{{font-size:16px;font-weight:700}}
.sk{{font-size:10px;color:#94a3b8;margin-top:2px}}
.stag{{font-size:10px;padding:3px 10px;border-radius:20px;font-weight:500;white-space:nowrap}}
.sc-price{{margin-left:auto;text-align:right}}
.price-val{{font-size:18px;font-weight:700}}
.price-chg{{font-size:12px;margin-top:3px}}
.ths-badge{{font-size:9px;color:#7c3aed;background:#ede9fe;padding:1px 6px;border-radius:4px;margin-left:6px;vertical-align:middle}}

/* ── 图表区 单列 ──────────────────────────── */
.charts-row{{display:block;border-top:1px solid #f1f5f9}}
.chart-cell{{padding:14px 18px}}
.chart-cell+.chart-cell{{border-top:1px solid #f1f5f9}}
.chart-label{{font-size:11px;font-weight:600;color:#64748b;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center}}
.chart-label span{{font-size:9px;color:#94a3b8;font-weight:400}}
.chart-img{{width:100%;height:auto;min-height:120px;max-height:360px;border-radius:6px;display:block;object-fit:contain;background:#f8fafc}}

/* ── 主力资金 ─────────────────────────────── */
.cf-wrap{{border-top:1px solid #f1f5f9;padding:14px 18px;background:#fdfdfe}}
.cf-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:6px}}
.cf-title{{font-size:11px;font-weight:700;color:#475569;letter-spacing:1px}}
.cf-hint{{font-size:9px;color:#94a3b8;font-weight:400}}
.cf-note{{font-size:11px;color:#94a3b8;padding:8px 0}}
.cf-empty{{background:#fafbfc}}
.cf-kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}}
.cf-kpi{{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:8px 10px}}
.cf-label{{font-size:9px;color:#94a3b8;margin-bottom:3px;font-weight:500}}
.cf-value{{font-size:14px;font-weight:700;display:flex;align-items:baseline;gap:6px}}
.cf-pct{{font-size:10px;color:#64748b;font-weight:500}}
.cf-breakdown{{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:8px 10px;margin-bottom:10px}}
.cf-bd-title{{font-size:9px;color:#94a3b8;margin-bottom:5px;font-weight:500}}
.cf-bd-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}
.cf-item{{display:flex;flex-direction:column;gap:2px;font-size:11px}}
.cf-k{{font-size:9px;color:#64748b}}
.cf-svg{{width:100%;height:auto;display:block;border:1px solid #e2e8f0;border-radius:6px;background:#fafbfc}}

/* ── 深度分析 ─────────────────────────────── */
.depth-section{{border-top:1px solid #f1f5f9;padding:12px 18px;background:#fafdff}}
.depth-toggle{{font-size:12px;font-weight:600;color:#3b82f6;cursor:pointer;user-select:none;display:flex;align-items:center;gap:6px;padding:4px 0}}
.depth-toggle-icon{{font-size:10px;transition:transform .2s;display:inline-block}}
.depth-toggle.rotated .depth-toggle-icon{{transform:rotate(90deg)}}
.depth-body.hidden{{display:none}}
.depth-cols{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}}
.depth-col{{min-width:0}}
.depth-sub-title{{font-size:10px;font-weight:700;color:#64748b;letter-spacing:1px;margin-bottom:6px}}
.da-row{{display:flex;gap:6px;margin-bottom:4px;flex-wrap:wrap}}
.da-cell{{flex:1;min-width:0}}
.da-tag{{display:inline-block;font-size:10px;padding:3px 7px;border-radius:4px;background:#f1f5f9;color:#475569;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}}
.da-tag.up{{background:#fef2f2;color:#dc2626}}.da-tag.dn{{background:#f0fdf4;color:#16a34a}}
.da-tag.ovb{{background:#fef2f2;color:#b91c1c}}.da-tag.ovs{{background:#f0fdf4;color:#15803d}}
.da-tag.str{{background:#eff6ff;color:#1d4ed8}}.da-tag.wkr{{background:#fff7ed;color:#c2410c}}
.da-tag.neu{{background:#f8fafc;color:#64748b}}
.ev-title{{font-size:10px;font-weight:700;color:#64748b;letter-spacing:1px;margin:10px 0 6px}}
.ev-list{{list-style:none;padding:0;margin:0}}
.ev-list li{{font-size:11px;color:#475569;line-height:1.6;padding:3px 0;border-bottom:1px solid #f1f5f9}}
.ev-list li:last-child{{border-bottom:none}}
.da-verdict{{display:flex;align-items:center;gap:8px;margin-top:10px;padding-top:10px;border-top:1px solid #f1f5f9}}
.verdict-label{{font-size:11px;font-weight:600;color:#475569}}
.verdict-score{{font-weight:700;font-size:12px}}

/* ── 技术图表 ─────────────────────────────── */
.tc-row{{display:flex;flex-direction:column;gap:8px;margin:10px 0 0}}
.tc{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:8px 10px}}
.tc-label{{font-size:10px;font-weight:700;color:#64748b;letter-spacing:.5px;margin-bottom:4px}}
.tc-img{{width:100%;height:auto;display:block;border-radius:4px}}
.tech-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}}

/* ── 要闻 / 免责 ─────────────────────────── */
.news{{background:#fff;border-radius:10px;border:1px solid #e2e8f0;padding:14px 18px}}
.news ul{{padding-left:18px}}
.news li{{font-size:12px;color:#475569;line-height:2;border-bottom:1px solid #f8fafc;padding:2px 0}}
.news li:last-child{{border-bottom:none}}
.disc{{font-size:10px;color:#94a3b8;padding:10px 14px;background:#fff;border-radius:8px;text-align:center;margin-top:14px;line-height:1.7;border:1px solid #e2e8f0}}

/* ── 移动端响应式 ─────────────────────────── */
@media(max-width:768px){{
  body{{padding:12px 8px}}
  .rpt-card{{padding:12px 14px}}
  .idx-row{{grid-template-columns:repeat(3,1fr)}}
  .cf-kpis{{grid-template-columns:repeat(2,1fr)}}
  .cf-bd-row{{grid-template-columns:repeat(2,1fr)}}
  .depth-cols{{grid-template-columns:1fr}}
  .tech-grid{{grid-template-columns:repeat(2,1fr)}}
}}
@media(max-width:480px){{
  .ht{{font-size:18px}}
  .idx-row{{grid-template-columns:repeat(2,1fr)}}
  .sc-header{{gap:8px}}
  .price-val{{font-size:16px}}
  .rpt-tbl{{font-size:11px}}
  .rpt-tbl th,.rpt-tbl td{{padding:5px 4px}}
  .rpt-meta{{font-size:10px}}
  .depth-toggle{{font-size:11px}}
}}
</style>
</head>
<body>
<div class="w">
<div class="hd">
  <div>
    <div class="ht">{title_name} · 慧股AI</div>
    <div class="hs">北京时间 {date_str}（{weekday}）· {period_txt} · 生成于 {gen_time} BJ · Huigu-AI 自动存档</div>
  </div>
  <span class="bdg">📁 {file_badge}</span>
</div>
{report_html}
<div class="sec">主要指数（实时行情）</div>
<div class="idx-row">{idx_cells}</div>
<div class="sec">个股行情 · 分时图 + 日K线快照（离线存档）</div>
{stock_cards}
<div class="sec">当日要闻摘要</div>
<div class="news"><ul>{news_items}</ul></div>
<div class="disc">⚠ 本报告由 Huigu-AI 自动生成（{meta["slot"]} · {gen_time} BJ），数据来自新浪财经 / 同花顺 / 东方财富，仅供个人存档参考，不构成投资建议。<br>{period_txt}，图表已离线内嵌，无需网络即可查看 · 北京时间（UTC+8）</div>
</div>
</body>
</html>"""

# ─────────────────────────────────────────────
# 11. GitHub Pages 索引页
# ─────────────────────────────────────────────
def generate_index_html(report_dir, out_path):
    WEEKDAYS = ["周一","周二","周三","周四","周五","周六","周日"]
    html_pat = re.compile(r'^astock_(\d{4})(\d{2})(\d{2})_(\d{4})\.html$')
    md_pat   = re.compile(r'^stock_report_(\d{8})_([早午晚])\.md$')

    entries = []
    for p in sorted(report_dir.glob("astock_*.html")):
        m = html_pat.match(p.name)
        if not m: continue
        try:
            dt = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)[:2]), int(m.group(4)[2:]))
        except Exception: continue
        entries.append({"name": p.name, "dt": dt, "date_key": f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "is_noon": dt.hour < 15})

    md_entries = []
    for p in sorted(report_dir.glob("stock_report_*.md")):
        m = md_pat.match(p.name)
        if not m: continue
        try:
            dt = datetime.datetime(int(m.group(1)[:4]), int(m.group(1)[4:6]), int(m.group(1)[6:]))
        except Exception: continue
        md_entries.append({"name": p.name, "dt": dt, "date_key": m.group(1), "session": m.group(2)})

    entries.sort(key=lambda e: e["dt"], reverse=True)
    md_entries.sort(key=lambda e: e["dt"], reverse=True)

    groups_html = ""
    if entries:
        current = None
        for e in entries:
            if not current or current[0] != e["date_key"]:
                label = f"{e['dt'].year}年{e['dt'].month}月{e['dt'].day}日 · {WEEKDAYS[e['dt'].weekday()]}"
                current = (e["date_key"], label, [])
                groups_html += f'<div class="date-group"><div class="date-header">{label.split(" · ")[0]}<span class="wd"> · {label.split(" · ")[1]}</span></div>\n'
            badge = "badge-noon" if e["is_noon"] else "badge-daily"
            badge_txt = "午间" if e["is_noon"] else "每日收盘"
            groups_html += f'  <a class="report-link" href="A-Stock-Analysis/reports/{e["name"]}"><span class="badge {badge}">{badge_txt}</span><span class="time">{e["dt"].strftime("%H:%M")}</span><span class="fname">{e["name"]}</span><span class="arrow">›</span></a>\n'
        groups_html += "</div>\n"

    md_groups_html = ""
    if md_entries:
        current = None
        for e in md_entries:
            if not current or current[0] != e["date_key"]:
                label = f"{e['dt'].year}年{e['dt'].month}月{e['dt'].day}日 · {WEEKDAYS[e['dt'].weekday()]}"
                current = (e["date_key"], label, [])
                md_groups_html += f'<div class="date-group"><div class="date-header">{label.split(" · ")[0]}<span class="wd"> · {label.split(" · ")[1]}</span></div>\n'
            session_map = {"早": "早盘","午":"午盘","晚":"收盘"}
            md_groups_html += f'  <a class="report-link" href="A-Stock-Analysis/reports/{e["name"]}"><span class="badge badge-md">{session_map.get(e["session"],e["session"])}</span><span class="time">{e["dt"].strftime("%H:%M")}</span><span class="fname">{e["name"]}</span><span class="arrow">›</span></a>\n'
        md_groups_html += "</div>\n"

    total = len(entries)
    latest = entries[0]["dt"].strftime("%Y-%m-%d %H:%M") if entries else "—"
    build_time = get_bj_now().strftime("%Y-%m-%d %H:%M")

    index_html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>慧股AI · A股报告存档</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
body{{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;color:#0f172a;padding:18px 14px 28px;max-width:720px;margin:0 auto;background:#f1f5f9}}
.header{{text-align:center;margin-bottom:18px;padding:6px 0}}
.header h1{{font-size:22px;font-weight:700}}
.subtitle{{font-size:12px;color:#94a3b8;margin-top:6px}}
.count{{font-size:11px;color:#64748b;margin-top:10px}}
.count strong{{color:#0f172a;font-weight:700}}
.date-group{{background:#fff;border-radius:12px;border:1px solid #e2e8f0;box-shadow:0 1px 4px rgba(0,0,0,.04);margin-bottom:14px;overflow:hidden}}
.date-header{{padding:14px 18px 10px;font-size:14px;font-weight:700;border-bottom:1px solid #f1f5f9;background:linear-gradient(to bottom,#fafbfc,#fff)}}
.date-header .wd{{font-size:11px;color:#94a3b8;font-weight:500;margin-left:4px}}
a.report-link{{display:flex;align-items:center;gap:12px;padding:14px 18px;font-size:14px;color:#0f172a;text-decoration:none;border-bottom:1px solid #f8fafc;min-height:52px;transition:background .1s}}
a.report-link:last-child{{border-bottom:none}}
a.report-link:hover,a.report-link:active{{background:#f8fafc}}
.badge{{display:inline-block;padding:3px 10px;border-radius:14px;font-size:10px;font-weight:600;white-space:nowrap}}
.badge-noon{{background:#fef3c7;color:#a16207;border:1px solid #fde68a}}
.badge-daily{{background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe}}
.badge-md{{background:#ede9fe;color:#5b21b6;border:1px solid #ddd6fe}}
.time{{font-size:13px;color:#475569;font-weight:500;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}
.fname{{font-size:10px;color:#94a3b8;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;margin-left:2px}}
.arrow{{margin-left:auto;color:#cbd5e1;font-size:20px;font-weight:300}}
.empty{{text-align:center;color:#94a3b8;font-size:13px;padding:40px 20px;background:#fff;border-radius:12px;border:1px solid #e2e8f0}}
.footer{{text-align:center;font-size:10px;color:#94a3b8;margin-top:22px;padding-top:14px;border-top:1px solid #e2e8f0;line-height:1.8}}
.footer a{{color:#64748b;text-decoration:none}}
.footer a:hover{{color:#0f172a}}
</style>
</head>
<body>
<div class="header">
  <h1>📊 慧股AI · A股报告存档</h1>
  <div class="subtitle">每交易日 早市（08:30）/ 午市（12:30）/ 晚市（19:30）自动更新</div>
  <div class="count">共 <strong>{total}</strong> 份 HTML 报告 · 最近更新 {latest} BJ</div>
</div>
{groups_html}
<div class="header" style="margin-top:28px">
  <h1 style="font-size:18px">📝 Markdown 报告</h1>
</div>
{md_groups_html}
<div class="footer">
  由 <a href="https://github.com/berming/Huigu-AI">berming/Huigu-AI</a>
  · A-Stock-Analysis 自动生成<br>
  索引刷新于 {build_time} BJ · 仅供参考，不构成投资建议
</div>
</body>
</html>"""
    out_path.write_text(index_html, encoding="utf-8")
    log.info(f"✅ 索引页已更新: {out_path}")

# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────
def detect_session():
    h = get_bj_now().hour
    if h < 12: return "morning"
    if h < 15: return "noon"
    return "evening"

def parse_session_arg(argv):
    if "--session" in argv:
        idx = argv.index("--session")
        if idx + 1 < len(argv):
            val = argv[idx + 1].strip().lower()
            if val in SESSIONS: return val
            raise ValueError(f"未知 --session 值：{val}")
    return detect_session()

def main(session=None):
    bs.login()
    log.info("=" * 60)
    log.info("A-Stock-Analysis 报告生成器 启动")

    if session is None:
        session = parse_session_arg(sys.argv)
    if session not in SESSIONS:
        raise ValueError(f"未知场次：{session}")
    meta = SESSIONS[session]
    log.info(f"场次 = {session}（{meta['title']}）")

    t_day = get_t_day()
    gen_dt = get_bj_now()
    today = gen_dt.date()
    hhmm = gen_dt.strftime("%H%M")
    file_date = t_day.strftime("%Y%m%d")

    log.info(f"最近交易日 T = {t_day}")
    if not is_trading_day(today):
        log.info(f"今日 {today} 非交易日")

    # ── Baostock 数据 ──
    log.info("抓取 Baostock 主要指数...")
    indices = get_index_data()
    log.info(f"  获得 {len(indices)} 个指数")

    log.info("抓取 Baostock 市场广度...")
    breadth = get_market_breadth()

    log.info("抓取 Baostock 自选股...")
    watch = get_watch_stocks()
    for s in watch:
        if not s.get('error'):
            log.info(f"  {s['name']} ({s['code']}) 收{s['close']:.2f} 涨跌{s['pctChg']:+.2f}%")

    stats = get_market_stats(indices)
    analyses = analyze_trends(indices, watch, breadth)
    summary = make_summary(indices, watch, stats)

    # ── 新浪实时行情 ──
    log.info("抓取新浪实时指数...")
    sina_indices = fetch_sina_index()
    log.info(f"  获得 {len(sina_indices)} 个指数")

    log.info("抓取新浪实时个股 + 同花顺校验...")
    stock_pool = [
        {"name": "比亚迪",   "code": "002594", "market": "sz", "tag": "新能源汽车"},
        {"name": "华天科技", "code": "002185", "market": "sz", "tag": "先进封装"},
        {"name": "三六零",   "code": "601360", "market": "sh", "tag": "AI应用/安全"},
        {"name": "中航光电", "code": "002179", "market": "sz", "tag": "连接器/液冷"},
        {"name": "科大讯飞", "code": "002230", "market": "sz", "tag": "AI大模型"},
        {"name": "华胜天成", "code": "600410", "market": "sh", "tag": "云计算/算力"},
        {"name": "立讯精密", "code": "002475", "market": "sz", "tag": "消费电子/连接器"},
        {"name": "浪潮信息", "code": "000977", "market": "sz", "tag": "AI服务器/算力"},
        {"name": "通威股份", "code": "600438", "market": "sh", "tag": "光伏/硅料"},
    ]
    stock_data = []
    for s in stock_pool:
        log.info(f"  → {s['name']} ({s['code']})")
        d = fetch_sina_stock(s)
        log.info(f"    · 主力资金流向...")
        d["cf"] = fetch_capital_flow(s, lmt=10)
        stock_data.append(d)
        time.sleep(0.3)

    # ── 要闻 ──
    log.info("抓取当日要闻...")
    news = fetch_market_news(t_day)
    log.info(f"  获得 {len(news)} 条")

    # ── 生成报告 ──
    html_path = REPORT_DIR / f"astock_{file_date}_{hhmm}.html"
    html = generate_html(t_day, sina_indices, stock_data, news, session, gen_dt, indices, watch, breadth, stats, analyses, summary)
    html_path.write_text(html, encoding="utf-8")
    size_kb = html_path.stat().st_size // 1024
    log.info(f"✅ HTML 报告已保存: {html_path} ({size_kb} KB)")

    # Markdown 报告已融合至 HTML，不再单独生成
    log.info(f"✅ Markdown 数据已融合至 HTML 报告")

    # ── 刷新索引 ──
    try:
        repo_root = BASE_DIR.parent
        index_path = repo_root / "index.html"
        generate_index_html(REPORT_DIR, index_path)
    except Exception as e:
        log.info(f"⚠ 索引页更新失败: {e}")

    # ── 推送到 GitHub ──
    try:
        from git_push import main as push_main
        push_main(session=session)
    except Exception as e:
        log.info(f"⚠ GitHub 推送失败: {e}")

    bs.logout()
    print(str(html_path))
    return html_path

if __name__ == "__main__":
    main()
