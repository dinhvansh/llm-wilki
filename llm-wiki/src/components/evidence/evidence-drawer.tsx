'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { EvidenceCardAction } from './evidence-card'

interface EvidenceDrawerProps {
  open: boolean
  title: string
  subtitle?: string | null
  snippet?: ReactNode
  meta?: Array<string | null | undefined>
  actions?: EvidenceCardAction[]
  onClose: () => void
}

export function EvidenceDrawer({ open, title, subtitle, snippet, meta = [], actions = [], onClose }: EvidenceDrawerProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50">
      <button type="button" aria-label="Close evidence drawer" className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-xl flex-col border-l border-border bg-background shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Evidence</div>
            <h2 className="mt-1 text-lg font-semibold text-foreground">{title}</h2>
            {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
          </div>
          <button type="button" className="rounded-full border border-input p-2 hover:bg-accent" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {snippet && (
            <div className="rounded-lg border border-border bg-accent/40 p-4 text-sm leading-relaxed">
              {snippet}
            </div>
          )}
          {meta.filter(Boolean).length > 0 && (
            <div className="mt-4 grid gap-2">
              {meta.filter(Boolean).map(item => (
                <div key={item} className="rounded-md border border-border px-3 py-2 text-xs text-muted-foreground">
                  {item}
                </div>
              ))}
            </div>
          )}
        </div>
        {actions.length > 0 && (
          <div className="flex flex-wrap gap-2 border-t border-border px-5 py-4">
            {actions.map(action => {
              const className = cn(
                'inline-flex items-center rounded-md border px-3 py-2 text-sm font-medium disabled:opacity-50',
                action.variant === 'primary'
                  ? 'border-primary bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'border-input bg-background hover:bg-accent',
              )
              if (action.href) {
                return (
                  <Link key={action.label} href={action.href} className={className} onClick={onClose}>
                    {action.label}
                  </Link>
                )
              }
              return (
                <button key={action.label} type="button" className={className} disabled={action.disabled} onClick={action.onClick}>
                  {action.label}
                </button>
              )
            })}
          </div>
        )}
      </aside>
    </div>
  )
}
