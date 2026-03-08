import { NextRequest, NextResponse } from 'next/server';
import { getSentimentScore } from '../../../_lib/mock';

export const dynamic = 'force-dynamic';

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ symbol: string }> }
) {
  const { symbol } = await params;
  return NextResponse.json(getSentimentScore(symbol));
}
