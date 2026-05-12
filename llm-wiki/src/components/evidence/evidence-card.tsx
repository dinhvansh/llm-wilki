'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { BookOpen, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface EvidenceCardAction {
  label: string
  href?: string
  onClick?: () => void
  disabled?: boolean
  variant?: 'primary' | 'secondary'
}

interface EvidenceCardProps {
  index?: number
  title: string
  subtitle?: string | null
  snippet: ReactNode
  href?: string
  type?: string | null
  confidence?: number | null
  meta?: Array<string | null | undefined>
  actions?: EvidenceCardAction[]
  tone?: 'default' | 'artifact' | 'review'
  footer?: ReactNode
}

function formatType(value: string | null | undefined): string {
  return String(value || '').replace(/_/g, ' ')
}

export function EvidenceCard({
  index,
  title,
  subtitle,
  snippet,
  href,
  type,
  confidence,
  meta = [],
  actions = [],
  tone = 'default',
  footer,
}: EvidenceCardProps) {
  const body = (
    <div
      className={cn(
        'flex items-start gap-3 rounded-lg border p-3 transition-colors',
        tone === 'artifact'
          ? 'border-sky-200 bg-sky-50/70 hover:border-sky-300'
          : tone === 'review'
            ? 'border-amber-200 bg-amber-50/60 hover:border-amber-300'
            : 'border-border/60 bg-accent/40 hover:border-primary/50 hover:bg-accent',
      )}
    >
      <span className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
        {typeof index === 'number' ? index : <BookOpen className="h-3.5 w-3.5" />}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{title}</span>
          {type && <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">{formatType(type)}</span>}
          {typeof confidence === 'number' && (
            <span className="rounded-full bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
              {Math.round(confidence)}%
            </span>
          )}
        </div>
        {subtitle && <div className="mt-0.5 text-xs text-muted-foreground">{subtitle}</div>}
        <div className="mt-2 text-sm leading-relaxed text-foreground">{snippet}</div>
        {meta.filter(Boolean).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
            {meta.filter(Boolean).map(item => (
              <span key={item} className="rounded-full bg-background px-2 py-0.5">
                {item}
              </span>
            ))}
          </div>
        )}
        {footer}
        {actions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {actions.map(action => {
              const className = cn(
                'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-50',
                action.variant === 'primary'
                  ? 'border-primary bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'border-input bg-background hover:bg-accent',
              )
              if (action.href) {
                return (
                  <Link key={action.label} href={action.href} className={className}>
                    {action.label}
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                )
              }
              return (
                <button key={action.label} type="button" disabled={action.disabled} onClick={action.onClick} className={className}>
                  {action.label}
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )

  if (!href || actions.length > 0) {
    return body
  }

  return (
    <Link href={href} className="block">
      {body}
    </Link>
  )
}
