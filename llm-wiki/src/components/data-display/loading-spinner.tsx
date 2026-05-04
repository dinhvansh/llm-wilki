import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  label?: string
  className?: string
}

export function LoadingSpinner({ label, className }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 gap-3', className)}>
      <div className="w-8 h-8 border-2 border-border border-t-primary rounded-full animate-spin" />
      {label && <p className="text-sm text-muted-foreground">{label}</p>}
    </div>
  )
}
