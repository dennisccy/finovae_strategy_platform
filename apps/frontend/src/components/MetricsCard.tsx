interface MetricsCardProps {
  label: string
  value: string
  variant: 'positive' | 'negative' | 'neutral'
}

export function MetricsCard({ label, value, variant }: MetricsCardProps) {
  const valueColors = {
    positive: 'text-emerald-600',
    negative: 'text-red-600',
    neutral: 'text-slate-800',
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3 lg:p-4 metric-card">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-0.5 lg:mb-1 truncate">
        {label}
      </p>
      <p className={`text-lg lg:text-2xl font-bold ${valueColors[variant]} truncate`}>{value}</p>
    </div>
  )
}
