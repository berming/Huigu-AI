from pydantic import BaseModel
from typing import Optional


class DebateArgument(BaseModel):
    point: str
    evidence: str
    strength: int   # 1–5


class BullBearDebate(BaseModel):
    symbol: str
    name: str
    generated_at: str
    bull_ratio: float          # 0–100, market sentiment %
    bull_arguments: list[DebateArgument]
    bear_arguments: list[DebateArgument]
    key_risks: list[str]
    key_opportunities: list[str]
    ai_summary: str


class AnnouncementSummary(BaseModel):
    symbol: str
    name: str
    announcement_date: str
    title: str
    one_line_summary: str
    opportunities: list[str]    # green highlights
    risks: list[str]            # red warnings
    full_summary: str
    source_url: Optional[str] = None


class ConceptStock(BaseModel):
    symbol: str
    name: str
    relevance_score: float      # 0–1
    reason: str


class HotConcept(BaseModel):
    concept_name: str
    heat_score: float           # 0–100
    drive_logic: str            # core driver narrative
    policy_background: str
    leading_stocks: list[ConceptStock]
    related_symbols: list[str]


class AIAnalysis(BaseModel):
    symbol: str
    name: str
    generated_at: str
    overall_sentiment: str      # 看多 / 看空 / 中性
    price_target_range: Optional[str] = None
    analysis_text: str
    bullet_points: list[str]
    disclaimer: str = "以上分析由AI生成，仅供参考，不构成投资建议。投资有风险，入市须谨慎。"
