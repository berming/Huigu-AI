from pydantic import BaseModel
from typing import Optional
from enum import Enum


class SentimentLabel(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SentimentScore(BaseModel):
    bull_ratio: float      # 0–1
    bear_ratio: float
    neutral_ratio: float
    total_posts: int
    heat_score: float      # 0–100, relative discussion intensity


class HeatPoint(BaseModel):
    time: str
    count: int
    sentiment: float       # -1 to +1


class SocialPost(BaseModel):
    id: str
    platform: str          # weibo / xiaohongshu / zhihu / xueqiu / guba
    author: str
    avatar_url: Optional[str] = None
    content: str
    published_at: str
    likes: int
    comments: int
    sentiment: SentimentLabel
    sentiment_score: float  # -1 to +1
    is_influencer: bool = False


class Influencer(BaseModel):
    id: str
    name: str
    platform: str
    avatar_url: Optional[str] = None
    followers: int
    win_rate: float         # 0–1, historical recommendation accuracy
    avg_return: float       # average return on recommendations
    total_calls: int
    latest_view: str
    latest_view_sentiment: SentimentLabel
    watchlist_overlap: list[str] = []   # symbols they also hold


class AnomalySource(BaseModel):
    platform: str
    author: str
    content_snippet: str
    published_at: str
    minutes_before_move: int   # how many minutes before price moved


class AnomalyAlert(BaseModel):
    symbol: str
    detected_at: str
    move_type: str             # surge / drop
    move_pct: float
    sources: list[AnomalySource]
    summary: str
