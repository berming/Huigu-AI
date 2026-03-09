import { NextRequest, NextResponse } from 'next/server';
import { getStockQuote } from '../../../_lib/mock';

export const dynamic = 'force-dynamic';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  const quote = getStockQuote(symbol);
  if (!quote) return NextResponse.json({ error: 'Not found' }, { status: 404 });
  return NextResponse.json(quote);
}
