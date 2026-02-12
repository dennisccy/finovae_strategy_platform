import { StrategySpec } from '../hooks/useBacktest'
import { Zap, LogOut, BarChart2 } from 'lucide-react'

interface StrategyDisplayProps {
  spec: StrategySpec
}

export function StrategyDisplay({ spec }: StrategyDisplayProps) {
  const formatCondition = (condition: {
    left_operand: string
    operator: string
    right_operand: string | number
  }) => {
    const operatorMap: Record<string, string> = {
      '>': '>',
      '<': '<',
      '>=': '>=',
      '<=': '<=',
      '==': '=',
      cross_above: 'crosses above',
      cross_below: 'crosses below',
    }

    const op = operatorMap[condition.operator] || condition.operator
    const right =
      typeof condition.right_operand === 'number'
        ? condition.right_operand
        : condition.right_operand

    return `${condition.left_operand} ${op} ${right}`
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
      <div className="flex items-start justify-between mb-3 lg:mb-4">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-slate-700 truncate">{spec.name}</h3>
          <p className="text-xs lg:text-sm text-slate-500 mt-0.5 lg:mt-1 line-clamp-2">{spec.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 lg:gap-4">
        {/* Entry Conditions */}
        <div className="bg-emerald-50 rounded-lg p-2.5 lg:p-3">
          <div className="flex items-center gap-1.5 lg:gap-2 mb-1.5 lg:mb-2">
            <Zap className="w-3.5 h-3.5 lg:w-4 lg:h-4 text-emerald-600 flex-shrink-0" />
            <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wide truncate">
              Entry (ALL)
            </span>
          </div>
          <ul className="space-y-0.5 lg:space-y-1">
            {spec.entry_conditions.map((cond, i) => (
              <li key={i} className="text-xs lg:text-sm text-emerald-800 break-words">
                {formatCondition(cond)}
              </li>
            ))}
          </ul>
        </div>

        {/* Exit Conditions */}
        <div className="bg-red-50 rounded-lg p-2.5 lg:p-3">
          <div className="flex items-center gap-1.5 lg:gap-2 mb-1.5 lg:mb-2">
            <LogOut className="w-3.5 h-3.5 lg:w-4 lg:h-4 text-red-600 flex-shrink-0" />
            <span className="text-xs font-semibold text-red-700 uppercase tracking-wide truncate">
              Exit (ANY)
            </span>
          </div>
          <ul className="space-y-0.5 lg:space-y-1">
            {spec.exit_conditions.map((cond, i) => (
              <li key={i} className="text-xs lg:text-sm text-red-800 break-words">
                {formatCondition(cond)}
              </li>
            ))}
          </ul>
        </div>

        {/* Indicators */}
        <div className="bg-blue-50 rounded-lg p-2.5 lg:p-3">
          <div className="flex items-center gap-1.5 lg:gap-2 mb-1.5 lg:mb-2">
            <BarChart2 className="w-3.5 h-3.5 lg:w-4 lg:h-4 text-blue-600 flex-shrink-0" />
            <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide truncate">
              Indicators
            </span>
          </div>
          <ul className="space-y-0.5 lg:space-y-1">
            {spec.indicators.map((ind, i) => (
              <li key={i} className="text-xs lg:text-sm text-blue-800 break-words">
                {ind.name}
                {Object.keys(ind.params).length > 0 && (
                  <span className="text-blue-600">
                    ({Object.entries(ind.params)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(', ')})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
