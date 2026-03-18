#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股市场行情报告生成器
早市 08:30 / 午市 12:30 / 晚市 19:30
数据来源: Baostock
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time

# ─────────────────────────────────────────────
# 登录
# ─────────────────────────────────────────────
bs.login()

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
]

SPOT_STOCKS = [
    ('sh.600036', '招商银行'),
    ('sh.601318', '中国平安'),
    ('sh.600519', '贵州茅台'),
    ('sz.000858', '五粮液'),
    ('sz.000333', '美的集团'),
    ('sz.300750', '宁德时代'),
]

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def get_date_range():
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    return week_ago, today

def fmt_vol(v):
    if v >= 1e8: return f"{v/1e8:.2f}亿"
    if v >= 1e4: return f"{v/1e4:.0f}万"
    return str(v)

def fmt_amt(v):
    if v >= 1e8: return f"{v/1e8:.2f}亿"
    if v >= 1e4: return f"{v/1e4:.0f}万"
    return f"{v:.0f}"

def query_df(code, fields, start, end):
    week_ago, today = start, end
    rs = bs.query_history_k_data_plus(
        code, fields,
        start_date=week_ago, end_date=today,
        frequency='d', adjustflag='3'
    )
    data = []
    while rs.error_code == '0' and rs.next():
        data.append(rs.get_row_data())
    if not data:
        return pd.DataFrame()
    cols = [c.strip() for c in fields.split(',')]
    df = pd.DataFrame(data, columns=cols)
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df.dropna(subset=['close'])

# ─────────────────────────────────────────────
# 1. 主要指数
# ─────────────────────────────────────────────
def get_index_data():
    week_ago, today = get_date_range()
    results = []
    for code, name in INDICES:
        df = query_df(code, 'date,open,high,low,close,volume,amount,pctChg', week_ago, today)
        time.sleep(0.3)
        if df.empty or len(df) < 1:
            continue
        cur = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else cur
        results.append({
            'name': name,
            'code': code,
            'date': cur['date'],
            'close': cur['close'],
            'pctChg': cur['pctChg'],
            'open': cur['open'],
            'high': cur['high'],
            'low': cur['low'],
            'volume': int(cur['volume']),
            'amount': cur['amount'],
            'prev_close': prev['close'],
            'change': cur['close'] - prev['close'],
        })
    return results

# ─────────────────────────────────────────────
# 2. 个股动态
# ─────────────────────────────────────────────
def get_stock_data():
    week_ago, today = get_date_range()
    up_list, down_list = [], []
    for code, name in SPOT_STOCKS:
        df = query_df(code, 'date,close,pctChg,volume,amount', week_ago, today)
        time.sleep(0.2)
        if df.empty or len(df) < 1:
            continue
        cur = df.iloc[-1]
        pct = float(cur['pctChg'])
        entry = {
            'name': name,
            'code': code,
            'close': float(cur['close']),
            'pctChg': pct,
            'volume': int(cur['volume']),
            'amount': float(cur['amount']),
        }
        if pct > 0:
            up_list.append(entry)
        else:
            down_list.append(entry)

    up_list.sort(key=lambda x: x['pctChg'], reverse=True)
    down_list.sort(key=lambda x: x['pctChg'])
    return up_list[:6], down_list[:6]

# ─────────────────────────────────────────────
# 3. 综合评述
# ─────────────────────────────────────────────
def make_comment(indices, up, down):
    if not indices:
        return "暂无数据，请稍后重试。"
    avg_pct = sum(i['pctChg'] for i in indices) / len(indices)
    vol_total = sum(i['volume'] for i in indices)
    
    if avg_pct > 1.5:
        mood = "强势上涨"
        detail = f"主要指数平均涨幅 {avg_pct:.2f}%，市场做多情绪高涨，成交量 {fmt_vol(vol_total)}。"
    elif avg_pct > 0.3:
        mood = "小幅走强"
        detail = f"主要指数平均涨幅 {avg_pct:.2f}%，整体走势平稳，板块分化为主，成交量 {fmt_vol(vol_total)}。"
    elif avg_pct < -1.5:
        mood = "承压下行"
        detail = f"主要指数平均跌幅 {abs(avg_pct):.2f}%，空头占优，成交量 {fmt_vol(vol_total)}，建议控制仓位。"
    elif avg_pct < -0.3:
        mood = "小幅回调"
        detail = f"主要指数平均跌幅 {abs(avg_pct):.2f}%，整体在震荡区间，成交量 {fmt_vol(vol_total)}。"
    else:
        mood = "基本持平"
        detail = f"主要指数平均涨跌幅 {avg_pct:.2f}%，多空均衡，交投平淡，成交量 {fmt_vol(vol_total)}。"
    
    hot = "今日强势个股：" + ", ".join(f"{s['name']}(+{s['pctChg']:.2f}%)" for s in up[:3]) + "。" if up else ""
    weak = "今日弱势个股：" + ", ".join(f"{s['name']}({s['pctChg']:.2f}%)" for s in down[:3]) + "。" if down else ""
    
    return f"**市场概览：{mood}** {detail} {hot} {weak}"

# ─────────────────────────────────────────────
# 4. 生成 Markdown
# ─────────────────────────────────────────────
def generate_report(period):
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    period_map = {'morning': '早市', 'noon': '午市', 'evening': '晚市'}
    period_cn = period_map.get(period, '日常')

    # 文件名: stock_report_YYYYMMDD_早.md
    fname = f"stock_report_{date_str.replace('-','')}_{period_map[period][0]}.md"

    indices = get_index_data()
    up_list, down_list = get_stock_data()

    rising = sum(1 for i in indices if i['pctChg'] > 0)
    falling = sum(1 for i in indices if i['pctChg'] < 0)
    sentiment_map = {'偏多': rising > falling, '偏空': falling > rising}
    sentiment = '偏多' if rising > falling else ('偏空' if falling > rising else '中性')

    lines = []
    lines.append(f"# A股市场行情日报")
    lines.append(f"")
    lines.append(f"| 项目 | 内容 |")
    lines.append(f"|------|------|")
    lines.append(f"| 报告日期 | {date_str} {period_cn} |")
    lines.append(f"| 生成时间 | {now.strftime('%H:%M:%S')} |")
    lines.append(f"| 市场情绪 | {sentiment}（{rising}涨 / {falling}跌）|")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## 一、主要指数表现")
    lines.append(f"")
    lines.append(f"| 指数 | 代码 | 收盘 | 涨跌幅 | 涨跌额 | 最高 | 最低 | 成交量 | 成交额 |")
    lines.append(f"|------|------|------|--------|--------|------|------|--------|--------|")

    for idx in indices:
        a = '▲' if idx['pctChg'] > 0 else '▼' if idx['pctChg'] < 0 else '―'
        s = '+' if idx['pctChg'] > 0 else ''
        chg_sign = '+' if idx['change'] > 0 else ''
        lines.append(
            f"| {idx['name']} | {idx['code']} | "
            f"{idx['close']:,.2f} | {a} {s}{idx['pctChg']:.2f}% | "
            f"{chg_sign}{idx['change']:,.2f} | "
            f"{idx['high']:,.2f} | {idx['low']:,.2f} | "
            f"{fmt_vol(idx['volume'])} | {fmt_amt(idx['amount'])} |"
        )

    lines.append(f"")
    lines.append(f"## 二、个股动态")
    lines.append(f"")
    lines.append(f"### ▲ 强势个股（涨幅居前）")
    lines.append(f"")
    if up_list:
        lines.append(f"| 名称 | 代码 | 最新价 | 涨幅 | 成交量 |")
        lines.append(f"|------|------|--------|------|--------|")
        for s in up_list:
            lines.append(f"| {s['name']} | {s['code']} | {s['close']:.2f} | **+{s['pctChg']:.2f}%** | {fmt_vol(s['volume'])} |")
    else:
        lines.append(f"暂无数据")

    lines.append(f"")
    lines.append(f"### ▼ 弱势个股（跌幅居前）")
    lines.append(f"")
    if down_list:
        lines.append(f"| 名称 | 代码 | 最新价 | 跌幅 | 成交量 |")
        lines.append(f"|------|------|--------|------|--------|")
        for s in down_list:
            lines.append(f"| {s['name']} | {s['code']} | {s['close']:.2f} | **{s['pctChg']:.2f}%** | {fmt_vol(s['volume'])} |")
    else:
        lines.append(f"暂无数据")

    lines.append(f"")
    lines.append(f"## 三、市场简评")
    lines.append(f"")
    lines.append(make_comment(indices, up_list, down_list))
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*🤖 本报告由灵侠（OpenClaw）自动生成 · 数据来源 Baostock · 仅供参考，不构成投资建议*")

    content = '\n'.join(lines)
    return fname, content

# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────
if __name__ == '__main__':
    period = sys.argv[1] if len(sys.argv) > 1 else 'evening'
    fname, content = generate_report(period)

    out_dir = os.environ.get('REPORT_DIR', '.')
    out_path = os.path.join(out_dir, fname)

    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"REPORT_PATH={out_path}")
    bs.logout()
