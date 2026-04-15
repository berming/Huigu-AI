#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_guba.py
抓取东方财富股吧指定作者的最新帖子，提炼所有个股相关信息。

接口（已验证）：
  https://i.eastmoney.com/api/guba/postCenterList
  参数：uid, pagenum, pagesize, type=1, filterType=0, onlyYt=0

Cookie 管理：
  存放于 config/cookie.txt（每行一个完整 Cookie 字符串）
  Cookie 过期后只需更新该文件，代码无需修改。
  从 Chrome DevTools → Network → 复制 Request Headers 中的 Cookie 值。

用法：
  python3 scripts/fetch_guba.py           # 正常运行，输出提炼结果
  python3 scripts/fetch_guba.py --all     # 输出所有帖子（不过滤个股）
  python3 scripts/fetch_guba.py --days=3  # 抓取最近3天
"""

import json
import re
import sys
import time
import datetime
import urllib.request
import urllib.parse
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
BASE_DIR    = SCRIPTS_DIR.parent
CONFIG_DIR  = BASE_DIR / "config"
COOKIE_FILE = CONFIG_DIR / "cookie.txt"

# ── 接口 ──────────────────────────────────────────────────
API_URL = "https://i.eastmoney.com/api/guba/postCenterList"

# ── 作者配置 ───────────────────────────────────────────────
AUTHORS = [
    {
        "name":    "延安路老猫K",
        "uid":     "1141175439727114",
        "url":     "https://i.eastmoney.com/1141175439727114",
        "style":   "技术派·缺口/K线·晚评",
    },
    {
        "name":    "马上钧看市",
        "uid":     "3602094136829916",
        "url":     "https://i.eastmoney.com/3602094136829916",
        "style":   "盘面·板块轮动·早评",
    },
]

# ── 关注个股池 ─────────────────────────────────────────────
WATCH_STOCKS = {
    "002594": "比亚迪",
    "002185": "华天科技",
    "601360": "三六零",
    "002179": "中航光电",
    "002230": "科大讯飞",
}

# 别名（含帖子中常见缩写）
STOCK_ALIASES = {
    "比亚迪": "002594", "BYD": "002594",
    "华天":   "002185", "华天科技": "002185",
    "三六零": "601360", "360安全": "601360",
    "中航光电": "002179", "光电": "002179",
    "讯飞": "002230", "科大讯飞": "002230",
}

# ─────────────────────────────────────────────────────────
# Cookie 读取
# ─────────────────────────────────────────────────────────

def load_cookie() -> str:
    """从 config/cookie.txt 读取 Cookie，支持多行拼接"""
    if not COOKIE_FILE.exists():
        print(f"⚠ Cookie 文件不存在: {COOKIE_FILE}")
        print(f"  请将浏览器 Cookie 写入该文件，格式参考 README。")
        return ""
    lines = COOKIE_FILE.read_text(encoding="utf-8").strip().splitlines()
    # 过滤空行和注释行
    parts = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    return "; ".join(parts) if len(parts) > 1 else (parts[0] if parts else "")

# ─────────────────────────────────────────────────────────
# HTTP 抓取
# ─────────────────────────────────────────────────────────

def fetch_posts(uid: str, cookie: str,
                pagenum: int = 1, pagesize: int = 20) -> list:
    """
    调用东财接口获取用户帖子列表。
    返回原始 result 列表，空列表表示失败。
    """
    ts = int(time.time() * 1000)
    params = urllib.parse.urlencode({
        "uid":          uid,
        "pagenum":      pagenum,
        "pagesize":     pagesize,
        "type":         1,
        "filterType":   0,
        "onlyYt":       0,
        "callbackParam": "",
        "_":            ts,
    })
    url = f"{API_URL}?{params}"
    headers = {
        "User-Agent":       "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/147.0.0.0 Safari/537.36",
        "Accept":           "application/json, text/javascript, */*; q=0.01",
        "Accept-Language":  "zh-CN,zh;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "Referer":          f"https://i.eastmoney.com/{uid}",
        "Cookie":           cookie,
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
            if data.get("re") is True:
                return data.get("result") or []
            print(f"  ⚠ 接口返回 re=false，可能 Cookie 已过期")
            return []
    except Exception as e:
        print(f"  ❌ 抓取失败 (uid={uid}): {e}")
        return []

# ─────────────────────────────────────────────────────────
# 个股提取
# ─────────────────────────────────────────────────────────

def extract_stocks_from_content(text: str) -> list:
    """
    从正文中提取所有 $股票名(市场代码)$ 格式的股票。
    例：$三花智控(SZ002050)$ → {"name": "三花智控", "code": "002050", "market": "SZ"}
    同时检查是否命中关注池。
    """
    found = []
    seen  = set()
    # 东财正文标准格式：$名称(市场代码)$
    for m in re.finditer(r'\$([^($]+)\(([A-Z]{2})(\d{6})\)\$', text):
        name   = m.group(1).strip()
        market = m.group(2)
        code   = m.group(3)
        key    = code
        if key not in seen:
            seen.add(key)
            found.append({
                "name":      name,
                "code":      code,
                "market":    market,
                "watch":     code in WATCH_STOCKS,   # 是否在关注池
                "watch_name": WATCH_STOCKS.get(code, ""),
            })
    # 再检查别名（正文无 $ 标记时）
    for alias, code in STOCK_ALIASES.items():
        if alias in text and code not in seen:
            seen.add(code)
            found.append({
                "name":      alias,
                "code":      code,
                "market":    "SH" if code.startswith("6") else "SZ",
                "watch":     True,
                "watch_name": WATCH_STOCKS.get(code, alias),
            })
    return found

def extract_guba_stock(post: dict) -> dict:
    """从 post_guba 字段提取帖子所在股吧"""
    g = post.get("post_guba") or {}
    code = g.get("stockbar_code", "")
    # 过滤 cfhpl（财富号评论吧，非个股吧）
    if not code or code == "cfhpl" or not re.match(r'^\d{6}$', code):
        return {}
    return {
        "name":   g.get("stockbar_name", "").replace("吧", ""),
        "code":   code,
        "market": "SH" if code.startswith("6") else "SZ",
        "watch":  code in WATCH_STOCKS,
        "watch_name": WATCH_STOCKS.get(code, ""),
    }

# ─────────────────────────────────────────────────────────
# 情绪分析
# ─────────────────────────────────────────────────────────

BULL_KW = ["看多","做多","低吸","买入","抄底","突破","缺口向上","放量上攻",
           "强势","涨停","反弹","底部","金叉","拉升","新高","大阳"]
BEAR_KW = ["看空","做空","减仓","卖出","止损","破位","缺口向下","放量下跌",
           "弱势","跌停","回调","顶部","死叉","下跌","新低","大阴"]
NEUT_KW = ["震荡","观望","中性","等待","谨慎","横盘","分化"]

def sentiment(title: str, content: str) -> tuple:
    full = title + " " + content
    bull = sum(2 if kw in title else 1 for kw in BULL_KW if kw in full)
    bear = sum(2 if kw in title else 1 for kw in BEAR_KW if kw in full)
    if bull > bear and bull >= 2:
        return "📈 看多", "bullish"
    if bear > bull and bear >= 2:
        return "📉 看空", "bearish"
    return "➡️ 中性", "neutral"

def extract_price_info(text: str) -> dict:
    """提取目标价、支撑位、压力位、缺口"""
    return {
        "targets":    re.findall(r'目标[价位]*[：:]\s*(\d+\.?\d*)\s*元?', text),
        "support":    re.findall(r'支撑[位线]*[：:]\s*(\d+\.?\d*)\s*元?', text),
        "resistance": re.findall(r'压力[位线]*[：:]\s*(\d+\.?\d*)\s*元?', text),
        "gaps":       re.findall(r'缺口\s*(\d+\.?\d*)\s*[-–~至到]\s*(\d+\.?\d*)', text),
    }

# ─────────────────────────────────────────────────────────
# 帖子处理
# ─────────────────────────────────────────────────────────

def process_post(raw: dict, author: dict) -> dict:
    """将原始 JSON 帖子提炼为结构化信息"""
    title   = raw.get("post_title", "")
    content = raw.get("post_content", "")
    pub_time = raw.get("post_publish_time", "")
    post_id  = raw.get("post_id", "")
    clicks   = raw.get("post_click_count", 0)
    likes    = raw.get("post_like_count", 0)
    comments = raw.get("post_comment_count", 0)

    # 所有提到的股票
    all_stocks   = extract_stocks_from_content(title + " " + content)
    # 帖子所在股吧
    guba_stock   = extract_guba_stock(raw)
    # 是否命中关注池
    watch_stocks = [s for s in all_stocks if s["watch"]]
    if guba_stock and guba_stock.get("watch") and guba_stock not in watch_stocks:
        watch_stocks.insert(0, guba_stock)

    sent_label, sent_cls = sentiment(title, content)
    prices = extract_price_info(title + " " + content)

    return {
        "author":       author["name"],
        "author_style": author.get("style", ""),
        "author_url":   author.get("url", ""),
        "post_id":      str(post_id),
        "title":        title,
        "content":      content[:500],          # 前500字
        "pub_time":     pub_time,
        "post_url":     f"https://guba.eastmoney.com/news,{raw.get('post_guba',{}).get('stockbar_code','00'),post_id}.html" if post_id else "",
        "clicks":       clicks,
        "likes":        likes,
        "comments":     comments,
        "all_stocks":   all_stocks,             # 正文中所有 $股票$ 标记
        "watch_stocks": watch_stocks,           # 关注池命中的个股
        "guba_stock":   guba_stock,             # 帖子所在股吧
        "sentiment":    sent_label,
        "sent_cls":     sent_cls,
        "prices":       prices,
        "pic_urls":     raw.get("post_pic_url", []),
    }

def is_in_time_window(pub_time: str, days_back: int) -> bool:
    """判断帖子是否在时间窗口内"""
    if not pub_time:
        return True   # 无时间戳则不过滤
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            t = datetime.datetime.strptime(pub_time[:len(fmt)], fmt)
            return t >= cutoff
        except Exception:
            continue
    return True

# ─────────────────────────────────────────────────────────
# 主逻辑
# ─────────────────────────────────────────────────────────

def fetch_all(days_back: int = 1, show_all: bool = False,
              pagesize: int = 20) -> dict:
    """
    抓取所有作者帖子，返回：
    {
      "posts":     [全部帖子],
      "by_stock":  {"002594": [帖子...], ...},
      "fetch_time": "...",
      "cookie_ok":  bool,
    }
    """
    cookie = load_cookie()
    if not cookie:
        return {"posts": [], "by_stock": {}, "fetch_time": "", "cookie_ok": False}

    all_posts = []
    for author in AUTHORS:
        print(f"  → 抓取 {author['name']} (uid={author['uid']})...")
        raw_list = fetch_posts(author["uid"], cookie, pagesize=pagesize)
        print(f"    获取 {len(raw_list)} 条帖子")

        for raw in raw_list:
            pub_time = raw.get("post_publish_time", "")
            if not is_in_time_window(pub_time, days_back):
                continue
            post = process_post(raw, author)
            # 过滤：仅保留命中关注池的（--all 时不过滤）
            if show_all or post["watch_stocks"]:
                all_posts.append(post)
        time.sleep(0.5)

    # 按个股分组
    by_stock: dict = {code: [] for code in WATCH_STOCKS}
    for post in all_posts:
        added = set()
        for s in post["watch_stocks"]:
            c = s["code"]
            if c in by_stock and c not in added:
                by_stock[c].append(post)
                added.add(c)

    return {
        "posts":      all_posts,
        "by_stock":   by_stock,
        "fetch_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "cookie_ok":  True,
    }

# ─────────────────────────────────────────────────────────
# HTML 渲染（供 generate_report.py 调用）
# ─────────────────────────────────────────────────────────

SENT_STYLE = {
    # A股红涨绿跌：看多（期待上涨）用红，看空（期待下跌）用绿
    "bullish": ("background:#fee2e2;color:#b91c1c;border:1px solid #fecaca", "📈 看多"),
    "bearish": ("background:#dcfce7;color:#15803d;border:1px solid #bbf7d0", "📉 看空"),
    "neutral": ("background:#f1f5f9;color:#475569;border:1px solid #e2e8f0", "➡️ 中性"),
}

def render_stock_badge(s: dict) -> str:
    cls = "watch" if s.get("watch") else "other"
    bg  = "#ede9fe" if s.get("watch") else "#f1f5f9"
    fg  = "#5b21b6" if s.get("watch") else "#475569"
    label = s.get("watch_name") or s.get("name", "")
    code  = s.get("code", "")
    return (f'<span style="font-size:9px;padding:1px 7px;border-radius:4px;'
            f'background:{bg};color:{fg};margin-right:4px;font-weight:500">'
            f'{label} {code}</span>')

def render_guba_html(insights: dict) -> str:
    posts      = insights.get("posts", [])
    fetch_time = insights.get("fetch_time", "")
    cookie_ok  = insights.get("cookie_ok", True)
    authors    = "、".join(a["name"] for a in AUTHORS)

    if not cookie_ok:
        return f"""<div class="guba-empty">
  ⚠ Cookie 未配置，股吧数据无法获取。
  请将浏览器 Cookie 写入 <code>config/cookie.txt</code> 后重试。
</div>"""

    if not posts:
        return f"""<div class="guba-empty">
  📭 近期「{authors}」无与关注个股相关的帖子
  <span style="color:#94a3b8;font-size:10px;margin-left:8px">抓取时间 {fetch_time}</span>
</div>"""

    cards = ""
    for p in posts:
        sty, slabel = SENT_STYLE.get(p["sent_cls"], SENT_STYLE["neutral"])

        # 关注池个股徽章
        watch_badges = "".join(render_stock_badge(s) for s in p["watch_stocks"])
        # 正文中所有个股（非关注池）
        other_stocks = [s for s in p["all_stocks"] if not s.get("watch")]
        other_badges = ""
        if other_stocks:
            other_badges = (
                '<span style="font-size:9px;color:#94a3b8;margin-right:4px">也提到：</span>'
                + "".join(render_stock_badge(s) for s in other_stocks[:5])
            )

        # 价格信息
        pr = p.get("prices", {})
        price_parts = []
        if pr.get("targets"):    price_parts.append(f'目标价 <b>{"/".join(pr["targets"])}元</b>')
        if pr.get("support"):    price_parts.append(f'支撑 <b>{"/".join(pr["support"])}元</b>')
        if pr.get("resistance"): price_parts.append(f'压力 <b>{"/".join(pr["resistance"])}元</b>')
        for g in pr.get("gaps", []):
            price_parts.append(f'缺口 <b>{g[0]}–{g[1]}元</b>')
        price_html = '　'.join(price_parts)

        # 热度
        heat = []
        if p.get("clicks"):   heat.append(f'👁 {p["clicks"]}')
        if p.get("likes"):    heat.append(f'👍 {p["likes"]}')
        if p.get("comments"): heat.append(f'💬 {p["comments"]}')
        heat_html = '　'.join(heat)

        # 图片（最多1张缩略图）
        pic_html = ""
        if p.get("pic_urls"):
            pic_html = (f'<img src="{p["pic_urls"][0]}" '
                        f'style="max-width:100%;max-height:200px;border-radius:6px;'
                        f'margin-top:8px;display:block" '
                        f'onerror="this.style.display=\'none\'">')

        cards += f"""
  <div class="guba-card">
    <div class="guba-card-hd">
      <span class="guba-author">👤 {p["author"]}</span>
      <span class="guba-style">{p["author_style"]}</span>
      <span class="guba-time">{p["pub_time"]}</span>
      <span class="guba-sent" style="{sty}">{slabel}</span>
    </div>
    <div class="guba-title">{p["title"] or "（无标题）"}</div>
    <div class="guba-stocks">{watch_badges}{other_badges}</div>
    {f'<div class="guba-content">{p["content"]}</div>' if p.get("content") else ""}
    {f'<div class="guba-prices">{price_html}</div>' if price_html else ""}
    {pic_html}
    <div class="guba-foot">
      <span style="color:#94a3b8;font-size:10px">{heat_html}</span>
      {f'<a href="{p["author_url"]}" target="_blank" class="guba-link">查看主页 →</a>' if p.get("author_url") else ""}
    </div>
  </div>"""

    return f"""<div class="guba-wrap">
  <div class="guba-hd">
    📋 股吧大V · 今日洞察
    <span class="guba-meta">来源：{authors} · {fetch_time}</span>
    <span class="guba-warn">⚠ 个人观点，不构成投资建议</span>
  </div>
  {cards}
</div>"""

# HTML 所需 CSS（inject 进 generate_report.py 的 <style>）
GUBA_CSS = """
/* ── 股吧区块 ── */
.guba-wrap{margin-bottom:16px}
.guba-hd{font-size:13px;font-weight:700;color:#0f172a;margin-bottom:12px;
         display:flex;align-items:center;flex-wrap:wrap;gap:6px}
.guba-meta{font-size:10px;color:#94a3b8;font-weight:400}
.guba-warn{font-size:9px;color:#d97706;font-weight:400}
.guba-card{background:#fff;border-radius:10px;border:1px solid #e2e8f0;
           box-shadow:0 1px 3px rgba(0,0,0,.04);padding:14px 18px;margin-bottom:10px}
.guba-card-hd{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.guba-author{font-size:12px;font-weight:700;color:#0f172a}
.guba-style{font-size:10px;color:#94a3b8}
.guba-time{font-size:10px;color:#94a3b8;margin-left:auto}
.guba-sent{font-size:10px;padding:2px 9px;border-radius:20px;font-weight:600}
.guba-title{font-size:13px;font-weight:600;color:#0f172a;margin-bottom:7px;line-height:1.5}
.guba-stocks{margin-bottom:7px;display:flex;flex-wrap:wrap;align-items:center;gap:3px}
.guba-content{font-size:11px;color:#475569;line-height:1.75;margin-bottom:8px;
              padding:9px 12px;background:#f8fafc;border-radius:6px;
              border-left:3px solid #e2e8f0;white-space:pre-line}
.guba-prices{font-size:11px;color:#475569;margin-bottom:6px}
.guba-foot{display:flex;justify-content:space-between;align-items:center;
           margin-top:8px;padding-top:8px;border-top:1px solid #f1f5f9}
.guba-link{font-size:10px;color:#2563eb;text-decoration:none}
.guba-empty{background:#fff;border-radius:10px;border:1px solid #e2e8f0;
            padding:14px 18px;color:#94a3b8;font-size:12px;margin-bottom:14px}
"""

# ─────────────────────────────────────────────────────────
# 命令行入口
# ─────────────────────────────────────────────────────────

def main():
    show_all  = "--all"  in sys.argv
    days_back = 1
    pagesize  = 20
    for arg in sys.argv[1:]:
        if arg.startswith("--days="):
            try: days_back = int(arg.split("=")[1])
            except: pass
        if arg.startswith("--size="):
            try: pagesize = int(arg.split("=")[1])
            except: pass

    print(f"[股吧] 开始抓取，作者={len(AUTHORS)}，回溯={days_back}天，"
          f"每页={pagesize}，{'全部' if show_all else '仅关注个股'}")

    insights = fetch_all(days_back=days_back, show_all=show_all, pagesize=pagesize)
    posts    = insights["posts"]
    print(f"[股吧] 共 {len(posts)} 条相关帖子\n")

    for p in posts:
        print(f"{'─'*60}")
        print(f"【{p['author']}】{p['pub_time']}  {p['sentiment']}")
        print(f"标题：{p['title']}")
        if p["watch_stocks"]:
            names = [s.get("watch_name") or s["name"] for s in p["watch_stocks"]]
            print(f"关注：{', '.join(names)}")
        if p["all_stocks"]:
            all_names = [s["name"] for s in p["all_stocks"]]
            print(f"提到：{', '.join(all_names)}")
        if p["content"]:
            print(f"摘要：{p['content'][:200]}...")
        pr = p.get("prices", {})
        if any(pr.values()):
            print(f"价位：目标{pr['targets']} 支撑{pr['support']} 压力{pr['resistance']}")
        print(f"热度：{p['clicks']}阅 {p['likes']}赞 {p['comments']}评")
        print()

if __name__ == "__main__":
    main()
