'use client'

import { useState } from 'react'
import { BookMarked, Search } from 'lucide-react'

import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { PageHeader } from '@/components/layout/page-header'
import { Input } from '@/components/ui/input'
import { useGlossary } from '@/hooks/use-pages'

export default function GlossaryPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading, isError, error, refetch } = useGlossary({ search: search || undefined, pageSize: 100 })

  return (
    <div>
      <PageHeader title="Glossary" description="Browse structured term-definition pairs extracted from source material." />
      <div className="p-6 space-y-4">
        <div className="relative max-w-sm">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search glossary..." className="pl-8 h-9" />
        </div>

        {isLoading ? <LoadingSpinner label="Loading glossary..." /> : null}
        {isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load glossary'} onRetry={() => refetch()} /> : null}
        {!isLoading && !isError ? (
          <div className="grid gap-4 md:grid-cols-2">
            {(data?.data ?? []).map(term => (
              <article key={term.id} className="rounded-lg border border-border bg-card p-4">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <h2 className="font-semibold">{term.term}</h2>
                  <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                    {(term.confidenceScore * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{term.definition}</p>
                {term.aliases.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {term.aliases.map(alias => (
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
            <BookMarked className="mx-auto mb-3 h-8 w-8" />
            No glossary terms extracted yet.
          </div>
        ) : null}
      </div>
    </div>
  )
}
