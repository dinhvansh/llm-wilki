'use client'
import { useDeferredValue, useState, use } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { MarkdownRenderer } from '@/components/data-display/markdown-renderer'
import { EvidenceCard } from '@/components/evidence/evidence-card'
import { EvidenceDrawer } from '@/components/evidence/evidence-drawer'
import { formatDate, formatDateTime, cn } from '@/lib/utils'
import { usePage, usePageAudit, usePageVersions, usePublishPage, useUnpublishPage, useUpdatePage } from '@/hooks/use-pages'
import { useSources } from '@/hooks/use-sources'
import { usePages } from '@/hooks/use-pages'
import { useAssignPageCollection, useCollections } from '@/hooks/use-collections'
import { useAssessDiagramPage, useDiagrams, useGenerateDiagramFromPage } from '@/hooks/use-diagrams'
import { useAuth } from '@/providers/auth-provider'
import type { Page, PageCitation } from '@/lib/types'
import {
  BookOpen, ChevronLeft, ChevronRight,
  Edit3, History, AlertTriangle, RefreshCw,
  Layers, Tag, FileText, Link2, CheckCircle,
  Eye, PanelLeft, PanelRight, Search, Star, CalendarDays, ListChecks,
} from 'lucide-react'

type SavedView = 'all' | 'drafts' | 'review' | 'stale' | 'source-linked'

const SAVED_VIEWS: Array<{ id: SavedView; label: string }> = [
  { id: 'all', label: 'All pages' },
  { id: 'drafts', label: 'Drafts' },
  { id: 'review', label: 'In review' },
  { id: 'stale', label: 'Stale' },
  { id: 'source-linked', label: 'Source-linked' },
]

const PAGE_TYPE_LABELS: Record<string, string> = {
  summary: 'Summaries',
  overview: 'Overviews',
  deep_dive: 'Deep dives',
  faq: 'FAQs',
}

function pageCitationAskPrompt(pageTitle: string, claimText: string, sourceTitle: string): string {
  return `Explain how the source "${sourceTitle}" supports the page "${pageTitle}" claim: ${claimText}`
}

export default function PageDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params)
  const [leftPanelOpen, setLeftPanelOpen] = useState(true)
  const [rightPanelOpen, setRightPanelOpen] = useState(true)
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [pageSearch, setPageSearch] = useState('')
  const [savedView, setSavedView] = useState<SavedView>('all')
  const [mobileEditorPane, setMobileEditorPane] = useState<'edit' | 'preview'>('edit')
  const [selectedCitation, setSelectedCitation] = useState<PageCitation | null>(null)
  const [selectedBacklink, setSelectedBacklink] = useState<NonNullable<Page['backlinks']>[number] | null>(null)

  const { data: page, isLoading, isError, error, refetch } = usePage(slug)
  const { data: versions } = usePageVersions(page?.id ?? '')
  const { data: auditLogs } = usePageAudit(page?.id ?? '')
  const { data: sourcesData } = useSources()
  const { data: pagesData } = usePages({ pageSize: 100, sort: 'title' })
  const { data: collections } = useCollections()
  const assignCollection = useAssignPageCollection()
  const publishMutation = usePublishPage()
  const unpublishMutation = useUnpublishPage()
  const updateMutation = useUpdatePage()
  const generateDiagramMutation = useGenerateDiagramFromPage()
  const { data: bpmAssessment } = useAssessDiagramPage(page?.id ?? '')
  const { data: relatedDiagrams } = useDiagrams({ pageId: page?.id, pageSize: 20 })
  const { hasRole } = useAuth()
  const router = useRouter()
  const deferredPageSearch = useDeferredValue(pageSearch)
  const canEdit = hasRole('editor', 'reviewer', 'admin')

  if (isLoading) return <LoadingSpinner label="Loading page..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load page'} onRetry={() => refetch()} />
  if (!page) return <ErrorState message="Page not found" />

  const relatedSources = sourcesData?.data.filter(s => page.relatedSourceIds.includes(s.id)) ?? []
  const allPages = pagesData?.data ?? []
  const citations = page.citations ?? []
  const searchedPages = allPages.filter(navPage => {
    const matchesSearch = [navPage.title, navPage.summary, navPage.slug, ...navPage.tags]
      .join(' ')
      .toLowerCase()
      .includes(deferredPageSearch.trim().toLowerCase())
    const matchesView =
      savedView === 'all' ||
      (savedView === 'drafts' && navPage.status === 'draft') ||
      (savedView === 'review' && navPage.status === 'in_review') ||
      (savedView === 'stale' && navPage.status === 'stale') ||
      (savedView === 'source-linked' && navPage.relatedSourceIds.length > 0)
    return matchesSearch && matchesView
  })
  const pagesByType = searchedPages.reduce<Record<string, typeof allPages>>((groups, navPage) => {
    const key = navPage.pageType || 'summary'
    groups[key] = groups[key] ?? []
    groups[key].push(navPage)
    return groups
  }, {})
  const totalCitations = citations.length
  const backlinkCount = page.backlinks?.length ?? 0
  const timelineEvents = page.timelineEvents ?? []
  const glossaryTerms = page.glossaryTerms ?? []

  const statusBanner = page.status === 'stale' ? (
    <div className="flex items-center gap-2 px-4 py-2 bg-red-50 border-b border-red-200 text-red-800 text-sm">
      <AlertTriangle className="w-4 h-4" />
      <span>This page may contain outdated information. A newer source version is available.</span>
      <button className="ml-auto text-xs underline hover:no-underline">Update now</button>
    </div>
  ) : page.status === 'in_review' ? (
    <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border-b border-blue-200 text-blue-800 text-sm">
      <RefreshCw className="w-4 h-4" />
      <span>This page is currently under review.</span>
    </div>
  ) : null

  return (
    <div className="flex flex-col h-full">
      <EvidenceDrawer
        open={Boolean(selectedCitation)}
        title={selectedCitation?.sourceTitle ?? 'Citation evidence'}
        subtitle={selectedCitation?.chunkSectionTitle}
        snippet={selectedCitation?.claimText}
        meta={[
          selectedCitation?.pageNumber ? `Page ${selectedCitation.pageNumber}` : null,
          selectedCitation?.chunkId ? `Chunk: ${selectedCitation.chunkId}` : null,
          typeof selectedCitation?.sourceSpanStart === 'number' && typeof selectedCitation?.sourceSpanEnd === 'number'
            ? `Source span: ${selectedCitation.sourceSpanStart}-${selectedCitation.sourceSpanEnd}`
            : null,
          selectedCitation ? `Confidence: ${Math.round(selectedCitation.confidence)}%` : null,
        ]}
        actions={selectedCitation ? [
          { label: 'Open source chunk', href: `/sources/${selectedCitation.sourceId}?chunkId=${selectedCitation.chunkId}`, variant: 'primary' },
          {
            label: 'Ask about citation',
            href: `/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&pageSummary=${encodeURIComponent(page.summary ?? '')}&prompt=${encodeURIComponent(pageCitationAskPrompt(page.title, selectedCitation.claimText, selectedCitation.sourceTitle))}`,
          },
        ] : []}
        onClose={() => setSelectedCitation(null)}
      />
      <EvidenceDrawer
        open={Boolean(selectedBacklink)}
        title={selectedBacklink?.title ?? 'Backlink'}
        subtitle={selectedBacklink?.relationType?.replaceAll('_', ' ')}
        snippet={selectedBacklink ? `This page links back to ${page.title} as ${selectedBacklink.relationType.replaceAll('_', ' ')}.` : null}
        actions={selectedBacklink ? [
          { label: 'Open backlink page', href: `/pages/${selectedBacklink.slug}`, variant: 'primary' },
          { label: 'Ask about relationship', href: `/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&prompt=${encodeURIComponent(`Explain the relationship between ${page.title} and ${selectedBacklink.title}.`)}` },
        ] : []}
        onClose={() => setSelectedBacklink(null)}
      />
      {/* Page Header */}
      <PageHeader
        title={page.title}
        description={page.summary}
        breadcrumbs={[{ label: 'Pages', href: '/pages' }, { label: page.title }]}
        actions={
          <div className="flex items-center gap-1.5">
            <StatusBadge status={page.status} type="page" />
            <StatusBadge status={page.pageType} type="pageType" />
            <Link
              href={`/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&pageSummary=${encodeURIComponent(page.summary ?? '')}`}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-input rounded-md hover:bg-accent transition-colors"
            >
              <BookOpen className="w-4 h-4" />
              Ask This Page
            </Link>
            {page.status === 'draft' && (
              <button
                onClick={() => publishMutation.mutate(page.id)}
                disabled={publishMutation.isPending || !canEdit}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                <CheckCircle className="w-4 h-4" />
                {publishMutation.isPending ? 'Publishing...' : 'Publish'}
              </button>
            )}
            {page.status === 'published' && (
              <button
                onClick={() => unpublishMutation.mutate(page.id)}
                disabled={unpublishMutation.isPending || !canEdit}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-amber-600 text-white rounded-md hover:bg-amber-700 disabled:opacity-50 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                {unpublishMutation.isPending ? 'Unpublishing...' : 'Unpublish'}
              </button>
            )}
            <button
              onClick={() => {
                if (!canEdit) return
                setIsEditing(!isEditing)
                if (!isEditing) setEditContent(page.contentMd)
              }}
              disabled={!canEdit}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-input rounded-md hover:bg-accent transition-colors"
            >
              <Edit3 className="w-4 h-4" />
              {isEditing ? 'Cancel' : 'Edit'}
            </button>
            <button
              onClick={() => {
                if (!canEdit) return
                generateDiagramMutation.mutate(
                  { pageId: page.id, payload: { title: `${page.title} BPM Flow`, objective: page.summary } },
                  { onSuccess: (diagram) => router.push(`/diagrams/${diagram.slug}`) },
                )
              }}
              disabled={generateDiagramMutation.isPending || !canEdit}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-input rounded-md hover:bg-accent transition-colors disabled:opacity-50"
            >
              <Layers className="w-4 h-4" />
              {generateDiagramMutation.isPending ? 'Generating BPM...' : bpmAssessment?.classification === 'not_recommended' ? 'Generate BPM Anyway' : 'Generate BPM Draft'}
            </button>
          </div>
        }
      />

      {/* Status banner */}
      {statusBanner}

      {/* Metadata bar */}
      <div className="px-4 py-2 border-b border-border bg-muted/30 flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
        <span>v{page.currentVersion}</span>
        <span>Updated {formatDateTime(page.lastComposedAt)}</span>
        {page.publishedAt && <span>Published {formatDate(page.publishedAt)}</span>}
        <span>{totalCitations} key facts</span>
        <span>{page.relatedSourceIds.length} sources</span>
        <span>{page.relatedPageIds.length} related pages</span>
        <span>{backlinkCount} backlinks</span>
        <span>
          Collection:{' '}
          <select
            value={page.collectionId ?? ''}
            onChange={event => assignCollection.mutate({ pageId: page.id, collectionId: event.target.value || null })}
            disabled={assignCollection.isPending || !canEdit}
            className="h-7 rounded-md border border-input bg-background px-2 text-xs text-foreground"
          >
            <option value="">Standalone</option>
            {collections?.map(collection => (
              <option key={collection.id} value={collection.id}>{collection.name}</option>
            ))}
          </select>
        </span>
        <span className="ml-auto">Owner: {page.owner}</span>
      </div>

      {/* Workspace layout */}
      <div className="flex flex-1 min-h-0 flex-col lg:flex-row lg:overflow-hidden">
        {/* LEFT: Page navigation */}
        <div className={cn(
          'border-r border-border bg-card flex-shrink-0 overflow-y-auto transition-all',
          leftPanelOpen ? 'max-h-80 w-full lg:max-h-none lg:w-72' : 'hidden lg:block lg:w-0'
        )}>
          <div className="p-3 border-b border-border">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                type="text"
                value={pageSearch}
                onChange={event => setPageSearch(event.target.value)}
                placeholder="Search collection..."
                className="w-full h-8 pl-8 pr-2 text-sm border border-input rounded-md bg-background"
              />
            </div>
            <div className="mt-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-2">
                <Star className="w-3.5 h-3.5" />
                Saved Views
              </div>
              <div className="flex flex-wrap gap-1.5">
                {SAVED_VIEWS.map(view => (
                  <button
                    key={view.id}
                    onClick={() => setSavedView(view.id)}
                    className={cn(
                      'px-2 py-1 text-xs rounded-full border transition-colors',
                      savedView === view.id
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border text-muted-foreground hover:text-foreground'
                    )}
                  >
                    {view.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="p-2">
            <div className="text-xs font-medium text-muted-foreground px-2 mb-2">Collection Tree</div>
            {Object.entries(pagesByType).map(([pageType, navPages]) => (
              <div key={pageType} className="mb-3">
                <div className="flex items-center justify-between px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <span>{PAGE_TYPE_LABELS[pageType] ?? pageType.replaceAll('_', ' ')}</span>
                  <span>{navPages.length}</span>
                </div>
                {navPages.map(navPage => (
                  <Link
                    key={navPage.id}
                    href={`/pages/${navPage.slug}`}
                    className={cn(
                      'flex items-center gap-2 px-2 py-1.5 rounded-md text-xs transition-colors',
                      navPage.slug === slug
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-muted-foreground hover:bg-accent',
                    )}
                  >
                    <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="truncate">{navPage.title}</span>
                    <StatusBadge status={navPage.status} type="page" />
                  </Link>
                ))}
              </div>
            ))}
            {searchedPages.length === 0 && (
              <p className="px-2 py-4 text-xs text-muted-foreground">No pages match this saved view.</p>
            )}
          </div>
        </div>

        {/* Toggle left panel */}
        <button
          onClick={() => setLeftPanelOpen(!leftPanelOpen)}
          className="flex-shrink-0 h-8 lg:h-auto lg:w-4 bg-muted border-r border-border flex items-center justify-center hover:bg-accent transition-colors"
          title="Toggle collection tree"
        >
          <PanelLeft className="w-3 h-3 lg:hidden" />
          <span className="hidden lg:inline">{leftPanelOpen ? <ChevronLeft className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}</span>
        </button>

        {/* CENTER: Main content */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className={cn('p-6', isEditing ? 'w-full max-w-none' : 'max-w-3xl mx-auto')}>
            {/* Tags */}
            {page.tags.length > 0 && (
              <div className="flex gap-1.5 flex-wrap mb-4">
                {page.tags.map(tag => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 text-xs bg-secondary text-secondary-foreground rounded-full flex items-center gap-1"
                  >
                    <Tag className="w-3 h-3" />
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Edit mode */}
            {isEditing ? (
              <div className="w-full space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold">Markdown Workspace</h3>
                    <p className="text-xs text-muted-foreground">Native editor strategy: plain Markdown textarea with live preview.</p>
                  </div>
                  <div className="flex lg:hidden border border-border rounded-md overflow-hidden">
                    {(['edit', 'preview'] as const).map(pane => (
                      <button
                        key={pane}
                        onClick={() => setMobileEditorPane(pane)}
                        className={cn('px-2.5 py-1 text-xs capitalize', mobileEditorPane === pane ? 'bg-primary text-primary-foreground' : 'bg-background')}
                      >
                        {pane}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <div className={cn('space-y-2', mobileEditorPane === 'preview' && 'hidden lg:block')}>
                    <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <Edit3 className="w-3.5 h-3.5" />
                      Edit
                    </div>
                    <textarea
                      value={editContent}
                      onChange={e => setEditContent(e.target.value)}
                      className="block w-full min-h-[70vh] p-4 text-sm font-mono border border-input rounded-md bg-background resize-y"
                    />
                  </div>
                  <div className={cn('space-y-2', mobileEditorPane === 'edit' && 'hidden lg:block')}>
                    <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      <Eye className="w-3.5 h-3.5" />
                      Preview
                    </div>
                    <div className="min-h-[70vh] p-4 border border-input rounded-md bg-card overflow-y-auto">
                      <MarkdownRenderer content={editContent || '_Nothing to preview yet._'} />
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => updateMutation.mutate({ pageId: page.id, contentMd: editContent }, { onSuccess: () => setIsEditing(false) })}
                    disabled={updateMutation.isPending || !canEdit}
                    className="px-3 py-1.5 text-sm border border-input rounded-md hover:bg-accent"
                  >
                    {updateMutation.isPending ? 'Saving...' : 'Save Draft'}
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Content */}
                <MarkdownRenderer content={page.contentMd} />

            {timelineEvents.length > 0 && (
                  <div className="mt-8 rounded-xl border border-border bg-card p-5">
                    <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                      <CalendarDays className="h-4 w-4 text-primary" />
                      Structured Timeline
                    </h3>
                    <div className="space-y-3">
                      {timelineEvents.slice(0, 12).map(event => (
                        <div key={event.id} className="grid grid-cols-[96px_1fr] gap-3 border-l-2 border-primary/30 pl-3">
                          <div className="text-xs font-semibold text-primary">{event.eventDate}</div>
                          <div>
                            <div className="text-sm font-medium">{event.title}</div>
                            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{event.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                </div>
              )}

                {(relatedDiagrams?.data?.length ?? 0) > 0 && (
                  <div className="mt-8 rounded-xl border border-border bg-card p-5">
                    <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                      <Layers className="h-4 w-4 text-primary" />
                      Linked Process Diagrams
                    </h3>
                    <div className="space-y-2">
                      {relatedDiagrams?.data.map(diagram => (
                        <Link key={diagram.id} href={`/diagrams/${diagram.slug}`} className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm hover:bg-accent">
                          <span>{diagram.title}</span>
                          <StatusBadge status={diagram.status} type="page" />
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {bpmAssessment && (
                  <div className="mt-8 rounded-xl border border-border bg-card p-5">
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                      <Layers className="h-4 w-4 text-primary" />
                      BPM Suitability
                    </h3>
                    <div className="mb-2 flex items-center gap-2 text-xs">
                      <StatusBadge status={bpmAssessment.classification} type="page" />
                      <span className="text-muted-foreground">Score {Math.round(bpmAssessment.score * 100)}%</span>
                    </div>
                    <p className="mb-3 text-xs text-muted-foreground">
                      Recommended action: {bpmAssessment.recommendedAction.replaceAll('_', ' ')}
                    </p>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {bpmAssessment.reasons.map((reason, index) => <li key={index}>• {reason}</li>)}
                    </ul>
                  </div>
                )}

                {glossaryTerms.length > 0 && (
                  <div className="mt-8 rounded-xl border border-border bg-card p-5">
                    <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                      <ListChecks className="h-4 w-4 text-primary" />
                      Structured Glossary
                    </h3>
                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                      {glossaryTerms.slice(0, 12).map(term => (
                        <div key={term.id} className="rounded-lg border border-border bg-background p-3">
                          <div className="text-sm font-semibold">{term.term}</div>
                          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{term.definition}</p>
                          {term.aliases.length > 0 && (
                            <div className="mt-2 text-[11px] text-muted-foreground">Aliases: {term.aliases.join(', ')}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Key Facts */}
                {page.keyFacts.length > 0 && (
                  <div className="mt-8 pt-6 border-t border-border">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      Key Facts
                    </h3>
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <ul className="space-y-2">
                        {page.keyFacts.map((fact, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm">
                            <span className="w-1.5 h-1.5 rounded-full bg-green-500 mt-1.5 flex-shrink-0" />
                            <span>{fact}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Related Pages footer */}
            {page.relatedPageIds.length > 0 && (
              <div className="mt-8 pt-6 border-t border-border">
                <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <Link2 className="w-4 h-4" />
                  Related Pages
                </h3>
                <div className="flex gap-2 flex-wrap">
                  {page.relatedPageIds.map(id => {
                    const relatedPage = allPages.find(candidate => candidate.id === id)
                    const title = relatedPage?.title ?? id
                    return (
                      <Link
                        key={id}
                        href={`/pages/${relatedPage?.slug ?? slug}`}
                        className="px-2.5 py-1 text-xs border border-border rounded-md hover:border-primary/50 transition-colors"
                      >
                        {title}
                      </Link>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Toggle right panel */}
        <button
          onClick={() => setRightPanelOpen(!rightPanelOpen)}
          className="flex-shrink-0 h-8 lg:h-auto lg:w-4 bg-muted border-l border-border flex items-center justify-center hover:bg-accent transition-colors"
          title="Toggle context panel"
        >
          <PanelRight className="w-3 h-3 lg:hidden" />
          <span className="hidden lg:inline">{rightPanelOpen ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}</span>
        </button>

        {/* RIGHT: Context panel */}
        <div className={cn(
          'border-l border-border bg-card flex-shrink-0 overflow-y-auto transition-all',
          rightPanelOpen ? 'max-h-96 w-full lg:max-h-none lg:w-80' : 'hidden lg:block lg:w-0'
        )}>
          <div className="p-4">
            {/* Backlinks */}
            <div className="mb-6">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Link2 className="w-3.5 h-3.5" />
                Backlinks ({backlinkCount})
              </h4>
              <div className="space-y-2">
                {page.backlinks?.map(backlink => (
                  <button
                    key={`${backlink.id}-${backlink.relationType}`}
                    type="button"
                    onClick={() => setSelectedBacklink(backlink)}
                    className="block w-full p-2 rounded-md border border-border text-left hover:border-primary/50 transition-colors"
                  >
                    <div className="text-xs font-medium line-clamp-1">{backlink.title}</div>
                    <div className="mt-1 text-[11px] text-muted-foreground capitalize">{backlink.relationType.replaceAll('_', ' ')}</div>
                  </button>
                ))}
                {backlinkCount === 0 && (
                  <p className="text-xs text-muted-foreground">No pages link back here yet.</p>
                )}
              </div>
            </div>

            {/* Citations */}
            <div className="mb-6">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5" />
                Citations ({totalCitations})
              </h4>
              <div className="space-y-2">
                {citations.map(citation => {
                  const askHref = `/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&pageSummary=${encodeURIComponent(page.summary ?? '')}&prompt=${encodeURIComponent(pageCitationAskPrompt(page.title, citation.claimText, citation.sourceTitle))}`
                  return (
                  <EvidenceCard
                    key={citation.id}
                    index={citation.index}
                    title={citation.sourceTitle}
                    subtitle={citation.chunkSectionTitle}
                    snippet={citation.claimText}
                    type="page citation"
                    confidence={citation.confidence}
                    meta={[
                      citation.pageNumber ? `Page ${citation.pageNumber}` : null,
                      typeof citation.sourceSpanStart === 'number' && typeof citation.sourceSpanEnd === 'number' ? `Span ${citation.sourceSpanStart}-${citation.sourceSpanEnd}` : null,
                    ]}
                    actions={[
                      { label: 'Inspect', onClick: () => setSelectedCitation(citation), variant: 'primary' },
                      { label: 'Open source', href: `/sources/${citation.sourceId}?chunkId=${citation.chunkId}` },
                      { label: 'Ask', href: askHref },
                    ]}
                  />
                  )
                  /*
                  <div key={citation.id} className="space-y-1">
                  <Link
                    href={`/sources/${citation.sourceId}?chunkId=${citation.chunkId}`}
                    className="block p-2.5 bg-accent/50 rounded-md border border-border/50 hover:border-primary/50 transition-colors"
                  >
                    <p className="text-xs leading-relaxed">{citation.claimText}</p>
                    <div className="flex items-center gap-1 mt-1.5">
                      <span className="w-4 h-4 rounded bg-primary/10 text-primary flex items-center justify-center text-xs font-bold">
                        {citation.index}
                      </span>
                      <span className="text-xs text-muted-foreground truncate">
                        {citation.sourceTitle}
                        {citation.pageNumber ? ` · p.${citation.pageNumber}` : ''}
                      </span>
                      <span className="ml-auto text-[11px] text-muted-foreground">{Math.round(citation.confidence)}%</span>
                    </div>
                    <div className="mt-1 text-[11px] text-muted-foreground">
                      {citation.chunkSectionTitle}
                      {typeof citation.sourceSpanStart === 'number' && typeof citation.sourceSpanEnd === 'number' ? ` · span ${citation.sourceSpanStart}-${citation.sourceSpanEnd}` : ''}
                    </div>
                  </Link>
                  <div className="mt-1.5 flex flex-wrap gap-2 px-2">
                    <Link
                      href={`/sources/${citation.sourceId}?chunkId=${citation.chunkId}`}
                      className="rounded-full border border-border px-2.5 py-1 text-[11px] hover:border-primary/50 hover:bg-background"
                    >
                      Inspect source chunk
                    </Link>
                    <Link
                      href={askHref}
                      className="rounded-full border border-border px-2.5 py-1 text-[11px] hover:border-primary/50 hover:bg-background"
                    >
                      Ask about this citation
                    </Link>
                  </div>
                  </div>
                  )
                  */
                })}
                {totalCitations === 0 && (
                  <p className="text-xs text-muted-foreground">No citations mapped to claims yet.</p>
                )}
              </div>
            </div>

            {/* Related Sources */}
            <div className="mb-6">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" />
                Related Sources
              </h4>
              <div className="space-y-2">
                {relatedSources.map(source => (
                  <Link
                    key={source.id}
                    href={`/sources/${source.id}`}
                    className="block p-2 rounded-md border border-border hover:border-primary/50 transition-colors"
                  >
                    <div className="text-xs font-medium line-clamp-1">{source.title}</div>
                    <div className="flex items-center gap-1 mt-1">
                      <StatusBadge status={source.trustLevel} type="trust" />
                    </div>
                  </Link>
                ))}
                {relatedSources.length === 0 && (
                  <p className="text-xs text-muted-foreground">No sources linked.</p>
                )}
              </div>
            </div>

            <div className="mb-6 rounded-lg border border-border bg-background p-4">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Ask Next</h4>
              <div className="flex flex-wrap gap-2">
                {[
                  `What source evidence backs ${page.title} most strongly?`,
                  `What parts of ${page.title} may be stale or need review?`,
                  `Summarize ${page.title} for a quick handoff.`,
                ].map(prompt => (
                  <Link
                    key={prompt}
                    href={`/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&pageSummary=${encodeURIComponent(page.summary ?? '')}&prompt=${encodeURIComponent(prompt)}`}
                    className="rounded-full border border-border px-3 py-1.5 text-xs hover:border-primary/50 hover:bg-accent"
                  >
                    {prompt}
                  </Link>
                ))}
              </div>
            </div>

            {/* Version History */}
            <div>
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <History className="w-3.5 h-3.5" />
                Version History
              </h4>
              <div className="space-y-2">
                {versions?.slice(0, 5).map(v => (
                  <div key={v.id} className="p-2 rounded-md border border-border">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium">v{v.versionNo}</span>
                      <span className="text-xs text-muted-foreground">{formatDate(v.createdAt)}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{v.changeSummary}</p>
                    <div className="flex items-center gap-1 mt-1">
                      <StatusBadge status={v.reviewStatus} type="page" />
                    </div>
                  </div>
                ))}
                {(!versions || versions.length === 0) && (
                  <p className="text-xs text-muted-foreground">No version history.</p>
                )}
              </div>
            </div>

            <div className="mt-6">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <RefreshCw className="w-3.5 h-3.5" />
                Audit Trail
              </h4>
              <div className="space-y-2">
                {auditLogs?.slice(0, 8).map(log => (
                  <div key={log.id} className="p-2 rounded-md border border-border">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium capitalize">{log.action.replaceAll('_', ' ')}</span>
                      <span className="text-[11px] text-muted-foreground">{formatDate(log.createdAt)}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{log.summary}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">By {log.actor}</p>
                  </div>
                ))}
                {(!auditLogs || auditLogs.length === 0) && (
                  <p className="text-xs text-muted-foreground">No audit events recorded yet.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
