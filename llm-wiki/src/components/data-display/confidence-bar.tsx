import { cn } from '@/lib/utils'

interface ConfidenceBarProps {
  score: number
  showLabel?: boolean
  className?: string
}

export function ConfidenceBar({ score, showLabel = true, className }: ConfidenceBarProps) {
  const normalizedScore = score <= 1 ? score * 100 : score
  const displayScore = Number.isFinite(normalizedScore) ? Math.round(normalizedScore) : 0
  const color = displayScore >= 85 ? 'bg-green-500' : displayScore >= 70 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${displayScore}%` }} />
      </div>
      {showLabel && <span className={cn('text-xs font-medium', displayScore >= 85 ? 'text-green-600' : displayScore >= 70 ? 'text-yellow-600' : 'text-red-600')}>{displayScore}%</span>}
    </div>
  )
}
