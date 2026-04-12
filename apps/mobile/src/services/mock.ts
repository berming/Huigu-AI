/**
 * Standalone mock data for the mobile app.
 * Mirrors apps/web/app/api/_lib/mock.ts — no backend required.
 */

// ── Seeded RNG ────────────────────────────────────────────────────────────────

function seeded(seed: number) {
  let s = (seed >>> 0) || 1;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967295;
  };
}

function symbolHash(sym: string, extra = 0): number {
  let h = extra >>> 0;
  for (let i = 0; i < sym.length; i++) {
    h = (Math.imul(h + sym.charCodeAt(i), 2654435761)) >>> 0;
  }
  return h;
}

function hourSeed(): number {
  const d = new Date();
  return d.getFullYear() * 1000000 + (d.getMonth() + 1) * 10000 + d.getDate() * 100 + d.getHours();
}

// ── Stock database ────────────────────────────────────────────────────────────

export const STOCK_DB: Record<string, { name: string; basePrice: number; marketCap: number }> = {
  '000001': { name: '平安银行',   basePrice: 11.5,   marketCap: 2.23e11 },
  '600519': { name: '贵州茅台',   basePrice: 1680.0, marketCap: 2.12e12 },
  '000858': { name: '五粮液',     basePrice: 148.5,  marketCap: 5.77e11 },
  '601318': { name: '中国平安',   basePrice: 45.2,   marketCap: 8.22e11 },
  '300750': { name: '宁德时代',   basePrice: 236.0,  marketCap: 5.53e11 },
  '002594': { name: '比亚迪',     basePrice: 278.0,  marketCap: 8.07e11 },
  '600036': { name: '招商银行',   basePrice: 35.8,   marketCap: 9.04e11 },
  '601166': { name: '兴业银行',   basePrice: 18.2,   marketCap: 3.76e11 },
  '000333': { name: '美的集团',   basePrice: 55.6,   marketCap: 4.00e11 },
  '002415': { name: '海康威视',   basePrice: 27.3,   marketCap: 2.61e11 },
  '688111': { name: '金山办公',   basePrice: 185.0,  marketCap: 7.43e10 },
  '601398': { name: '工商银行',   basePrice: 5.62,   marketCap: 2.00e12 },
  '600900': { name: '长江电力',   basePrice: 26.8,   marketCap: 6.44e11 },
  '000725': { name: '京东方A',    basePrice: 4.35,   marketCap: 1.83e11 },
  '601012': { name: '隆基绿能',   basePrice: 22.1,   marketCap: 1.67e11 },
  '600276': { name: '恒瑞医药',   basePrice: 43.5,   marketCap: 2.78e11 },
  '002475': { name: '立讯精密',   basePrice: 33.2,   marketCap: 2.38e11 },
  '300760': { name: '迈瑞医疗',   basePrice: 258.0,  marketCap: 3.14e11 },
  '601888': { name: '中国中免',   basePrice: 58.3,   marketCap: 1.18e11 },
  '000568': { name: '泸州老窖',   basePrice: 92.5,   marketCap: 1.43e11 },
};

const INDICES = [
  { symbol: '000001', name: '上证指数', base: 3280.0 },
  { symbol: '399001', name: '深证成指', base: 10520.0 },
  { symbol: '399006', name: '创业板指', base: 2085.0 },
  { symbol: '000300', name: '沪深300',  base: 3890.0 },
  { symbol: '000688', name: '科创50',   base: 960.0 },
];

// ── Market helpers ────────────────────────────────────────────────────────────

function cleanSymbol(symbol: string) {
  return symbol.replace(/^(SH|SZ)\.?/i, '').replace(/\.(SH|SZ)$/i, '');
}

function getPrice(sym: string, base: number) {
  const rng = seeded(symbolHash(sym) ^ hourSeed());
  const changePct = (rng() - 0.48) * 0.07;
  const price    = Math.round(base * (1 + changePct) * 100) / 100;
  const change   = Math.round((price - base) * 100) / 100;
  return { price, change, changePct: Math.round(changePct * 10000) / 100 };
}

export function getStockQuote(symbol: string) {
  const code  = cleanSymbol(symbol);
  const stock = STOCK_DB[code];
  if (!stock) return null;

  const { price, change, changePct } = getPrice(code, stock.basePrice);
  const rng  = seeded(symbolHash(code, 42));
  const open = Math.round(stock.basePrice * (1 + (rng() - 0.5) * 0.01) * 100) / 100;
  const high = Math.round(Math.max(open, price) * (1 + rng() * 0.02) * 100) / 100;
  const low  = Math.round(Math.min(open, price) * (1 - rng() * 0.02) * 100) / 100;
  const vol  = Math.floor(rng() * 4900000 + 100000);

  return {
    symbol: code,
    name: stock.name,
    price,
    change,
    change_pct: changePct,
    open,
    high,
    low,
    prev_close: stock.basePrice,
    volume: vol,
    amount: Math.round(vol * price * 100),
    turnover_rate: Math.round(rng() * 750 + 50) / 100,
    pe_ratio:      Math.round(rng() * 3700 + 800) / 100,
    market_cap:    stock.marketCap,
  };
}

export function getBatchQuotes(symbols: string[]) {
  return symbols.map(getStockQuote).filter(Boolean) as ReturnType<typeof getStockQuote>[];
}

export function getMarketOverview() {
  const rng = seeded(hourSeed());
  const indices = INDICES.map(idx => {
    const { price, change, changePct } = getPrice(idx.symbol, idx.base);
    return { symbol: idx.symbol, name: idx.name, price, change, change_pct: changePct };
  });
  const total = 5300;
  const up    = Math.floor(rng() * 1500 + 2000);
  const down  = Math.floor(rng() * 1000 + 1500);
  return { indices, up_count: up, down_count: down, flat_count: total - up - down };
}

export function getKline(symbol: string, period = 'D') {
  const code  = cleanSymbol(symbol);
  const stock = STOCK_DB[code] ?? { name: symbol, basePrice: 10.0, marketCap: 0 };
  const days  = period === 'D' ? 250 : period === 'W' ? 52 : 24;
  const msStep = period === 'D' ? 86400000 : period === 'W' ? 604800000 : 2592000000;

  const bars: Array<{
    date: string; open: number; high: number; low: number;
    close: number; volume: number; amount: number;
  }> = [];
  let price = stock.basePrice * 0.7;
  const end = Date.now();
  const rng = seeded(symbolHash(code, 99));

  for (let i = days; i >= 0; i--) {
    const d = new Date(end - msStep * i);
    if (period === 'D' && (d.getDay() === 0 || d.getDay() === 6)) continue;

    const u1 = Math.max(rng(), 1e-9);
    const u2 = rng();
    const gauss = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    const openP  = Math.round(price * 100) / 100;
    const closeP = Math.round(price * (1 + 0.001 + gauss * 0.018) * 100) / 100;
    const highP  = Math.round(Math.max(openP, closeP) * (1 + rng() * 0.015) * 100) / 100;
    const lowP   = Math.round(Math.min(openP, closeP) * (1 - rng() * 0.015) * 100) / 100;
    const vol    = Math.floor(rng() * 2900000 + 100000);

    bars.push({
      date: d.toISOString().slice(0, 10),
      open: openP, high: highP, low: lowP, close: closeP,
      volume: vol, amount: Math.round(vol * closeP * 100),
    });
    price = closeP;
  }

  return { symbol: code, name: stock.name, period, bars };
}

export function searchStocks(query: string) {
  const q = query.toLowerCase();
  return Object.entries(STOCK_DB)
    .filter(([code, s]) => code.includes(q) || s.name.includes(q))
    .slice(0, 20)
    .map(([code, s]) => ({
      symbol: code,
      name: s.name,
      market: code.startsWith('6') || code.startsWith('9') ? 'SH' : 'SZ',
    }));
}

// ── Sentiment helpers ─────────────────────────────────────────────────────────

const MOCK_AUTHORS = [
  { name: '股海老兵',     platform: 'xueqiu',     isInfluencer: true,  winRate: 0.68 },
  { name: '价值猎手',     platform: 'weibo',       isInfluencer: true,  winRate: 0.72 },
  { name: '技术流分析师', platform: 'zhihu',       isInfluencer: true,  winRate: 0.65 },
  { name: '短线快手',     platform: 'weibo',       isInfluencer: false, winRate: 0.55 },
  { name: '量化小王子',   platform: 'xueqiu',     isInfluencer: true,  winRate: 0.70 },
  { name: '散户小明',     platform: 'guba',        isInfluencer: false, winRate: 0.48 },
  { name: '北上资金追踪', platform: 'weibo',       isInfluencer: true,  winRate: 0.73 },
  { name: '红书股坛',     platform: 'xiaohongshu', isInfluencer: false, winRate: 0.52 },
  { name: '财经老法师',   platform: 'zhihu',       isInfluencer: true,  winRate: 0.66 },
  { name: '追涨停板',     platform: 'guba',        isInfluencer: false, winRate: 0.51 },
];

const BULLISH_TPL = [
  '今天{n}放量突破，主力资金明显流入，短线看涨！',
  '{n}近期基本面改善明显，业绩预增，值得重点关注。',
  '从技术面看{n}已在底部震荡，MACD金叉，看多！',
  '{n}北上资金持续加仓，外资看好，建议逢低布局。',
  '板块联动效应明显，{n}有望带动整板上行。',
  '{n}订单大增，业绩有望超预期，持股待涨。',
];
const BEARISH_TPL = [
  '{n}高位震荡，量能萎缩，注意风险！',
  '大盘压力较大，{n}短线承压，建议观望。',
  '{n}业绩低于预期，机构可能减仓，谨慎！',
  '技术面来看{n}已到压力位，短线可能调整。',
  '{n}解禁压力较大，近期小心砸盘。',
];
const NEUTRAL_TPL = [
  '{n}今日成交平淡，短期方向待定，持续观察。',
  '对{n}保持中性，等待更明确的信号。',
  '{n}横盘整理，等待方向选择，暂时观望。',
];

function pickTpl(templates: string[], rng: () => number, name: string) {
  return templates[Math.floor(rng() * templates.length)].replace(/{n}/g, name);
}

export function getSentimentScore(symbol: string) {
  const rng  = seeded(symbolHash(symbol) ^ hourSeed());
  const bull = Math.floor(rng() * 30 + 25);
  const bear = Math.floor(rng() * 20 + 10);
  const neu  = Math.floor(rng() * 15 + 10);
  const total = bull + bear + neu;
  return {
    bull_ratio:    Math.round(bull  / total * 1000) / 1000,
    bear_ratio:    Math.round(bear  / total * 1000) / 1000,
    neutral_ratio: Math.round(neu   / total * 1000) / 1000,
    total_posts: total,
    heat_score:  Math.round(rng() * 65 + 30),
  };
}

export function getSocialPosts(symbol: string, name: string, limit = 30) {
  const rng  = seeded(symbolHash(symbol, 77) ^ hourSeed());
  const now  = Date.now();
  const posts = [];

  for (let i = 0; i < limit; i++) {
    const author = MOCK_AUTHORS[Math.floor(rng() * MOCK_AUTHORS.length)];
    const roll   = rng();
    let sentiment: string, content: string, score: number;

    if (roll < 0.5) {
      sentiment = 'bullish'; content = pickTpl(BULLISH_TPL, rng, name);
      score = Math.round((rng() * 0.7 + 0.3) * 100) / 100;
    } else if (roll < 0.8) {
      sentiment = 'bearish'; content = pickTpl(BEARISH_TPL, rng, name);
      score = -Math.round((rng() * 0.7 + 0.3) * 100) / 100;
    } else {
      sentiment = 'neutral'; content = pickTpl(NEUTRAL_TPL, rng, name);
      score = Math.round((rng() - 0.5) * 0.4 * 100) / 100;
    }

    const minsAgo = Math.floor(rng() * 475 + 5);
    posts.push({
      id:           `post_${symbol}_${i}`,
      platform:     author.platform,
      author:       author.name,
      content,
      published_at: new Date(now - minsAgo * 60000).toISOString(),
      likes:        Math.floor(rng() * 4995 + 5),
      comments:     Math.floor(rng() * 499 + 1),
      sentiment,
      sentiment_score: score,
      is_influencer: author.isInfluencer,
    });
  }

  return posts.sort((a, b) => b.published_at.localeCompare(a.published_at));
}

export function getHeatTimeline(symbol: string) {
  const rng = seeded(symbolHash(symbol, 11) ^ hourSeed());
  const now = Date.now();
  return Array.from({ length: 24 }, (_, i) => ({
    time:      new Date(now - (23 - i) * 3600000).toISOString(),
    count:     Math.floor(rng() * 180 + 20),
    sentiment: Math.round((rng() - 0.4) * 2 * 100) / 100,
  }));
}

export function getInfluencers(symbol: string, name: string) {
  const rng = seeded(symbolHash(symbol, 55) ^ hourSeed());
  return MOCK_AUTHORS.filter(a => a.isInfluencer).map(a => {
    const isBull = rng() > 0.4;
    const view   = isBull ? pickTpl(BULLISH_TPL, rng, name) : pickTpl(BEARISH_TPL, rng, name);
    return {
      id:                    `inf_${a.name}`,
      name:                  a.name,
      platform:              a.platform,
      followers:             Math.floor(rng() * 490000 + 10000),
      win_rate:              a.winRate,
      avg_return:            Math.round((rng() * 27 + 8) * 10) / 10,
      total_calls:           Math.floor(rng() * 250 + 50),
      latest_view:           view,
      latest_view_sentiment: isBull ? 'bullish' : 'bearish',
    };
  });
}

export function getMockDebate(symbol: string, name: string) {
  const code  = cleanSymbol(symbol);
  const { price, changePct } = getPrice(code, STOCK_DB[code]?.basePrice ?? 10);
  const rng   = seeded(symbolHash(symbol, 33) ^ hourSeed());
  const bullR = Math.round(rng() * 30 + 45);

  return {
    symbol,
    name,
    generated_at: new Date().toISOString(),
    bull_ratio: bullR,
    bull_arguments: [
      { point: '基本面持续改善', evidence: `${name}近三季度营收同比增长${Math.floor(rng() * 20 + 8)}%，净利润增速超预期。`, strength: Math.floor(rng() * 2 + 3) },
      { point: '机构持续加仓',   evidence: `最新季报显示公募持股比例环比提升，北上资金近30日净买入超${Math.floor(rng() * 30 + 10)}亿元。`, strength: Math.floor(rng() * 2 + 3) },
      { point: '技术形态突破',   evidence: '周线MACD金叉，站上60日均线且成交量有效放大，形态较为标准。', strength: Math.floor(rng() * 2 + 2) },
      { point: '行业政策利好',   evidence: '近期政策扶持力度加大，行业景气周期有望持续向上，龙头优势进一步强化。', strength: Math.floor(rng() * 1 + 3) },
    ],
    bear_arguments: [
      { point: '估值偏高风险', evidence: `当前PE-TTM为${Math.floor(rng() * 20 + 25)}倍，高于行业均值，存在估值回归压力。`, strength: Math.floor(rng() * 2 + 2) },
      { point: '解禁减持压力', evidence: `未来3个月内有约${Math.floor(rng() * 5 + 2)}亿股限售解禁，可能短期压制股价。`, strength: Math.floor(rng() * 2 + 2) },
      { point: '宏观环境不确定', evidence: '全球流动性环境仍有不确定性，外资波动可能加剧。', strength: Math.floor(rng() * 1 + 2) },
    ],
    key_risks: [
      '若业绩增速低于预期，可能引发估值重塑',
      '大盘系统性风险传导，板块联动下行压力',
      '限售股解禁带来的潜在减持压力',
    ],
    key_opportunities: [
      '政策红利持续释放，行业景气有望超预期',
      '公司新产品/新业务有望打开估值空间',
      '机构低配背景下，若业绩超预期将引发补仓行情',
    ],
    ai_summary: `${name}当前股价${price}元，今日${changePct >= 0 ? '上涨' : '下跌'}${Math.abs(changePct).toFixed(2)}%。多方看好基本面改善与机构持续布局；空方担忧高估值与解禁减持压力。多空比约${bullR}:${100 - bullR}，${bullR >= 55 ? '情绪偏乐观，可适度关注但需控制仓位' : '分歧较大，建议等待信号明朗后再行决策'}。`,
  };
}

export function getMockAnalysis(symbol: string, name: string): string {
  const code  = cleanSymbol(symbol);
  const stock = STOCK_DB[code];
  const { price, changePct } = getPrice(code, stock?.basePrice ?? 10);
  const trend = changePct >= 0 ? '上涨' : '下跌';
  const pct   = Math.abs(changePct).toFixed(2);

  return `## ${name}（${symbol}）智能投研分析\n\n### 一、基本面分析\n\n${name}当前股价 ${price} 元，今日${trend} ${pct}%。公司所处行业景气度${changePct >= 0 ? '持续向好' : '有所承压'}，主营业务收入保持稳健增长。近期机构调研频次上升，估值处于历史中位，具备一定安全边际。\n\n### 二、技术面分析\n\n近期走势${changePct >= 0 ? '强于大盘，突破前期压力位，放量上攻' : '弱于大盘，均线附近反复震荡，方向未明'}。MACD ${changePct >= 0 ? 'DIF与DEA金叉，短期动能较强' : '柱状图收窄，多空分歧加剧'}。关键支撑${(price * 0.95).toFixed(2)}元，阻力${(price * 1.06).toFixed(2)}元。\n\n### 三、资金面分析\n\n北上资金近期持股${changePct >= 0 ? '小幅增加，外资认可长期价值' : '有所下降，需关注外资动向'}。融资余额${changePct >= 0 ? '持续增加，多头情绪积极' : '小幅回落，加仓意愿减弱'}。\n\n### 四、综合研判\n\n${name}${changePct >= 0 ? '短期偏强，可关注量能配合情况。持仓者适当持有，观望者可在回调支撑位择机介入，严格控制仓位。' : '短期偏弱，建议等待企稳信号后布局。关注关键支撑位表现，若有效守住可逐步参与。'}\n\n> ⚠️ 以上分析由AI生成，仅供参考，不构成投资建议。`;
}
