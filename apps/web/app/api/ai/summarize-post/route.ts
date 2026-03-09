import { NextRequest, NextResponse } from 'next/server';
import Anthropic from '@anthropic-ai/sdk';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(req: NextRequest) {
  const { content } = await req.json();
  const apiKey = process.env.ANTHROPIC_API_KEY;

  if (!apiKey) {
    return NextResponse.json({ summary: '该帖子分析了相关股票的投资逻辑，结合技术面与基本面给出了操作建议，可作为参考依据之一。' });
  }

  try {
    const client = new Anthropic({ apiKey });
    const response = await client.messages.create({
      model: 'claude-sonnet-4-6',
      max_tokens: 200,
      system: '你是一个金融内容摘要助手，用2-3句话提炼社区帖子的核心投资逻辑。语言简洁直接。',
      messages: [{ role: 'user', content: `请提炼以下帖子的核心投资逻辑：\n\n${content}` }],
    });
    const text = response.content[0]?.type === 'text' ? response.content[0].text : '';
    return NextResponse.json({ summary: text });
  } catch {
    return NextResponse.json({ summary: '摘要生成失败，请稍后重试。' });
  }
}
