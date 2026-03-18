#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股市场行情报告生成器 - 增强版
早市 08:30 / 午市 12:30 / 晚市 19:30
数据来源: Baostock
"""

import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time

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
    ('sz.399005', '中小100'),
    ('sh.000905', '中证500'),
]

# 自选股
WATCH_STOCKS = [
    ('sz.002594', '比亚迪',     '新能源汽车龙头'),
    ('sz.002185', '华天科技',   '半导体封装测试'),
    ('sh.601360', '三六零',     '网络安全/AI'),
    ('sz.002179', '中航光电',   '军工连接器龙头'),
    ('sz.002230', '科大讯飞',   'AI语音龙头'),
]

# 宽基指数（用于市场广度）
BREADTH_INDICES = [
    ('sh.000001', '上证指数'),
    ('sz.399001', '深证成指'),
    ('sz.399006', '创业板指'),
]

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def today_str():
    return datetime.now().strftime('%Y-%m-%d')

def week_ago_str(days=7):
    return (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

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

def query_k(code, fields, start, end, freq='d'):
    rs = bs.query_history_k_data_plus(
        code, fields,
        start_date=start, end_date=end,
        frequency=freq, adjustflag='3'
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

def sleep_short():
    time.sleep(0.4)

# ─────────────────────────────────────────────
# 1. 主要指数
# ─────────────────────────────────────────────
def get_index_data():
    start, end = week_ago_str(10), today_str()
    results = []
    for code, name in INDICES:
        df = query_k(code, 'date,open,high,low,close,volume,amount,pctChg', start, end)
        sleep_short()
        if df.empty or len(df) < 1:
            continue
        cur = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else cur
        results.append({
            'name': name, 'code': code, 'date': cur['date'],
            'close': float(cur['close']), 'pctChg': float(cur['pctChg']),
            'open': float(cur['open']), 'high': float(cur['high']),
            'low': float(cur['low']),
            'volume': float(cur['volume']), 'amount': float(cur['amount']),
            'prev_close': float(prev['close']),
            'change': float(cur['close']) - float(prev['close']),
        })
    return results

# ─────────────────────────────────────────────
# 2. 全市场统计（用三个宽基指数代理市场广度）
# ─────────────────────────────────────────────
def get_market_breadth():
    """通过主要指数近期涨跌趋势评估市场广度"""
    start, end = week_ago_str(20), today_str()
    results = {}
    for code, name in BREADTH_INDICES:
        df = query_k(code, 'date,close,pctChg', start, end)
        sleep_short()
        if df.empty or len(df) < 3:
            continue
        # 近5日涨跌序列
        recent = df.tail(5)['pctChg'].tolist()
        up_days = sum(1 for x in recent if x > 0)
        results[name] = {
            'up_days': up_days,
            'total_days': len(recent),
            'recent_avg': sum(recent) / len(recent),
            'latest_pct': float(df.iloc[-1]['pctChg']),
        }
    return results

def get_market_stats(indices):
    """全市场综合统计"""
    if not indices:
        return {}
    rising = sum(1 for i in indices if i['pctChg'] > 0)
    falling = sum(1 for i in indices if i['pctChg'] < 0)
    avg_pct = sum(i['pctChg'] for i in indices) / len(indices)
    total_vol = sum(i['volume'] for i in indices)
    total_amt = sum(i['amount'] for i in indices)
    avg_vol = total_vol / len(indices)
    # 量能对比近5日均值
    return {
        'rising': rising, 'falling': falling,
        'avg_pct': avg_pct,
        'total_vol': total_vol, 'total_amt': total_amt,
        'avg_vol': avg_vol,
    }

# ─────────────────────────────────────────────
# 3. 自选股详细行情
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
        # 计算MA5, MA10
        ma5 = df.tail(5)['close'].mean() if len(df) >= 5 else float(cur['close'])
        ma10 = df.tail(10)['close'].mean() if len(df) >= 10 else ma5
        # 近5日趋势
        recent5 = df.tail(5)['pctChg'].tolist()
        # 近期高低点
        high20 = df['high'].tail(20).max()
        low20 = df['low'].tail(20).min()
        current_close = float(cur['close'])
        pct_from_high = (current_close - high20) / high20 * 100 if high20 else 0
        pct_from_low = (current_close - low20) / low20 * 100 if low20 else 0

        results.append({
            'name': name, 'code': code, 'tag': tag,
            'date': cur['date'],
            'close': current_close,
            'pctChg': float(cur['pctChg']),
            'open': float(cur['open']),
            'high': float(cur['high']),
            'low': float(cur['low']),
            'volume': float(cur['volume']),
            'amount': float(cur['amount']),
            'prev_close': float(prev['close']),
            'change': current_close - float(prev['close']),
            'prev2_close': float(prev2['close']),
            'ma5': ma5, 'ma10': ma10,
            'up5': sum(1 for x in recent5 if x > 0),
            'high20': high20, 'low20': low20,
            'pct_from_high': pct_from_high,
            'pct_from_low': pct_from_low,
        })
    return results

# ─────────────────────────────────────────────
# 4. 趋势与规律分析
# ─────────────────────────────────────────────
def analyze_trends(indices, watch_stocks, breadth):
    """趋势规律分析"""
    analyses = []

    # 4.1 大盘趋势
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

    # 4.2 量价关系
    if indices:
        total_vol = sum(i['volume'] for i in indices)
        total_amt = sum(i['amount'] for i in indices)
        if total_amt > 1e12:
            vol_desc = "成交活跃（单市场成交超万亿），资金参与度高。"
        elif total_amt > 8e11:
            vol_desc = "量能处于中等水平，存量资金博弈特征明显。"
        else:
            vol_desc = "量能萎缩，市场观望情绪浓厚。"
        analyses.append({'title': '量价特征', 'trend': '', 'desc': vol_desc})

    # 4.3 风格特征
    if indices:
        # 找最强和最弱指数
        sorted_idx = sorted(indices, key=lambda x: x['pctChg'], reverse=True)
        strongest = sorted_idx[0]
        weakest = sorted_idx[-1]
        style_desc = f"{strongest['name']}({strongest['pctChg']:+.2f}%)领跑，{weakest['name']}({weakest['pctChg']:+.2f}%)偏弱。"
        analyses.append({'title': '风格特征', 'trend': '', 'desc': style_desc})

    # 4.4 自选股综合评述
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

    # 4.5 近期规律（近5日涨跌节奏）
    if breadth:
        rhythm = []
        for name, info in breadth.items():
            up = info['up_days']
            rhythm.append(f"{name}近5日{up}涨{info['total_days']-up}跌")
        analyses.append({'title': '近期节奏', 'trend': '', 'desc': '；'.join(rhythm)})

    return analyses

# ─────────────────────────────────────────────
# 5. 综合评述
# ─────────────────────────────────────────────
def make_summary(indices, watch_stocks, stats, analyses):
    if not indices:
        return "暂无数据，请稍后重试。"

    avg_pct = stats.get('avg_pct', 0)
    rising = stats.get('rising', 0)
    falling = stats.get('falling', 0)

    # 整体判断
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

    # 自选股亮点
    valid = [s for s in watch_stocks if not s.get('error')]
    if valid:
        strong = max(valid, key=lambda x: x['pctChg'])
        weak = min(valid, key=lambda x: x['pctChg'])
        overall += f" 个股方面，{strong['name']}({strong['pctChg']:+.2f}%)表现最强，{weak['name']}({weak['pctChg']:+.2f}%)偏弱。"

    return overall

# ─────────────────────────────────────────────
# 6. Markdown 报告生成
# ─────────────────────────────────────────────
def generate_report(period):
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    period_map = {
        'morning': '早市（盘前参考）',
        'noon':    '午市（午盘总结）',
        'evening': '晚市（收盘复盘）',
    }
    period_cn = period_map.get(period, '日常')
    period_key = {'morning': '早', 'noon': '午', 'evening': '晚'}[period]
    fname = f"stock_report_{date_str.replace('-','')}_{period_key}.md"

    indices = get_index_data()
    breadth = get_market_breadth()
    stats = get_market_stats(indices)
    watch = get_watch_stocks()
    analyses = analyze_trends(indices, watch, breadth)
    summary = make_summary(indices, watch, stats, analyses)

    rising = stats.get('rising', 0)
    falling = stats.get('falling', 0)
    sentiment = '偏多' if rising > falling else ('偏空' if falling > rising else '中性')

    lines = []
    lines.append(f"# 📈 A股市场行情日报")
    lines.append(f"")
    lines.append(f"**报告日期：** {date_str} {period_cn}")
    lines.append(f"**生成时间：** {now.strftime('%H:%M:%S')} · 数据截至 {date_str}")
    lines.append(f"**市场情绪：** {sentiment}（{rising}涨 / {falling}跌）")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # ── 一、大盘整体行情 ──
    lines.append(f"## 一、中国A股整体行情")
    lines.append(f"")
    if stats:
        lines.append(f"**市场广度：** {rising}涨 / {falling}跌（主要指数）")
        lines.append(f"**平均涨跌幅：** {stats['avg_pct']:+.2f}%")
        lines.append(f"**合计成交额：** {fmt_amt(stats['total_amt'])}元")
        lines.append(f"")
    lines.append(f"### 主要指数表现")
    lines.append(f"")
    lines.append(f"| 指数 | 代码 | 收盘点位 | 涨跌幅 | 涨跌额 | 最高 | 最低 | 成交量 | 成交额 |")
    lines.append(f"|------|------|---------|--------|--------|------|------|--------|--------|")
    for idx in indices:
        a = '▲' if idx['pctChg'] > 0 else '▼' if idx['pctChg'] < 0 else '―'
        s = '+' if idx['pctChg'] > 0 else ''
        lines.append(
            f"| {idx['name']} | {idx['code']} | "
            f"{idx['close']:,.2f} | {a} {s}{idx['pctChg']:.2f}% | "
            f"{idx['change']:+,.2f} | "
            f"{idx['high']:,.2f} | {idx['low']:,.2f} | "
            f"{fmt_vol(idx['volume'])} | {fmt_amt(idx['amount'])} |"
        )
    lines.append(f"")
    lines.append(f"> 数据来源：Baostock · 仅供参考，不构成投资建议")
    lines.append(f"")

    # ── 二、今日动态 ──
    lines.append(f"## 二、今日动态")
    lines.append(f"")
    if breadth:
        lines.append(f"### 市场节奏（近5日涨跌）")
        lines.append(f"")
        for name, info in breadth.items():
            up = info['up_days']
            dn = info['total_days'] - up
            bars = '🟢' * up + '🔴' * dn
            lines.append(f"- **{name}**：{bars} （{up}涨 / {dn}跌 · 均幅 {info['recent_avg']:+.2f}%）")
        lines.append(f"")
    lines.append(f"### 盘面特征")
    lines.append(f"")
    for a in analyses:
        if a['title'] in ('大盘趋势', '量价特征', '风格特征'):
            icon = '📊' if a['title'] == '大盘趋势' else ('📉' if a['title'] == '量价特征' else '🎯')
            lines.append(f"- **{icon} {a['title']}：** {a['trend']} {a['desc']}".strip())
    lines.append(f"")

    # ── 三、自选个股 ──
    lines.append(f"## 三、自选个股动态")
    lines.append(f"")
    valid = [s for s in watch if not s.get('error')]
    if valid:
        lines.append(f"| 股票 | 代码 | 业务 | 收盘价 | 涨跌幅 | 涨跌额 | MA5 | MA10 | 距20日高点 | 距20日低点 |")
        lines.append(f"|------|------|------|--------|--------|--------|-----|------|----------|----------|")
        for s in valid:
            a = '▲' if s['pctChg'] > 0 else '▼' if s['pctChg'] < 0 else '―'
            sp = '+' if s['pctChg'] > 0 else ''
            ma5_v = s.get('ma5', 0)
            ma10_v = s.get('ma10', 0)
            lines.append(
                f"| {s['name']} | {s['code']} | {s['tag']} | "
                f"{s['close']:.2f} | {a} {sp}{s['pctChg']:.2f}% | "
                f"{s['change']:+.2f} | "
                f"{ma5_v:.2f} | {ma10_v:.2f} | "
                f"{s['pct_from_high']:.1f}% | {s['pct_from_low']:+.1f}% |"
            )
        lines.append(f"")

        # 自选股小结
        strong = max(valid, key=lambda x: x['pctChg'])
        weak = min(valid, key=lambda x: x['pctChg'])
        avg_pct_s = sum(s['pctChg'] for s in valid) / len(valid)
        lines.append(f"**自选股小结：** 平均 {avg_pct_s:+.2f}%，{strong['name']}({strong['pctChg']:+.2f}%)最强，{weak['name']}({weak['pctChg']:+.2f}%)最弱。")
    else:
        lines.append(f"暂无数据")
    lines.append(f"")

    # ── 四、规律及趋势分析 ──
    lines.append(f"## 四、规律及趋势分析")
    lines.append(f"")
    for a in analyses:
        icon_map = {
            '大盘趋势': '📈', '量价特征': '📊',
            '风格特征': '🎯', '自选股动向': '🔍', '近期节奏': '🔄'
        }
        icon = icon_map.get(a['title'], '•')
        if a['trend']:
            lines.append(f"- **{icon} {a['title']}（{a['trend']}）：** {a['desc']}")
        else:
            lines.append(f"- **{icon} {a['title']}：** {a['desc']}")
    lines.append(f"")

    # ── 五、综合评述 ──
    lines.append(f"## 五、综合评述")
    lines.append(f"")
    lines.append(f"{summary}")
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
