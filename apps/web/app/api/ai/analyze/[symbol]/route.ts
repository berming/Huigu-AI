import { NextRequest } from 'next/server';
import { getMockAnalysis, STOCK_DB } from '../../../_lib/mock';
import Anthropic from '@anthropic-ai/sdk';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const SYSTEM_PROMPT = `你是慧股AI的智能投研助手，专注于中国A股市场分析。
分析原则：多空并重，客观呈现市场分歧；引用具体数据支撑观点；明确标注风险因素；语言简洁专业。
所有分析仅供参考，不构成投资建议。请用中文回答。`;

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  const name = req.nextUrl.searchParams.get('name') ?? (STOCK_DB[symbol]?.name ?? symbol);
  const encoder = new TextEncoder();

  // Without API key → stream mock analysis character-by-character
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    const text = getMockAnalysis(symbol, name);
    const chars = [...text]; // Unicode-safe split
    let i = 0;
    const stream = new ReadableStream({
      start(controller) {
        const tick = () => {
          if (i >= chars.length) { controller.close(); return; }
          const chunk = chars.slice(i, i + 4).join('');
          controller.enqueue(encoder.encode(chunk));
          i += 4;
          // Use setImmediate-equivalent to yield between chunks
          setTimeout(tick, 15);
        };
        tick();
      },
    });
    return new Response(stream, {
      headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Accel-Buffering': 'no' },
    });
  }

  // With API key → stream real Claude response
  const client = new Anthropic({ apiKey });
  const prompt = `请对股票 ${name}（${symbol}）进行综合投研分析，包括：基本面、技术面、资金面、舆情分析和综合研判。`;
  const stream = new ReadableStream({
    async start(controller) {
      try {
        const claudeStream = client.messages.stream({
          model: 'claude-sonnet-4-6',
          max_tokens: 1500,
          system: SYSTEM_PROMPT,
          messages: [{ role: 'user', content: prompt }],
        });
        for await (const event of claudeStream) {
          if (
            event.type === 'content_block_delta' &&
            event.delta.type === 'text_delta'
          ) {
            controller.enqueue(encoder.encode(event.delta.text));
          }
        }
      } catch {
        controller.enqueue(encoder.encode('\n\nAI分析服务暂时不可用，请稍后重试。'));
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Accel-Buffering': 'no' },
  });
}
