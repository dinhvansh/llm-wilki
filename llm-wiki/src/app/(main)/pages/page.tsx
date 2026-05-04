'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { EmptyState } from '@/components/data-display/empty-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { formatRelativeTime, cn } from '@/lib/utils'
import { useComposePage, usePages } from '@/hooks/use-pages'
import { useCollections } from '@/hooks/use-collections'
import { PAGE_TYPE_CONFIG, PAGE_STATUS_CONFIG } from '@/lib/constants'
import type { PageStatus, PageType } from '@/lib/constants'
import { Input } from '@/components/ui/input'
import { Search, LayoutGrid, List, Plus } from 'lucide-react'

type ViewMode = 'grid' | 'table'
type SortKey = 'updated' | 'title' | 'status' | 'type'

export default function PagesPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<PageStatus | ''>('')
  const [typeFilter, setTypeFilter] = useState<PageType | ''>('')
  const [collectionFilter, setCollectionFilter] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [sortKey, setSortKey] = useState<SortKey>('updated')
  const composeMutation = useComposePage()
  const { data: collections } = useCollections()

  useEffect(() => {
    setCollectionFilter(new URLSearchParams(window.location.search).get('collectionId') ?? '')
  }, [])

  const { data, isLoading, isError, error, refetch } = usePages({
    search: search || undefined,
    status: statusFilter || undefined,
    type: typeFilter || undefined,
    collectionId: collectionFilter || undefined,
    sort: sortKey,
  })

  const pages = data?.data ?? []
  const counts = data?.total ?? 0

  return (
    <div>
      <PageHeader
        title="Pages"
        description="Browse and manage wiki pages"
        actions={
          <button
            onClick={() => {
              const topic = window.prompt('Page topic')
              if (topic?.trim()) composeMutation.mutate(topic.trim())
            }}
            disabled={composeMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            {composeMutation.isPending ? 'Creating...' : 'New Page'}
          </button>
        }
      />

      <div className="p-6 space-y-4">
        {/* Toolbar */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              placeholder="Search pages..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 h-9"
            />
          </div>

          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value as PageStatus | '')}
            className="h-9 px-3 text-sm border border-input bg-background rounded-md"
          >
            <option value="">All Status</option>
            {(['draft', 'in_review', 'reviewed', 'published', 'stale', 'archived'] as PageStatus[]).map(s => (
              <option key={s} value={s}>{PAGE_STATUS_CONFIG[s].label}</option>
            ))}
          </select>

          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value as PageType | '')}
            className="h-9 px-3 text-sm border border-input bg-background rounded-md"
          >
            <option value="">All Types</option>
            {Object.entries(PAGE_TYPE_CONFIG).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>

          <select
            value={collectionFilter}
            onChange={e => setCollectionFilter(e.target.value)}
            className="h-9 px-3 text-sm border border-input bg-background rounded-md"
          >
            <option value="">All Collections</option>
            <option value="standalone">Standalone</option>
            {collections?.map(collection => (
              <option key={collection.id} value={collection.id}>{collection.name}</option>
            ))}
          </select>

          <div className="flex items-center gap-1 border border-input rounded-md">
            <button
              onClick={() => setViewMode('grid')}
              className={cn('p-1.5', viewMode === 'grid' ? 'bg-accent' : '')}
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={cn('p-1.5', viewMode === 'table' ? 'bg-accent' : '')}
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          <span className="text-xs text-muted-foreground ml-auto">{counts} page{counts !== 1 ? 's' : ''}</span>
        </div>

        {/* Content */}
        {isLoading ? <LoadingSpinner /> :
         isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load pages'} onRetry={() => refetch()} /> :
         pages.length === 0 ? (
           <EmptyState
             icon="file-text"
             title="No pages found"
             description="Pages will be auto-generated from your sources, or you can create them manually."
             action={<button className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
               <Plus className="w-4 h-4" /> Create First Page
             </button>}
           />
         ) :
         viewMode === 'grid' ? (
           <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
             {pages.map(page => (
               <Link
                 key={page.id}
                 href={`/pages/${page.slug}`}
                 className="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors group"
               >
                 <div className="flex items-start justify-between mb-2">
                   <div className="flex items-center gap-1.5">
                     <StatusBadge status={page.status} type="page" />
                     <StatusBadge status={page.pageType} type="pageType" />
                   </div>
                   <span className="text-xs text-muted-foreground">v{page.currentVersion}</span>
                 </div>
                 <h3 className="font-semibold text-sm group-hover:text-primary transition-colors mb-1">{page.title}</h3>
                 <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{page.summary}</p>
                 <div className="flex items-center gap-3 text-xs text-muted-foreground">
                   <span>{page.relatedSourceIds.length} source{page.relatedSourceIds.length !== 1 ? 's' : ''}</span>
                   <span>{formatRelativeTime(page.lastComposedAt)}</span>
                   <span>{collections?.find(collection => collection.id === page.collectionId)?.name ?? 'Standalone'}</span>
                   <span className="ml-auto">{page.owner}</span>
                 </div>
                 {page.tags.length > 0 && (
                   <div className="flex gap-1 flex-wrap mt-2">
                     {page.tags.slice(0, 3).map(tag => (
                       <span key={tag} className="px-1.5 py-0.5 text-xs bg-secondary text-secondary-foreground rounded">{tag}</span>
                     ))}
                     {page.tags.length > 3 && <span className="text-xs text-muted-foreground">+{page.tags.length - 3}</span>}
                   </div>
                 )}
               </Link>
             ))}
           </div>
         ) : (
           <div className="bg-card border border-border rounded-lg overflow-hidden">
             <table className="w-full text-sm">
               <thead>
                 <tr className="border-b border-border bg-muted/50">
                   <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Title</th>
                   <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Type</th>
                   <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Status</th>
                   <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Version</th>
                   <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Collection</th>
                   <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Updated</th>
                   <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Owner</th>
                 </tr>
               </thead>
               <tbody>
                 {pages.map(page => (
                   <tr key={page.id} className="border-b border-border last:border-0 hover:bg-accent/50">
                     <td className="px-4 py-3">
                       <Link href={`/pages/${page.slug}`} className="font-medium hover:text-primary transition-colors">{page.title}</Link>
                       <div className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{page.summary}</div>
                     </td>
                     <td className="px-4 py-3"><StatusBadge status={page.pageType} type="pageType" /></td>
                     <td className="px-4 py-3"><StatusBadge status={page.status} type="page" /></td>
                     <td className="px-4 py-3 text-muted-foreground">v{page.currentVersion}</td>
                     <td className="px-4 py-3 text-muted-foreground">{collections?.find(collection => collection.id === page.collectionId)?.name ?? 'Standalone'}</td>
                     <td className="px-4 py-3 text-muted-foreground">{formatRelativeTime(page.lastComposedAt)}</td>
                     <td className="px-4 py-3 text-muted-foreground">{page.owner}</td>
                   </tr>
                 ))}
               </tbody>
             </table>
           </div>
         )}
      </div>
    </div>
  )
}
