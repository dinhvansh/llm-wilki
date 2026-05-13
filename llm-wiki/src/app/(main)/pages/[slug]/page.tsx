'use client'
import { useDeferredValue, useEffect, useRef, useState, use, type ClipboardEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/data-display/status-badge'
import { LoadingSpinner } from '@/components/data-display/loading-spinner'
import { ErrorState } from '@/components/data-display/error-state'
import { MarkdownRenderer } from '@/components/data-display/markdown-renderer'
import { formatDate, formatDateTime, cn } from '@/lib/utils'
import { usePage, usePublishPage, useUnpublishPage, useUpdatePage, usePages } from '@/hooks/use-pages'
import { useAssignPageCollection, useCollections } from '@/hooks/use-collections'
import { useAssessDiagramPage, useDiagrams, useGenerateDiagramFromPage } from '@/hooks/use-diagrams'
import { useAuth } from '@/providers/auth-provider'
import {
  BookOpen, ChevronLeft, ChevronRight,
  Edit3, AlertTriangle, RefreshCw,
  Layers, Tag, FileText, Link2, CheckCircle,
  Eye, PanelLeft, Search, Star, CalendarDays, ListChecks,
  Sparkles, PenSquare, ClipboardList, Wand2, Copy, Check, ImagePlus,
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

const WORKSPACE_INSERTS = [
  { label: 'Summary', content: '\n## Summary\n\n- \n' },
  { label: 'Key points', content: '\n## Key points\n\n- \n' },
  { label: 'Questions', content: '\n## Open questions\n\n- \n' },
  { label: 'Action items', content: '\n## Action items\n\n- [ ] \n' },
  { label: 'Source notes', content: '\n## Source notes\n\n- Source:\n- Why it matters:\n' },
]

export default function PageDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params)
  const [leftPanelOpen, setLeftPanelOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [pageSearch, setPageSearch] = useState('')
  const [savedView, setSavedView] = useState<SavedView>('all')
  const [mobileEditorPane, setMobileEditorPane] = useState<'edit' | 'preview'>('edit')
  const [copyState, setCopyState] = useState<'idle' | 'copied'>('idle')
  const [imagePasteState, setImagePasteState] = useState<'idle' | 'pasting' | 'ready' | 'failed'>('idle')
  const editorRef = useRef<HTMLTextAreaElement | null>(null)

  const { data: page, isLoading, isError, error, refetch } = usePage(slug)
  const { data: pagesData } = usePages({ pageSize: 100, sort: 'title' }, { enabled: leftPanelOpen || (page?.relatedPageIds?.length ?? 0) > 0 })
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

  useEffect(() => {
    if (!isEditing || !canEdit || !page?.id) return

    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        if (!updateMutation.isPending) {
          updateMutation.mutate({ pageId: page.id, contentMd: editContent }, { onSuccess: () => setIsEditing(false) })
        }
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [canEdit, editContent, isEditing, page?.id, updateMutation])

  useEffect(() => {
    if (!page?.id) return
    setLeftPanelOpen(page.status !== 'draft')
  }, [page?.id, page?.status])

  if (isLoading) return <LoadingSpinner label="Loading page..." />
  if (isError) return <ErrorState message={(error as Error)?.message ?? 'Failed to load page'} onRetry={() => refetch()} />
  if (!page) return <ErrorState message="Page not found" />

  const allPages = pagesData?.data ?? []
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
  const timelineEvents = page.timelineEvents ?? []
  const glossaryTerms = page.glossaryTerms ?? []
  const backlinkCount = page.backlinks?.length ?? 0
  const totalCitations = page.citations?.length ?? 0
  const collectionName = collections?.find(collection => collection.id === page.collectionId)?.name ?? 'Standalone'
  const authoringPrompts = [
    `Clarify the top 3 claims in ${page.title}.`,
    `What citations are still missing from ${page.title}?`,
    `Turn ${page.title} into a concise internal note.`,
  ]

  const copyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(isEditing ? editContent : page.contentMd)
      setCopyState('copied')
      window.setTimeout(() => setCopyState('idle'), 1800)
    } catch {
      setCopyState('idle')
    }
  }

  const insertIntoEditor = (content: string) => {
    if (!canEdit) return
    if (!isEditing) {
      setEditContent(page.contentMd)
      setIsEditing(true)
    }

    const textarea = editorRef.current
    if (!textarea) {
      setEditContent(prev => `${prev.trimEnd()}${content}`)
      return
    }

    const start = textarea.selectionStart ?? editContent.length
    const end = textarea.selectionEnd ?? start
    const nextContent = `${editContent.slice(0, start)}${content}${editContent.slice(end)}`
    setEditContent(nextContent)

    window.requestAnimationFrame(() => {
      const nextCursor = start + content.length
      textarea.focus()
      textarea.setSelectionRange(nextCursor, nextCursor)
    })
  }

  const handleEditorPaste = async (event: ClipboardEvent<HTMLTextAreaElement>) => {
    const imageItem = Array.from(event.clipboardData.items).find(item => item.type.startsWith('image/'))
    if (!imageItem) return

    const file = imageItem.getAsFile()
    if (!file) return

    event.preventDefault()
    setImagePasteState('pasting')

    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(String(reader.result || ''))
        reader.onerror = () => reject(reader.error)
        reader.readAsDataURL(file)
      })
      const safeName = file.name?.trim() || `clipboard-${Date.now()}.png`
      insertIntoEditor(`\n![${safeName}](${dataUrl})\n`)
      setImagePasteState('ready')
    } catch {
      setImagePasteState('failed')
    } finally {
      window.setTimeout(() => setImagePasteState('idle'), 2200)
    }
  }

  const statusBanner = page.status === 'stale' ? (
    <div className="flex items-center gap-2 border-b border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
      <AlertTriangle className="h-4 w-4" />
      <span>This page may contain outdated information. A newer source version is available.</span>
    </div>
  ) : page.status === 'in_review' ? (
    <div className="flex items-center gap-2 border-b border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800">
      <RefreshCw className="h-4 w-4" />
      <span>This page is currently under review.</span>
    </div>
  ) : null

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title={page.title}
        description={page.summary}
        breadcrumbs={[{ label: 'Pages', href: '/pages' }, { label: page.title }]}
        className="border-b border-border/70 bg-background/95 backdrop-blur"
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            <div className="mr-1 flex items-center gap-1.5">
              <StatusBadge status={page.status} type="page" />
              <StatusBadge status={page.pageType} type="pageType" />
            </div>
            <Link
              href={`/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&pageSummary=${encodeURIComponent(page.summary ?? '')}`}
              className="flex items-center gap-1.5 rounded-full border border-input px-3 py-1.5 text-sm transition-colors hover:bg-accent"
            >
              <BookOpen className="h-4 w-4" />
              Ask page
            </Link>
            <button
              type="button"
              onClick={copyMarkdown}
              className="flex items-center gap-1.5 rounded-full border border-input px-3 py-1.5 text-sm transition-colors hover:bg-accent"
            >
              {copyState === 'copied' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copyState === 'copied' ? 'Copied' : 'Copy markdown'}
            </button>
            {page.status === 'draft' && (
              <button
                onClick={() => publishMutation.mutate(page.id)}
                disabled={publishMutation.isPending || !canEdit}
                className="flex items-center gap-1.5 rounded-full bg-green-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-green-700 disabled:opacity-50"
              >
                <CheckCircle className="h-4 w-4" />
                {publishMutation.isPending ? 'Publishing...' : 'Publish'}
              </button>
            )}
            {page.status === 'published' && (
              <button
                onClick={() => unpublishMutation.mutate(page.id)}
                disabled={unpublishMutation.isPending || !canEdit}
                className="flex items-center gap-1.5 rounded-full bg-amber-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-amber-700 disabled:opacity-50"
              >
                <RefreshCw className="h-4 w-4" />
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
              className="flex items-center gap-1.5 rounded-full border border-input px-3 py-1.5 text-sm transition-colors hover:bg-accent"
            >
              <PenSquare className="h-4 w-4" />
              {isEditing ? 'Close editor' : 'Refine note'}
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
              className="flex items-center gap-1.5 rounded-full border border-input px-3 py-1.5 text-sm transition-colors hover:bg-accent disabled:opacity-50"
            >
              <Layers className="h-4 w-4" />
              {generateDiagramMutation.isPending ? 'Generating BPM...' : bpmAssessment?.classification === 'not_recommended' ? 'Generate BPM anyway' : 'Generate BPM draft'}
            </button>
          </div>
        }
      />

      {statusBanner}

      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
        <span className="rounded-full border border-border bg-background px-2.5 py-1">v{page.currentVersion}</span>
        <span className="rounded-full border border-border bg-background px-2.5 py-1">Updated {formatDateTime(page.lastComposedAt)}</span>
        {page.publishedAt && <span className="rounded-full border border-border bg-background px-2.5 py-1">Published {formatDate(page.publishedAt)}</span>}
        <span className="rounded-full border border-border bg-background px-2.5 py-1">{totalCitations} citations</span>
        <span className="rounded-full border border-border bg-background px-2.5 py-1">{page.relatedSourceIds.length} sources</span>
        <span className="rounded-full border border-border bg-background px-2.5 py-1">{page.relatedPageIds.length} related pages</span>
        <span className="rounded-full border border-border bg-background px-2.5 py-1">{backlinkCount} backlinks</span>
        <span className="flex items-center gap-2 rounded-full border border-border bg-background px-2.5 py-1">
          Collection
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
        <span className="ml-auto rounded-full border border-border bg-background px-2.5 py-1">Owner: {page.owner}</span>
      </div>

      <div className="flex flex-1 min-h-0 flex-col lg:flex-row lg:overflow-hidden">
        <div className={cn(
          'border-r border-border bg-card flex-shrink-0 overflow-y-auto transition-all',
          leftPanelOpen ? 'max-h-80 w-full lg:max-h-none lg:w-72' : 'hidden lg:block lg:w-0',
        )}>
          <div className="border-b border-border p-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={pageSearch}
                onChange={event => setPageSearch(event.target.value)}
                placeholder="Search collection..."
                className="h-8 w-full rounded-md border border-input bg-background pl-8 pr-2 text-sm"
              />
            </div>
            <div className="mt-3">
              <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <Star className="h-3.5 w-3.5" />
                Saved Views
              </div>
              <div className="flex flex-wrap gap-1.5">
                {SAVED_VIEWS.map(view => (
                  <button
                    key={view.id}
                    onClick={() => setSavedView(view.id)}
                    className={cn(
                      'rounded-full border px-2 py-1 text-xs transition-colors',
                      savedView === view.id
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {view.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="p-2">
            <div className="mb-2 px-2 text-xs font-medium text-muted-foreground">Collection Tree</div>
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
                      'flex items-center gap-2 rounded-md px-2 py-1.5 text-xs transition-colors',
                      navPage.slug === slug
                        ? 'bg-primary/10 font-medium text-primary'
                        : 'text-muted-foreground hover:bg-accent',
                    )}
                  >
                    <FileText className="h-3.5 w-3.5 flex-shrink-0" />
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

        <button
          onClick={() => setLeftPanelOpen(!leftPanelOpen)}
          className="flex h-8 flex-shrink-0 items-center justify-center border-r border-border bg-muted transition-colors hover:bg-accent lg:h-auto lg:w-4"
          title="Toggle collection tree"
        >
          <PanelLeft className="h-3 w-3 lg:hidden" />
          <span className="hidden lg:inline">{leftPanelOpen ? <ChevronLeft className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}</span>
        </button>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className={cn('mx-auto p-6', isEditing ? 'max-w-5xl' : 'max-w-3xl')}>
            <div className="mb-6">
              <div className="flex flex-wrap gap-1.5">
                {page.tags.map(tag => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 rounded-full border border-border bg-background px-2.5 py-1 text-xs text-muted-foreground"
                  >
                    <Tag className="h-3 w-3" />
                    {tag}
                  </span>
                ))}
                {page.tags.length === 0 && (
                  <span className="inline-flex items-center gap-1 rounded-full border border-dashed border-border px-2.5 py-1 text-xs text-muted-foreground">
                    <Tag className="h-3 w-3" />
                    add note tags as the page becomes clearer
                  </span>
                )}
              </div>
            </div>

            {isEditing ? (
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Authoring workspace</div>
                  <h2 className="text-3xl font-semibold tracking-tight">Write fast. Clean it up later.</h2>
                  <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
                    This draft lives in <span className="font-medium text-foreground">{collectionName}</span>. Keep the top idea close to the title, drop raw notes freely, then turn them into clearer sections.
                  </p>
                  <div className="flex flex-wrap gap-2 pt-2">
                    {authoringPrompts.map(prompt => (
                      <Link
                        key={prompt}
                        href={`/ask?pageId=${encodeURIComponent(page.id)}&pageTitle=${encodeURIComponent(page.title)}&pageSummary=${encodeURIComponent(page.summary ?? '')}&prompt=${encodeURIComponent(prompt)}`}
                        className="rounded-full border border-border bg-background px-3 py-1.5 text-xs hover:bg-accent"
                      >
                        {prompt}
                      </Link>
                    ))}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {WORKSPACE_INSERTS.map(block => (
                    <button
                      key={block.label}
                      type="button"
                      onClick={() => insertIntoEditor(block.content)}
                      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-xs hover:bg-accent"
                    >
                      <Wand2 className="h-3.5 w-3.5 text-primary" />
                      Insert {block.label}
                    </button>
                  ))}
                </div>

                <div className="rounded-2xl border border-dashed border-border bg-background px-4 py-3 text-xs text-muted-foreground">
                  Tip: paste screenshots directly from your clipboard, then press <span className="font-medium text-foreground">Ctrl/Cmd + S</span> to save the draft quickly.
                </div>

                <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                  <div className={cn('space-y-2', mobileEditorPane === 'preview' && 'hidden xl:block')}>
                    <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      <Edit3 className="h-3.5 w-3.5" />
                      Edit
                    </div>
                    <textarea
                      ref={editorRef}
                      value={editContent}
                      onChange={event => setEditContent(event.target.value)}
                      onPaste={handleEditorPaste}
                      className="min-h-[72vh] w-full rounded-3xl border border-input bg-background p-6 text-sm leading-7 resize-y"
                      placeholder="Type your note here..."
                    />
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <ImagePlus className="h-3.5 w-3.5 text-primary" />
                      {imagePasteState === 'pasting' && <span>Processing clipboard image...</span>}
                      {imagePasteState === 'ready' && <span>Image inserted into the draft.</span>}
                      {imagePasteState === 'failed' && <span>Could not read the clipboard image.</span>}
                      {imagePasteState === 'idle' && <span>Paste an image from outside with <span className="font-medium text-foreground">Ctrl/Cmd + V</span>.</span>}
                    </div>
                  </div>

                  <div className={cn('space-y-2', mobileEditorPane === 'edit' && 'hidden xl:block')}>
                    <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      <Eye className="h-3.5 w-3.5" />
                      Preview
                    </div>
                    <div className="min-h-[72vh] rounded-3xl border border-input bg-background p-6">
                      <MarkdownRenderer content={editContent || '_Nothing to preview yet._'} />
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => updateMutation.mutate({ pageId: page.id, contentMd: editContent }, { onSuccess: () => setIsEditing(false) })}
                    disabled={updateMutation.isPending || !canEdit}
                    className="rounded-full border border-input px-4 py-2 text-sm hover:bg-accent"
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
              <div className="space-y-10">
                <div className="space-y-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Note page</div>
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <h2 className="text-4xl font-semibold tracking-tight">{page.title}</h2>
                      {page.summary && <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">{page.summary}</p>}
                    </div>
                    {canEdit && (
                      <button
                        type="button"
                        onClick={() => {
                          setEditContent(page.contentMd)
                          setIsEditing(true)
                        }}
                        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1.5 text-xs hover:bg-accent"
                      >
                        <Edit3 className="h-3.5 w-3.5" />
                        Refine this draft
                      </button>
                    )}
                  </div>
                </div>

                <div className="rounded-[32px] border border-border bg-card px-8 py-10 shadow-sm">
                  <MarkdownRenderer content={page.contentMd} className="prose-headings:tracking-tight prose-p:text-[15px] prose-p:leading-7" />
                </div>

                {(relatedDiagrams?.data?.length ?? 0) > 0 && (
                  <div className="rounded-2xl border border-border bg-card p-5">
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
                  <div className="rounded-2xl border border-border bg-card p-5">
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
                      {bpmAssessment.reasons.map((reason, index) => <li key={index}>- {reason}</li>)}
                    </ul>
                  </div>
                )}

                {timelineEvents.length > 0 && (
                  <div className="rounded-2xl border border-border bg-card p-5">
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

                {glossaryTerms.length > 0 && (
                  <div className="rounded-2xl border border-border bg-card p-5">
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

                {page.keyFacts.length > 0 && (
                  <div className="rounded-2xl border border-green-200 bg-green-50 p-5">
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Key Facts
                    </h3>
                    <ul className="space-y-2">
                      {page.keyFacts.map((fact, index) => (
                        <li key={index} className="flex items-start gap-2 text-sm">
                          <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-green-500" />
                          <span>{fact}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {page.relatedPageIds.length > 0 && (
                  <div className="border-t border-border pt-6">
                    <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
                      <Link2 className="h-4 w-4" />
                      Related Pages
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {page.relatedPageIds.map(id => {
                        const relatedPage = allPages.find(candidate => candidate.id === id)
                        return (
                          <Link
                            key={id}
                            href={`/pages/${relatedPage?.slug ?? slug}`}
                            className="rounded-md border border-border px-2.5 py-1 text-xs transition-colors hover:border-primary/50"
                          >
                            {relatedPage?.title ?? id}
                          </Link>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
