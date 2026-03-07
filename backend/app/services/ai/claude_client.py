"""
Claude API client for AI-powered investment research features.
Uses claude-sonnet-4-6 with tool use for structured outputs and streaming
for real-time analysis.
"""
import json
from datetime import datetime
from typing import AsyncIterator

import anthropic

from app.config import get_settings
from app.models.ai import (
    BullBearDebate, DebateArgument, AnnouncementSummary,
    HotConcept, ConceptStock, AIAnalysis
)

SYSTEM_PROMPT = """你是慧股AI的智能投研助手，专注于中国A股市场分析。
你的任务是基于提供的市场数据、公告内容和社区舆情，生成专业、客观的投研分析。

分析原则：
1. 多空并重，客观呈现市场分歧
2. 引用具体数据支撑观点
3. 明确标注风险因素
4. 语言简洁专业，使用金融术语
5. 所有分析仅供参考，不构成投资建议

请用中文回答。"""


def _get_client() -> anthropic.Anthropic:
    settings = get_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


# ── Bull/Bear Debate ─────────────────────────────────────────────────────────

DEBATE_TOOL = {
    "name": "generate_bull_bear_debate",
    "description": "生成结构化多空辩论分析报告",
    "input_schema": {
        "type": "object",
        "properties": {
            "bull_ratio": {
                "type": "number",
                "description": "看多比例 0-100，代表当前市场多空情绪中看多方的百分比"
            },
            "bull_arguments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "point": {"type": "string", "description": "核心论点"},
                        "evidence": {"type": "string", "description": "支撑证据"},
                        "strength": {"type": "integer", "description": "论点强度 1-5"}
                    },
                    "required": ["point", "evidence", "strength"]
                },
                "description": "看多论点列表，3-5条"
            },
            "bear_arguments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "point": {"type": "string"},
                        "evidence": {"type": "string"},
                        "strength": {"type": "integer"}
                    },
                    "required": ["point", "evidence", "strength"]
                },
                "description": "看空论点列表，3-5条"
            },
            "key_risks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "主要风险提示，3条"
            },
            "key_opportunities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "主要机会亮点，3条"
            },
            "ai_summary": {
                "type": "string",
                "description": "AI综合研判摘要，150字以内"
            }
        },
        "required": ["bull_ratio", "bull_arguments", "bear_arguments", "key_risks", "key_opportunities", "ai_summary"]
    }
}


async def generate_bull_bear_debate(
    symbol: str,
    name: str,
    quote_context: str,
    sentiment_context: str,
) -> BullBearDebate:
    client = _get_client()

    prompt = f"""请对股票 {name}（{symbol}）进行多空辩论分析。

当前行情数据：
{quote_context}

社区舆情概况：
{sentiment_context}

请生成一份全面的多空辩论报告，包含：
- 多方核心论点（基本面、技术面、资金面、政策面等维度）
- 空方核心论点（估值、风险、竞争、宏观等维度）
- 关键风险提示
- 核心机会亮点
- AI综合判断

保持客观中立，多空论据均需有数据或逻辑支撑。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[DEBATE_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract tool use result
    for block in response.content:
        if block.type == "tool_use" and block.name == "generate_bull_bear_debate":
            data = block.input
            return BullBearDebate(
                symbol=symbol,
                name=name,
                generated_at=datetime.now().isoformat(),
                bull_ratio=data["bull_ratio"],
                bull_arguments=[DebateArgument(**a) for a in data["bull_arguments"]],
                bear_arguments=[DebateArgument(**a) for a in data["bear_arguments"]],
                key_risks=data["key_risks"],
                key_opportunities=data["key_opportunities"],
                ai_summary=data["ai_summary"],
            )

    raise ValueError("Claude did not return a tool use block for debate generation")


# ── Announcement Summary ─────────────────────────────────────────────────────

ANNOUNCEMENT_TOOL = {
    "name": "summarize_announcement",
    "description": "解读上市公司公告，生成结构化摘要",
    "input_schema": {
        "type": "object",
        "properties": {
            "one_line_summary": {"type": "string", "description": "一句话核心亮点"},
            "opportunities": {
                "type": "array", "items": {"type": "string"},
                "description": "绿色机会信号，2-3条"
            },
            "risks": {
                "type": "array", "items": {"type": "string"},
                "description": "红色风险提示，2-3条"
            },
            "full_summary": {"type": "string", "description": "完整摘要，200字以内"}
        },
        "required": ["one_line_summary", "opportunities", "risks", "full_summary"]
    }
}


async def summarize_announcement(
    symbol: str,
    name: str,
    title: str,
    content: str,
    date: str,
) -> AnnouncementSummary:
    client = _get_client()

    prompt = f"""请解读以下上市公司公告：

公司：{name}（{symbol}）
日期：{date}
标题：{title}

公告内容：
{content[:3000]}

请生成结构化解读，重点标注：
🟢 机会信号（利好因素）
🔴 风险提示（利空因素）
并提炼一句话核心亮点。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        tools=[ANNOUNCEMENT_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "summarize_announcement":
            data = block.input
            return AnnouncementSummary(
                symbol=symbol,
                name=name,
                announcement_date=date,
                title=title,
                one_line_summary=data["one_line_summary"],
                opportunities=data["opportunities"],
                risks=data["risks"],
                full_summary=data["full_summary"],
            )

    raise ValueError("Claude did not return announcement summary")


# ── AI Stock Analysis (Streaming) ────────────────────────────────────────────

async def stream_stock_analysis(
    symbol: str,
    name: str,
    quote_context: str,
    sentiment_context: str,
) -> AsyncIterator[str]:
    client = _get_client()

    prompt = f"""请对股票 {name}（{symbol}）进行综合投研分析。

行情数据：
{quote_context}

市场情绪：
{sentiment_context}

请从以下维度分析：
1. 基本面分析（业绩、估值、行业地位）
2. 技术面分析（趋势、支撑阻力位、指标信号）
3. 资金面分析（主力动向、北上资金、融资融券）
4. 舆情分析（市场预期、社区情绪）
5. 综合研判与操作建议

最后注明：以上分析由AI生成，仅供参考，不构成投资建议。"""

    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


# ── Hot Concept Analysis ─────────────────────────────────────────────────────

CONCEPT_TOOL = {
    "name": "analyze_hot_concept",
    "description": "分析市场热点概念，生成结构化报告",
    "input_schema": {
        "type": "object",
        "properties": {
            "drive_logic": {"type": "string", "description": "核心驱动逻辑，100字以内"},
            "policy_background": {"type": "string", "description": "政策背景，100字以内"},
            "leading_criteria": {"type": "string", "description": "龙头辨识标准"},
            "heat_score": {"type": "number", "description": "热度评分 0-100"},
        },
        "required": ["drive_logic", "policy_background", "leading_criteria", "heat_score"]
    }
}


async def analyze_hot_concept(concept_name: str, news_context: str) -> dict:
    client = _get_client()

    prompt = f"""请分析市场热点概念：{concept_name}

相关资讯背景：
{news_context[:2000]}

请提供：
1. 核心驱动逻辑
2. 政策背景
3. 龙头股辨识标准（谁最纯正、谁有实质订单等）
4. 当前热度评分（0-100）"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        tools=[CONCEPT_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return {}


# ── Post Summarizer (Long-press feature) ─────────────────────────────────────

async def summarize_post(content: str) -> str:
    """Quick one-paragraph summary of a social post (for long-press feature)."""
    client = _get_client()

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system="你是一个金融内容摘要助手，用2-3句话提炼社区帖子的核心投资逻辑。语言简洁直接。",
        messages=[{"role": "user", "content": f"请提炼以下帖子的核心投资逻辑：\n\n{content}"}],
    )

    return response.content[0].text if response.content else ""
