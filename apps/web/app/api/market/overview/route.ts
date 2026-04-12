import { NextResponse } from 'next/server';
import { getMarketOverview } from '../../_lib/mock';

export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json(getMarketOverview());
}
