const ASSET_NAMES: Record<string, string> = {
  BTCUSDT: 'Bitcoin', ETHUSDT: 'Ethereum', BNBUSDT: 'BNB', SOLUSDT: 'Solana',
  XRPUSDT: 'XRP', ADAUSDT: 'Cardano', DOGEUSDT: 'Dogecoin', AVAXUSDT: 'Avalanche',
  DOTUSDT: 'Polkadot', LINKUSDT: 'Chainlink', MATICUSDT: 'Polygon', UNIUSDT: 'Uniswap',
  LTCUSDT: 'Litecoin', ATOMUSDT: 'Cosmos', NEARUSDT: 'NEAR Protocol', ARBUSDT: 'Arbitrum',
  OPUSDT: 'Optimism', SUIUSDT: 'Sui', APTUSDT: 'Aptos', INJUSDT: 'Injective',
  TIAUSDT: 'Celestia', SEIUSDT: 'Sei', FETUSDT: 'Fetch.ai', RENDERUSDT: 'Render',
  WLDUSDT: 'Worldcoin',
}

type AssetCat = 'blue-chip' | 'exchange-token' | 'large-alt' | 'defi-alt' | 'high-beta'
type TfCat = 'scalp' | 'intraday' | 'swing' | 'position'

const ASSET_CATEGORIES: Record<string, AssetCat> = {
  BTCUSDT: 'blue-chip', ETHUSDT: 'blue-chip',
  BNBUSDT: 'exchange-token',
  SOLUSDT: 'large-alt', XRPUSDT: 'large-alt', ADAUSDT: 'large-alt', AVAXUSDT: 'large-alt',
  DOTUSDT: 'large-alt', LTCUSDT: 'large-alt', ATOMUSDT: 'large-alt', NEARUSDT: 'large-alt',
  LINKUSDT: 'defi-alt', UNIUSDT: 'defi-alt', MATICUSDT: 'defi-alt',
  ARBUSDT: 'defi-alt', OPUSDT: 'defi-alt', INJUSDT: 'defi-alt',
  DOGEUSDT: 'high-beta', SUIUSDT: 'high-beta', APTUSDT: 'high-beta',
  TIAUSDT: 'high-beta', SEIUSDT: 'high-beta', FETUSDT: 'high-beta',
  RENDERUSDT: 'high-beta', WLDUSDT: 'high-beta',
}

const TF_CATEGORIES: Record<string, TfCat> = {
  '1m': 'scalp', '5m': 'scalp',
  '15m': 'intraday', '1h': 'intraday',
  '4h': 'swing',
  '1d': 'position',
}

const TF_LABELS: Record<string, string> = {
  '1m': '1-minute', '5m': '5-minute', '15m': '15-minute',
  '1h': '1-hour', '4h': '4-hour', '1d': 'daily',
}

interface StrategyParams {
  assetName: string
  tfLabel: string
  stop: string
  target: string
  trendP: number
  fastEma: number
  slowEma: number
  rsiOS: number
  rsiOB: number
  bbPeriod: number
  lookback: number
  holdBars: number
  volMult: string
}

// Parameter table: [assetCat, tfCat] → params
type ParamKey = `${AssetCat}|${TfCat}`

const PARAM_TABLE: Record<ParamKey, Omit<StrategyParams, 'assetName' | 'tfLabel' | 'volMult'> & { volMult: number }> = {
  'blue-chip|scalp':        { stop: '0.5%', target: '1.5%', trendP: 50, fastEma: 9,  slowEma: 21, rsiOS: 38, rsiOB: 62, bbPeriod: 15, lookback: 15, holdBars: 20, volMult: 1.5 },
  'blue-chip|intraday':     { stop: '1.2%', target: '3%',   trendP: 50, fastEma: 9,  slowEma: 21, rsiOS: 38, rsiOB: 62, bbPeriod: 20, lookback: 20, holdBars: 15, volMult: 1.5 },
  'blue-chip|swing':        { stop: '2.5%', target: '7%',   trendP: 50, fastEma: 9,  slowEma: 21, rsiOS: 36, rsiOB: 64, bbPeriod: 20, lookback: 20, holdBars: 10, volMult: 1.5 },
  'blue-chip|position':     { stop: '5%',   target: '14%',  trendP: 100,fastEma: 20, slowEma: 50, rsiOS: 32, rsiOB: 68, bbPeriod: 20, lookback: 20, holdBars: 8,  volMult: 1.5 },
  'exchange-token|scalp':   { stop: '0.6%', target: '1.6%', trendP: 50, fastEma: 9,  slowEma: 21, rsiOS: 39, rsiOB: 61, bbPeriod: 15, lookback: 15, holdBars: 20, volMult: 1.5 },
  'exchange-token|intraday':{ stop: '1.5%', target: '4%',   trendP: 50, fastEma: 9,  slowEma: 21, rsiOS: 39, rsiOB: 61, bbPeriod: 20, lookback: 20, holdBars: 12, volMult: 1.5 },
  'exchange-token|swing':   { stop: '3%',   target: '8%',   trendP: 50, fastEma: 9,  slowEma: 21, rsiOS: 36, rsiOB: 64, bbPeriod: 20, lookback: 20, holdBars: 8,  volMult: 1.5 },
  'exchange-token|position':{ stop: '6%',   target: '15%',  trendP: 100,fastEma: 20, slowEma: 50, rsiOS: 32, rsiOB: 68, bbPeriod: 20, lookback: 20, holdBars: 6,  volMult: 1.5 },
  'large-alt|scalp':        { stop: '0.8%', target: '2.2%', trendP: 20, fastEma: 7,  slowEma: 14, rsiOS: 40, rsiOB: 60, bbPeriod: 14, lookback: 12, holdBars: 18, volMult: 1.5 },
  'large-alt|intraday':     { stop: '2%',   target: '5.5%', trendP: 20, fastEma: 7,  slowEma: 14, rsiOS: 40, rsiOB: 60, bbPeriod: 20, lookback: 15, holdBars: 12, volMult: 1.5 },
  'large-alt|swing':        { stop: '4%',   target: '11%',  trendP: 50, fastEma: 9,  slowEma: 21, rsiOS: 38, rsiOB: 62, bbPeriod: 20, lookback: 20, holdBars: 8,  volMult: 1.5 },
  'large-alt|position':     { stop: '7%',   target: '18%',  trendP: 100,fastEma: 20, slowEma: 50, rsiOS: 35, rsiOB: 65, bbPeriod: 20, lookback: 20, holdBars: 6,  volMult: 1.5 },
  'defi-alt|scalp':         { stop: '1%',   target: '2.8%', trendP: 20, fastEma: 7,  slowEma: 14, rsiOS: 41, rsiOB: 59, bbPeriod: 14, lookback: 10, holdBars: 15, volMult: 1.5 },
  'defi-alt|intraday':      { stop: '2.5%', target: '6.5%', trendP: 20, fastEma: 7,  slowEma: 14, rsiOS: 41, rsiOB: 59, bbPeriod: 20, lookback: 15, holdBars: 12, volMult: 1.5 },
  'defi-alt|swing':         { stop: '5%',   target: '13%',  trendP: 50, fastEma: 9,  slowEma: 21, rsiOS: 39, rsiOB: 61, bbPeriod: 20, lookback: 20, holdBars: 8,  volMult: 1.5 },
  'defi-alt|position':      { stop: '8%',   target: '20%',  trendP: 100,fastEma: 20, slowEma: 50, rsiOS: 36, rsiOB: 64, bbPeriod: 20, lookback: 20, holdBars: 6,  volMult: 1.5 },
  'high-beta|scalp':        { stop: '1.2%', target: '3.5%', trendP: 14, fastEma: 5,  slowEma: 10, rsiOS: 42, rsiOB: 58, bbPeriod: 12, lookback: 10, holdBars: 12, volMult: 1.5 },
  'high-beta|intraday':     { stop: '3%',   target: '8%',   trendP: 14, fastEma: 5,  slowEma: 10, rsiOS: 42, rsiOB: 58, bbPeriod: 14, lookback: 12, holdBars: 10, volMult: 1.5 },
  'high-beta|swing':        { stop: '6%',   target: '16%',  trendP: 20, fastEma: 7,  slowEma: 14, rsiOS: 40, rsiOB: 60, bbPeriod: 20, lookback: 15, holdBars: 6,  volMult: 1.5 },
  'high-beta|position':     { stop: '10%',  target: '26%',  trendP: 50, fastEma: 14, slowEma: 28, rsiOS: 38, rsiOB: 62, bbPeriod: 20, lookback: 20, holdBars: 5,  volMult: 1.5 },
}

function buildParams(symbol: string, timeframe: string): StrategyParams {
  const assetCat: AssetCat = ASSET_CATEGORIES[symbol] ?? 'large-alt'
  const tfCat: TfCat = TF_CATEGORIES[timeframe] ?? 'swing'
  const key: ParamKey = `${assetCat}|${tfCat}`
  const row = PARAM_TABLE[key]
  return {
    assetName: ASSET_NAMES[symbol] ?? symbol.replace('USDT', ''),
    tfLabel: TF_LABELS[timeframe] ?? timeframe,
    ...row,
    volMult: `${row.volMult}x`,
  }
}

// ── 10 strategy direction generators ──────────────────────────────────────────

type StrategyGenerator = (p: StrategyParams) => { title: string; tagline: string; prompt: string }

const strategies: StrategyGenerator[] = [
  // 1. EMA Trend Follow
  (p) => ({
    title: 'EMA Trend Follow',
    tagline: `Dual EMA crossover (${p.fastEma}/${p.slowEma}) with ${p.trendP}-period trend filter`,
    prompt: `Build an EMA trend-following strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use the ${p.trendP}-period EMA as a trend filter — only enter long when price is above it. Enter when the ${p.fastEma}-period EMA crosses above the ${p.slowEma}-period EMA. Exit when the ${p.fastEma} EMA crosses back below the ${p.slowEma} EMA. Place a stop-loss ${p.stop} below entry. This dual-EMA crossover within a trend filter avoids counter-trend trades and keeps the system aligned with the dominant move.`,
  }),

  // 2. RSI Mean Reversion
  (p) => ({
    title: 'RSI Mean Reversion',
    tagline: `RSI dip below ${p.rsiOS} within uptrend, exit above ${p.rsiOB}`,
    prompt: `Build an RSI mean reversion strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Only enter when price is above the ${p.trendP}-period EMA (uptrend filter). Buy when RSI(14) drops below ${p.rsiOS}, signalling an oversold pullback within the trend. Exit when RSI rises back above ${p.rsiOB}. Place a stop-loss ${p.stop} below entry. This targets high-probability bounce setups where momentum has temporarily exhausted against a larger up-move.`,
  }),

  // 3. Momentum Continuation
  (p) => ({
    title: 'Momentum Continuation',
    tagline: `RSI 50–65 momentum zone with ${p.fastEma}/${p.slowEma} EMA stack`,
    prompt: `Build a momentum continuation strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when all three conditions align: (1) RSI(14) is between 50 and 65 — strong momentum, not yet overbought, (2) the ${p.fastEma}-period EMA is above the ${p.slowEma}-period EMA, and (3) price is above both EMAs — full bullish stack. Exit when RSI drops below 45 or price closes below the ${p.fastEma} EMA. Place a stop-loss ${p.stop} below the ${p.fastEma} EMA at entry. This captures the middle phase of a trending move before exhaustion.`,
  }),

  // 4. Bollinger Band Bounce
  (p) => ({
    title: 'Bollinger Band Bounce',
    tagline: `Price at lower BB (${p.bbPeriod}-period) + RSI < ${p.rsiOS} confirmation`,
    prompt: `Build a Bollinger Band mean reversion strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when price touches or closes below the lower Bollinger Band (${p.bbPeriod}-period, 2.0 std dev) and RSI(14) is below ${p.rsiOS}, confirming the oversold condition. Exit when price reaches the middle Bollinger Band (${p.bbPeriod}-period SMA). Place a stop-loss ${p.stop} below entry. This double-confirmation — price at statistical extreme plus RSI oversold — reduces false signals and targets the mean-reversion snap back to the midline.`,
  }),

  // 5. Range Breakout
  (p) => ({
    title: 'Range Breakout',
    tagline: `${p.lookback}-bar high breakout with volume confirmation`,
    prompt: `Build a range breakout strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when price closes above the highest close of the past ${p.lookback} bars, with the current bar's volume exceeding the 20-bar average volume. This dual confirmation — price breakout plus volume participation — filters false breaks. Exit after ${p.holdBars} bars or if price drops back below the midpoint of the ${p.lookback}-bar range. Place a stop-loss ${p.stop} below entry. Targeting ${p.target} as the profit objective.`,
  }),

  // 6. MACD Crossover
  (p) => ({
    title: 'MACD Crossover',
    tagline: `MACD(12,26,9) bullish cross above ${p.trendP}-period EMA`,
    prompt: `Build a MACD crossover strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when the MACD line (12,26,9) crosses above the signal line while price is above the ${p.trendP}-period EMA — requiring trend alignment before acting on the momentum signal. Exit when the MACD line crosses back below the signal line. Place a stop-loss ${p.stop} below the entry bar's low. Targeting ${p.target} on the way up. The trend filter prevents entering MACD crosses in downtrending conditions where they are statistically unreliable.`,
  }),

  // 7. EMA Pullback Entry
  (p) => ({
    title: 'EMA Pullback Entry',
    tagline: `Dip to ${p.fastEma} EMA within uptrend, target ${p.target}`,
    prompt: `Build a pullback-to-EMA strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Define an uptrend as the ${p.fastEma}-period EMA above the ${p.slowEma}-period EMA. Within this trend, enter long when price pulls back to within 0.5% of the ${p.fastEma} EMA — buying the dip in a rising market. Exit when price gains ${p.target} from entry or when the ${p.fastEma} EMA crosses below the ${p.slowEma} EMA (trend breaks). Place a stop-loss ${p.stop} below the pullback low. This high-probability setup enters at value within an established trend.`,
  }),

  // 8. Stochastic Reversal
  (p) => ({
    title: 'Stochastic Reversal',
    tagline: `StochRSI %K crosses %D from below 20, trend-filtered`,
    prompt: `Build a Stochastic reversal strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when Stochastic %K crosses above %D while both are below 20 (oversold zone), and price is above the ${p.trendP}-period EMA — requiring trend alignment to avoid catching falling knives. Exit when Stochastic %K rises above 80 (overbought). Place a stop-loss ${p.stop} below the most recent swing low. Targeting ${p.target} from entry. The combination of momentum oscillator reversal signal plus trend filter produces high-accuracy entries at local price lows within uptrends.`,
  }),

  // 9. Volume Surge Breakout
  (p) => ({
    title: 'Volume Surge Breakout',
    tagline: `${p.lookback}-bar high + volume ≥ ${p.volMult} avg, RSI > 50`,
    prompt: `Build a volume surge breakout strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when three conditions align simultaneously: (1) price closes at the ${p.lookback}-bar high, (2) current bar volume is at least ${p.volMult} the 20-bar average volume — confirming genuine participation, and (3) RSI(14) is above 50 — momentum confirmation. Hold for up to ${p.holdBars} bars or exit early if the stop triggers. Place a stop-loss ${p.stop} below entry. Targeting ${p.target}. The triple-confirmation design filters fake breakouts caused by low-liquidity price spikes.`,
  }),

  // 10. ATR Volatility Trend
  (p) => ({
    title: 'ATR Volatility Trend',
    tagline: `Expanding ATR + ${p.slowEma} EMA trend, 2×ATR stop`,
    prompt: `Build an ATR volatility trend strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when: (1) price is above the ${p.slowEma}-period EMA — trend filter, (2) the current 14-period ATR is greater than its 10-bar average ATR (expanding volatility — trend is accelerating), and (3) RSI(14) is above 50 — momentum confirmation. Exit when price closes below the ${p.fastEma}-period EMA or RSI drops below 45. Place an initial stop-loss at 2×ATR below entry, capped at ${p.stop} maximum. Expanding volatility alongside trend alignment is a strong signal that a directional move is underway rather than random noise.`,
  }),
]

// ── Public API ─────────────────────────────────────────────────────────────────

export interface StrategyCard {
  id: string
  title: string
  tagline: string
  prompt: string
}

export function getStrategyPrompts(symbol: string, timeframe: string): StrategyCard[] {
  const p = buildParams(symbol, timeframe)
  return strategies.map((gen, i) => {
    const { title, tagline, prompt } = gen(p)
    return { id: `strategy-${i}`, title, tagline, prompt }
  })
}
