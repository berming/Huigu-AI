import { NextRequest, NextResponse } from 'next/server';
import { getInfluencers, STOCK_DB } from '../../../_lib/mock';

export const dynamic = 'force-dynamic';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  const name = req.nextUrl.searchParams.get('name') ?? (STOCK_DB[symbol]?.name ?? symbol);
  return NextResponse.json(getInfluencers(symbol, name));
}
