import { NextRequest, NextResponse } from 'next/server';
import { getMockDebate, getStockQuote, getSentimentScore, STOCK_DB } from '../../../_lib/mock';
import Anthropic from '@anthropic-ai/sdk';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const SYSTEM_PROMPT = `你是慧股AI的智能投研助手，专注于中国A股市场分析。请用中文回答。`;

const DEBATE_TOOL: Anthropic.Tool = {
  name: 'generate_bull_bear_debate',
  description: '生成结构化多空辩论分析报告',
  input_schema: {
    type: 'object' as const,
    properties: {
      bull_ratio: { type: 'number', description: '看多比例 0-100' },
      bull_arguments: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            point:    { type: 'string' },
            evidence: { type: 'string' },
            strength: { type: 'integer' },
          },
          required: ['point', 'evidence', 'strength'],
        },
        description: '看多论点列表，3-5条',
      },
      bear_arguments: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            point:    { type: 'string' },
            evidence: { type: 'string' },
            strength: { type: 'integer' },
          },
          required: ['point', 'evidence', 'strength'],
        },
        description: '看空论点列表，3-5条',
      },
      key_risks:         { type: 'array', items: { type: 'string' }, description: '主要风险提示，3条' },
      key_opportunities: { type: 'array', items: { type: 'string' }, description: '主要机会亮点，3条' },
      ai_summary:        { type: 'string', description: 'AI综合研判摘要，150字以内' },
    },
    required: ['bull_ratio', 'bull_arguments', 'bear_arguments', 'key_risks', 'key_opportunities', 'ai_summary'],
  },
};

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  const name = req.nextUrl.searchParams.get('name') ?? (STOCK_DB[symbol]?.name ?? symbol);

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return NextResponse.json(getMockDebate(symbol, name));
  }

  try {
    const quote     = getStockQuote(symbol);
    const sentiment = getSentimentScore(symbol);
    const quoteCtx  = quote
      ? `价格: ${quote.price} 元，涨跌幅: ${quote.change_pct}%，市盈率: ${quote.pe_ratio}，成交量: ${quote.volume}`
      : '数据暂缺';
    const sentCtx = `看多${Math.round(sentiment.bull_ratio * 100)}%，看空${Math.round(sentiment.bear_ratio * 100)}%，热度${sentiment.heat_score}分`;

    const client = new Anthropic({ apiKey });
    const prompt = `请对股票 ${name}（${symbol}）进行多空辩论分析。\n行情：${quoteCtx}\n舆情：${sentCtx}`;

    const response = await client.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 2000,
      system: SYSTEM_PROMPT,
      tools: [DEBATE_TOOL],
      tool_choice: { type: 'any' },
      messages: [{ role: 'user', content: prompt }],
    });

    for (const block of response.content) {
      if (block.type === 'tool_use' && block.name === 'generate_bull_bear_debate') {
        const d = block.input as Record<string, unknown>;
        return NextResponse.json({
          symbol, name,
          generated_at: new Date().toISOString(),
          ...d,
        });
      }
    }
  } catch (e) {
    console.error('[debate]', e);
  }

  // Fallback to mock if Claude call fails
  return NextResponse.json(getMockDebate(symbol, name));
}
