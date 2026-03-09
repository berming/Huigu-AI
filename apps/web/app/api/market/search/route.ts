import { NextRequest, NextResponse } from 'next/server';
import { searchStocks } from '../../_lib/mock';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get('q') ?? '';
  return NextResponse.json(searchStocks(q));
}
