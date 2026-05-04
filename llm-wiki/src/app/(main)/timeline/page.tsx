'use client'

import { useState } from 'react'
import { Milestone, Search } from 'lucide-react'

import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { PageHeader } from '@/components/layout/page-header'
import { Input } from '@/components/ui/input'
import { useTimelineExplorer } from '@/hooks/use-pages'

export default function TimelineExplorerPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading, isError, error, refetch } = useTimelineExplorer({ search: search || undefined, pageSize: 100 })

  return (
    <div>
      <PageHeader title="Timeline Explorer" description="Review dated events extracted from uploaded sources and derived pages." />
      <div className="p-6 space-y-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search timeline..." className="pl-8 h-9" />
        </div>

        {isLoading ? <LoadingSpinner label="Loading timeline..." /> : null}
        {isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load timeline'} onRetry={() => refetch()} /> : null}
        {!isLoading && !isError ? (
          <div className="space-y-3">
            {(data?.data ?? []).map(event => (
              <article key={event.id} className="rounded-lg border border-border bg-card p-4">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold">{event.title}</h2>
                  <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">{event.eventDate}</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{event.description}</p>
                <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
                  <span>Precision: {event.precision}</span>
                  <span>{event.entityIds.length} linked entities</span>
                </div>
              </article>
            ))}
          </div>
        ) : null}

        {!isLoading && !isError && (data?.data ?? []).length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-card p-10 text-center text-sm text-muted-foreground">
            <Milestone className="mx-auto mb-3 h-8 w-8" />
            No timeline events extracted yet.
          </div>
        ) : null}
      </div>
    </div>
  )
}
