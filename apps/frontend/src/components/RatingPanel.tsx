import { useState } from 'react'
import { StrategyRating } from '../hooks/useBacktest'
import { CategoryHeader } from './rating/CategoryHeader'
import { StarRating } from './rating/StarRating'
import { ProfitabilityTab } from './rating/ProfitabilityTab'
import { RiskResistanceTab } from './rating/RiskResistanceTab'
import { RiskRewardTab } from './rating/RiskRewardTab'
import { WinRateEvTab } from './rating/WinRateEvTab'
import { LiquidityTab } from './rating/LiquidityTab'

interface RatingPanelProps {
  rating: StrategyRating
}

export function RatingPanel({ rating }: RatingPanelProps) {
  const [activeCategory, setActiveCategory] = useState('profitability')

  const categories = [
    rating.profitability,
    rating.risk_resistance,
    rating.risk_reward,
    rating.win_rate_ev,
    rating.liquidity,
  ]

  // Overall stars (average)
  const avgStars = Math.round(
    categories.reduce((sum, c) => sum + c.stars, 0) / categories.length
  )

  return (
    <div className="space-y-4">
      {/* Overall Rating */}
      <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-700">Strategy Rating</h3>
          <div className="flex items-center gap-2">
            <StarRating stars={avgStars} size="lg" />
            <span className="text-xs text-slate-500">{avgStars}/5</span>
          </div>
        </div>

        {/* Category tabs */}
        <CategoryHeader
          categories={categories}
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
        />
      </div>

      {/* Active tab content */}
      {activeCategory === 'profitability' && <ProfitabilityTab rating={rating} />}
      {activeCategory === 'risk_resistance' && <RiskResistanceTab rating={rating} />}
      {activeCategory === 'risk_reward' && <RiskRewardTab rating={rating} />}
      {activeCategory === 'win_rate_ev' && <WinRateEvTab rating={rating} />}
      {activeCategory === 'liquidity' && <LiquidityTab rating={rating} />}
    </div>
  )
}
