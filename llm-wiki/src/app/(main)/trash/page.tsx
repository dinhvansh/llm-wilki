'use client'

import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { StatusBadge } from '@/components/data-display/status-badge'
import { usePages, useRestorePage } from '@/hooks/use-pages'
import { useArchiveSourceAction, useRestoreSourceAction, useSources } from '@/hooks/use-sources'
import { formatRelativeTime } from '@/lib/utils'
import { RefreshCw, Trash2 } from 'lucide-react'

export default function TrashPage() {
  const pagesQuery = usePages({ status: 'archived', pageSize: 100, sort: 'updated' })
  const sourcesQuery = useSources({ status: 'archived' as any, pageSize: 100 })
  const restorePageMutation = useRestorePage()
  const restoreSourceMutation = useRestoreSourceAction()
  const archivedPages = pagesQuery.data?.data ?? []
  const archivedSources = sourcesQuery.data?.data ?? []
  const totalItems = archivedPages.length + archivedSources.length
  const isLoading = pagesQuery.isLoading || sourcesQuery.isLoading
  const hasError = pagesQuery.isError || sourcesQuery.isError
  const errorMessage =
    (pagesQuery.error as Error | undefined)?.message ??
    (sourcesQuery.error as Error | undefined)?.message ??
    'Failed to load trash'

  return (
    <div>
      <PageHeader
        title="Trash"
        description="Soft-deleted pages and sources live here until you restore them."
        actions={
          <div className="rounded-full border border-border px-3 py-1.5 text-sm text-muted-foreground">
            {totalItems} item{totalItems !== 1 ? 's' : ''} in trash
          </div>
        }
      />

      <div className="space-y-6 p-6">
        {isLoading ? (
          <LoadingSpinner label="Loading trash..." />
        ) : hasError ? (
          <ErrorState message={errorMessage} onRetry={() => { void pagesQuery.refetch(); void sourcesQuery.refetch() }} />
        ) : totalItems === 0 ? (
          <EmptyState
            icon="file-text"
            title="Trash is empty"
            description="When you move a page or source to trash, it will show up here until you restore it."
          />
        ) : (
          <>
            <section className="rounded-2xl border border-border bg-card">
              <div className="flex items-center justify-between border-b border-border px-5 py-4">
                <div>
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                    Archived pages
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">Restore notes and docs without losing their versions.</p>
                </div>
                <div className="text-sm text-muted-foreground">{archivedPages.length} page{archivedPages.length !== 1 ? 's' : ''}</div>
              </div>
              {archivedPages.length === 0 ? (
                <div className="px-5 py-8 text-sm text-muted-foreground">No archived pages.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/40">
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Title</th>
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Type</th>
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Updated</th>
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Owner</th>
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {archivedPages.map(page => (
                        <tr key={page.id} className="border-b border-border last:border-0">
                          <td className="px-5 py-4">
                            <div className="font-medium">{page.title}</div>
                            <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">{page.summary}</div>
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2">
                              <StatusBadge status={page.status} type="page" />
                              <StatusBadge status={page.pageType} type="pageType" />
                            </div>
                          </td>
                          <td className="px-5 py-4 text-muted-foreground">{formatRelativeTime(page.lastComposedAt)}</td>
                          <td className="px-5 py-4 text-muted-foreground">{page.owner}</td>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => restorePageMutation.mutate(page.id)}
                                disabled={restorePageMutation.isPending}
                                className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:bg-accent disabled:opacity-50"
                              >
                                <RefreshCw className="h-3.5 w-3.5" />
                                Restore
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-border bg-card">
              <div className="flex items-center justify-between border-b border-border px-5 py-4">
                <div>
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                    Archived sources
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">Restore uploaded documents and keep their linked context intact.</p>
                </div>
                <div className="text-sm text-muted-foreground">{archivedSources.length} source{archivedSources.length !== 1 ? 's' : ''}</div>
              </div>
              {archivedSources.length === 0 ? (
                <div className="px-5 py-8 text-sm text-muted-foreground">No archived sources.</div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/40">
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Title</th>
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Type</th>
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Parse status</th>
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Uploaded</th>
                        <th className="px-5 py-3 text-left font-medium text-muted-foreground">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {archivedSources.map(source => (
                        <tr key={source.id} className="border-b border-border last:border-0">
                          <td className="px-5 py-4">
                            <div className="font-medium">{source.title}</div>
                            {source.description ? <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">{source.description}</div> : null}
                          </td>
                          <td className="px-5 py-4">
                            <StatusBadge status={source.sourceType} type="source" />
                          </td>
                          <td className="px-5 py-4">
                            <StatusBadge status={source.parseStatus} type="source" />
                          </td>
                          <td className="px-5 py-4 text-muted-foreground">{formatRelativeTime(source.uploadedAt)}</td>
                          <td className="px-5 py-4">
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => restoreSourceMutation.mutate(source.id)}
                                disabled={restoreSourceMutation.isPending}
                                className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:bg-accent disabled:opacity-50"
                              >
                                <RefreshCw className="h-3.5 w-3.5" />
                                Restore
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  )
}
