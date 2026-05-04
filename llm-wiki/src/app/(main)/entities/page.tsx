'use client'

import { useState } from 'react'
import { Boxes, Search } from 'lucide-react'

import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { StatusBadge } from '@/components/data-display/status-badge'
import { PageHeader } from '@/components/layout/page-header'
import { Input } from '@/components/ui/input'
import { useEntityExplorer } from '@/hooks/use-pages'

export default function EntityExplorerPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading, isError, error, refetch } = useEntityExplorer({ search: search || undefined, pageSize: 100 })

  return (
    <div>
      <PageHeader title="Entity Explorer" description="Browse extracted entities and see how widely they connect across pages and sources." />
      <div className="p-6 space-y-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search entities..." className="pl-8 h-9" />
        </div>

        {isLoading ? <LoadingSpinner label="Loading entities..." /> : null}
        {isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load entities'} onRetry={() => refetch()} /> : null}
        {!isLoading && !isError ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(data?.data ?? []).map(entity => (
              <article key={entity.id} className="rounded-lg border border-border bg-card p-4">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <h2 className="font-semibold">{entity.name}</h2>
                  <StatusBadge status={entity.entityType} type="entity" />
                </div>
                <p className="mb-3 text-sm text-muted-foreground">{entity.description || 'No description available.'}</p>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span>{entity.sourceCount} sources</span>
                  <span>{entity.pageCount} pages</span>
                </div>
                {entity.aliases.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {entity.aliases.map(alias => (
                      <span key={alias} className="rounded bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">{alias}</span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}

        {!isLoading && !isError && (data?.data ?? []).length === 0 ? (
          <div className="rounded-lg border border-dashed border-border bg-card p-10 text-center text-sm text-muted-foreground">
            <Boxes className="mx-auto mb-3 h-8 w-8" />
            No extracted entities yet.
          </div>
        ) : null}
      </div>
    </div>
  )
}
