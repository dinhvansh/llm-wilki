'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { EmptyState } from '@/components/data-display/empty-state'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { formatRelativeTime, cn } from '@/lib/utils'
import { useComposePage, usePages, useUpdatePage } from '@/hooks/use-pages'
import { useCollections } from '@/hooks/use-collections'
import { PAGE_TYPE_CONFIG, PAGE_STATUS_CONFIG } from '@/lib/constants'
import type { PageStatus, PageType } from '@/lib/constants'
import { Input } from '@/components/ui/input'
import { Search, LayoutGrid, List, Plus, Sparkles, X, FileText, BookOpen, CheckSquare, Lightbulb } from 'lucide-react'

type ViewMode = 'grid' | 'table'
type SortKey = 'updated' | 'title' | 'status' | 'type'
type DraftTemplate = 'blank' | 'meeting' | 'doc' | 'decision'

const draftTemplates: Array<{
  id: DraftTemplate
  title: string
  description: string
  icon: typeof FileText
  sections: string[]
}> = [
  {
    id: 'blank',
    title: 'Blank note',
    description: 'A clean page for quick thinking.',
    icon: FileText,
    sections: ['Notes', 'Next steps'],
  },
  {
    id: 'doc',
    title: 'Document notes',
    description: 'Summarize a source or internal document.',
    icon: BookOpen,
    sections: ['Summary', 'Key points', 'Open questions', 'Sources to attach'],
  },
  {
    id: 'meeting',
    title: 'Meeting note',
    description: 'Capture decisions, action items, and context.',
    icon: CheckSquare,
    sections: ['Context', 'Discussion notes', 'Decisions', 'Action items'],
  },
  {
    id: 'decision',
    title: 'Decision log',
    description: 'Record options, tradeoffs, and final choice.',
    icon: Lightbulb,
    sections: ['Problem', 'Options considered', 'Decision', 'Rationale', 'Follow-up'],
  },
]

function buildDraftMarkdown(title: string, template: (typeof draftTemplates)[number], notes: string, collectionName?: string) {
  const cleanNotes = notes.trim()
  return [
    `# ${title}`,
    '',
    collectionName ? `> Collection: ${collectionName}` : '> Draft page',
    '',
    ...template.sections.flatMap(section => [
      `## ${section}`,
      '',
      section === 'Notes' && cleanNotes ? cleanNotes : '- ',
      '',
    ]),
    cleanNotes && template.id !== 'blank' ? '## Raw notes' : '',
    cleanNotes && template.id !== 'blank' ? '' : '',
    cleanNotes && template.id !== 'blank' ? cleanNotes : '',
  ].filter(line => line !== '').join('\n')
}

export default function PagesPage() {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<PageStatus | ''>('')
  const [typeFilter, setTypeFilter] = useState<PageType | ''>('')
  const [collectionFilter, setCollectionFilter] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [sortKey, setSortKey] = useState<SortKey>('updated')
  const [isComposerOpen, setIsComposerOpen] = useState(false)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftNotes, setDraftNotes] = useState('')
  const [draftTemplate, setDraftTemplate] = useState<DraftTemplate>('doc')
  const [draftCollectionId, setDraftCollectionId] = useState('')
  const [composerError, setComposerError] = useState<string | null>(null)
  const composeMutation = useComposePage()
  const updatePageMutation = useUpdatePage()
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
  const selectedTemplate = draftTemplates.find(template => template.id === draftTemplate) ?? draftTemplates[0]
  const selectedCollectionName = collections?.find(collection => collection.id === draftCollectionId)?.name
  const isCreatingDraft = composeMutation.isPending || updatePageMutation.isPending

  const createDraft = async () => {
    const title = draftTitle.trim()
    if (!title) {
      setComposerError('Page title is required.')
      return
    }
    setComposerError(null)
    try {
      const page = await composeMutation.mutateAsync(title)
      const contentMd = buildDraftMarkdown(title, selectedTemplate, draftNotes, selectedCollectionName)
      await updatePageMutation.mutateAsync({ pageId: page.id, contentMd })
      setIsComposerOpen(false)
      setDraftTitle('')
      setDraftNotes('')
      setDraftTemplate('doc')
      setDraftCollectionId('')
      router.push(`/pages/${page.slug}`)
    } catch (error) {
      setComposerError((error as Error)?.message ?? 'Failed to create page draft.')
    }
  }

  const openComposerWithTemplate = (templateId: DraftTemplate) => {
    setDraftTemplate(templateId)
    setIsComposerOpen(true)
  }

  return (
    <div>
      <PageHeader
        title="Pages"
        description="Browse and manage wiki pages"
        actions={
          <button
            onClick={() => setIsComposerOpen(true)}
            disabled={isCreatingDraft}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            {isCreatingDraft ? 'Creating...' : 'New Note / Page'}
          </button>
        }
      />

      {isComposerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur-sm">
          <div className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
            <div className="flex items-start justify-between border-b border-border p-5">
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
                  <Sparkles className="h-4 w-4" />
                  Notion-style draft composer
                </div>
                <h2 className="mt-2 text-xl font-semibold">Create a page for notes, docs, or decisions</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Pick a structure, add rough notes, then continue editing in the page editor.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsComposerOpen(false)}
                className="rounded-full p-2 text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="grid max-h-[calc(90vh-88px)] overflow-y-auto lg:grid-cols-[1fr_320px]">
              <div className="space-y-5 p-5">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Title</label>
                  <input
                    value={draftTitle}
                    onChange={event => setDraftTitle(event.target.value)}
                    placeholder="Untitled page"
                    className="mt-2 w-full border-0 bg-transparent px-0 text-3xl font-semibold outline-none placeholder:text-muted-foreground/50"
                    autoFocus
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Template</label>
                  <div className="mt-2 grid gap-2 md:grid-cols-2">
                    {draftTemplates.map(template => {
                      const Icon = template.icon
                      return (
                        <button
                          key={template.id}
                          type="button"
                          onClick={() => setDraftTemplate(template.id)}
                          className={cn(
                            'rounded-xl border p-3 text-left transition-colors',
                            draftTemplate === template.id ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent',
                          )}
                        >
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4 text-primary" />
                            <span className="text-sm font-medium">{template.title}</span>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">{template.description}</p>
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Rough notes</label>
                  <textarea
                    value={draftNotes}
                    onChange={event => setDraftNotes(event.target.value)}
                    placeholder="Paste notes, context, source reminders, or questions here..."
                    className="mt-2 min-h-40 w-full resize-y rounded-xl border border-input bg-background p-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Collection context</label>
                  <select
                    value={draftCollectionId}
                    onChange={event => setDraftCollectionId(event.target.value)}
                    className="mt-2 h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  >
                    <option value="">Standalone draft</option>
                    {collections?.map(collection => (
                      <option key={collection.id} value={collection.id}>{collection.name}</option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-muted-foreground">
                    This adds context to the draft body. You can assign the final page to a collection after opening it.
                  </p>
                </div>

                {composerError && (
                  <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                    {composerError}
                  </div>
                )}
              </div>

              <aside className="border-t border-border bg-muted/30 p-5 lg:border-l lg:border-t-0">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Preview outline</div>
                <div className="mt-3 rounded-xl border border-border bg-background p-4">
                  <div className="text-lg font-semibold">{draftTitle.trim() || 'Untitled page'}</div>
                  <div className="mt-1 text-xs text-muted-foreground">{selectedTemplate.title}</div>
                  <div className="mt-4 space-y-2">
                    {selectedTemplate.sections.map(section => (
                      <div key={section} className="rounded-lg border border-border/70 px-3 py-2 text-sm">
                        {section}
                      </div>
                    ))}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={createDraft}
                  disabled={isCreatingDraft}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  <Sparkles className="h-4 w-4" />
                  {isCreatingDraft ? 'Creating draft...' : 'Create and open'}
                </button>
              </aside>
            </div>
          </div>
        </div>
      )}

      <div className="p-6 space-y-4">
        <div className="rounded-2xl border border-border bg-card p-5">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-primary">Quick create</div>
              <h2 className="mt-1 text-xl font-semibold">Start from a friendly note template</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                This is the faster path for document notes, meeting notes, decision logs, and blank pages.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsComposerOpen(true)}
              className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm hover:bg-accent"
            >
              <Sparkles className="h-4 w-4 text-primary" />
              Open full composer
            </button>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {draftTemplates.map(template => {
              const Icon = template.icon
              return (
                <button
                  key={template.id}
                  type="button"
                  onClick={() => openComposerWithTemplate(template.id)}
                  className="rounded-xl border border-border bg-background p-4 text-left transition-colors hover:border-primary/40 hover:bg-accent"
                >
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-primary" />
                    <span className="text-sm font-medium">{template.title}</span>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{template.description}</p>
                  <div className="mt-3 text-xs text-foreground/80">
                    {template.sections.slice(0, 2).join(' • ')}
                  </div>
                </button>
              )
            })}
          </div>
        </div>

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
             action={<button onClick={() => setIsComposerOpen(true)} className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
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
