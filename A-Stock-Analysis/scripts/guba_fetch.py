#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富股吧帖子抓取模块
抓取指定股票的吧内最新帖子（标题/作者/时间/阅读/评论）
"""

import re
import json
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List


def fetch_guba_posts(stock_code: str, page: int = 1, page_size: int = 80) -> Dict[str, Any]:
    """
    抓取东方财富股吧帖子数据。
    返回: {"posts": [...], "count": int, "stock_name": str}
    """
    raw_code = stock_code.split(".")[-1] if "." in stock_code else stock_code
    url = f"https://guba.eastmoney.com/list,{raw_code}.html"

    try:
        from generate_report import fetch_text
        text = fetch_text(url, referer="https://guba.eastmoney.com/", timeout=15)
    except Exception:
        return {"posts": [], "count": 0, "stock_name": ""}

    # Extract JSON from <script>var article_list={...};</script>
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


def format_guba_markdown(stock_code: str, stock_name: str,
                         posts: List[Dict], total: int = 0) -> str:
    """将帖子列表格式化为 Markdown 文本。"""
    now_bj = datetime.now(timezone(timedelta(hours=8)))
    time_str = now_bj.strftime("%Y-%m-%d %H:%M")

    sections = [
        f"# 📋 {stock_name}（{stock_code}）股吧帖子",
        f"> 🤖 生成时间：{time_str} · 共抓取 {len(posts)} 条 · 吧内总计 {total} 条",
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
        hot = "🔥" if click > 500 else ("📈" if click > 100 else "")
        pic = "📷" if p.get("has_pic") else ""

        # Shorten publish time
        pub_short = publish[:16] if len(publish) >= 16 else publish

        # URL to the post
        post_url = f"https://guba.eastmoney.com/news,{stock_code},{p['id']}.html"

        sections.extend([
            f"### {i}. {title} {pic}",
            "",
            f"- 👤 **作者**: {author}  |  ⏰ **发布时间**: {pub_short}",
            f"- 👁️ **阅读**: {click:,}  💬 **评论**: {reply}",
            f"  > 🔗 [查看原文]({post_url})",
            "",
            "---",
            ""
        ])

    return "\n".join(sections)


def fetch_all_watch_guba(watch_list: List, _logger=None) -> Dict[str, str]:
    """
    为自选股列表抓取所有股吧帖子 Markdown。
    _logger: optional logger (falls back to print)
    Returns {code: markdown_str}
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
            md = format_guba_markdown(raw, stock_name, posts, total)
            results[code] = md
        else:
            results[code] = (f"# 📋 {name}（{code}）股吧帖子\n\n"
                             f"> ⚠️ 暂无数据或抓取失败\n")
    return results


if __name__ == "__main__":
    # Test
    stock_code = "002179"
    result = fetch_guba_posts(stock_code)
    print(f"Fetched {result['count']} posts, total={result.get('total_count', 0)}, name={result['stock_name']}")
    md = format_guba_markdown(stock_code, result['stock_name'], result['posts'][:3], result.get('total_count', 0))
    print(md)
