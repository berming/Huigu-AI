import { NextRequest, NextResponse } from 'next/server';
import { getBatchQuotes } from '../../../_lib/mock';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const symbols: string[] = await req.json();
  return NextResponse.json(getBatchQuotes(symbols));
}
