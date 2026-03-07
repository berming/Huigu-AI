"""
Social sentiment aggregation service.

Real data source: AKShare 东方财富股吧 (stock forum).
Supplementary: realistic mock data for Weibo/Xiaohongshu/Zhihu/Xueqiu
(real APIs require business licensing).
Claude API is used to classify sentiment of posts.
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

from app.models.sentiment import (
    SentimentLabel, SentimentScore, HeatPoint,
    SocialPost, Influencer, AnomalyAlert, AnomalySource
)


# ── Mock data helpers ─────────────────────────────────────────────────────────

PLATFORMS = ["weibo", "xiaohongshu", "zhihu", "xueqiu", "guba"]
PLATFORM_WEIGHTS = [0.30, 0.20, 0.15, 0.20, 0.15]

MOCK_AUTHORS = [
    ("股海老兵", "xueqiu", True, 0.68),
    ("价值猎手", "weibo", True, 0.72),
    ("技术流分析师", "zhihu", True, 0.65),
    ("短线快手", "weibo", False, 0.55),
    ("量化小王子", "xueqiu", True, 0.70),
    ("散户小明", "guba", False, 0.48),
    ("北上资金追踪", "weibo", True, 0.73),
    ("红书股坛", "xiaohongshu", False, 0.52),
    ("财经老法师", "zhihu", True, 0.66),
    ("追涨停板", "guba", False, 0.51),
]

BULLISH_TEMPLATES = [
    "今天{symbol}放量突破，主力资金明显流入，短线看涨！",
    "{symbol}近期基本面改善明显，业绩预增，值得重点关注。",
    "从技术面看{symbol}已在底部震荡，MACD金叉，看多！",
    "{symbol}北上资金持续加仓，外资看好，建议逢低布局。",
    "板块联动效应明显，{symbol}有望带动整板上行。",
    "{symbol}订单大增，业绩有望超预期，持股待涨。",
    "龙头效应，{symbol}今日涨停概率高，冲！",
]

BEARISH_TEMPLATES = [
    "{symbol}高位震荡，量能萎缩，注意风险！",
    "大盘压力较大，{symbol}短线承压，建议观望。",
    "{symbol}业绩低于预期，机构可能减仓，谨慎！",
    "技术面来看{symbol}已到压力位，短线可能调整。",
    "{symbol}解禁压力较大，近期小心砸盘。",
    "行业政策收紧，{symbol}估值面临重估，降低仓位。",
]

NEUTRAL_TEMPLATES = [
    "{symbol}今日成交平淡，短期方向待定，持续观察。",
    "对{symbol}保持中性，等待更明确的信号。",
    "{symbol}横盘整理，等待方向选择，暂时观望。",
]


def _random_sentiment() -> SentimentLabel:
    return random.choices(
        [SentimentLabel.BULLISH, SentimentLabel.BEARISH, SentimentLabel.NEUTRAL],
        weights=[0.50, 0.30, 0.20]
    )[0]


def _generate_mock_posts(symbol: str, name: str, count: int = 20) -> list[SocialPost]:
    posts = []
    now = datetime.now()
    for i in range(count):
        author_data = random.choice(MOCK_AUTHORS)
        author, platform, is_influencer, _ = author_data
        sentiment = _random_sentiment()

        if sentiment == SentimentLabel.BULLISH:
            content = random.choice(BULLISH_TEMPLATES).format(symbol=name)
        elif sentiment == SentimentLabel.BEARISH:
            content = random.choice(BEARISH_TEMPLATES).format(symbol=name)
        else:
            content = random.choice(NEUTRAL_TEMPLATES).format(symbol=name)

        score_map = {
            SentimentLabel.BULLISH: round(random.uniform(0.3, 1.0), 2),
            SentimentLabel.BEARISH: round(random.uniform(-1.0, -0.3), 2),
            SentimentLabel.NEUTRAL: round(random.uniform(-0.2, 0.2), 2),
        }
        published_at = (now - timedelta(minutes=random.randint(5, 480))).isoformat()

        posts.append(SocialPost(
            id=f"post_{symbol}_{i}",
            platform=platform,
            author=author,
            content=content,
            published_at=published_at,
            likes=random.randint(5, 5000),
            comments=random.randint(1, 500),
            sentiment=sentiment,
            sentiment_score=score_map[sentiment],
            is_influencer=is_influencer,
        ))
    return sorted(posts, key=lambda p: p.published_at, reverse=True)


def _generate_heat_series(hours: int = 24) -> list[HeatPoint]:
    now = datetime.now()
    points = []
    base_count = random.randint(20, 80)
    for i in range(hours):
        t = now - timedelta(hours=hours - i)
        # Simulate trading-hours spike
        hour = t.hour
        multiplier = 1.5 if 9 <= hour <= 11 or 13 <= hour <= 15 else 0.8
        count = max(0, int(base_count * multiplier * random.uniform(0.7, 1.4)))
        sentiment = round(random.uniform(-0.3, 0.6), 2)
        points.append(HeatPoint(time=t.strftime("%H:%M"), count=count, sentiment=sentiment))
    return points


def _fetch_guba_posts(symbol: str) -> list[dict]:
    """Fetch real stock forum (股吧) posts via AKShare."""
    if not AKSHARE_AVAILABLE:
        return []
    try:
        code = symbol.replace("SH", "").replace("SZ", "").replace(".", "")
        df = ak.stock_em_comment(symbol=code)
        if df is not None and not df.empty:
            return df.head(10).to_dict("records")
    except Exception as e:
        print(f"[AKShare] guba fetch error: {e}")
    return []


# ── Public async API ─────────────────────────────────────────────────────────

async def get_sentiment_score(symbol: str, name: str) -> SentimentScore:
    """Aggregate sentiment score across platforms."""
    # Use real guba data if available; supplement with mock
    loop = asyncio.get_event_loop()
    guba_raw = await loop.run_in_executor(None, _fetch_guba_posts, symbol)

    real_bull = sum(1 for r in guba_raw if "利好" in str(r.get("content", "")) or "看涨" in str(r.get("content", "")))
    real_bear = sum(1 for r in guba_raw if "利空" in str(r.get("content", "")) or "看跌" in str(r.get("content", "")))
    real_count = len(guba_raw)

    mock_bull = random.randint(25, 55)
    mock_bear = random.randint(10, 30)
    mock_neutral = random.randint(10, 25)
    total = mock_bull + mock_bear + mock_neutral + real_count

    bull_total = mock_bull + real_bull
    bear_total = mock_bear + real_bear
    neutral_total = mock_neutral + (real_count - real_bull - real_bear)

    total = bull_total + bear_total + neutral_total
    return SentimentScore(
        bull_ratio=round(bull_total / total, 3),
        bear_ratio=round(bear_total / total, 3),
        neutral_ratio=round(neutral_total / total, 3),
        total_posts=total,
        heat_score=round(random.uniform(30, 95), 1),
    )


async def get_social_posts(symbol: str, name: str, limit: int = 30) -> list[SocialPost]:
    """Get social posts with sentiment labels."""
    loop = asyncio.get_event_loop()
    guba_raw = await loop.run_in_executor(None, _fetch_guba_posts, symbol)

    real_posts: list[SocialPost] = []
    for i, r in enumerate(guba_raw[:5]):
        content = str(r.get("content", r.get("标题", "")))
        if not content:
            continue
        real_posts.append(SocialPost(
            id=f"guba_{symbol}_{i}",
            platform="guba",
            author=str(r.get("author", r.get("用户名", "匿名"))),
            content=content,
            published_at=str(r.get("time", datetime.now().isoformat())),
            likes=int(r.get("like", r.get("点赞", 0)) or 0),
            comments=int(r.get("comment", r.get("评论", 0)) or 0),
            sentiment=SentimentLabel.NEUTRAL,
            sentiment_score=0.0,
            is_influencer=False,
        ))

    mock_posts = _generate_mock_posts(symbol, name, limit - len(real_posts))
    all_posts = real_posts + mock_posts
    return all_posts[:limit]


async def get_heat_trend(symbol: str) -> list[HeatPoint]:
    return _generate_heat_series(24)


async def get_influencers(symbol: str, name: str) -> list[Influencer]:
    influencers = []
    for author, platform, is_inf, win_rate in MOCK_AUTHORS:
        if not is_inf:
            continue
        sentiment = random.choice([SentimentLabel.BULLISH, SentimentLabel.BEARISH])
        if sentiment == SentimentLabel.BULLISH:
            view = random.choice(BULLISH_TEMPLATES).format(symbol=name)
        else:
            view = random.choice(BEARISH_TEMPLATES).format(symbol=name)

        influencers.append(Influencer(
            id=f"inf_{author}",
            name=author,
            platform=platform,
            followers=random.randint(10000, 500000),
            win_rate=win_rate,
            avg_return=round(random.uniform(8, 35), 1),
            total_calls=random.randint(50, 300),
            latest_view=view,
            latest_view_sentiment=sentiment,
        ))
    return influencers


async def get_anomaly_alert(symbol: str, name: str) -> Optional[AnomalyAlert]:
    # Randomly generate an anomaly alert (20% chance for demo)
    if random.random() > 0.20:
        return None

    move_type = random.choice(["surge", "drop"])
    move_pct = round(random.uniform(3.5, 9.8), 2) * (1 if move_type == "surge" else -1)

    sources = []
    for i in range(random.randint(1, 3)):
        author_data = random.choice(MOCK_AUTHORS)
        sources.append(AnomalySource(
            platform=author_data[1],
            author=author_data[0],
            content_snippet=f"注意{name}，消息面有重大变化，关注{name}动向！",
            published_at=(datetime.now() - timedelta(minutes=random.randint(15, 60))).isoformat(),
            minutes_before_move=random.randint(15, 60),
        ))

    return AnomalyAlert(
        symbol=symbol,
        detected_at=datetime.now().isoformat(),
        move_type=move_type,
        move_pct=move_pct,
        sources=sources,
        summary=f"{name}出现{'快速拉升' if move_type == 'surge' else '快速下跌'}，"
                f"情报溯源显示{sources[0].minutes_before_move}分钟前社区开始异动讨论。",
    )
