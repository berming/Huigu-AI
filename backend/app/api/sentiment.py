from fastapi import APIRouter, Query
from app.services.sentiment.aggregator import (
    get_sentiment_score, get_social_posts, get_heat_trend,
    get_influencers, get_anomaly_alert
)

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


@router.get("/{symbol}/score")
async def sentiment_score(symbol: str, name: str = Query("股票")):
    return await get_sentiment_score(symbol, name)


@router.get("/{symbol}/posts")
async def social_posts(
    symbol: str,
    name: str = Query("股票"),
    limit: int = Query(30, le=100),
):
    return await get_social_posts(symbol, name, limit)


@router.get("/{symbol}/heat")
async def heat_trend(symbol: str):
    return await get_heat_trend(symbol)


@router.get("/{symbol}/influencers")
async def influencers(symbol: str, name: str = Query("股票")):
    return await get_influencers(symbol, name)


@router.get("/{symbol}/anomaly")
async def anomaly_alert(symbol: str, name: str = Query("股票")):
    result = await get_anomaly_alert(symbol, name)
    return result or {"message": "No anomaly detected"}
