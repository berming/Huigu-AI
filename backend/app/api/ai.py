from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.ai.claude_client import (
    generate_bull_bear_debate,
    summarize_announcement,
    stream_stock_analysis,
    summarize_post,
)
from app.config import get_settings

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _check_api_key():
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI service not configured. Please set ANTHROPIC_API_KEY."
        )


class DebateRequest(BaseModel):
    quote_context: str = ""
    sentiment_context: str = ""


class AnnouncementRequest(BaseModel):
    title: str
    content: str
    date: str


class PostSummaryRequest(BaseModel):
    content: str


@router.post("/debate/{symbol}")
async def bull_bear_debate(
    symbol: str,
    name: str = Query("股票"),
    body: DebateRequest = DebateRequest(),
):
    _check_api_key()
    return await generate_bull_bear_debate(
        symbol=symbol,
        name=name,
        quote_context=body.quote_context,
        sentiment_context=body.sentiment_context,
    )


@router.post("/announcement/{symbol}")
async def announcement_summary(
    symbol: str,
    name: str = Query("股票"),
    body: AnnouncementRequest = ...,
):
    _check_api_key()
    return await summarize_announcement(
        symbol=symbol,
        name=name,
        title=body.title,
        content=body.content,
        date=body.date,
    )


@router.get("/analyze/{symbol}")
async def analyze_stock(
    symbol: str,
    name: str = Query("股票"),
    quote_context: str = Query(""),
    sentiment_context: str = Query(""),
):
    _check_api_key()

    async def generate():
        async for chunk in stream_stock_analysis(
            symbol=symbol,
            name=name,
            quote_context=quote_context,
            sentiment_context=sentiment_context,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/summarize-post")
async def summarize_social_post(body: PostSummaryRequest):
    _check_api_key()
    result = await summarize_post(body.content)
    return {"summary": result}
