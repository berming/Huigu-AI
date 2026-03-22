import { NextRequest, NextResponse } from 'next/server';
import { getKline } from '../../../_lib/mock';

export const dynamic = 'force-dynamic';

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  const period = req.nextUrl.searchParams.get('period') ?? 'D';
  return NextResponse.json(getKline(symbol, period));
}
