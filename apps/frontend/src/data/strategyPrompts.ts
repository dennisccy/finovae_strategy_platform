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

  // 11. VWAP Reversion
  (p) => ({
    title: 'VWAP Reversion',
    tagline: `Price dips below VWAP + RSI < ${p.rsiOS}, snap back to VWAP`,
    prompt: `Build a VWAP mean reversion strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Only trade in the direction of the ${p.trendP}-period EMA trend. Enter long when price closes below VWAP (Volume Weighted Average Price) and RSI(14) is below ${p.rsiOS} — a statistically oversold dip below the institutional fair value level. Exit when price returns to VWAP or gains ${p.target} from entry. Place a stop-loss ${p.stop} below entry. VWAP acts as the market's consensus fair value — oversold dips below it in an uptrend create high-probability reversion opportunities back to equilibrium.`,
  }),

  // 12. Ichimoku Cloud Breakout
  (p) => ({
    title: 'Ichimoku Breakout',
    tagline: `Price breaks above Ichimoku Cloud with Tenkan/Kijun cross`,
    prompt: `Build an Ichimoku Cloud breakout strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when all three conditions hold: (1) price closes above both Senkou Span A and Senkou Span B (price is above the cloud), (2) Tenkan-sen (9-period) crosses above Kijun-sen (26-period) — the Ichimoku bullish cross, and (3) Chikou Span is above the price from 26 bars ago. Exit when price closes back inside or below the cloud. Place a stop-loss ${p.stop} below the top of the cloud at entry. This triple confirmation from Ichimoku ensures price, momentum, and lagging confirmation all align before entering.`,
  }),

  // 13. Supertrend Follow
  (p) => ({
    title: 'Supertrend Follow',
    tagline: `Price above Supertrend (ATR×3 trailing) with ${p.trendP} EMA filter`,
    prompt: `Build a Supertrend trend-following strategy for ${p.assetName} on the ${p.tfLabel} timeframe. The Supertrend indicator uses ATR(14) multiplied by 3.0 as a dynamic trailing stop line. Enter long when price closes above the Supertrend line AND price is above the ${p.trendP}-period EMA — double trend confirmation. Exit when price closes below the Supertrend line (the trailing stop triggers). Place a hard stop-loss ${p.stop} below entry as a maximum loss guard. Supertrend adapts to volatility automatically — in calm markets the line is tight, in volatile markets it widens, making it robust across conditions.`,
  }),

  // 14. Donchian Channel Breakout
  (p) => ({
    title: 'Donchian Breakout',
    tagline: `${p.lookback}-bar channel breakout with ${p.holdBars}-bar hold`,
    prompt: `Build a Donchian Channel breakout strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when price closes above the upper Donchian Channel (the highest close of the past ${p.lookback} bars) — a new ${p.lookback}-bar high. This breakout signals that bears have been unable to stop price from making a new high, often the start of a directional move. Hold for ${p.holdBars} bars unless stopped out. Exit early if price falls below the midpoint of the Donchian Channel (average of upper and lower bands). Place a stop-loss ${p.stop} below entry. Targeting ${p.target}.`,
  }),

  // 15. OBV Divergence
  (p) => ({
    title: 'OBV Divergence',
    tagline: `OBV uptrend + price ${p.lookback}-bar consolidation, volume-led entry`,
    prompt: `Build an OBV divergence strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when: (1) On-Balance Volume (OBV) is above its ${p.lookback}-bar moving average — showing consistent accumulation, and (2) price is trading within 1% of its ${p.lookback}-bar low — price consolidating while volume is bullish (bullish divergence). Exit when OBV drops back below its ${p.lookback}-bar moving average or price gains ${p.target}. Place a stop-loss ${p.stop} below entry. OBV leads price — when volume flows in (OBV rising) while price stagnates, a breakout to the upside often follows as the market catches up to the volume signal.`,
  }),

  // 16. Williams %R Oversold
  (p) => ({
    title: 'Williams %R Reversal',
    tagline: `Williams %R crosses above -80 from oversold in uptrend`,
    prompt: `Build a Williams %R reversal strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when two conditions align: (1) Williams %R(14) crosses from below -80 to above -80 — exiting the oversold zone and signalling a momentum reversal, and (2) price is above the ${p.trendP}-period EMA — confirming the larger uptrend. Exit when Williams %R rises above -20 (overbought). Place a stop-loss ${p.stop} below the entry bar's low. Targeting ${p.target}. Williams %R is more sensitive than RSI at detecting short-term reversals from extreme oversold levels within established trends.`,
  }),

  // 17. Parabolic SAR Reversal
  (p) => ({
    title: 'Parabolic SAR Flip',
    tagline: `SAR flips below price (start=0.02, max=0.2) + EMA uptrend`,
    prompt: `Build a Parabolic SAR reversal strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when the Parabolic SAR (step=0.02, maximum=0.2) flips from above price to below price — signalling a bullish reversal. Require that price is also above the ${p.trendP}-period EMA to ensure the flip occurs within an uptrend context. Exit when the SAR flips back above price. Use the SAR value itself as the trailing stop-loss (not a fixed percentage). Place a maximum hard stop at ${p.stop} below entry. The SAR accelerates as price extends, tightening the trail to capture more profit in fast moves.`,
  }),

  // 18. Keltner Channel Squeeze
  (p) => ({
    title: 'Keltner Squeeze',
    tagline: `BB inside Keltner squeeze → breakout entry with momentum`,
    prompt: `Build a Keltner Channel squeeze breakout strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Detect a squeeze when the Bollinger Bands (${p.bbPeriod}-period, 2.0 std) are entirely inside the Keltner Channel (${p.bbPeriod}-period EMA ± 1.5×ATR). Enter long when the squeeze resolves upward: price closes above the upper Keltner Channel with RSI(14) above 50 confirming momentum. Exit after ${p.holdBars} bars or when price closes back inside the Keltner Channel. Place a stop-loss ${p.stop} below entry. A squeeze represents compressed volatility — the breakout direction after the squeeze often marks the start of a powerful directional move.`,
  }),

  // 19. ADX Trend Strength
  (p) => ({
    title: 'ADX Trend Strength',
    tagline: `ADX > 25 with +DI above -DI, ${p.fastEma} EMA confirmation`,
    prompt: `Build an ADX trend strength strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Enter long when three conditions align: (1) ADX(14) is above 25 — confirming a strong trend is in place, (2) +DI is above -DI — the trend is bullish, and (3) price is above the ${p.fastEma}-period EMA. Exit when ADX drops below 20 (trend weakening) or -DI crosses above +DI (trend reversal). Place a stop-loss ${p.stop} below entry. Targeting ${p.target}. ADX filters out choppy, trendless markets where trend-following systems fail — only entering when momentum is measurably strong reduces false signals significantly.`,
  }),

  // 20. CCI Mean Reversion
  (p) => ({
    title: 'CCI Mean Reversion',
    tagline: `CCI dips below -100 in uptrend, exit at zero crossing`,
    prompt: `Build a CCI mean reversion strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Only trade when price is above the ${p.trendP}-period EMA (uptrend filter). Enter long when the Commodity Channel Index CCI(20) drops below -100 — extreme oversold territory — and then crosses back above -100 on the following bar (reversal confirmed). Exit when CCI crosses above 0 (returned to equilibrium). Place a stop-loss ${p.stop} below the entry bar's low. Targeting ${p.target}. CCI measures how far price has deviated from its statistical mean — readings below -100 indicate a severe short-term dip within a larger uptrend, prime conditions for a snap-back.`,
  }),
]

// ── 10 SHORT-AWARE bidirectional strategy generators ──────────────────────────
// All strategies return signal 1 (long) and -1 (short) symmetrically.

const shortStrategies: StrategyGenerator[] = [
  // 1. EMA Crossover — Bidirectional
  (p) => ({
    title: 'EMA Crossover L/S',
    tagline: `Long on ${p.fastEma}/${p.slowEma} golden cross, short on death cross`,
    prompt: `Build a bidirectional EMA crossover strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use the ${p.fastEma}-period EMA and ${p.slowEma}-period EMA. Return signal 1 (go long) when the ${p.fastEma} EMA crosses above the ${p.slowEma} EMA (golden cross). Return signal -1 (go short) when the ${p.fastEma} EMA crosses below the ${p.slowEma} EMA (death cross). Return 0 while no crossover occurs. Place a stop-loss ${p.stop} from entry in both directions. Both long AND short trades must fire — this is a fully symmetric, always-in-market trend strategy.`,
  }),

  // 2. RSI Midline — Bidirectional
  (p) => ({
    title: 'RSI Midline L/S',
    tagline: `Long RSI > 55, short RSI < 45, neutral band around 50`,
    prompt: `Build a bidirectional RSI momentum strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use RSI(14). Return signal 1 (go long) when RSI rises above 55 — bullish momentum confirmed. Return signal -1 (go short) when RSI drops below 45 — bearish momentum confirmed. Return 0 when RSI is between 45 and 55 (neutral zone — hold current position). Place a stop-loss ${p.stop} from entry. This symmetric RSI midline strategy captures directional momentum in both directions with a neutral buffer to avoid whipsaws.`,
  }),

  // 3. MACD Signal Crossover — Bidirectional
  (p) => ({
    title: 'MACD Crossover L/S',
    tagline: `Long on MACD bullish cross, short on bearish cross`,
    prompt: `Build a bidirectional MACD crossover strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use MACD(12,26,9). Return signal 1 (go long) when the MACD line crosses above the signal line — bullish momentum shift. Return signal -1 (go short) when the MACD line crosses below the signal line — bearish momentum shift. Return 0 while no crossover occurred. Place a stop-loss ${p.stop} from entry for both directions. This fully symmetric MACD strategy trades every momentum reversal in both directions, producing long and short trades in roughly equal measure.`,
  }),

  // 4. Bollinger Band Mean Reversion — Bidirectional
  (p) => ({
    title: 'BB Fade L/S',
    tagline: `Long at lower band, short at upper band, exit at midline`,
    prompt: `Build a bidirectional Bollinger Band mean reversion strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use Bollinger Bands (${p.bbPeriod}-period, 2.0 std dev). Return signal 1 (go long) when price touches or closes below the lower band — statistically oversold. Return signal -1 (go short) when price touches or closes above the upper band — statistically overbought. Return signal 2 (flatten) when price reaches the middle band (${p.bbPeriod}-period SMA) to take profit in either direction. Place a stop-loss ${p.stop} from entry. This symmetric fade strategy exploits mean reversion from extremes in both directions.`,
  }),

  // 5. Dual EMA Trend Direction — Bidirectional
  (p) => ({
    title: 'EMA Trend Direction L/S',
    tagline: `Long above ${p.slowEma} EMA + RSI > 50, short below + RSI < 50`,
    prompt: `Build a bidirectional EMA trend-direction strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Return signal 1 (go long) when price is above the ${p.slowEma}-period EMA AND RSI(14) is above 50 — both trend and momentum are bullish. Return signal -1 (go short) when price is below the ${p.slowEma}-period EMA AND RSI(14) is below 50 — both trend and momentum are bearish. Return 0 otherwise. Place a stop-loss ${p.stop} from entry in both directions. The dual confirmation (price location + RSI side) reduces false signals and ensures both long and short entries are high-quality.`,
  }),

  // 6. MACD Histogram Sign — Bidirectional
  (p) => ({
    title: 'MACD Histogram L/S',
    tagline: `Long when histogram turns positive, short when negative`,
    prompt: `Build a bidirectional MACD histogram strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use MACD(12,26,9). Return signal 1 (go long) when the MACD histogram crosses from negative to positive — momentum turning bullish. Return signal -1 (go short) when the MACD histogram crosses from positive to negative — momentum turning bearish. Return 0 while no sign change. Place a stop-loss ${p.stop} from entry. This histogram sign-change strategy is highly responsive and produces both long and short trades symmetrically at every momentum direction shift.`,
  }),

  // 7. Stochastic Reversal — Bidirectional
  (p) => ({
    title: 'Stochastic Reversal L/S',
    tagline: `Long from oversold (<20), short from overbought (>80)`,
    prompt: `Build a bidirectional Stochastic reversal strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use Stochastic(14,3). Return signal 1 (go long) when %K crosses above %D while both are below 20 — reversal from oversold. Return signal -1 (go short) when %K crosses below %D while both are above 80 — reversal from overbought. Return 0 otherwise. Place a stop-loss ${p.stop} from entry in both directions. Both long and short trades must be generated — this is a symmetric oscillator reversal strategy that exploits exhaustion at extremes in both directions.`,
  }),

  // 8. EMA Pullback — Bidirectional
  (p) => ({
    title: 'EMA Pullback L/S',
    tagline: `Long: dip to ${p.fastEma} EMA in uptrend · Short: rally to ${p.fastEma} EMA in downtrend`,
    prompt: `Build a bidirectional EMA pullback strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Uptrend: ${p.fastEma} EMA above ${p.slowEma} EMA. Downtrend: ${p.fastEma} EMA below ${p.slowEma} EMA. Return signal 1 (go long) when in an uptrend and price pulls back to within 0.5% of the ${p.fastEma} EMA from above. Return signal -1 (go short) when in a downtrend and price rallies back to within 0.5% of the ${p.fastEma} EMA from below. Place a stop-loss ${p.stop} from entry in both directions, target ${p.target}. Both long and short pullback trades must fire — each mirrors the other's logic exactly.`,
  }),

  // 9. Range Breakout — Bidirectional
  (p) => ({
    title: 'Breakout L/S',
    tagline: `Long on ${p.lookback}-bar high break, short on ${p.lookback}-bar low break`,
    prompt: `Build a bidirectional range breakout strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Return signal 1 (go long) when price closes above the highest close of the past ${p.lookback} bars — bullish breakout. Return signal -1 (go short) when price closes below the lowest close of the past ${p.lookback} bars — bearish breakout. Return 0 otherwise. Place a stop-loss ${p.stop} from entry in both directions. Targeting ${p.target} from entry. Both long and short breakout trades must be generated — the breakout logic is fully symmetric and must not favour one direction.`,
  }),

  // 10. ATR Volatility Trend — Bidirectional
  (p) => ({
    title: 'ATR Trend L/S',
    tagline: `Expanding ATR + ${p.fastEma}/${p.slowEma} direction, 2×ATR stop both ways`,
    prompt: `Build a bidirectional ATR volatility trend strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Measure expanding volatility as: 14-period ATR greater than its 10-bar average (trend accelerating). Return signal 1 (go long) when: ${p.fastEma} EMA is above ${p.slowEma} EMA AND ATR is expanding AND RSI(14) is above 50. Return signal -1 (go short) when: ${p.fastEma} EMA is below ${p.slowEma} EMA AND ATR is expanding AND RSI(14) is below 50. Return 0 otherwise. Place an initial stop at 2×ATR from entry, capped at ${p.stop}, for both directions. Both long and short trades must fire — the conditions are symmetric.`,
  }),

  // 11. VWAP Reversion — Bidirectional
  (p) => ({
    title: 'VWAP Reversion L/S',
    tagline: `Long below VWAP oversold, short above VWAP overbought`,
    prompt: `Build a bidirectional VWAP mean reversion strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Return signal 1 (go long) when price closes below VWAP AND RSI(14) is below ${p.rsiOS} — oversold dip below fair value. Return signal -1 (go short) when price closes above VWAP AND RSI(14) is above ${p.rsiOB} — overbought rally above fair value. Return 0 otherwise. Exit by returning signal 2 (flatten) when price reaches VWAP from either side. Place a stop-loss ${p.stop} from entry in both directions. Both long and short trades must fire — the strategy is symmetric around VWAP as the mean.`,
  }),

  // 12. Ichimoku Cloud — Bidirectional
  (p) => ({
    title: 'Ichimoku Cloud L/S',
    tagline: `Long above cloud with Tenkan/Kijun cross, short below cloud`,
    prompt: `Build a bidirectional Ichimoku Cloud strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Return signal 1 (go long) when: price is above both Senkou Span A and Span B (above cloud) AND Tenkan-sen crosses above Kijun-sen. Return signal -1 (go short) when: price is below both Senkou Span A and Span B (below cloud) AND Tenkan-sen crosses below Kijun-sen. Return 0 when price is inside the cloud (neutral zone). Exit when price re-enters the cloud. Place a stop-loss ${p.stop} from entry in both directions. Both long and short trades must be generated — the Ichimoku signals are symmetric for bearish and bullish breakouts.`,
  }),

  // 13. Supertrend — Bidirectional
  (p) => ({
    title: 'Supertrend L/S',
    tagline: `Long above Supertrend (ATR×3), short below — always in market`,
    prompt: `Build a bidirectional Supertrend strategy for ${p.assetName} on the ${p.tfLabel} timeframe. The Supertrend indicator uses ATR(14) multiplied by 3.0. Return signal 1 (go long) when price closes above the Supertrend line — bullish side. Return signal -1 (go short) when price closes below the Supertrend line — bearish side. This is an always-in-market strategy: when one position closes, the opposite opens immediately. Use the Supertrend value as the trailing stop for both directions. Place a maximum hard stop ${p.stop} from entry as a guard. Both long and short trades must fire — the strategy reverses direction on every Supertrend flip.`,
  }),

  // 14. Donchian Channel — Bidirectional
  (p) => ({
    title: 'Donchian Breakout L/S',
    tagline: `Long on ${p.lookback}-bar high break, short on ${p.lookback}-bar low break`,
    prompt: `Build a bidirectional Donchian Channel breakout strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Return signal 1 (go long) when price closes above the upper Donchian Channel (highest close of past ${p.lookback} bars) — bullish breakout to new highs. Return signal -1 (go short) when price closes below the lower Donchian Channel (lowest close of past ${p.lookback} bars) — bearish breakout to new lows. Return 0 otherwise. Place a stop-loss ${p.stop} from entry in both directions. Targeting ${p.target}. Hold for ${p.holdBars} bars or until the midpoint of the channel is reached. Both long and short breakout trades must fire symmetrically.`,
  }),

  // 15. OBV Divergence — Bidirectional
  (p) => ({
    title: 'OBV Divergence L/S',
    tagline: `Long: OBV up + price dip. Short: OBV down + price rally`,
    prompt: `Build a bidirectional OBV divergence strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Return signal 1 (go long) when OBV is above its ${p.lookback}-bar moving average (accumulation) AND price is within 1% of its ${p.lookback}-bar low — bullish divergence. Return signal -1 (go short) when OBV is below its ${p.lookback}-bar moving average (distribution) AND price is within 1% of its ${p.lookback}-bar high — bearish divergence. Return 0 otherwise. Exit when OBV crosses its moving average in the opposite direction, or price gains ${p.target}. Place a stop-loss ${p.stop} from entry. Both long and short OBV divergence trades must fire symmetrically.`,
  }),

  // 16. Williams %R — Bidirectional
  (p) => ({
    title: 'Williams %R L/S',
    tagline: `Long above -80 cross, short below -20 cross`,
    prompt: `Build a bidirectional Williams %R strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use Williams %R(14). Return signal 1 (go long) when Williams %R crosses from below -80 to above -80 — exiting oversold. Return signal -1 (go short) when Williams %R crosses from above -20 to below -20 — exiting overbought. Return 0 otherwise. Exit the long when %R rises above -20; exit the short when %R falls below -80. Place a stop-loss ${p.stop} from entry in both directions. Targeting ${p.target}. Both long and short reversal signals must fire — the strategy is symmetric around the Williams %R extremes.`,
  }),

  // 17. Parabolic SAR — Bidirectional
  (p) => ({
    title: 'Parabolic SAR L/S',
    tagline: `Long on SAR flip below price, short on SAR flip above price`,
    prompt: `Build a bidirectional Parabolic SAR strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use Parabolic SAR (step=0.02, maximum=0.2). Return signal 1 (go long) when SAR flips from above price to below price — bullish reversal signal. Return signal -1 (go short) when SAR flips from below price to above price — bearish reversal signal. This is a reversal strategy — when one side closes, the other opens. Use the SAR value as the trailing stop for both directions, with a maximum hard stop of ${p.stop} from entry. Both long and short trades must fire on every SAR direction change — the strategy is fully symmetric.`,
  }),

  // 18. Keltner Channel — Bidirectional
  (p) => ({
    title: 'Keltner Channel L/S',
    tagline: `Long at lower Keltner touch + RSI < ${p.rsiOS}, short at upper touch`,
    prompt: `Build a bidirectional Keltner Channel mean reversion strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use Keltner Channels (${p.bbPeriod}-period EMA ± 2.0×ATR). Return signal 1 (go long) when price touches or closes below the lower Keltner Channel AND RSI(14) is below ${p.rsiOS} — oversold at lower extreme. Return signal -1 (go short) when price touches or closes above the upper Keltner Channel AND RSI(14) is above ${p.rsiOB} — overbought at upper extreme. Exit when price returns to the middle band (${p.bbPeriod}-period EMA). Place a stop-loss ${p.stop} from entry. Both long and short trades must fire symmetrically.`,
  }),

  // 19. ADX Trend Strength — Bidirectional
  (p) => ({
    title: 'ADX Trend L/S',
    tagline: `ADX > 25: long on +DI > -DI, short on -DI > +DI`,
    prompt: `Build a bidirectional ADX trend strength strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use ADX(14) with +DI and -DI. Return signal 1 (go long) when ADX is above 25 (strong trend) AND +DI is above -DI (bullish) AND price is above the ${p.fastEma}-period EMA. Return signal -1 (go short) when ADX is above 25 AND -DI is above +DI (bearish) AND price is below the ${p.fastEma}-period EMA. Return 0 when ADX is below 20 (no trend — stay flat). Exit when ADX drops below 20 or the DI lines cross. Place a stop-loss ${p.stop} from entry in both directions. Both long and short trades must fire when the trend is strong enough — the conditions mirror each other exactly.`,
  }),

  // 20. CCI Mean Reversion — Bidirectional
  (p) => ({
    title: 'CCI Reversal L/S',
    tagline: `Long: CCI crosses above -100. Short: CCI crosses below +100`,
    prompt: `Build a bidirectional CCI mean reversion strategy for ${p.assetName} on the ${p.tfLabel} timeframe. Use CCI(20). Return signal 1 (go long) when CCI crosses from below -100 to above -100 — exiting oversold territory, reversal confirmed. Return signal -1 (go short) when CCI crosses from above +100 to below +100 — exiting overbought territory, reversal confirmed. Return 0 otherwise. Exit long when CCI reaches 0; exit short when CCI reaches 0. Place a stop-loss ${p.stop} from entry in both directions. Targeting ${p.target}. Both long and short reversal trades must fire — the CCI ±100 levels act as symmetric extreme zones in both directions.`,
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

export function getShortStrategyPrompts(symbol: string, timeframe: string): StrategyCard[] {
  const p = buildParams(symbol, timeframe)
  return shortStrategies.map((gen, i) => {
    const { title, tagline, prompt } = gen(p)
    return { id: `short-strategy-${i}`, title, tagline, prompt }
  })
}
