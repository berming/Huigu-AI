export const Colors = {
  // Background layers
  bg: {
    primary: '#0D1117',
    secondary: '#161B22',
    card: '#1C2128',
    elevated: '#21262D',
    border: '#30363D',
  },

  // Brand
  brand: {
    primary: '#F0B429',    // gold — 慧股AI brand color
    secondary: '#E6A817',
  },

  // Market colors (A-share standard: red = up, green = down)
  market: {
    up: '#F84960',         // 涨 red
    upLight: 'rgba(248,73,96,0.15)',
    down: '#26A17B',       // 跌 green
    downLight: 'rgba(38,161,123,0.15)',
    flat: '#8B949E',
  },

  // Sentiment
  sentiment: {
    bull: '#F84960',
    bear: '#26A17B',
    neutral: '#8B949E',
  },

  // AI / highlights
  ai: {
    purple: '#A855F7',
    blue: '#3B82F6',
    teal: '#14B8A6',
  },

  // Risk / opportunity
  risk: '#F84960',
  opportunity: '#26A17B',

  // Text
  text: {
    primary: '#E6EDF3',
    secondary: '#8B949E',
    muted: '#484F58',
    inverse: '#0D1117',
  },
} as const;

export const Typography = {
  price: { fontSize: 28, fontWeight: '700' as const },
  priceMd: { fontSize: 20, fontWeight: '700' as const },
  priceSm: { fontSize: 16, fontWeight: '600' as const },
  label: { fontSize: 12, fontWeight: '400' as const },
  body: { fontSize: 14, fontWeight: '400' as const },
  bodyBold: { fontSize: 14, fontWeight: '600' as const },
  caption: { fontSize: 11, fontWeight: '400' as const },
  h1: { fontSize: 22, fontWeight: '700' as const },
  h2: { fontSize: 18, fontWeight: '700' as const },
  h3: { fontSize: 16, fontWeight: '600' as const },
} as const;

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const Radius = {
  sm: 6,
  md: 10,
  lg: 16,
  full: 999,
} as const;
