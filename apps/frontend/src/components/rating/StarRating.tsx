import { Star } from 'lucide-react'

interface StarRatingProps {
  stars: number
  size?: 'sm' | 'md' | 'lg'
}

export function StarRating({ stars, size = 'md' }: StarRatingProps) {
  const sizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  }

  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className={`${sizeClasses[size]} ${
            i <= stars
              ? 'text-amber-400 fill-amber-400'
              : 'text-slate-300'
          }`}
        />
      ))}
    </div>
  )
}
