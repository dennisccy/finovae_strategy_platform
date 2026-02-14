import { TrendingUp, Shield, Scale, Target, Droplets } from 'lucide-react'
import { CategoryRating } from '../../hooks/useBacktest'
import { StarRating } from './StarRating'

const CATEGORY_CONFIG: Record<string, { icon: typeof TrendingUp; color: string }> = {
  profitability: { icon: TrendingUp, color: 'text-emerald-600' },
  risk_resistance: { icon: Shield, color: 'text-blue-600' },
  risk_reward: { icon: Scale, color: 'text-purple-600' },
  win_rate_ev: { icon: Target, color: 'text-orange-600' },
  liquidity: { icon: Droplets, color: 'text-cyan-600' },
}

interface CategoryHeaderProps {
  categories: CategoryRating[]
  activeCategory: string
  onCategoryChange: (name: string) => void
}

export function CategoryHeader({
  categories,
  activeCategory,
  onCategoryChange,
}: CategoryHeaderProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
      {categories.map((cat) => {
        const config = CATEGORY_CONFIG[cat.name] || CATEGORY_CONFIG.profitability
        const Icon = config.icon
        const isActive = cat.name === activeCategory

        return (
          <button
            key={cat.name}
            onClick={() => onCategoryChange(cat.name)}
            className={`flex-shrink-0 flex flex-col items-center gap-1 px-3 py-2 rounded-lg border transition-all text-center min-w-[100px] ${
              isActive
                ? 'border-primary-500 bg-primary-50 shadow-sm'
                : 'border-slate-200 bg-white hover:border-slate-300'
            }`}
          >
            <Icon className={`w-4 h-4 ${config.color}`} />
            <span className="text-xs font-medium text-slate-700 whitespace-nowrap">
              {cat.label}
            </span>
            <StarRating stars={cat.stars} size="sm" />
          </button>
        )
      })}
    </div>
  )
}
