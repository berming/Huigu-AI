#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富股吧帖子抓取模块
抓取指定股票的吧内最新帖子（标题/作者/时间/阅读/评论/正文）
"""

import re
import json
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────
# 股吧帖子列表抓取（从列表页提取 JSON）
# ─────────────────────────────────────────

def fetch_guba_posts(stock_code: str, page: int = 1, page_size: int = 80) -> Dict[str, Any]:
    """
    抓取东方财富股吧帖子列表数据。
    返回: {"posts": [...], "count": int, "stock_name": str}
    """
    raw_code = stock_code.split(".")[-1] if "." in stock_code else stock_code
    url = f"https://guba.eastmoney.com/list,{raw_code}.html"

    try:
        from generate_report import fetch_text
        text = fetch_text(url, referer="https://guba.eastmoney.com/", timeout=15)
    except Exception:
        return {"posts": [], "count": 0, "stock_name": ""}

    # 从 <script>var article_list={...}</script> 提取 JSON
    m = re.search(r'var\s+article_list\s*=\s*(\{.*?\})\s*;', text, re.DOTALL)
    if not m:
        return {"posts": [], "count": 0, "stock_name": ""}

    try:
        data = json.loads(m.group(1))
    except Exception:
        return {"posts": [], "count": 0, "stock_name": ""}

    posts_raw = data.get("re", [])
    bar_name = data.get("bar_name", "") or ""

    posts = []
    for p in posts_raw:
        posts.append({
            "id":           p.get("post_id", ""),
            "title":        p.get("post_title", ""),
            "author":       p.get("user_nickname", ""),
            "publish_time": p.get("post_publish_time", ""),
            "last_time":    p.get("post_last_time", ""),
            "click":        p.get("post_click_count", 0),
            "reply":        p.get("post_comment_count", 0),
            "forward":      p.get("post_forward_count", 0),
            "has_pic":      p.get("post_has_pic", False),
            "user_id":      p.get("user_id", ""),
        })

    return {
        "posts": posts,
        "count": len(posts),
        "stock_name": bar_name.replace("吧", ""),
        "total_count": data.get("count", 0),
    }


# ─────────────────────────────────────────
# 股吧帖子正文抓取（从详情页提取正文，最多 8 行）
# ─────────────────────────────────────────

def fetch_post_body(post_id: str, stock_code: str) -> str:
    """
    抓取单个帖子的正文内容，返回前 8 行文本。
    """
    raw_code = stock_code.split(".")[-1] if "." in stock_code else stock_code
    url = f"https://guba.eastmoney.com/news,{raw_code},{post_id}.html"

    try:
        from generate_report import fetch_text
        text = fetch_text(url, referer="https://guba.eastmoney.com/", timeout=10)
    except Exception:
        return ""

    body = ""

    # 方式1：<div class="newstext ">（普通帖子）
    m = re.search(r'class="newstext [^"]*"[^>]*>(.*?)(?=<div[^>]*class="(?:footer|newsinter|newsoperation|author|stock-head))',
                  text, re.DOTALL)
    if m:
        raw = m.group(1)
        body = _strip_html(raw)

    # 方式2：<div class="xeditor_content...">（财富号/视频类帖子）
    if not body:
        m = re.search(r'class="xeditor_content[^"]*"[^>]*>(.*?)(?=<div[^>]*>)', text, re.DOTALL)
        if m:
            raw = m.group(1)
            body = _strip_html(raw)

    # 方式3：直接从 HTML 提取大段中文文本
    if not body:
        # 找正文区域（标题之后的第一个大文本块）
        m = re.search(r'class="newstitle"[^>]*>.*?</div>.*?class="newstext',
                      text, re.DOTALL)
        if m:
            chunk = text[m.end():m.end()+8000]
            clean = _strip_html(chunk)
            if len(clean) > 20:
                body = clean

    if not body:
        return ""

    # 清理股吧特有的标记字符
    body = body.replace("¶¶", "\n")
    body = re.sub(r'\[举报\]', '', body)
    body = re.sub(r'郑重声明：.*', '', body, flags=re.DOTALL)
    body = re.sub(r'请勿相信.*', '', body, flags=re.DOTALL)
    body = body.strip()

    # 切成行，取前 8 行
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    return "\n".join(lines[:8])


def _strip_html(html: str) -> str:
    """将 HTML 内容转为纯文本（保留换行结构）。"""
    # 先把<br>和<p>换成换行
    t = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    t = re.sub(r'</p>', '\n', t, flags=re.IGNORECASE)
    t = re.sub(r'<[^>]+>', '', t)
    t = re.sub(r'&nbsp;', ' ', t)
    t = re.sub(r'&[a-z]+;', ' ', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()


# ─────────────────────────────────────────
# Markdown 格式化
# ─────────────────────────────────────────

def format_guba_markdown(stock_code: str, stock_name: str,
                         posts: List[Dict],
                         total: int = 0,
                         fetch_bodies: bool = False) -> str:
    """
    将帖子列表格式化为 Markdown。
    fetch_bodies=True 时会逐个抓取正文（慢，但内容完整）。
    """
    now_bj = datetime.now(timezone(timedelta(hours=8)))
    time_str = now_bj.strftime("%Y-%m-%d %H:%M")

    sections = [
        f"# 📋 {stock_name}（{stock_code}）股吧帖子",
        f"> 🤖 生成时间：{time_str} · 共 {len(posts)} 条 · 吧内总计 {total} 条",
        "",
        "---",
        ""
    ]

    for i, p in enumerate(posts, 1):
        title = p["title"].strip()
        if not title:
            title = "（无标题）"
        author = p["author"] or "匿名"
        publish = p["publish_time"]
        click = p["click"] or 0
        reply = p["reply"] or 0

        # Emoji indicators
        pic = "📷" if p.get("has_pic") else ""
        # Shorten publish time
        pub_short = publish[:16] if len(publish) >= 16 else publish
        # Post URL
        post_url = f"https://guba.eastmoney.com/news,{stock_code},{p['id']}.html"

        # ── 第1行：序号 · 标题 ──
        sections.append(f"**{i}. {title}** {pic}")

        # ── 第2行：元信息一行 ──
        sections.append(
            f"👤 **作者**: {author} · "
            f"👁️ **阅读**: {click:,} · "
            f"💬 **评论**: {reply} · "
            f"🔗 [查看原文]({post_url}) · "
            f"⏰ **发布时间**: {pub_short}"
        )

        # ── 第3-8行：帖子正文（最多6行）──
        body_lines = []
        if fetch_bodies and p["id"]:
            body = fetch_post_body(p["id"], stock_code)
            if body:
                all_lines = [l.strip() for l in body.split("\n") if l.strip()]
                body_lines = all_lines[:8]  # 取前8行

        if body_lines:
            for line in body_lines:
                sections.append(f"  {line}")
        else:
            sections.append("  _（正文为空或获取失败）_")

        sections.append("---")
        sections.append("")

    return "\n".join(sections)


# ─────────────────────────────────────────
# 批量抓取（供 generate_report.py 调用）
# ─────────────────────────────────────────

def fetch_all_watch_guba(watch_list: List, _logger=None) -> Dict[str, str]:
    """
    为自选股列表抓取所有股吧帖子 Markdown。
    默认抓取正文（fetch_bodies=True），每只股票约 80 条 × 2 秒 ≈ 3 分钟总计。
    _logger: optional logger (falls back to print)
    """
    def _log(*args, **kwargs):
        msg = " ".join(str(a) for a in args)
        if _logger:
            _logger.info(msg)
        else:
            print(msg)

    results = {}
    for item in watch_list:
        code = item.get("code", "")
        name = item.get("name", "")
        raw = code.split(".")[-1] if "." in code else code
        _log(f"  抓取股吧: {name}({code})...")
        result = fetch_guba_posts(code)
        posts = result.get("posts", [])
        stock_name = result.get("stock_name") or name
        total = result.get("total_count", 0)
        if posts:
            md = format_guba_markdown(raw, stock_name, posts, total, fetch_bodies=True)
            results[code] = md
        else:
            results[code] = (f"# 📋 {name}（{code}）股吧帖子\n\n"
                             f"> ⚠️ 暂无数据或抓取失败\n")
    return results


if __name__ == "__main__":
    # Test
    stock_code = "002179"
    result = fetch_guba_posts(stock_code)
    print(f"Fetched {result['count']} posts, name={result['stock_name']}")

    # Test body fetch for first post
    if result["posts"]:
        p = result["posts"][0]
        body = fetch_post_body(p["id"], stock_code)
        print(f"\nFirst post body:\n{body[:300]}")

    md = format_guba_markdown(stock_code, result["stock_name"],
                               result["posts"][:3], 0, fetch_bodies=True)
    print(f"\nMarkdown preview:\n{md}")
