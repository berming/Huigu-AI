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
]

# ── 报告场次配置 ───────────────────────────────────────────
# 每日两次定时运行：
#   12:00 BJ → noon  （午间报告，反映上午盘中/午休行情）
#   17:00 BJ → daily （每日收盘报告，反映全日收盘数据）
SESSIONS = {
    "noon": {
        "hhmm":   "1200",
        "title":  "A股午报",
        "slot":   "午间",
        "period": "上午盘中（11:30 前后）快照",
        "disc":   "图表为上午休市附近的盘中快照",
    },
    "daily": {
        "hhmm":   "1700",
        "title":  "A股日报",
        "slot":   "每日",
        "period": "全日收盘（15:00）快照",
        "disc":   "图表为当日收盘后快照",
    },
}

def detect_session() -> str:
    """根据当前北京时间判断报告场次：
       北京时间 < 15:00（下午收盘前）→ noon（午间）
       否则                          → daily（每日收盘）"""
    bj_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    return "noon" if bj_now.hour < 15 else "daily"

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
    "002594": "#16a34a",
    "002185": "#2563eb",
    "601360": "#d97706",
    "002179": "#7c3aed",
    "002230": "#dc2626",
}
STOCK_TAGS_BG = {
    "002594": ("#dcfce7", "#15803d"),
    "002185": ("#dbeafe", "#1d4ed8"),
    "601360": ("#fef9c3", "#a16207"),
    "002179": ("#ede9fe", "#5b21b6"),
    "002230": ("#fee2e2", "#b91c1c"),
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
                  session: str = "daily") -> str:
    meta = SESSIONS[session]
    title_name = meta["title"]   # A股午报 / A股日报
    slot_name  = meta["slot"]    # 午间 / 每日
    period_txt = meta["period"]  # 盘中快照 / 收盘快照
    disc_txt   = meta["disc"]
    hhmm       = meta["hhmm"]    # 1200 / 1700

    date_str  = t_day.strftime("%Y年%-m月%-d日")
    weekday   = ["周一","周二","周三","周四","周五","周六","周日"][t_day.weekday()]
    gen_time  = (datetime.datetime.now(datetime.timezone.utc)
                 + datetime.timedelta(hours=8)).strftime("%H:%M")
    file_date  = t_day.strftime("%Y%m%d")
    file_badge = f"{file_date}_{hhmm}"
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

/* 图表区：全宽，左右各占50%，图大 */
.charts-row{{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid #f1f5f9}}
.chart-cell{{padding:14px 18px}}
.chart-cell:first-child{{border-right:1px solid #f1f5f9}}
.chart-label{{font-size:11px;font-weight:600;color:#64748b;margin-bottom:10px;
              display:flex;justify-content:space-between;align-items:center}}
.chart-label span{{font-size:9px;color:#94a3b8;font-weight:400}}
/* 图表图片：最大高度限制，宽度撑满 */
.chart-img{{width:100%;height:auto;min-height:120px;max-height:260px;
            border-radius:6px;display:block;object-fit:contain;background:#f8fafc}}

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
    log(f"报告场次 = {session}（{meta['title']} · 固定文件后缀 {meta['hhmm']}）")

    t_day = get_t_day()
    today = get_today_bj()
    log(f"最近交易日 T = {t_day} ({['周一','周二','周三','周四','周五','周六','周日'][t_day.weekday()]})")

    if not is_trading_day(today):
        log(f"今日 {today} 为非交易日，按最近交易日 T = {t_day} 生成报告")

    # 检查是否已存在（文件名含时分，午间 / 每日 各自独立）
    file_date   = t_day.strftime("%Y%m%d")
    report_path = REPORT_DIR / f"astock_{file_date}_{meta['hhmm']}.html"
    if report_path.exists() and "--force" not in sys.argv:
        log(f"报告已存在: {report_path}，跳过（使用 --force 强制重新生成）")
        sys.exit(0)

    # 抓行情数据
    log("抓取指数行情...")
    indices = fetch_index_data()
    log(f"  获得 {len(indices)} 个指数")

    log("抓取个股数据...")
    stock_data = []
    for s in STOCKS:
        log(f"  → {s['name']} ({s['code']})")
        d = fetch_stock_data(s)
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
                         guba_html=guba_html, session=session)

    report_path.write_text(html, encoding="utf-8")
    size_kb = report_path.stat().st_size // 1024
    log(f"✅ 报告已保存: {report_path} ({size_kb} KB)")

    print(str(report_path))


if __name__ == "__main__":
    main()
