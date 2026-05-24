import { Trophy, Award } from 'lucide-react'
import type { IterationNode } from '../hooks/useBacktest'
import type { AutoRunStatus, LeaderboardEntry } from '../lib/sessionApi'

interface AutoSessionLeaderboardProps {
  /** Canonical backend autoRun block (single source of truth). The leaderboard
   *  rides `autoRun.leaderboard`; the marked best is `autoRun.bestIterationId`. */
  autoRun: AutoRunStatus | null
  /** The session's iteration nodes — the leaderboard JOINS each entry to its node
   *  by `iterationId` for display metrics (return, WFE, trades, drawdown). */
  iterations: IterationNode[]
}

// WFE color thresholds — reuse the established semantics from IterationCard
// (emerald ≥ 0.5 / amber ≥ 0.3 / red < 0.3). Display-only; never recomputed here.
function wfeColorClass(wfe: number): string {
  if (wfe >= 0.5) return 'bg-emerald-100 text-emerald-700'
  if (wfe >= 0.3) return 'bg-amber-100 text-amber-700'
  return 'bg-red-100 text-red-700'
}

function formatReturn(value: number): string {
  const pct = (value * 100).toFixed(2)
  return value >= 0 ? `+${pct}%` : `${pct}%`
}

// The robust score is read VERBATIM from the entry (the one RobustScorer output);
// this only formats it. `null` = ineligible / no-trades (JSON-safe -inf).
function formatScore(score: number | null): string {
  if (score === null) return '—'
  return `${score >= 0 ? '+' : ''}${score.toFixed(4)}`
}

const STAGE_BADGE: Record<LeaderboardEntry['stage'], { label: string; cls: string }> = {
  screen: { label: 'SCREEN', cls: 'bg-slate-100 text-slate-600' },
  promote: { label: 'PROMOTE', cls: 'bg-blue-100 text-blue-700' },
}

/**
 * Overfit-gating leaderboard (J-16) for an open-universe automated run. Renders
 * the candidates the optimizer evaluated, ranked by the canonical robust score,
 * with the marked best highlighted — and a higher-return-but-rejected candidate
 * showing WHY it isn't best (its gating reason). It reads canonical served values
 * only: `robustScore`/`eligible`/`gatingReason` verbatim from `autoRun.leaderboard`,
 * and the display metrics joined from the matching `iterationHistory` node by
 * `iterationId`. It never recomputes the score and never defines a second "best".
 *
 * Renders nothing for a manual session or a run with no evaluated candidates yet.
 */
export function AutoSessionLeaderboard({ autoRun, iterations }: AutoSessionLeaderboardProps) {
  const entries = autoRun?.leaderboard ?? []
  if (entries.length === 0) return null

  const bestId = autoRun?.bestIterationId ?? null
  const nodeById = new Map(iterations.map(n => [n.id, n]))

  // Rank by robustScore descending; ineligible/no-trades rows (null score) last.
  const ranked = [...entries].sort((a, b) => {
    if (a.robustScore === null && b.robustScore === null) return 0
    if (a.robustScore === null) return 1
    if (b.robustScore === null) return -1
    return b.robustScore - a.robustScore
  })

  return (
    <div className="mb-3 rounded-lg border border-slate-200 bg-white overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-100 bg-slate-50">
        <Trophy className="w-3.5 h-3.5 text-amber-500" />
        <h3 className="text-xs font-semibold text-slate-700">Candidate leaderboard</h3>
        <span className="text-xs text-slate-400">· ranked by robust score</span>
        <span className="ml-auto text-xs text-slate-400">
          {ranked.length} candidate{ranked.length === 1 ? '' : 's'}
        </span>
      </div>

      <ul className="divide-y divide-slate-100">
        {ranked.map((entry, idx) => {
          const node = nodeById.get(entry.iterationId)
          const isBest = bestId != null && entry.iterationId === bestId
          const stage = STAGE_BADGE[entry.stage]
          const params = node?.params
          const family = params ? `${params.symbol} ${params.timeframe}` : '—'
          const wfe = node?.walkForwardStatus === 'complete' ? node.walkForwardResult?.wfe : undefined
          const totalReturn = node?.totalReturn
          const numTrades = node?.numTrades
          const maxDrawdown = node?.maxDrawdown

          return (
            <li
              key={entry.iterationId}
              className={`px-3 py-2 ${isBest ? 'bg-violet-50' : 'bg-white'}`}
            >
              {/* Header line: rank · family · stage · BEST */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono text-slate-400 w-5 shrink-0">#{idx + 1}</span>
                <span className="text-xs font-semibold text-slate-700">{family}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${stage.cls}`}>
                  {stage.label}
                </span>
                {isBest && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 text-[10px] font-semibold">
                    <Award className="w-3 h-3" />
                    BEST
                  </span>
                )}
                <span className="ml-auto text-xs font-semibold text-slate-700" title="Canonical robust score">
                  {formatScore(entry.robustScore)}
                </span>
              </div>

              {/* Metrics line: return · WFE · trades · drawdown (joined from the node) */}
              <div className="flex items-center gap-2 mt-1 text-xs flex-wrap">
                <span className={`font-medium ${(totalReturn ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                  {totalReturn != null ? formatReturn(totalReturn) : '—'}
                </span>
                <span className="text-slate-300">·</span>
                {wfe != null ? (
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${wfeColorClass(wfe)}`}>
                    WFE {wfe.toFixed(2)}
                  </span>
                ) : (
                  <span className="text-slate-400" title="No walk-forward (screened only)">WFE —</span>
                )}
                <span className="text-slate-300">·</span>
                <span className="text-slate-500">{numTrades ?? 0} trades</span>
                <span className="text-slate-300">·</span>
                <span className="text-red-500">DD {((maxDrawdown ?? 0) * 100).toFixed(1)}%</span>
              </div>

              {/* Gating reason: why this candidate is / isn't the marked best.
                  Read verbatim from the backend — the UI never re-derives it. */}
              {!isBest && entry.gatingReason && (
                <p
                  className={`mt-1 text-[11px] ${entry.eligible ? 'text-slate-400' : 'text-red-500'}`}
                  title="Why this candidate is not the marked best"
                >
                  {entry.gatingReason}
                </p>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
