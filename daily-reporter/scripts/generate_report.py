#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_report.py
每交易日 12:00（午间） / 17:00（每日收盘）自动生成 A股动态报告（HTML），
存档到 reports/ 目录。
- 分时图 / 日K线在生成时下载，以 base64 内嵌入 HTML（离线可查、git 存档完整）
- 个股卡片单列全宽展示，图表更大更清晰
- 报告文件名带时分后缀（HHMM），午间与每日两份不互相覆盖
依赖：Python 3.8+，仅标准库
"""

import base64
import json
import re
import sys
import time
import datetime
import urllib.request
import urllib.error
from pathlib import Path

# 股吧模块（同目录）
try:
    from fetch_guba import fetch_all, render_guba_html, GUBA_CSS
    GUBA_ENABLED = True
except ImportError:
    GUBA_ENABLED = False
    GUBA_CSS = ""
    def fetch_all(**kw): return {"posts":[], "by_stock":{}, "fetch_time":"", "cookie_ok":False}
    def render_guba_html(i): return ""


# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent  # huigu-reporter/
REPORT_DIR = BASE_DIR / "reports"
LOG_DIR    = BASE_DIR / "logs"
REPORT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── 默认个股池 ─────────────────────────────────────────────
STOCKS = [
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

# ── 报告场次配置 ───────────────────────────────────────────
# 每日两次定时运行（BJ 时间）：
#   12:00 → noon  （午间报告，反映上午盘中/午休行情）
#   17:00 → daily （每日收盘报告，反映全日收盘数据）
# 说明：文件名的 HHMM 使用「实际生成时刻」；session 只决定 HTML 标题 /
# 免责声明 / 跳过判断的时间窗（noon = 00:00–14:59，daily = 15:00–23:59）。
SESSIONS = {
    "noon": {
        "title":  "A股午报",
        "slot":   "午间",
        "period": "上午盘中（11:30 前后）快照",
        "disc":   "图表为上午休市附近的盘中快照",
        "window": (0, 15),   # [start, end)  小时窗口（半开区间）
    },
    "daily": {
        "title":  "A股日报",
        "slot":   "每日",
        "period": "全日收盘（15:00）快照",
        "disc":   "图表为当日收盘后快照",
        "window": (15, 24),
    },
}

def get_bj_now() -> datetime.datetime:
    """当前北京时间（naive datetime，便于 strftime）。"""
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)

def detect_session() -> str:
    """根据当前北京时间判断报告场次：
       北京时间 < 15:00（下午收盘前）→ noon（午间）
       否则                          → daily（每日收盘）"""
    return "noon" if get_bj_now().hour < 15 else "daily"

def parse_session_arg(argv) -> str:
    """解析命令行 --session noon|daily，未指定则按时间自动判断。"""
    if "--session" in argv:
        idx = argv.index("--session")
        if idx + 1 < len(argv):
            val = argv[idx + 1].strip().lower()
            if val in SESSIONS:
                return val
            raise ValueError(f"未知 --session 值：{val}（允许：noon / daily）")
    return detect_session()

# ── 上交所法定休市日 ────────────────────────────────────────
SSE_HOLIDAYS_2026 = {
    (2026,1,1),(2026,1,2),(2026,1,3),
    (2026,2,15),(2026,2,16),(2026,2,17),(2026,2,18),(2026,2,19),
    (2026,2,20),(2026,2,21),(2026,2,22),(2026,2,23),
    (2026,4,4),(2026,4,5),(2026,4,6),
    (2026,5,1),(2026,5,2),(2026,5,3),(2026,5,4),(2026,5,5),
    (2026,6,19),(2026,6,20),(2026,6,21),
    (2026,9,25),(2026,9,26),(2026,9,27),
    (2026,10,1),(2026,10,2),(2026,10,3),(2026,10,4),
    (2026,10,5),(2026,10,6),(2026,10,7),
}

# ── 个股卡片颜色 ───────────────────────────────────────────
STOCK_COLORS = {
    "002594": "#16a34a",  # 比亚迪   绿
    "002185": "#2563eb",  # 华天科技 蓝
    "601360": "#d97706",  # 三六零   橙
    "002179": "#7c3aed",  # 中航光电 紫
    "002230": "#dc2626",  # 科大讯飞 红
    "600410": "#0891b2",  # 华胜天成 青
    "002475": "#db2777",  # 立讯精密 粉
    "000977": "#475569",  # 浪潮信息 深灰
    "600438": "#ca8a04",  # 通威股份 金
}
STOCK_TAGS_BG = {
    "002594": ("#dcfce7", "#15803d"),
    "002185": ("#dbeafe", "#1d4ed8"),
    "601360": ("#fef9c3", "#a16207"),
    "002179": ("#ede9fe", "#5b21b6"),
    "002230": ("#fee2e2", "#b91c1c"),
    "600410": ("#cffafe", "#0e7490"),
    "002475": ("#fce7f3", "#9d174d"),
    "000977": ("#e2e8f0", "#1e293b"),
    "600438": ("#fef3c7", "#854d0e"),
}

# ─────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────

def log(msg: str):
    ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_file = LOG_DIR / f"{datetime.date.today()}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def is_trading_day(d: datetime.date) -> bool:
    if d.weekday() >= 5:
        return False
    if (d.year, d.month, d.day) in SSE_HOLIDAYS_2026:
        return False
    return True

def get_today_bj() -> datetime.date:
    bj_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    return bj_now.date()

def get_t_day() -> datetime.date:
    d = get_today_bj()
    for _ in range(10):
        if is_trading_day(d):
            return d
        d -= datetime.timedelta(days=1)
    raise RuntimeError("无法确定最近交易日，请检查节假日配置")

def fetch(url: str, timeout: int = 12, referer: str = "") -> bytes:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
    }
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def fetch_text(url: str, timeout: int = 12, referer: str = "",
               encoding: str = "utf-8") -> str:
    return fetch(url, timeout, referer).decode(encoding, errors="replace")

# ─────────────────────────────────────────────────────────
# 图表快照：下载 GIF → base64 内嵌
# ─────────────────────────────────────────────────────────

PLACEHOLDER_SVG = (
    "data:image/svg+xml;base64,"
    + __import__("base64").b64encode(
        b'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="180">'
        b'<rect width="600" height="180" fill="#f8fafc" rx="6"/>'
        b'<text x="300" y="96" text-anchor="middle" font-size="13" '
        b'fill="#94a3b8" font-family="sans-serif">Chart unavailable</text>'
        b'</svg>'
    ).decode()
)

def download_chart_b64(url: str, label: str) -> str:
    """
    下载图表图片，返回 data URI（base64）字符串。
    失败时返回占位 SVG，不中断整体流程。
    """
    try:
        data = fetch(url, timeout=15, referer="http://finance.sina.com.cn/")
        if len(data) < 1000:
            raise ValueError(f"响应过小({len(data)}B)，可能是限流")
        b64 = base64.b64encode(data).decode()
        # GIF 格式
        return f"data:image/gif;base64,{b64}"
    except Exception as e:
        log(f"  ⚠ {label} 图表下载失败: {e}")
        return PLACEHOLDER_SVG

# ─────────────────────────────────────────────────────────
# 行情数据抓取
# ─────────────────────────────────────────────────────────

def fetch_index_data() -> dict:
    """新浪实时简化行情：s_sh000001 等"""
    codes  = "s_sh000001,s_sz399001,s_sz399006,s_sh000688,s_sh000016"
    url    = f"http://hq.sinajs.cn/list={codes}"
    result = {}
    try:
        text = fetch_text(url, referer="http://finance.sina.com.cn/")
        for line in text.strip().splitlines():
            m = re.search(r'var hq_str_(s_\w+)="([^"]*)"', line)
            if not m:
                continue
            code   = m.group(1)
            fields = m.group(2).split(",")
            if len(fields) < 5:
                continue
            name, price, chg_amt, chg_pct, vol = fields[:5]
            result[code] = {
                "name":    name,
                "price":   price,
                "chg_amt": chg_amt,
                "chg_pct": chg_pct,
                "vol":     vol,
            }
    except Exception as e:
        log(f"⚠ 指数行情抓取失败: {e}")
    return result

def fetch_stock_data(stock: dict) -> dict:
    """新浪实时行情 + 同花顺涨跌幅校验"""
    code   = stock["code"]
    market = stock["market"]
    result = {"code": code, "market": market, "name": stock["name"], "tag": stock["tag"]}

    # 新浪实时报价
    try:
        url  = f"http://hq.sinajs.cn/list={market}{code}"
        text = fetch_text(url, referer="http://finance.sina.com.cn/")
        m    = re.search(r'"([^"]+)"', text)
        if m:
            fields = m.group(1).split(",")
            if len(fields) >= 32:
                result["open"]  = fields[1]
                result["prev"]  = fields[2]
                result["price"] = fields[3]
                result["high"]  = fields[4]
                result["low"]   = fields[5]
                result["vol"]   = fields[8]
                result["amt"]   = fields[9]
                result["date"]  = fields[30]
                result["time"]  = fields[31]
                try:
                    prev  = float(fields[2])
                    cur   = float(fields[3])
                    result["chg_pct"] = round((cur - prev) / prev * 100, 2) if prev else 0
                    result["chg_amt"] = round(cur - prev, 2)
                except Exception:
                    pass
    except Exception as e:
        log(f"  新浪行情 {code} 失败: {e}")

    # 同花顺涨跌幅校验
    try:
        url  = f"http://stockpage.10jqka.com.cn/{code}/"
        text = fetch_text(url, referer="http://stockpage.10jqka.com.cn/")
        arr_match = re.search(r'(\[\{"date":"\d+".*?"item1":"[\d.\-]+"\}\])', text, re.DOTALL)
        if arr_match:
            arr = json.loads(arr_match.group(1))
            if arr:
                latest = arr[-1]
                result["ths_date"]    = latest.get("date", "")
                result["ths_idx_pct"] = latest.get("item0", "")
                result["ths_stk_pct"] = latest.get("item1", "")
    except Exception as e:
        log(f"  同花顺数据 {code} 失败: {e}")

    return result

# ─────────────────────────────────────────────────────────
# 主力资金追踪（参考同花顺 /funds/ 页面的口径）
# 数据源：东方财富 push2his.eastmoney.com/api/qt/stock/fflow/kline/get
#   - secid = "1.{code}"（沪） / "0.{code}"（深）
#   - klt  = 101  日线
#   - 返回 klines 逗号分隔字段（按 fields2 顺序）：
#       f51 日期 / f52 主力净流入 / f53 小单净流入 / f54 中单净流入 /
#       f55 大单净流入 / f56 超大单净流入 / f57 主力净流入占比 /
#       f58 小单占比 / f59 中单占比 / f60 大单占比 / f61 超大单占比 /
#       f62 收盘价 / f63 涨跌幅
#   金额单位：元
# ─────────────────────────────────────────────────────────

def fetch_capital_flow(stock: dict, lmt: int = 10) -> dict:
    """拉取最近 lmt 个交易日主力资金流向。失败返回 {'ok': False, ...}。"""
    code   = stock["code"]
    market = stock["market"]
    secid  = ("1" if market == "sh" else "0") + "." + code
    url = (
        "http://push2his.eastmoney.com/api/qt/stock/fflow/kline/get"
        f"?lmt={lmt}&klt=101"
        "&fields1=f1,f2,f3,f7"
        "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
        f"&secid={secid}"
    )
    result = {"ok": False, "name": stock["name"], "days": [], "error": ""}
    try:
        raw  = fetch_text(url, timeout=12, referer="https://data.eastmoney.com/")
        data = json.loads(raw)
        if data.get("rc") not in (0, None):
            raise ValueError(f"接口返回 rc={data.get('rc')} em={data.get('em','')}")
        payload = data.get("data") or {}
        if payload.get("name"):
            result["name"] = payload["name"]
        klines = payload.get("klines") or []
        days = []
        for line in klines:
            parts = line.split(",")
            if len(parts) < 13:
                continue
            def _f(i, typ=float):
                try:
                    return typ(parts[i])
                except Exception:
                    return 0.0 if typ is float else 0
            days.append({
                "date":      parts[0],
                "main":      _f(1),   # 主力净流入（元）
                "small":     _f(2),
                "medium":    _f(3),
                "large":     _f(4),
                "xlarge":    _f(5),
                "main_pct":  _f(6),
                "small_pct": _f(7),
                "medium_pct":_f(8),
                "large_pct": _f(9),
                "xlarge_pct":_f(10),
                "close":     _f(11),
                "chg_pct":   _f(12),
            })
        if not days:
            raise ValueError("klines 为空")
        result["days"]  = days
        result["today"] = days[-1]
        def _sum(n, key):
            return sum(d[key] for d in days[-n:]) if len(days) >= 1 else 0.0
        result["sum5"]  = {k: _sum(5,  k) for k in ("main","small","medium","large","xlarge")}
        result["sum10"] = {k: _sum(10, k) for k in ("main","small","medium","large","xlarge")}
        result["ok"]    = True
    except Exception as e:
        result["error"] = str(e)
        log(f"  ⚠ 主力资金 {code} 失败: {e}")
    return result

def fmt_amount_cn(v) -> str:
    """元 → 中文大数（亿 / 万 / 元），带符号。None / 非数字 → — """
    try:
        v = float(v)
    except Exception:
        return "—"
    if v == 0:
        return "0"
    sign = "+" if v > 0 else "-"
    a = abs(v)
    if a >= 1e8:
        return f"{sign}{a/1e8:.2f}亿"
    if a >= 1e4:
        return f"{sign}{a/1e4:.0f}万"
    return f"{sign}{int(round(a))}"

def _cf_amount_span(v) -> str:
    """根据符号给金额加 up/dn 颜色类（沿用本项目 up=绿 / dn=红 的西方配色）。"""
    try:
        vv = float(v)
    except Exception:
        return '<span class="nt">—</span>'
    if vv > 0:
        return f'<span class="up">{fmt_amount_cn(vv)}</span>'
    if vv < 0:
        return f'<span class="dn">{fmt_amount_cn(vv)}</span>'
    return f'<span class="nt">0</span>'

def render_capital_flow(cf: dict) -> str:
    """生成 stock card 内的主力资金追踪区块（含 SVG 柱状图）。"""
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
    sum5  = cf["sum5"]
    sum10 = cf["sum10"]

    # 5 档资金拆解（今日）
    breakdown = [
        ("超大单", today["xlarge"]),
        ("大单",   today["large"]),
        ("中单",   today["medium"]),
        ("小单",   today["small"]),
    ]
    breakdown_html = "".join(
        f'<div class="cf-item"><span class="cf-k">{k}</span>{_cf_amount_span(v)}</div>'
        for k, v in breakdown
    )

    # ── SVG 10 日柱状图（主力净流入，0 为中线） ──────────────
    W, H  = 560, 150
    PAD_L, PAD_R, PAD_T, PAD_B = 6, 6, 14, 22
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B
    n       = len(days)
    gap     = 4
    bar_w   = max(4, (plot_w - gap * (n - 1)) / max(n, 1))
    max_abs = max((abs(d["main"]) for d in days), default=1.0) or 1.0
    mid_y   = PAD_T + plot_h / 2
    bars, labels = [], []
    for i, d in enumerate(days):
        x = PAD_L + i * (bar_w + gap)
        v = d["main"]
        h = (abs(v) / max_abs) * (plot_h / 2)
        color = "#16a34a" if v > 0 else ("#dc2626" if v < 0 else "#cbd5e1")
        if v >= 0:
            y, rect_h = mid_y - h, h
        else:
            y, rect_h = mid_y, h
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{max(rect_h,0.5):.1f}" fill="{color}" rx="1"/>'
        )
        # 仅对首尾两根与每隔几根显示日期
        if n <= 6 or i == 0 or i == n - 1 or i % max(1, n // 5) == 0:
            mmdd = d["date"][5:] if len(d["date"]) >= 10 else d["date"]
            lx = x + bar_w / 2
            labels.append(
                f'<text x="{lx:.1f}" y="{H - 6}" font-size="9" '
                f'fill="#94a3b8" text-anchor="middle">{mmdd}</text>'
            )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'class="cf-svg" preserveAspectRatio="xMidYMid meet">'
        f'<rect width="{W}" height="{H}" fill="#fafbfc" rx="4"/>'
        f'<line x1="{PAD_L}" y1="{mid_y:.1f}" x2="{W-PAD_R}" y2="{mid_y:.1f}" '
        f'stroke="#e2e8f0" stroke-dasharray="2,2"/>'
        + "".join(bars) + "".join(labels) +
        '</svg>'
    )

    return f"""
      <div class="cf-wrap">
        <div class="cf-header">
          <div class="cf-title">💰 主力资金追踪 · 近 {len(days)} 交易日</div>
          <div class="cf-hint">数据：东方财富 fflow（与同花顺同源）· 单位 元</div>
        </div>
        <div class="cf-kpis">
          <div class="cf-kpi">
            <div class="cf-label">今日主力净流入</div>
            <div class="cf-value">{_cf_amount_span(today['main'])}
              <span class="cf-pct">{today['main_pct']:+.2f}%</span></div>
          </div>
          <div class="cf-kpi">
            <div class="cf-label">近 5 日合计</div>
            <div class="cf-value">{_cf_amount_span(sum5['main'])}</div>
          </div>
          <div class="cf-kpi">
            <div class="cf-label">近 {len(days)} 日合计</div>
            <div class="cf-value">{_cf_amount_span(sum10['main'])}</div>
          </div>
        </div>
        <div class="cf-breakdown">
          <div class="cf-bd-title">今日 5 档资金拆解</div>
          <div class="cf-bd-row">{breakdown_html}</div>
        </div>
        {svg}
      </div>"""

def fetch_market_news(t_day: datetime.date) -> list:
    """新浪财经滚动要闻"""
    headlines = []
    try:
        date_str = t_day.strftime("%Y-%m-%d")
        url      = f"https://finance.sina.com.cn/roll/index.d.html?cids=&date={date_str}&num=20"
        text     = fetch_text(url, referer="https://finance.sina.com.cn/")
        titles   = re.findall(r'<a[^>]*target="_blank"[^>]*>([^<]{10,60})</a>', text)
        for t in titles:
            t = t.strip()
            if t and any(kw in t for kw in ["股","市","A股","行情","指数","板块","券","基金"]):
                headlines.append(t)
                if len(headlines) >= 8:
                    break
    except Exception as e:
        log(f"⚠ 快讯抓取失败: {e}")
    return headlines

# ─────────────────────────────────────────────────────────
# HTML 报告生成
# ─────────────────────────────────────────────────────────

def fmt_pct(val) -> str:
    try:
        v    = float(val)
        sign = "▲" if v >= 0 else "▼"
        cls  = "up" if v >= 0 else "dn"
        return f'<span class="{cls}">{sign} {abs(v):.2f}%</span>'
    except Exception:
        return '<span class="nt">—</span>'

def generate_html(t_day: datetime.date, indices: dict,
                  stocks: list, news: list,
                  guba_html: str = "",
                  session: str = "daily",
                  gen_dt: datetime.datetime = None) -> str:
    meta = SESSIONS[session]
    title_name = meta["title"]   # A股午报 / A股日报
    slot_name  = meta["slot"]    # 午间 / 每日
    period_txt = meta["period"]  # 盘中快照 / 收盘快照
    disc_txt   = meta["disc"]

    if gen_dt is None:
        gen_dt = get_bj_now()
    hhmm_now   = gen_dt.strftime("%H%M")   # 实际生成时刻

    date_str  = t_day.strftime("%Y年%-m月%-d日")
    weekday   = ["周一","周二","周三","周四","周五","周六","周日"][t_day.weekday()]
    gen_time  = gen_dt.strftime("%H:%M")
    file_date  = t_day.strftime("%Y%m%d")
    file_badge = f"{file_date}_{hhmm_now}"
    guba_block     = guba_html if guba_html else ""
    guba_css_block = GUBA_CSS if guba_html else "" 
    # 插入股吧区块标题
    if guba_block:
        guba_block = '<div class="sec">股吧大V · 今日洞察</div>\n' + guba_block

    # ── 指数格 ────────────────────────────────────────────
    idx_map = [
        ("s_sh000001", "上证指数"),
        ("s_sz399001", "深证成指"),
        ("s_sz399006", "创业板指"),
        ("s_sh000688", "科创50"),
        ("s_sh000016", "上证50"),
    ]
    idx_cells = ""
    for key, label in idx_map:
        d       = indices.get(key, {})
        price   = d.get("price", "—")
        chg_pct = d.get("chg_pct", "")
        idx_cells += f"""
      <div class="idx">
        <div class="n">{label}</div>
        <div class="v">{price}</div>
        <div class="c">{fmt_pct(chg_pct) if chg_pct else '<span class="nt">—</span>'}</div>
      </div>"""

    # ── 个股卡片（单列全宽） ───────────────────────────────
    stock_cards = ""
    for s in stocks:
        code      = s["code"]
        color     = STOCK_COLORS.get(code, "#64748b")
        bg, fg    = STOCK_TAGS_BG.get(code, ("#f1f5f9", "#475569"))
        price     = s.get("price", "—")
        chg       = s.get("chg_pct", "")
        chg_html  = fmt_pct(chg) if chg != "" else '<span class="nt">待更新</span>'
        mkt       = s["market"]

        # 同花顺校验角标
        ths_note = ""
        if s.get("ths_stk_pct"):
            ths_note = (f'<span class="ths-badge">同花顺 {s["ths_stk_pct"]}%</span>')

        # ── 下载图表快照（base64 内嵌） ─────────────────────
        min_url   = f"http://image.sinajs.cn/newchart/min/n/{mkt}{code}.gif"
        daily_url = f"http://image.sinajs.cn/newchart/daily/n/{mkt}{code}.gif"
        log(f"  下载图表: {s['name']} 分时图...")
        min_b64   = download_chart_b64(min_url,   f"{s['name']} 分时图")
        log(f"  下载图表: {s['name']} 日K线...")
        daily_b64 = download_chart_b64(daily_url, f"{s['name']} 日K线")

        stock_cards += f"""
    <div class="sc" style="border-top:3px solid {color}">
      <!-- 个股标题行 -->
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
      <!-- 图表区：全宽，左右并排，图大 -->
      <div class="charts-row">
        <div class="chart-cell">
          <div class="chart-label">
            📈 分时图（{t_day.month}/{t_day.day} 快照）
            <span>来源：新浪财经 · 已离线存档</span>
          </div>
          <img src="{min_b64}" alt="{s["name"]}分时图" class="chart-img">
        </div>
        <div class="chart-cell">
          <div class="chart-label">
            🕯 日K线（近期 快照）
            <span>来源：新浪财经 · 已离线存档</span>
          </div>
          <img src="{daily_b64}" alt="{s["name"]}日K线" class="chart-img">
        </div>
      </div>
      <!-- 主力资金追踪（参考同花顺 /funds/ 页面口径） -->
      {render_capital_flow(s.get("cf"))}
    </div>"""

    # ── 要闻列表 ──────────────────────────────────────────
    news_items = "".join(f"<li>{n}</li>" for n in news) if news \
        else "<li>当日要闻抓取失败，请访问财经网站查看</li>"

    # ── 完整 HTML ─────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_name} · {date_str}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'PingFang SC','Noto Sans SC',sans-serif;background:#f1f5f9;color:#0f172a;padding:20px;line-height:1.5}}
.w{{max-width:980px;margin:0 auto}}

/* 标题 */
.hd{{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:14px}}
.ht{{font-size:22px;font-weight:700}}
.hs{{font-size:11px;color:#94a3b8;margin-top:4px}}
.bdg{{font-size:10px;padding:4px 13px;border-radius:20px;font-weight:600;
      background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe}}

/* 节标题 */
.sec{{font-size:10px;font-weight:700;letter-spacing:3px;color:#94a3b8;
      margin:20px 0 10px;padding-bottom:6px;border-bottom:1px solid #e2e8f0}}

/* 颜色 */
.up{{color:#16a34a}}.dn{{color:#dc2626}}.nt{{color:#64748b}}

/* 指数格 */
.idx-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:8px}}
.idx{{background:#fff;border-radius:8px;padding:12px 14px;border:1px solid #e2e8f0;
      box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.idx .n{{font-size:10px;color:#94a3b8;margin-bottom:4px;font-weight:500}}
.idx .v{{font-size:17px;font-weight:700}}
.idx .c{{font-size:11px;margin-top:3px;font-weight:600}}

/* 个股卡片 —— 单列全宽 */
.sc{{background:#fff;border-radius:12px;border:1px solid #e2e8f0;
     box-shadow:0 1px 4px rgba(0,0,0,.06);margin-bottom:16px;overflow:hidden}}

/* 个股标题行 */
.sc-header{{display:flex;align-items:center;gap:12px;padding:14px 18px 12px;flex-wrap:wrap}}
.sn{{font-size:16px;font-weight:700}}
.sk{{font-size:10px;color:#94a3b8;margin-top:2px}}
.stag{{font-size:10px;padding:3px 10px;border-radius:20px;font-weight:500;white-space:nowrap}}
.sc-price{{margin-left:auto;text-align:right}}
.price-val{{font-size:20px;font-weight:700}}
.price-chg{{font-size:12px;margin-top:3px}}
.ths-badge{{font-size:9px;color:#7c3aed;background:#ede9fe;padding:1px 6px;
            border-radius:4px;margin-left:6px;vertical-align:middle}}

/* 图表区：单列布局，移动端友好，每行一张图 */
.charts-row{{display:block;border-top:1px solid #f1f5f9}}
.chart-cell{{padding:14px 18px}}
.chart-cell + .chart-cell{{border-top:1px solid #f1f5f9}}
.chart-label{{font-size:11px;font-weight:600;color:#64748b;margin-bottom:10px;
              display:flex;justify-content:space-between;align-items:center}}
.chart-label span{{font-size:9px;color:#94a3b8;font-weight:400}}
/* 图表图片：宽度撑满、高度自适应（单列布局下可给更大最大高度） */
.chart-img{{width:100%;height:auto;min-height:140px;max-height:360px;
            border-radius:6px;display:block;object-fit:contain;background:#f8fafc}}

/* 主力资金追踪 */
.cf-wrap{{border-top:1px solid #f1f5f9;padding:14px 18px;background:#fdfdfe}}
.cf-header{{display:flex;align-items:center;justify-content:space-between;
            margin-bottom:10px;flex-wrap:wrap;gap:6px}}
.cf-title{{font-size:11px;font-weight:700;color:#475569;letter-spacing:1px}}
.cf-hint{{font-size:9px;color:#94a3b8;font-weight:400}}
.cf-note{{font-size:11px;color:#94a3b8;padding:8px 0}}
.cf-empty{{background:#fafbfc}}
.cf-kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}}
.cf-kpi{{background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:8px 10px}}
.cf-label{{font-size:9px;color:#94a3b8;margin-bottom:3px;font-weight:500}}
.cf-value{{font-size:14px;font-weight:700;display:flex;align-items:baseline;gap:6px}}
.cf-pct{{font-size:10px;color:#64748b;font-weight:500}}
.cf-breakdown{{background:#fff;border:1px solid #e2e8f0;border-radius:6px;
               padding:8px 10px;margin-bottom:10px}}
.cf-bd-title{{font-size:9px;color:#94a3b8;margin-bottom:5px;font-weight:500}}
.cf-bd-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}}
.cf-item{{display:flex;flex-direction:column;gap:2px;font-size:11px}}
.cf-k{{font-size:9px;color:#64748b}}
.cf-svg{{width:100%;height:auto;display:block;border:1px solid #e2e8f0;
         border-radius:6px;background:#fafbfc}}

/* 要闻 */
.news{{background:#fff;border-radius:10px;border:1px solid #e2e8f0;padding:14px 18px}}
.news ul{{padding-left:18px}}
.news li{{font-size:12px;color:#475569;line-height:2;border-bottom:1px solid #f8fafc;padding:2px 0}}
.news li:last-child{{border-bottom:none}}

/* 免责 */
.disc{{font-size:10px;color:#94a3b8;padding:10px 14px;background:#fff;
       border-radius:8px;text-align:center;margin-top:14px;line-height:1.7;
       border:1px solid #e2e8f0}}
{guba_css_block}</style>
</head>
<body>
<div class="w">

<div class="hd">
  <div>
    <div class="ht">{title_name} · 回顾AI</div>
    <div class="hs">北京时间 {date_str}（{weekday}）· {period_txt} · 生成于 {gen_time} BJ · Huigu-AI 自动存档</div>
  </div>
  <span class="bdg">📁 {file_badge}</span>
</div>

<div class="sec">主要指数（收盘）</div>
<div class="idx-row">{idx_cells}
</div>

<div class="sec">个股行情 · 分时图 + 日K线快照（离线存档）</div>
{stock_cards}

{guba_block}
<div class="sec">当日要闻摘要</div>
<div class="news"><ul>{news_items}</ul></div>

<div class="disc">
  ⚠ 本报告由 Huigu-AI 自动生成（{slot_name}场次 · {gen_time} BJ），数据来自新浪财经 / 同花顺，仅供个人存档参考，不构成投资建议。<br>
  {disc_txt}，已离线内嵌，无需网络即可查看 · 北京时间（UTC+8）
</div>

</div>
</body>
</html>"""

# ─────────────────────────────────────────────────────────
# GitHub Pages 首页索引（repo 根目录 index.html）
# ─────────────────────────────────────────────────────────

def generate_index_html(report_dir: Path, out_path: Path):
    """扫描 report_dir 下的 astock_YYYYMMDD_HHMM.html，按日期倒序 + 场次
    生成移动优先的索引页，写到 out_path（通常是 repo 根 index.html）。

    链接使用相对路径 daily-reporter/reports/... ，既适用 GitHub Pages
    （https://user.github.io/repo/），也适用本地 file:// 打开。"""
    WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    pattern  = re.compile(r'^astock_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})\.html$')

    entries = []
    for p in sorted(report_dir.glob("astock_*.html")):
        m = pattern.match(p.name)
        if not m:
            continue
        y, mo, d, h, mi = m.groups()
        try:
            dt = datetime.datetime(int(y), int(mo), int(d), int(h), int(mi))
        except ValueError:
            continue
        is_noon = dt.hour < 15
        entries.append({
            "name":     p.name,
            "dt":       dt,
            "date_key": f"{y}-{mo}-{d}",
            "is_noon":  is_noon,
        })

    # 倒序：日期新 → 老；同一天内时分新 → 老
    entries.sort(key=lambda e: e["dt"], reverse=True)

    # 分组
    groups = []  # list[(date_key, date_label, [entry, ...])]
    current = None
    for e in entries:
        if not current or current[0] != e["date_key"]:
            label = (
                f"{e['dt'].year}年{e['dt'].month}月{e['dt'].day}日"
                f" · {WEEKDAYS[e['dt'].weekday()]}"
            )
            current = (e["date_key"], label, [])
            groups.append(current)
        current[2].append(e)

    total       = len(entries)
    latest      = entries[0]["dt"].strftime("%Y-%m-%d %H:%M") if entries else "—"
    build_time  = get_bj_now().strftime("%Y-%m-%d %H:%M")

    # ── 渲染 ─────────────────────────────────────────────
    if groups:
        groups_html = "\n".join(_render_date_group(g) for g in groups)
    else:
        groups_html = '<div class="empty">暂无报告，定时任务首次运行后会自动填充</div>'

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0f172a">
<title>慧股AI · A股报告存档</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
html,body{{background:#f1f5f9}}
body{{font-family:-apple-system,'PingFang SC','Noto Sans SC','Helvetica Neue',sans-serif;
     color:#0f172a;padding:18px 14px 28px;line-height:1.5;
     max-width:720px;margin:0 auto}}
.header{{text-align:center;margin-bottom:18px;padding:6px 0}}
.header h1{{font-size:22px;font-weight:700;letter-spacing:-0.3px}}
.subtitle{{font-size:12px;color:#94a3b8;margin-top:6px}}
.count{{font-size:11px;color:#64748b;margin-top:10px}}
.count strong{{color:#0f172a;font-weight:700}}

.date-group{{background:#fff;border-radius:12px;border:1px solid #e2e8f0;
             box-shadow:0 1px 4px rgba(0,0,0,.04);margin-bottom:14px;overflow:hidden}}
.date-header{{padding:14px 18px 10px;font-size:14px;font-weight:700;
              color:#0f172a;border-bottom:1px solid #f1f5f9;
              background:linear-gradient(to bottom,#fafbfc,#fff)}}
.date-header .wd{{font-size:11px;color:#94a3b8;font-weight:500;margin-left:4px}}

a.report-link{{display:flex;align-items:center;gap:12px;
               padding:14px 18px;font-size:14px;color:#0f172a;
               text-decoration:none;border-bottom:1px solid #f8fafc;
               min-height:52px;transition:background .1s}}
a.report-link:last-child{{border-bottom:none}}
a.report-link:hover,a.report-link:active{{background:#f8fafc}}

.badge{{display:inline-block;padding:3px 10px;border-radius:14px;
        font-size:10px;font-weight:600;white-space:nowrap;letter-spacing:.3px}}
.badge-noon{{background:#fef3c7;color:#a16207;border:1px solid #fde68a}}
.badge-daily{{background:#dbeafe;color:#1d4ed8;border:1px solid #bfdbfe}}

.time{{font-size:13px;color:#475569;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
       font-weight:500}}
.fname{{font-size:10px;color:#94a3b8;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
        margin-left:2px}}
.arrow{{margin-left:auto;color:#cbd5e1;font-size:20px;font-weight:300}}

.empty{{text-align:center;color:#94a3b8;font-size:13px;
        padding:40px 20px;background:#fff;border-radius:12px;
        border:1px solid #e2e8f0}}

.footer{{text-align:center;font-size:10px;color:#94a3b8;margin-top:22px;
         padding-top:14px;border-top:1px solid #e2e8f0;line-height:1.8}}
.footer a{{color:#64748b;text-decoration:none}}
.footer a:hover{{color:#0f172a}}

@media (max-width:480px){{
  body{{padding:14px 10px 24px}}
  .header h1{{font-size:20px}}
  a.report-link{{padding:14px 14px}}
  .date-header{{padding:12px 14px 8px}}
}}
</style>
</head>
<body>

<div class="header">
  <h1>📊 慧股AI · A股报告存档</h1>
  <div class="subtitle">每交易日 12:00（午间） / 17:00（收盘）北京时间自动更新</div>
  <div class="count">共 <strong>{total}</strong> 份报告 · 最近更新 {latest} BJ</div>
</div>

{groups_html}

<div class="footer">
  由 <a href="https://github.com/berming/Huigu-AI">berming/Huigu-AI</a>
  · daily-reporter 自动生成<br>
  索引刷新于 {build_time} BJ · 仅供个人存档参考，不构成投资建议
</div>

</body>
</html>"""

    out_path.write_text(html, encoding="utf-8")
    log(f"✅ 索引页已更新: {out_path} ({total} 份报告)")


def _render_date_group(group) -> str:
    """渲染一个按日期分组的卡片。"""
    _, date_label, items = group
    # date_label 已经含 "YYYY年M月D日 · 周X"，拆回去只为样式
    main_label, _, wd = date_label.partition(" · ")
    rows = []
    for e in items:
        badge_cls = "badge-noon"  if e["is_noon"] else "badge-daily"
        badge_txt = "午间"        if e["is_noon"] else "每日收盘"
        time_str  = e["dt"].strftime("%H:%M")
        href      = f"daily-reporter/reports/{e['name']}"
        rows.append(
            f'  <a class="report-link" href="{href}">'
            f'<span class="badge {badge_cls}">{badge_txt}</span>'
            f'<span class="time">{time_str}</span>'
            f'<span class="fname">{e["name"]}</span>'
            f'<span class="arrow">›</span>'
            f'</a>'
        )
    return (
        '<div class="date-group">\n'
        f'  <div class="date-header">{main_label}<span class="wd"> · {wd}</span></div>\n'
        + "\n".join(rows)
        + "\n</div>"
    )


# ─────────────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────────────

def main(session: str = None):
    log("=" * 60)
    log("Huigu-AI 日报生成器 启动")

    # 场次：参数 > 命令行 > 按当前 BJ 时间自动判断
    if session is None:
        session = parse_session_arg(sys.argv)
    if session not in SESSIONS:
        raise ValueError(f"未知 session：{session}")
    meta = SESSIONS[session]
    log(f"报告场次 = {session}（{meta['title']}）")

    t_day = get_t_day()
    today = get_today_bj()
    log(f"最近交易日 T = {t_day} ({['周一','周二','周三','周四','周五','周六','周日'][t_day.weekday()]})")

    if not is_trading_day(today):
        log(f"今日 {today} 为非交易日，按最近交易日 T = {t_day} 生成报告")

    # 实际生成时刻 → 文件名 HHMM
    gen_dt      = get_bj_now()
    hhmm_now    = gen_dt.strftime("%H%M")
    file_date   = t_day.strftime("%Y%m%d")
    report_path = REPORT_DIR / f"astock_{file_date}_{hhmm_now}.html"
    log(f"输出文件 = {report_path.name}（按生成时刻 {gen_dt.strftime('%H:%M')} 命名）")

    # 覆盖语义：清掉同一交易日、同场次时间窗内已有的旧报告，再写入新时刻文件
    start_h, end_h = meta["window"]
    for p in sorted(REPORT_DIR.glob(f"astock_{file_date}_*.html")):
        m = re.search(r"_(\d{4})\.html$", p.name)
        if not m:
            continue
        hh = int(m.group(1)[:2])
        if start_h <= hh < end_h and p.resolve() != report_path.resolve():
            try:
                p.unlink()
                log(f"  ↻ 覆盖旧{meta['slot']}报告: {p.name}")
            except OSError as e:
                log(f"  ⚠ 无法移除旧报告 {p.name}: {e}")

    # 抓行情数据
    log("抓取指数行情...")
    indices = fetch_index_data()
    log(f"  获得 {len(indices)} 个指数")

    log("抓取个股数据...")
    stock_data = []
    for s in STOCKS:
        log(f"  → {s['name']} ({s['code']})")
        d = fetch_stock_data(s)
        log(f"    · 主力资金流向（近 10 日）...")
        d["cf"] = fetch_capital_flow(s, lmt=10)
        stock_data.append(d)
        time.sleep(0.4)

    log("抓取当日要闻...")
    news = fetch_market_news(t_day)
    log(f"  获得 {len(news)} 条要闻")

    # 抓取股吧洞察
    guba_html = ""
    if GUBA_ENABLED:
        log("抓取股吧大V帖子...")
        try:
            insights  = fetch_all(days_back=1)
            guba_html = render_guba_html(insights)
            log(f"  获得 {len(insights['posts'])} 条相关帖子")
        except Exception as e:
            log(f"⚠ 股吧抓取失败: {e}")

    # 生成 HTML（内含图表下载）
    log("生成报告 HTML（含图表快照下载）...")
    html = generate_html(t_day, indices, stock_data, news,
                         guba_html=guba_html, session=session, gen_dt=gen_dt)

    report_path.write_text(html, encoding="utf-8")
    size_kb = report_path.stat().st_size // 1024
    log(f"✅ 报告已保存: {report_path} ({size_kb} KB)")

    # 刷新 GitHub Pages 首页索引（repo 根 index.html）
    try:
        repo_root  = BASE_DIR.parent
        index_path = repo_root / "index.html"
        generate_index_html(REPORT_DIR, index_path)
    except Exception as e:
        log(f"⚠ 索引页更新失败: {e}（不影响报告本身）")

    print(str(report_path))


if __name__ == "__main__":
    main()
