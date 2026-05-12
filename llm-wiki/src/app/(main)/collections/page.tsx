'use client'
import Link from 'next/link'
import { Boxes, Database, FileText, Plus } from 'lucide-react'

import { EmptyState } from '@/components/data-display/empty-state'
import { ErrorState } from '@/components/data-display/error-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { PageHeader } from '@/components/layout/page-header'
import { useCollections, useCreateCollection } from '@/hooks/use-collections'
import { formatRelativeTime } from '@/lib/utils'

const COLOR_CLASS: Record<string, string> = {
  emerald: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  blue: 'bg-blue-100 text-blue-800 border-blue-200',
  amber: 'bg-amber-100 text-amber-800 border-amber-200',
  slate: 'bg-slate-100 text-slate-800 border-slate-200',
}

export default function CollectionsPage() {
  const { data: collections, isLoading, isError, error, refetch } = useCollections()
  const createMutation = useCreateCollection()

  return (
    <div>
      <PageHeader
        title="Collections"
        description="Organize sources and pages into durable knowledge workspaces."
        actions={
          <button
            onClick={() => {
              const name = window.prompt('Collection name')
              if (name?.trim()) createMutation.mutate({ name: name.trim(), description: 'New knowledge collection', color: 'slate' })
            }}
            disabled={createMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            {createMutation.isPending ? 'Creating...' : 'New Collection'}
          </button>
        }
      />

      <div className="p-6">
        {isLoading ? <LoadingSpinner label="Loading collections..." /> :
         isError ? <ErrorState message={(error as Error)?.message ?? 'Failed to load collections'} onRetry={() => refetch()} /> :
         !collections || collections.length === 0 ? (
           <EmptyState icon="database" title="No collections yet" description="Create a collection to group related sources and pages." />
         ) : (
           <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
             {collections.map(collection => (
               <div key={collection.id} className="bg-card border border-border rounded-xl p-4">
                 <div className="flex items-start justify-between gap-3">
                   <div className="flex items-center gap-2">
                     <span className={`flex h-9 w-9 items-center justify-center rounded-lg border ${COLOR_CLASS[collection.color] ?? COLOR_CLASS.slate}`}>
                       <Boxes className="h-4 w-4" />
                     </span>
                     <div>
                       <h3 className="text-sm font-semibold">{collection.name}</h3>
                       <p className="text-xs text-muted-foreground">{collection.slug}</p>
                     </div>
                   </div>
                   <span className="text-xs text-muted-foreground">{formatRelativeTime(collection.updatedAt)}</span>
                 </div>
                 <p className="mt-3 text-sm text-muted-foreground line-clamp-3">{collection.description}</p>
                 <div className="mt-4 grid grid-cols-2 gap-2">
                   <Link href={`/sources?collectionId=${collection.id}`} className="rounded-lg border border-border p-3 hover:border-primary/50">
                     <div className="flex items-center gap-1.5 text-xs text-muted-foreground"><Database className="h-3.5 w-3.5" /> Sources</div>
                     <div className="mt-1 text-lg font-semibold">{collection.sourceCount}</div>
                   </Link>
                   <Link href={`/pages?collectionId=${collection.id}`} className="rounded-lg border border-border p-3 hover:border-primary/50">
                     <div className="flex items-center gap-1.5 text-xs text-muted-foreground"><FileText className="h-3.5 w-3.5" /> Pages</div>
                     <div className="mt-1 text-lg font-semibold">{collection.pageCount}</div>
                   </Link>
                 </div>
                 <Link
                   href={`/ask?collectionId=${encodeURIComponent(collection.id)}&collectionTitle=${encodeURIComponent(collection.name)}&collectionDescription=${encodeURIComponent(collection.description)}`}
                   className="mt-3 block text-xs text-primary hover:underline"
                 >
                   Ask this collection
                 </Link>
                 <Link href={`/graph?collectionId=${collection.id}`} className="mt-3 block text-xs text-primary hover:underline">
                   Open collection graph
                 </Link>
               </div>
             ))}
           </div>
         )}
      </div>
    </div>
  )
}
