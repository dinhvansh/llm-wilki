import { Inbox, Search, AlertCircle, Database, FileText, MessageSquare } from 'lucide-react'
import { cn } from '@/lib/utils'

type IconName = 'database' | 'file-text' | 'alert' | 'search' | 'inbox' | 'message-square'

interface EmptyStateProps {
  icon?: IconName
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

const DEFAULT_ICONS: Record<IconName, React.ElementType> = {
  search: Search,
  inbox: Inbox,
  alert: AlertCircle,
  database: Database,
  'file-text': FileText,
  'message-square': MessageSquare,
}

export function EmptyState({ icon = 'inbox', title, description, action, className }: EmptyStateProps) {
  const Icon = DEFAULT_ICONS[icon as IconName] ?? Inbox
  return (
    <div className={cn('flex flex-col items-center justify-center py-16 px-6 text-center', className)}>
      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-muted-foreground" />
      </div>
      <h3 className="text-base font-medium mb-1">{title}</h3>
      {description && <p className="text-sm text-muted-foreground max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
